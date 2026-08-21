from utime import ticks_ms, ticks_us, ticks_diff, ticks_add, sleep_ms
from machine import Pin, ADC, SoftI2C

import network, ESPWebServer
from wifi import WIFI_SSID, WIFI_PASSWORD

from max30102 import (
    MAX30102,
    MAX30102_PULSE_AMP_MEDIUM,
    STORAGE_QUEUE_SIZE,
)
from filters import IIR_filter, Biquad, AGC
from detectors import Rate_calculator

from keras_lite import Model
import ulab as np

# Pin Definitions
SDA_PIN = 21
SCL_PIN = 22
ADC_PIN = 36
LO_POSITIVE_PIN = 32
LO_NEGATIVE_PIN = 33
LED_PIN = 5

# ---------------------------------------------------------------- PPG ------
# The chip samples at 400 Hz and averages SAMPLE_AVG of them, so all three of
# these move together: change SAMPLE_RATE alone.
#
# This was dropped to 50 while the HTTP server was eating 90% of the CPU and
# the loop could not afford the extra FIFO traffic. With the server polled by
# a non-blocking accept that cost is gone — loop measured at 1300/s with web
# at 5 ms/s — so 100 Hz is affordable again, and it halves both the trigger
# quantisation and the age of a popped sample. Worth ~20 ms of PWTT, which at
# 0.41 mmHg per ms is the difference between the model's flat region and its
# slope.
SAMPLE_RATE = 100
SAMPLE_AVG = 400 // SAMPLE_RATE
SAMPLE_PERIOD_MS = 1000 // SAMPLE_RATE

# sensor.check() reads the two FIFO pointers before it knows whether there is
# anything to fetch, and on SoftI2C that question alone costs four bus
# transactions, ~3 ms, every single iteration. Paying it at loop rate is what
# caps the loop, and those 3 ms are also 3 ms the ADC is not being read, so
# they land straight on the R timestamp. Throttle it to the sample rate: the
# chip has nothing new to give more often than that, so at this setting the
# throttle costs no extra sample age at all. Raise it above SAMPLE_PERIOD_MS
# and a popped sample starts arriving up to I2C_POLL_MS late instead.
I2C_POLL_MS = SAMPLE_PERIOD_MS

PPG_LOW_HZ = 0.5
# 010a uses 5.0 for a clean display trace. A 2nd order Butterworth low pass
# has a group delay of sqrt(2)/(2*pi*fc) at DC: 45 ms at 5 Hz, 28 ms at 8 Hz.
# That delay goes straight into the PWTT, so buy it back here.
PPG_HIGH_HZ = 8.0

AGC_TARGET = 100
# Trigger halfway up the normalised pulse: the steepest part of the upstroke,
# where timing jitter from noise is smallest. AGC keeps that point in the same
# place whatever the perfusion, which a fixed count threshold cannot.
PULSE_MARGIN = AGC_TARGET * 0.5

# Dead-signal gate only. AGC's own floor of 16 already caps the gain, so with
# no finger the output tops out around 12, well under PULSE_MARGIN and unable
# to trigger anything. Anything higher than this sits inside a real but weak
# finger signal and starts throwing away beats: at 20 it fired thousands of
# times a minute on a live finger and cost half the beats.
PPG_MIN_ENV = 5.0

# Full scale for dc is 32767: the driver right-shifts the 18-bit FIFO value
# by 3 at pulse_width 411. A dc pinned there means the LED has saturated the
# photodiode, the waveform is clipped flat and there is no AC left at all —
# measured at HIGH: dc 32766, env 0.4, one beat detected in ninety seconds.
#
# More light is NOT the cure for a small env; past saturation it is the cause.
# Aim for a dc in the middle of the range, roughly 10000-25000.
#   HIGH   0xFF  50.0 mA   -> saturated on this hardware
#   MEDIUM 0x7F  25.4 mA   <- measured dc 17200, env 60-88, R/P in lockstep
#   LOW    0x1F   6.4 mA   -> LED_POWER = 0x1F if MEDIUM is pinned near 32767
LED_POWER = MAX30102_PULSE_AMP_MEDIUM

# Everything between the pulse arriving at the finger and this code deciding
# it has: filter group delay plus where on the upstroke the trigger sits.
#
# Simulated against the same synthetic pulse, measured from the foot:
#
#   AC amplitude      LAB15 (one-pole DC, +20 counts)    here (AGC, 50%)
#     300 counts               33.6 ms                        83.6 ms
#     500 counts               25.7 ms                        83.6 ms
#     800 counts               18.6 ms                        83.6 ms
#
# So this pipeline reports a PWTT ~58 ms longer than the one bp_model.json
# was trained on, and 30 was leaving ~28 ms of that uncorrected — which is
# why every clean measurement landed at 244-268, past the 250 ms where the
# fitted curve goes flat, and BP sat at 109.4 whatever the pulse did.
#
# Note the second column does not move with amplitude and the first does, by
# 15 ms across that range. The AGC buys a trigger point that stays put; the
# training data has that scatter baked into it, which is part of why the fit
# is only trustworthy over 180-250 ms.
#
# This aligns the two pipelines. It does NOT calibrate the absolute pressure
# — that still needs a cuff reading, see the note on PWTT_TRAIN_MIN.
#
# The number belongs to the filter chain it was measured on. Simulated against
# the same pulse at 100 Hz, Channel's two biquads trigger 10 ms EARLIER than
# the one-pole DC subtraction used here (12.5 ms with the sample grid removed),
# and the offset does not move with amplitude. blood-pressure.py used to run
# Channel, so the two programs reported PWTTs 10 ms apart on the same beat.
# Both now run this chain.
PPG_DELAY_MS = 58

PPG_BUFFER_LEN = 100

# ---------------------------------------------------------------- ECG ------
# baseline_gen is IIR_filter(0.99) fed at 20 Hz, so its time constant is
# 100 samples = 5 s. One time constant is 63% of the way, not converged, and
# 5000 was exactly one. The AD8232 needs most of that time itself: measured
# from a soft reboot the first fed window was 312 counts and the steady state
# was ~1950, so IIR_filter seeds on the settling transient and climbs from
# there. Where the baseline actually is when the warm-up expires:
#
#   WARMUP_MS   predicted thr   measured thr
#      5000          1550           1467
#     10000          1931           2000
#     15000          2070           2119
#
# At 5000 the threshold came out ~600 counts low, and low here does not mean
# extra triggers — ecg_rearm is the baseline, so a baseline under the signal's
# own trough can never be crossed downward and r_is_high latches on. Measured:
# R stuck at 1 for three seconds while the PPG counted 4, then tracking again
# but three beats behind for the rest of the run. Three time constants.
#
# Let the filters see data during this window, just do not act on it.
WARMUP_MS = 15000

# The tick is the baseline and status cadence ONLY. R detection runs on every
# loop iteration: quantising the R timestamp to 50 ms would be +-20 mmHg.
ECG_TICK_MS = 50

# WARMUP_MS counts seconds, and that only equals a converged baseline while
# every window gets fed. ECG_CLIP skips the railed ones, so on a clipping run
# the warm-up can end on a filter that has seen far fewer than its 100
# samples: measured, warm-up ended at baseline 1403 against a steady state
# near 1700, and R detection started on a threshold 300 counts low. Count the
# feeds as well as the seconds. On a clean run this is the same 5 s.
#
# It is not a fix for a railing front end. Skipping windows can only slow the
# baseline down, and slowing it down alone does not explain a run that took
# 40 s to settle — that needs 62% of every window clipped, which would put
# ECG:4095 on every status line. What it does explain is a baseline that
# wanders, and a wandering baseline is an electrode problem. Watch clip:.
BASELINE_MIN_FEEDS = WARMUP_MS // ECG_TICK_MS

# 12-bit counts above the running baseline. 330 was tuned in 011-ecg against
# a stronger electrode signal; measured here the second's best peak was often
# BELOW threshold (2109/2301, 2070/2303, 2087/2301) and 40% of R waves were
# lost. Lower it until R/P track. Going too low lets T-waves in, but they
# land 250-300 ms after R and BEAT_REFRACTORY already blocks that window.
BEAT_MARGIN = 200

# 12-bit full scale. The AD8232 railing here is a hardware fault, not a big
# heartbeat, and it poisons the detector twice over: the clipped peak carries
# no timing information, and feeding 4095 into a baseline with a 5 s time
# constant lifts the threshold for seconds and costs every R wave behind it.
# Measured: 13 clipped seconds pushed thr from 2218-2331 up to 2328-2555.
ECG_CLIP = 4095

BEAT_REFRACTORY = 500

# A stalled loop cannot see an R wave until it resumes, so the R timestamp is
# late by however long the gap was and the PWTT comes out short or negative
# (measured -30, -37, -50). available() cannot detect this: it reports how
# many samples are waiting, which at STORAGE_QUEUE_SIZE = 32 no longer even
# saturates during a stall, and a full buffer was never the question anyway.
# The question is how late the R timestamp is. Time the loop itself instead
# and refuse any PWTT whose R was found after a gap longer than this.
R_MAX_GAP = 15

# --------------------------------------------------------------- PWTT ------
PWTT_MIN = 120  # finger PWTT is ~150-350 ms; outside this is a mispairing,
PWTT_MAX = 400  # usually an R wave that was missed
TARGET_N_BEATS = 5

# The chip's FIFO is 32 deep and the driver's CircularBuffer matches it, but
# both drop the OLDEST sample on overflow. Back-dating assumes every sample of
# the burst is present and one period apart, so once the loop has been away
# longer than the buffer holds, the timestamps in that burst are wrong by
# however much was lost. Serving one HTTP request inline costs 250-400 ms
# measured, so this is a real condition rather than a theoretical one: the
# beat is still a beat, its timing is not usable.
PPG_MAX_AGE_MS = STORAGE_QUEUE_SIZE * SAMPLE_PERIOD_MS

# Rejections skip rather than clear, which is right, but it means five beats
# can now be collected across an arbitrary stretch of time. Five beats is
# ~4 s of heart; if the run has taken more than this the earliest of them no
# longer describes the same moment, so start over.
PWTT_WINDOW_MS = 15000

# The dicrotic notch is a second, smaller upstroke inside the same cardiac
# cycle. At PPG_HIGH_HZ = 8.0 it survives the band-pass and after AGC it
# clears PULSE_MARGIN, so without this it counts as a beat.
#
# Measured: the notch triggers landed at 230, 333 and 392 ms, so 400 cleared
# the worst of them by 8 ms. 500 restores the margin and still allows 120 bpm.
PULSE_REFRACTORY = 500

# -------------------------------------------------------------- Model ------
MODEL_FILE = "bp_model.json"

# bp_model.py normalised the input with data /= 200 and the label with
# label /= 100, so predict() must be fed and read back the same way.
PWTT_SCALE = 200.0
BP_SCALE = 100

# pwtt_bp.txt spans 130-275 ms, but 55 of its 61 rows sit in 180-275 and the
# low end rests on a single contradictory point, (130, 114), where physiology
# wants the highest pressure of the set. Three dense layers of 20 fit that
# point, so the fitted curve turns non-monotonic below 180:
#   130 -> 122.3   180 -> 147.9   218 -> 125.7   275 -> 109.4
# Clamp to the region the data actually supports rather than trust the rest.
PWTT_TRAIN_MIN = 180
PWTT_TRAIN_MAX = 275

# Loading at import time with no guard crashes before the Wi-Fi message with
# nothing to say why, and bp_model.json is easy to forget to upload. Fail soft
# and report it: heart rate and PWTT still work without the model.
try:
    model = Model(MODEL_FILE)
except Exception as e:
    print("Model load error:", e)
    model = None

# ---------------------------------------------------------------- Web ------
# The status line is a diagnostic, not the product. Once a second, so it never
# competes with the sampling. Beat events still print as they happen.
STATUS_MS = 1000

# Set False to keep Wi-Fi associated but serve nothing, for comparison runs.
ENABLE_WEB = True

# The server is polled from the sampling loop, NOT from a _thread.
#
# Measured against this exact code with the radio associated either way:
#
#                     with _thread      polled from the loop
#   loop rate            100/s               1300/s
#   stalls per second    12 x up to 234 ms   0-2 x under 23 ms
#   R vs P counts        20% apart           exactly equal
#   PWTT spread          271-365             247-268
#
# The GIL handoff between two MicroPython threads costs an order of magnitude
# here, and it lands on the one loop whose timing IS the measurement.
#
# handleClient() is NOT used: its poller.poll(1) was measured at ~100 ms per
# call on this build, so ten calls a second cost web:500-1040ms out of every
# second. web_poll() below does a non-blocking accept() instead, which costs
# microseconds when nothing is pending. Serving a real request still runs
# inline and still stalls the loop, but R_MAX_GAP discards any PWTT caught by
# one, and that is two requests every three seconds.
WEB_POLL_MS = 100

# handle() reads the request line by line with no timeout of its own, so this
# is the cap on how long one bad client can hold the sampling loop. Seconds,
# and 1 was far too generous: a browser that pre-opens a connection and sends
# nothing costs the whole timeout, measured as gap:1108/1113/1118 ms with
# "Web handle error: [Errno 116] ETIMEDOUT" beside it. The real requests here
# are a ten byte GET over the LAN and complete in a fraction of this.
WEB_SOCKET_TIMEOUT = 0.2

# index.html never fetches /line. Registering it anyway keeps a 100 entry list
# maintained on every sample and builds a 100 element string on every request.
# Set True to serve the waveform for a chart.
SEND_PPG_WAVE = False

# Prints the interval of every raw PPG trigger, accepted or not. A notch shows
# up as a short interval followed by a long one: 320, 870, 340, 850...
DEBUG_INTVAL = False

# Adds loop rate, stall count, and the per-stage timers to the status line.
# Every one of these was added to find a specific fault and every one of them
# found it — the thread stalls, the ECG clipping, the 100 ms handleClient.
# They cost almost nothing to keep, so keep them, just not on screen.
DEBUG_TIMING = False


class Shared(object):
    """Everything the web thread is allowed to read.

    Plain attributes are enough: MicroPython's GIL makes a single load or
    store atomic, and the web thread only reads (send_ppg swaps the list
    reference, which is itself one store).
    """

    def __init__(self):
        self.heart_rate = 0
        self.bp = 0
        self.pwtt = 0
        self.ppg_buffer = []
        self.running = True


state = Shared()


def cal_bp(pwtt):
    if model is None:
        return 0

    # Say so when clamping. The fitted curve is already flat from 250 ms on
    # (250 -> 109.2, 275 -> 109.4), so every PWTT past that returns the same
    # 109.4 and a stuck reading looks like a frozen value rather than what it
    # is: a measurement outside the range the model was ever taught.
    if pwtt < PWTT_TRAIN_MIN:
        print("!! pwtt %d under training range, BP is a ceiling" % pwtt)
        pwtt = PWTT_TRAIN_MIN
    elif pwtt > PWTT_TRAIN_MAX:
        print("!! pwtt %d over training range, BP is a floor" % pwtt)
        pwtt = PWTT_TRAIN_MAX

    x = np.array([pwtt / PWTT_SCALE])
    bp = model.predict(x)

    return round(bp[0] * BP_SCALE, 1)


def reply(sock, body):
    """One write, with the two headers ESPWebServer.ok() leaves out.

    ok() writes the status line, then stats the body as a filename, then
    writes the body. Content-Length lets an HTTP/1.1 client see the end of
    the body without waiting for the close, Connection: close tells it not to
    hold the socket open for a follow-up, and one write cannot meet Nagle.

    That last one was the reason this function was written, and it was the
    wrong reason: a request cost 243 ms through ok() and 228 ms through this,
    measured the same way. Whatever the 200 ms is, it is under the HTTP
    layer. Keep the function anyway — the headers are correct and the os.stat
    that ok() performs on every response body is gone — but the cost of
    serving is not fixed here. See WEB_POLL_MS.
    """
    sock.write(
        "HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n"
        "Content-Length: %d\r\nConnection: close\r\n\r\n%s" % (len(body), body)
    )


def send_data(socket, args):
    """Both numbers down one connection.

    /hr and /bp were two requests every three seconds, and a connection is
    what costs 228 ms here, not the bytes in it. One request every five
    seconds is a sixth of the connections for the same two numbers, and BP
    only changes once every five beats anyway.
    """
    reply(socket, "%s,%s" % (state.bp, state.heart_rate))


def send_heart_rate(socket, args):
    reply(socket, str(state.heart_rate))


def send_blood_pressure(socket, args):
    reply(socket, str(state.bp))


def send_ppg(socket, args):
    # Hand over the whole list and start a fresh one, so the sampling loop
    # never waits on the socket.
    buffer = state.ppg_buffer
    state.ppg_buffer = []
    reply(socket, ",".join(str(v) for v in buffer))


def connect_wifi(ssid, password, timeout_ms=15000):
    sta = network.WLAN(network.STA_IF)
    sta.active(True)

    # Wi-Fi modem sleep is on by default: the radio wakes on the AP's DTIM
    # beacon, typically every 100 ms, and everything else waits for it. That
    # is a fixed cost on every socket round trip, and this server takes its
    # round trips inside the sampling loop.
    #
    # It is the residue left after WEB_SOCKET_TIMEOUT came down from 1 s:
    #
    #   timeout    measured gap    overhead
    #    1000 ms    1108-1118 ms    ~110 ms
    #     200 ms     313-382 ms     ~135 ms
    #
    # The overhead does not scale with the timeout, so it is not the timeout.
    # A trivial GET cost 265-350 ms on the same run, which is the same floor.
    #
    # This build refuses it outright: network.WLAN is a plain function so
    # there is no PM_NONE to read, and pm=0 comes back "unknown config param".
    # Left in for a firmware that does support it. It was NOT the cause of the
    # 243 ms requests — see reply() for what was — so a build without it is
    # not missing anything measurable here.
    #
    # Print which way it went either way: a silent failure looks exactly like
    # a successful fix, which is how the cost of serving hid for three runs.
    try:
        sta.config(pm=getattr(sta, "PM_NONE", 0))
        print("Wi-Fi power save off")
    except Exception as e:
        print("Wi-Fi power save left on:", e)

    if not sta.isconnected():
        sta.connect(ssid, password)
        start = ticks_ms()

        while not sta.isconnected():
            if ticks_diff(ticks_ms(), start) > timeout_ms:
                raise OSError("wifi connect timed out after %d ms" % timeout_ms)
            sleep_ms(100)

    return sta.ifconfig()[0]


def start_web_server(routes, port=80):
    ESPWebServer.begin(port)
    for path, handler in routes.items():
        ESPWebServer.onPath(path, handler)
    # begin() registers the listening socket with a poller that handleClient()
    # then waits on. Going non-blocking lets accept() answer "nothing pending"
    # immediately instead, which is the whole point of web_poll().
    ESPWebServer.server.setblocking(False)


def web_poll():
    """One non-blocking accept, in place of ESPWebServer.handleClient().

    Returns straight away when no client is waiting. When one is, the accepted
    socket is put back into blocking mode because handle() reads it line by
    line and would otherwise fail on a half-arrived request.
    """
    try:
        sock, _ = ESPWebServer.server.accept()
    except OSError:
        return 0

    try:
        # handle() does one readline for the request line and then loops on
        # readline until a blank one. A browser that opens the connection and
        # dawdles, or closes without a blank line, would otherwise hold the
        # sampling loop for as long as it likes.
        sock.settimeout(WEB_SOCKET_TIMEOUT)
        ESPWebServer.handle(sock)
    except Exception as e:
        print("Web handle error:", e)
    finally:
        sock.close()

    return 1


def setup():
    try:
        led = Pin(LED_PIN, Pin.OUT)
        led.value(1)

        i2c = SoftI2C(sda=Pin(SDA_PIN), scl=Pin(SCL_PIN))
        sensor = MAX30102(i2c=i2c)
        # led_mode defaults to 2 (IR + RED). Mode 1 is broken in this driver:
        # it files the single channel into sense.red while available() counts
        # sense.ir, so available() never returns anything.
        sensor.setup_sensor(sample_rate=400, sample_avg=SAMPLE_AVG, led_power=LED_POWER)

        adc_pin = Pin(ADC_PIN)
        adc = ADC(adc_pin)
        # no adc.width(): the default 12 bits give 4x the book's 10, which is
        # why BEAT_MARGIN is in the hundreds and not the book's 100
        adc.atten(ADC.ATTN_11DB)

        lo_p = Pin(LO_POSITIVE_PIN, Pin.IN)
        lo_n = Pin(LO_NEGATIVE_PIN, Pin.IN)

        return (led, sensor, adc, lo_p, lo_n)

    except Exception as e:
        print("Setup error:", e)
        return None


def main():
    sensors = setup()

    if sensors is None:
        print("Failed...")
        return

    led, sensor, adc, lo_p, lo_n = sensors

    # The driver buffer must be on the board, not just in the editor. At 4 a
    # 340 ms stall loses 13 of the 17 samples it spans, oldest first, and the
    # pulse upstroke goes with them — the trigger then fires on whatever
    # survived, which is later, and the PWTT comes out long.
    # print("STORAGE_QUEUE_SIZE on board:", STORAGE_QUEUE_SIZE)

    # Channel runs two biquads: a high pass to kill baseline drift and a low
    # pass to set the group delay. The high pass is the expensive half and the
    # cheap half is enough — subtracting a one-pole DC estimate IS a high pass,
    # 6 dB/octave against 12, and the AGC downstream does not care about the
    # difference. Group delay is set by the low pass, so PPG_DELAY_MS is
    # unchanged. Measured cost of the pair: 3.2 ms per sample.
    ppg_dc_filter = IIR_filter.from_cutoff(SAMPLE_RATE, PPG_LOW_HZ)
    ppg_lp = Biquad.low_pass(SAMPLE_RATE, PPG_HIGH_HZ)
    agc = AGC(SAMPLE_RATE, AGC_TARGET)
    baseline_gen = IIR_filter(0.99)

    # Two independent rate calculators on two different sensors. They should
    # agree within a beat or two: if they do not, one of the detectors is
    # miscounting, and no external instrument is needed to see it.
    rate = Rate_calculator(target_n_cycles=TARGET_N_BEATS)
    ecg_rate = Rate_calculator(target_n_cycles=TARGET_N_BEATS)

    ecg_tick = ticks_ms()
    status_tick = ticks_ms()
    i2c_tick = ticks_ms()
    web_tick = ticks_ms()
    ecg_peak = 0
    ecg_threshold = None
    ecg_rearm = None
    leads_off = False

    # ecg_peak is cleared every 50 ms, so a status line sampling it at an
    # arbitrary moment reads a half-built peak and, when the two ticks line
    # up, a clean 0. Carry the largest completed peak of the second instead.
    ecg_peak_max = 0

    # Wi-Fi and the HTTP thread did not exist in blood-pressure.py. R waves
    # are found on the instantaneous sample, not the 50 ms peak, so if this
    # loop is starved below roughly 200 Hz the ~30 ms R peak starts falling
    # between samples and is simply never seen. Count the iterations and find
    # out rather than guess.
    n_loops = 0
    n_leads_off = 0
    n_clip = 0

    # Non-clipped windows the baseline has actually seen. Cumulative, never
    # reset: it gates the warm-up, it is not a per-second statistic.
    n_baseline = 0

    # How late the R timestamp could be, and the worst gap of the second.
    # This replaces nmax, which only ever reported the driver's 4 deep buffer
    # being full and told us nothing about how long the loop was away.
    last_now = ticks_ms()
    r_gap = 0
    gap_max = 0

    # gap_max alone cannot tell one long stall from many short ones, and the
    # only thing this loop does exactly once a second is the status print —
    # so time that too. If ms_print accounts for gap_max, the diagnostic is
    # the disease and the cure is to print less.
    n_gap = 0
    ms_print = 0

    # The first FIFO samples step from nothing to a ~17000 count DC, which
    # rings the high pass: measured env 2219 against a steady state near 60.
    # The AGC release time constant is ~1 s, so it takes 15 s to decay on its
    # own, and until it does the gain is 100/2219 and no pulse gets anywhere
    # near PULSE_MARGIN. Re-seed the envelope when the warm-up ends instead.
    was_warm = False

    # nmax stuck at exactly 4 says one iteration takes 40 ms at 100 Hz, and
    # loop:17-54/s agrees. Memory is not the reason (mem sat at 43-70 kB), so
    # measure where the 40 ms goes instead of guessing again: ticks_ms is too
    # coarse per iteration, but microseconds accumulated over a second are not.
    us_i2c = 0
    us_ppg = 0

    # Removing the _thread took the loop from 100/s to 450/s but left 3-6
    # stalls a second of up to 320 ms, against 0-2 of under 23 ms with the
    # server off entirely. handleClient() was polled 10 times a second, which
    # matched the stall count too closely to be coincidence — but the print
    # looked equally guilty and was not, so measure instead of assuming.
    us_web = 0
    n_web = 0

    # True while the current burst came out of a FIFO that had time to overflow
    ppg_lost = False

    r_is_high = False
    last_r = ticks_ms()
    r_time = None

    # pulse_is_beating is the raw comparator state, pulse_accepted is the
    # subset that survived the refractory. Only the second one is a beat.
    pulse_is_beating = False
    pulse_accepted = False
    last_pulse = ticks_ms()

    pwtts = []
    pwtt_t0 = ticks_ms()
    ecg_heart_rate = 0

    # Two averages over five beats each cover different windows, so comparing
    # them cannot separate a real rate difference from a miscount. Raw counts
    # over the same run can: they must stay equal.
    n_beats_ecg = 0
    n_beats_ppg = 0
    ppg_dc = 0

    start_time = ticks_ms()

    try:
        ip = connect_wifi(WIFI_SSID, WIFI_PASSWORD)
        print("Connected, open http://%s/" % ip)

        if ENABLE_WEB:
            # /data is what index.html uses. /hr and /bp stay for curl.
            routes = {
                "/data": send_data,
                "/hr": send_heart_rate,
                "/bp": send_blood_pressure,
            }
            if SEND_PPG_WAVE:
                routes["/line"] = send_ppg
            start_web_server(routes)
        else:
            print("--- web server disabled")

        while state.running:
            now = ticks_ms()
            warm = (
                ticks_diff(now, start_time) > WARMUP_MS
                and n_baseline >= BASELINE_MIN_FEEDS
            )
            n_loops += 1

            loop_gap = ticks_diff(now, last_now)
            last_now = now
            if loop_gap > gap_max:
                gap_max = loop_gap
            if loop_gap > R_MAX_GAP:
                n_gap += 1

            if warm and not was_warm:
                was_warm = True
                agc.env = None  # drop the start-up transient, re-seed
                n_beats_ecg = 0
                n_beats_ppg = 0
                print("--- warmup done")

            # ---------------- ECG, every iteration (~1 kHz) ----------------
            if lo_p.value() or lo_n.value():
                leads_off = True

            raw_ecg = adc.read()
            if raw_ecg > ecg_peak:
                ecg_peak = raw_ecg
            if raw_ecg >= ECG_CLIP:
                n_clip += 1

            # The threshold only moves at 20 Hz, but the comparison has to run
            # at full speed: this timestamp IS the start of the PWTT.
            if ecg_threshold is not None and warm and not leads_off:
                if (
                    raw_ecg > ecg_threshold
                    and not r_is_high
                    and ticks_diff(now, last_r) > BEAT_REFRACTORY
                ):
                    r_is_high = True
                    last_r = now
                    r_time = now
                    r_gap = loop_gap  # how late this timestamp could be
                    n_beats_ecg += 1
                elif raw_ecg < ecg_rearm:
                    r_is_high = False

                ecg_rate.update(r_is_high)
                ecg_heart_rate = round(ecg_rate.get_rate(), 1)

            # ---------------- PPG, whenever the chip has samples ------------
            n = 0
            if ticks_diff(now, i2c_tick) >= I2C_POLL_MS:
                # measured against the last poll, not the last iteration: this
                # is how long the FIFO was left to fill, which is what decides
                # whether anything fell out of it
                ppg_lost = ticks_diff(now, i2c_tick) > PPG_MAX_AGE_MS
                i2c_tick = now
                t_mark = ticks_us()
                sensor.check()
                n = sensor.available()
                us_i2c += ticks_diff(ticks_us(), t_mark)

            if n:
                t_mark = ticks_us()

                for i in range(n):
                    ir = sensor.pop_ir_from_storage()

                    # check() just drained the FIFO, so the oldest of the n
                    # samples is (n-1) periods old. Stamping them all with now
                    # would put a backed-up sample up to n*SAMPLE_PERIOD_MS
                    # late, and that error goes straight into the PWTT.
                    t_ppg = ticks_add(now, -((n - 1 - i) * SAMPLE_PERIOD_MS))

                    ppg_dc = ppg_dc_filter.step(ir)
                    ac = ppg_lp.step(ir - ppg_dc)
                    # raw IR dips when blood arrives, invert so a pulse is a
                    # positive peak. AGC scales, it does not delay.
                    ppg = agc.step(-ac)

                    if SEND_PPG_WAVE:
                        # Re-read the attribute per sample: send_ppg can swap
                        # the list between iterations, and appending to the old
                        # one would drop those samples on the floor.
                        buffer = state.ppg_buffer
                        buffer.append(int(ppg + AGC_TARGET))
                        if len(buffer) > PPG_BUFFER_LEN:
                            del buffer[0]

                    if agc.env < PPG_MIN_ENV:
                        pulse_is_beating = False
                        pulse_accepted = False
                        led.value(1)
                        # Rate_calculator has to see the False as well. Skip it
                        # and is_cycling latches True, so the next beat is no
                        # longer a rising edge and the rate stays 0 for ever,
                        # while the beat detection itself looks perfectly fine.
                        rate.update(pulse_accepted)
                        continue

                    if warm and ppg > PULSE_MARGIN and not pulse_is_beating:
                        # Latching here, before the refractory test, is what
                        # blocks a wide peak from re-triggering: nothing gets
                        # back in until ppg has crossed under zero.
                        pulse_is_beating = True

                        if DEBUG_INTVAL:
                            print("intval:", ticks_diff(t_ppg, last_pulse))

                        if ticks_diff(t_ppg, last_pulse) > PULSE_REFRACTORY:
                            last_pulse = t_ppg
                            pulse_accepted = True
                            n_beats_ppg += 1
                            led.value(0)

                            if r_time is not None:
                                pwtt = ticks_diff(t_ppg, r_time) - PPG_DELAY_MS
                                r_time = None

                                # Skip, never clear. One bad beat is not a
                                # reason to throw away four good ones, and at
                                # roughly one rejection a second a clearing
                                # policy can never reach TARGET_N_BEATS.
                                if r_gap > R_MAX_GAP:
                                    print(
                                        "!! stall %d ms, pwtt dropped: %d"
                                        % (r_gap, pwtt)
                                    )
                                elif ppg_lost:
                                    # r_gap only guards the R end. This is the
                                    # pulse end: an R found cleanly before a
                                    # stall pairs with a pulse whose timestamp
                                    # was rebuilt from a burst that lost
                                    # samples, and that produced -44, -27, -13
                                    # and one memorable 1072.
                                    print("!! fifo overrun, pwtt dropped:", pwtt)
                                elif agc.env < agc.floor:
                                    # Below its floor the AGC has hit the gain
                                    # ceiling and stopped normalising, so the
                                    # 50 % trigger point moves with amplitude
                                    # and drags the PWTT with it. The beat is
                                    # still a beat, the timing is not usable,
                                    # and a bad PWTT here becomes a bad BP.
                                    print("!! weak signal, pwtt dropped:", pwtt)
                                elif PWTT_MIN < pwtt < PWTT_MAX:
                                    if (
                                        pwtts
                                        and ticks_diff(t_ppg, pwtt_t0) > PWTT_WINDOW_MS
                                    ):
                                        pwtts = []
                                    if not pwtts:
                                        pwtt_t0 = t_ppg
                                    pwtts.append(pwtt)

                                    if len(pwtts) == TARGET_N_BEATS:
                                        # median, not mean: one mispaired beat
                                        # drags a mean of five by tens of ms
                                        pwtts.sort()
                                        state.pwtt = pwtts[TARGET_N_BEATS // 2]
                                        state.bp = cal_bp(state.pwtt)
                                        print(
                                            "--> PWTT: %d  BP: %s"
                                            % (state.pwtt, state.bp)
                                        )
                                        pwtts = []
                                else:
                                    print("!! pwtt out of range:", pwtt)

                    elif ppg < 0:
                        pulse_is_beating = False
                        pulse_accepted = False
                        led.value(1)

                    # accepted beats only: a notch trigger never reaches here,
                    # and one sub-270 ms interval would reset Rate_calculator's
                    # run of five before it ever produces a number
                    rate.update(pulse_accepted)

                us_ppg += ticks_diff(ticks_us(), t_mark)
                state.heart_rate = round(rate.get_rate(), 1)

            # ---------------- 50 ms tick: ECG baseline ---------------------
            if ticks_diff(now, ecg_tick) > ECG_TICK_MS:
                if ecg_peak > ecg_peak_max:
                    ecg_peak_max = ecg_peak

                if leads_off:
                    n_leads_off += 1
                    r_is_high = False
                    r_time = None
                    # same trap that cost the PPG rate: clearing r_is_high
                    # without telling the calculator latches is_cycling True
                    # and the next R is no longer a rising edge
                    ecg_rate.update(False)
                elif ecg_peak < ECG_CLIP:
                    # fed the 50 ms peak exactly as in 011, so BEAT_MARGIN
                    # keeps the value tuned there — but never fed a clipped
                    # one, or the threshold chases the clipping upward
                    baseline = baseline_gen.step(ecg_peak)
                    ecg_threshold = baseline + BEAT_MARGIN
                    ecg_rearm = baseline
                    n_baseline += 1

                # an R with no pulse behind it is a missed beat: drop it
                # rather than let it pair with the beat after next
                if r_time is not None and ticks_diff(now, r_time) > PWTT_MAX:
                    r_time = None

                ecg_peak = 0
                leads_off = False
                ecg_tick = now

            # ---------------- 100 ms tick: serve HTTP ----------------------
            if ENABLE_WEB and ticks_diff(now, web_tick) > WEB_POLL_MS:
                web_tick = now
                t_mark = ticks_us()
                try:
                    # counts ACCEPTED connections, not calls. Many cheap calls
                    # and few expensive ones look identical in us_web alone.
                    n_web += web_poll()
                except Exception as e:
                    print("Web error:", e)
                us_web += ticks_diff(ticks_us(), t_mark)

            # ---------------- 1 s tick: status line ------------------------
            if ticks_diff(now, status_tick) > STATUS_MS:
                elapsed = ticks_diff(now, status_tick)
                t_mark = ticks_us()
                if DEBUG_TIMING:
                    print(
                        "%sECG:%d/%d  HR p/e:%.1f/%.1f  env:%.1f  dc:%d"
                        "  R/P:%d/%d  loop:%d/s  gap:%dx%dms  pr:%dms"
                        "  lo:%d  clip:%d  i2c:%dms ppg:%dms web:%dms/%d"
                        "  PWTT:%d  BP:%s"
                        % (
                            "" if warm else "[warmup] ",
                            ecg_peak_max,
                            ecg_threshold if ecg_threshold else 0,
                            state.heart_rate,
                            ecg_heart_rate,
                            # None between the warm-up re-seed and the next
                            # FIFO sample, and both ticks are counted from
                            # main(), so the 5 s one lands in that window
                            agc.env if agc.env else 0.0,
                            ppg_dc,
                            n_beats_ecg,
                            n_beats_ppg,
                            n_loops * 1000 // elapsed,
                            n_gap,
                            gap_max,
                            ms_print,
                            n_leads_off,
                            n_clip,
                            us_i2c // 1000,
                            us_ppg // 1000,
                            us_web // 1000,
                            n_web,
                            state.pwtt,
                            state.bp,
                        )
                    )
                else:
                    # ecg_peak_max against the threshold it had to clear, and
                    # the two beat counts, are the two things worth watching
                    # in normal use: R waves are being missed when the first
                    # pair converges or the second pair drifts apart.
                    #
                    # clip is here rather than behind DEBUG_TIMING because it
                    # is what explains the other two. A railing AD8232 starves
                    # the baseline through ECG_CLIP, the threshold comes out
                    # low, extra triggers get in, and R runs ahead of P — and
                    # none of that is visible from ECG:/R/P alone.
                    print(
                        # web:<ms>/<connections>. The count is the field that
                        # says whether a browser was attached at all, and
                        # without it a quiet run and a working fix look
                        # identical — which is exactly how the 250-400 ms
                        # cost of serving went unmeasured for three sessions.
                        "%sECG:%d/%d  HR p/e:%.1f/%.1f  env:%.1f  dc:%d"
                        "  R/P:%d/%d  gap:%dms  lo:%d  clip:%d  web:%dms/%d"
                        "  PWTT:%d  BP:%s"
                        % (
                            "" if warm else "[warmup] ",
                            ecg_peak_max,
                            ecg_threshold if ecg_threshold else 0,
                            state.heart_rate,
                            ecg_heart_rate,
                            # None between the warm-up re-seed and the next
                            # FIFO sample, and both ticks are counted from
                            # main(), so the 5 s one lands in that window
                            agc.env if agc.env else 0.0,
                            ppg_dc,
                            n_beats_ecg,
                            n_beats_ppg,
                            gap_max,
                            n_leads_off,
                            n_clip,
                            us_web // 1000,
                            n_web,
                            state.pwtt,
                            state.bp,
                        )
                    )
                ms_print = ticks_diff(ticks_us(), t_mark) // 1000

                ecg_peak_max = 0
                n_loops = 0
                gap_max = 0
                n_gap = 0
                n_leads_off = 0
                n_clip = 0
                us_i2c = 0
                us_ppg = 0
                us_web = 0
                n_web = 0
                status_tick = now

    except KeyboardInterrupt:
        pass

    finally:
        state.running = False
        led.value(1)
        if ENABLE_WEB:
            try:
                ESPWebServer.close()
                print("Web server closed")
            except Exception as e:
                print("Web close error:", e)
        try:
            sensor.shutdown()
            print("Sensor shut down")
        except Exception as e:
            print("Shutdown error:", e)
        print("Stopped...")


if __name__ == "__main__":
    main()

"""
Output:
MPY: soft reboot
Wi-Fi power save left on: unknown config param
Connected, open http://192.168.0.110/
[warmup] ECG:2576/1337  HR p/e:0.0/0.0  env:2080.0  dc:17839  R/P:0/0  gap:20ms  lo:0  clip:0  web:5ms/0  PWTT:0  BP:0
[warmup] ECG:2634/1476  HR p/e:0.0/0.0  env:880.7  dc:18146  R/P:0/0  gap:15ms  lo:0  clip:0  web:9ms/0  PWTT:0  BP:0
[warmup] ECG:3411/1595  HR p/e:0.0/0.0  env:495.2  dc:18179  R/P:0/0  gap:399ms  lo:0  clip:0  web:401ms/1  PWTT:0  BP:0
Web handle error: [Errno 116] ETIMEDOUT
[warmup] ECG:2672/1574  HR p/e:0.0/0.0  env:237.5  dc:18225  R/P:0/0  gap:312ms  lo:0  clip:0  web:539ms/2  PWTT:0  BP:0
[warmup] ECG:2919/1681  HR p/e:0.0/0.0  env:142.4  dc:18185  R/P:0/0  gap:14ms  lo:0  clip:0  web:4ms/0  PWTT:0  BP:0
[warmup] ECG:2801/1805  HR p/e:0.0/0.0  env:136.3  dc:18115  R/P:0/0  gap:10ms  lo:0  clip:0  web:5ms/0  PWTT:0  BP:0
[warmup] ECG:2567/1865  HR p/e:0.0/0.0  env:131.9  dc:18106  R/P:0/0  gap:14ms  lo:0  clip:0  web:5ms/0  PWTT:0  BP:0
[warmup] ECG:2617/1897  HR p/e:0.0/0.0  env:108.2  dc:18091  R/P:0/0  gap:232ms  lo:0  clip:0  web:237ms/1  PWTT:0  BP:0
[warmup] ECG:2346/1923  HR p/e:0.0/0.0  env:107.2  dc:18186  R/P:0/0  gap:89ms  lo:0  clip:0  web:4ms/0  PWTT:0  BP:0
[warmup] ECG:2593/1982  HR p/e:0.0/0.0  env:99.0  dc:18226  R/P:0/0  gap:13ms  lo:0  clip:0  web:5ms/0  PWTT:0  BP:0
[warmup] ECG:2623/2010  HR p/e:0.0/0.0  env:98.5  dc:18251  R/P:0/0  gap:10ms  lo:0  clip:0  web:5ms/0  PWTT:0  BP:0
[warmup] ECG:2554/2038  HR p/e:0.0/0.0  env:114.0  dc:18152  R/P:0/0  gap:15ms  lo:0  clip:0  web:5ms/0  PWTT:0  BP:0
[warmup] ECG:2890/2075  HR p/e:0.0/0.0  env:124.6  dc:18084  R/P:0/0  gap:222ms  lo:0  clip:0  web:225ms/1  PWTT:0  BP:0
[warmup] ECG:2409/2066  HR p/e:0.0/0.0  env:118.4  dc:18060  R/P:0/0  gap:31ms  lo:0  clip:0  web:5ms/0  PWTT:0  BP:0
[warmup] ECG:2545/2071  HR p/e:0.0/0.0  env:113.1  dc:18055  R/P:0/0  gap:13ms  lo:0  clip:0  web:5ms/0  PWTT:0  BP:0
[warmup] ECG:2694/2096  HR p/e:0.0/0.0  env:105.8  dc:18094  R/P:0/0  gap:13ms  lo:0  clip:0  web:5ms/0  PWTT:0  BP:0
--- warmup done
ECG:2679/2114  HR p/e:0.0/0.0  env:47.0  dc:18135  R/P:1/1  gap:16ms  lo:0  clip:0  web:5ms/0  PWTT:0  BP:0
ECG:2109/2107  HR p/e:0.0/0.0  env:88.6  dc:18152  R/P:1/2  gap:223ms  lo:0  clip:0  web:227ms/1  PWTT:0  BP:0
!! pwtt out of range: -26
ECG:2481/2122  HR p/e:0.0/0.0  env:118.4  dc:18058  R/P:3/4  gap:30ms  lo:0  clip:0  web:4ms/0  PWTT:0  BP:0
ECG:2553/2123  HR p/e:0.0/0.0  env:130.0  dc:17960  R/P:4/5  gap:14ms  lo:0  clip:0  web:4ms/0  PWTT:0  BP:0
ECG:2521/2121  HR p/e:74.9/0.0  env:121.7  dc:17940  R/P:5/6  gap:10ms  lo:0  clip:0  web:5ms/0  PWTT:0  BP:0
--> PWTT: 243  BP: 110.9
ECG:2608/2122  HR p/e:74.9/68.9  env:111.9  dc:17963  R/P:6/7  gap:15ms  lo:0  clip:0  web:4ms/0  PWTT:243  BP:110.9
ECG:2483/2133  HR p/e:74.9/68.9  env:113.1  dc:17966  R/P:8/8  gap:244ms  lo:0  clip:0  web:233ms/1  PWTT:243  BP:110.9
ECG:2615/2150  HR p/e:74.9/68.9  env:112.0  dc:18018  R/P:9/9  gap:13ms  lo:0  clip:0  web:4ms/0  PWTT:243  BP:110.9
ECG:2878/2174  HR p/e:74.9/68.9  env:108.8  dc:18080  R/P:10/10  gap:13ms  lo:0  clip:0  web:4ms/0  PWTT:243  BP:110.9
ECG:2777/2181  HR p/e:69.1/77.2  env:129.1  dc:17995  R/P:11/12  gap:10ms  lo:0  clip:0  web:5ms/0  PWTT:243  BP:110.9
--> PWTT: 240  BP: 112.7
ECG:2311/2130  HR p/e:69.1/77.2  env:124.2  dc:17926  R/P:12/13  gap:15ms  lo:0  clip:0  web:5ms/0  PWTT:240  BP:112.7
ECG:2722/2157  HR p/e:69.1/77.2  env:98.1  dc:17861  R/P:13/14  gap:15ms  lo:0  clip:0  web:8ms/0  PWTT:240  BP:112.7
ECG:2618/2169  HR p/e:69.1/77.2  env:97.9  dc:17872  R/P:15/15  gap:15ms  lo:0  clip:0  web:4ms/0  PWTT:240  BP:112.7
ECG:2496/2151  HR p/e:71.9/65.5  env:103.8  dc:17894  R/P:16/16  gap:12ms  lo:0  clip:0  web:8ms/0  PWTT:240  BP:112.7
"""
