from utime import ticks_ms, ticks_diff, ticks_add
from machine import Pin, ADC, SoftI2C

from max30102 import MAX30102, MAX30102_PULSE_AMP_MEDIUM, STORAGE_QUEUE_SIZE
from filters import IIR_filter, Biquad, AGC
from detectors import Rate_calculator

# Pin Definitions
SDA_PIN = 21
SCL_PIN = 22
ADC_PIN = 36
LO_POSITIVE_PIN = 32
LO_NEGATIVE_PIN = 33
LED_PIN = 5

SAMPLE_RATE = 100
SAMPLE_PERIOD_MS = 1000 // SAMPLE_RATE

# sensor.check() reads the two FIFO pointers before it knows whether there is
# anything to fetch, and on SoftI2C that question alone costs four bus
# transactions, ~3 ms, every single iteration. Paying it at loop rate is what
# caps the loop, and those 3 ms are also 3 ms the ADC is not being read, so
# they land straight on the R timestamp. Throttle it to the sample rate: the
# chip has nothing new to give more often than that anyway.
I2C_POLL_MS = SAMPLE_PERIOD_MS

PPG_LOW_HZ = 0.5
PPG_HIGH_HZ = 8.0

AGC_TARGET = 100
PULSE_MARGIN = AGC_TARGET * 0.5
# Dead-signal gate only. AGC's own floor of 16 already caps the gain, so with
# no finger the output tops out around 12, well under PULSE_MARGIN and unable
# to trigger anything. Anything higher than this sits inside a real but weak
# finger signal and starts throwing away beats.
PPG_MIN_ENV = 5.0

# Full scale for dc is 32767: the driver right-shifts the 18-bit FIFO value
# by 3 at pulse_width 411. A dc pinned there means the LED has saturated the
# photodiode, the waveform is clipped flat and there is no AC left at all —
# measured at HIGH: dc 32766, env 0.4, one beat detected in ninety seconds.
#
# More light is NOT the cure for a small env; past saturation it is the cause.
# Aim for a dc in the middle of the range, roughly 10000-25000.
#   HIGH   0xFF  50.0 mA   -> saturated here
#   MEDIUM 0x7F  25.4 mA   <- start here
#   LOW    0x1F   6.4 mA   -> LED_POWER = 0x1F if MEDIUM is still pinned
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
# was trained on. Note the second column does not move with amplitude and the
# first does, by 15 ms across that range: the AGC buys a trigger point that
# stays put, and the training data has that scatter baked into it.
#
# This aligns the two pipelines. It does NOT calibrate absolute pressure.
#
# The number belongs to the filter chain it was measured on. Simulated against
# the same pulse at 100 Hz, Channel's two biquads trigger 10 ms EARLIER than
# the one-pole DC subtraction below (12.5 ms with the sample grid removed),
# and the offset does not move with amplitude. Two programs on two chains
# would report PWTTs 10 ms apart on the same beat, which is 4 mmHg of
# disagreement for nothing. Both now run the DC-subtract chain.
PPG_DELAY_MS = 58

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

# The tick is the ECG baseline cadence ONLY. R detection runs on every loop
# iteration: quantising the R timestamp to 50 ms would be +-20 mmHg.
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

# 011 printed one line per 50 ms tick, but that loop held a single adc.read()
# and nothing else. Here the loop IS the measurement. One status line was
# measured at 6-35 ms, so twenty a second spend 120-700 ms of every second not
# looking at the ADC, and any R found on the far side of a print carries a
# timestamp that late. Baseline stays on the 50 ms tick, the print gets its
# own slower one.
STATUS_MS = 1000

# 12-bit counts above the running baseline. 330 was tuned in 011-ecg against a
# stronger electrode signal; measured on this hardware the second's best peak
# was often BELOW threshold (2109/2301, 2070/2303, 2087/2301) and 40% of R
# waves were lost. Lower it until R/P track. Going too low lets T-waves in,
# but they land 250-300 ms after R and BEAT_REFRACTORY already blocks that.
BEAT_MARGIN = 200

# 12-bit full scale. The AD8232 railing is a hardware fault, not a big
# heartbeat, and it poisons the detector twice over: the clipped peak carries
# no timing information, and feeding 4095 into a baseline with a 5 s time
# constant lifts the threshold for seconds and costs every R wave behind it.
ECG_CLIP = 4095

# A stalled loop cannot see an R wave until it resumes, so the R timestamp is
# late by however long the gap was and the PWTT comes out short or negative.
# There is no web thread here to cause that, which is exactly why a guard
# costs nothing: it only ever fires if something unexpected blocks the loop.
R_MAX_GAP = 15
# BEAT_REFRACTORY = 400
BEAT_REFRACTORY = 500

PWTT_MIN = 120
PWTT_MAX = 400
TARGET_N_BEATS = 5

# The chip's FIFO is 32 deep and the driver's CircularBuffer matches it, but
# both drop the OLDEST sample on overflow. Back-dating assumes every sample of
# the burst is present and one period apart, so once the loop has been away
# longer than the buffer holds, the timestamps in that burst are wrong by
# however much was lost. Nothing here should ever block that long, which is
# why the guard is worth having: if it fires, something did.
PPG_MAX_AGE_MS = STORAGE_QUEUE_SIZE * SAMPLE_PERIOD_MS

# Rejections skip rather than clear, which is right, but it means five beats
# can be collected across an arbitrary stretch of time. Five beats is ~4 s of
# heart; past this the earliest no longer describes the same moment.
PWTT_WINDOW_MS = 15000

# The dicrotic notch is a second, smaller upstroke inside the same cardiac
# cycle. At PPG_HIGH_HZ = 8.0 it survives the band-pass and after AGC it
# clears PULSE_MARGIN, so without this it counts as a beat. 400 ms matches
# BEAT_REFRACTORY and caps at 150 bpm; drop to 300 for post-exercise.
#
# Measured: the notch triggers landed at 230, 333 and 392 ms, so 400 cleared
# the worst of them by 8 ms. 500 restores the margin and still allows 120 bpm.
PULSE_REFRACTORY = 500

# Prints the interval of every raw PPG trigger, accepted or not. A notch
# shows up as a short interval followed by a long one: 320, 870, 340, 850...
DEBUG_INTVAL = False


def setup():
    try:
        led = Pin(LED_PIN, Pin.OUT)
        led.value(1)

        i2c = SoftI2C(sda=Pin(SDA_PIN), scl=Pin(SCL_PIN))
        sensor = MAX30102(i2c=i2c)
        sensor.setup_sensor(sample_rate=400, sample_avg=4, led_power=LED_POWER)

        adc_pin = Pin(ADC_PIN)
        adc = ADC(adc_pin)
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

    # Channel runs two biquads: a high pass to kill baseline drift and a low
    # pass to set the group delay. The high pass is the expensive half and the
    # cheap half is enough — subtracting a one-pole DC estimate IS a high pass,
    # 6 dB/octave against 12, and the AGC downstream does not care about the
    # difference. Same chain as bp-web.py, so PPG_DELAY_MS means the same thing
    # in both. Measured cost of the pair it replaces: 3.2 ms per sample.
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
    ecg_peak = 0
    ecg_threshold = None
    ecg_rearm = None
    leads_off = False

    # ecg_peak is cleared every 50 ms, so a status line sampling it at an
    # arbitrary moment reads a half-built peak and, when the two ticks line
    # up, a clean 0. Carry the largest completed peak of the second instead.
    ecg_peak_max = 0

    # The first FIFO samples step from nothing to a ~17000 count DC, which
    # rings the filters: measured env 2219 against a steady state near 60.
    # The AGC release time constant is ~1 s, so it takes 15 s to decay on its
    # own, and until it does the gain is 100/2219 and no pulse gets anywhere
    # near PULSE_MARGIN. Re-seed the envelope when the warm-up ends instead.
    was_warm = False

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
    heart_rate = 0
    ecg_heart_rate = 0

    # How late the R timestamp could be, measured rather than assumed. gap_max
    # carries the worst of the second: sampling loop_gap at print time is one
    # random iteration and says nothing about whether the loop ever stalled.
    last_now = ticks_ms()
    loop_gap = 0
    gap_max = 0
    r_gap = 0
    n_clip = 0
    n_leads_off = 0

    # Non-clipped windows the baseline has actually seen. Cumulative, never
    # reset: it gates the warm-up, it is not a per-second statistic.
    n_baseline = 0

    # True while the current burst came out of a FIFO that had time to overflow
    ppg_lost = False

    # Two averages over five beats each cover different windows, so comparing
    # them cannot separate a real rate difference from a miscount. Raw counts
    # over the same run can: they must stay equal.
    n_beats_ecg = 0
    n_beats_ppg = 0
    ppg_dc = 0

    start_time = ticks_ms()

    try:
        while True:
            now = ticks_ms()
            warm = (
                ticks_diff(now, start_time) > WARMUP_MS
                and n_baseline >= BASELINE_MIN_FEEDS
            )

            loop_gap = ticks_diff(now, last_now)
            last_now = now
            if loop_gap > gap_max:
                gap_max = loop_gap

            if warm and not was_warm:
                was_warm = True
                agc.env = None  # drop the start-up transient, re-seed
                n_beats_ecg = 0
                n_beats_ppg = 0
                print("--- warmup done")

            # ---------------- ECG, every iteration -------------------------
            if lo_p.value() or lo_n.value():
                leads_off = True

            raw_ecg = adc.read()
            if raw_ecg > ecg_peak:
                ecg_peak = raw_ecg
            if raw_ecg >= ECG_CLIP:
                n_clip += 1

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
                sensor.check()
                n = sensor.available()

            if n:
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

                    if agc.env < PPG_MIN_ENV:
                        pulse_is_beating = False
                        pulse_accepted = False
                        led.value(1)
                        # Rate_calculator has to see the False as well. Skip
                        # it and is_cycling latches True, so the next beat is
                        # no longer a rising edge and the rate stays 0 for
                        # ever, while the beat detection itself looks fine.
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
                                # reason to throw away four good ones.
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
                                    # samples.
                                    print("!! fifo overrun, pwtt dropped:", pwtt)
                                elif agc.env < agc.floor:
                                    # Below its floor the AGC has hit the gain
                                    # ceiling and stopped normalising, so the
                                    # 50 % trigger point moves with amplitude
                                    # and drags the PWTT with it. The beat is
                                    # still a beat, the timing is not usable.
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
                                        pwtts.sort()
                                        print("--> PWTT:", pwtts[TARGET_N_BEATS // 2])
                                        pwtts = []
                                else:
                                    print("!! pwtt out of range:", pwtt)

                    elif ppg < 0:
                        pulse_is_beating = False
                        pulse_accepted = False
                        led.value(1)

                    # accepted beats only: a notch trigger never reaches here,
                    # and one sub-270 ms interval would reset Rate_calculator's
                    # run of 5 before it ever produces a number
                    rate.update(pulse_accepted)

                heart_rate = round(rate.get_rate(), 1)

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
                    ecg_rate.update(False)
                elif ecg_peak < ECG_CLIP:
                    # never feed a clipped peak to the baseline, or the
                    # threshold chases the clipping upward and takes the
                    # next few seconds of R waves with it
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

            # ---------------- 1 s tick: status line ------------------------
            if ticks_diff(now, status_tick) > STATUS_MS:
                # ecg_peak_max against the threshold it had to clear, and the
                # two beat counts, are the two things worth watching: R waves
                # are being missed when the first pair converges or the second
                # pair drifts apart.
                print(
                    "%sECG:%d/%d  HR p/e:%.1f/%.1f  env:%.1f  dc:%d"
                    "  R/P:%d/%d  gap:%dms  lo:%d  clip:%d"
                    % (
                        "" if warm else "[warmup] ",
                        ecg_peak_max,
                        ecg_threshold if ecg_threshold else 0,
                        heart_rate,
                        ecg_heart_rate,
                        # None between the warm-up re-seed and the next FIFO
                        # sample, and both ticks are counted from main(), so
                        # the 5 s one lands inside that window sooner or later
                        agc.env if agc.env else 0.0,
                        ppg_dc,
                        n_beats_ecg,
                        n_beats_ppg,
                        gap_max,
                        n_leads_off,
                        n_clip,
                    )
                )

                ecg_peak_max = 0
                gap_max = 0
                n_leads_off = 0
                n_clip = 0
                status_tick = now

    except KeyboardInterrupt:
        pass

    finally:
        led.value(1)
        try:
            sensor.shutdown()
            print("Sensor shut down")
        except Exception as e:
            print("Shutdown error:", e)


if __name__ == "__main__":
    main()


"""
Output:
MPY: soft reboot
[warmup] ECG:2499/1912  HR p/e:0.0/0.0  env:1904.3  dc:17170  R/P:0/0  gap:9ms  lo:0  clip:0
[warmup] ECG:2448/1984  HR p/e:0.0/0.0  env:829.1  dc:17538  R/P:0/0  gap:12ms  lo:0  clip:0
[warmup] ECG:2423/1998  HR p/e:0.0/0.0  env:385.1  dc:17596  R/P:0/0  gap:12ms  lo:0  clip:0
[warmup] ECG:2029/1878  HR p/e:0.0/0.0  env:190.9  dc:17534  R/P:0/0  gap:13ms  lo:0  clip:0
[warmup] ECG:4095/1927  HR p/e:0.0/0.0  env:126.7  dc:17527  R/P:0/0  gap:11ms  lo:0  clip:1431
[warmup] ECG:3731/2014  HR p/e:0.0/0.0  env:103.2  dc:17546  R/P:0/0  gap:9ms  lo:0  clip:0
[warmup] ECG:2579/2004  HR p/e:0.0/0.0  env:86.4  dc:17562  R/P:0/0  gap:15ms  lo:0  clip:0
[warmup] ECG:2558/2013  HR p/e:0.0/0.0  env:93.0  dc:17633  R/P:0/0  gap:12ms  lo:0  clip:0
[warmup] ECG:2689/2057  HR p/e:0.0/0.0  env:103.8  dc:17692  R/P:0/0  gap:12ms  lo:0  clip:0
[warmup] ECG:2736/2084  HR p/e:0.0/0.0  env:114.9  dc:17624  R/P:0/0  gap:14ms  lo:0  clip:0
[warmup] ECG:2587/2084  HR p/e:0.0/0.0  env:118.4  dc:17594  R/P:0/0  gap:12ms  lo:0  clip:0
[warmup] ECG:2559/2085  HR p/e:0.0/0.0  env:108.5  dc:17568  R/P:0/0  gap:12ms  lo:0  clip:0
[warmup] ECG:2630/2104  HR p/e:0.0/0.0  env:100.9  dc:17551  R/P:0/0  gap:13ms  lo:0  clip:0
[warmup] ECG:2490/2103  HR p/e:0.0/0.0  env:94.0  dc:17581  R/P:0/0  gap:10ms  lo:0  clip:0
[warmup] ECG:2720/2115  HR p/e:0.0/0.0  env:97.5  dc:17603  R/P:0/0  gap:13ms  lo:0  clip:0
--- warmup done
ECG:2247/2112  HR p/e:0.0/0.0  env:122.1  dc:17637  R/P:0/0  gap:16ms  lo:0  clip:0
!! pwtt out of range: -33
ECG:2663/2116  HR p/e:0.0/0.0  env:112.4  dc:17634  R/P:2/2  gap:14ms  lo:0  clip:0
ECG:2845/2145  HR p/e:0.0/0.0  env:131.2  dc:17582  R/P:3/3  gap:11ms  lo:0  clip:0
ECG:2329/2063  HR p/e:0.0/0.0  env:129.9  dc:17567  R/P:4/4  gap:14ms  lo:0  clip:0
ECG:3088/2136  HR p/e:0.0/0.0  env:114.9  dc:17572  R/P:5/5  gap:10ms  lo:0  clip:0
ECG:2618/2147  HR p/e:66.7/70.7  env:111.0  dc:17570  R/P:6/6  gap:13ms  lo:0  clip:0
ECG:2575/2134  HR p/e:66.7/70.7  env:107.7  dc:17573  R/P:8/7  gap:13ms  lo:0  clip:0
--> PWTT: 228
ECG:2498/2139  HR p/e:66.7/70.7  env:105.5  dc:17589  R/P:9/8  gap:12ms  lo:0  clip:0
ECG:2559/2127  HR p/e:66.7/70.7  env:110.8  dc:17639  R/P:10/9  gap:13ms  lo:0  clip:0
ECG:2623/2133  HR p/e:67.9/67.9  env:121.8  dc:17579  R/P:11/11  gap:11ms  lo:0  clip:0
ECG:2493/2118  HR p/e:67.9/67.9  env:141.3  dc:17543  R/P:12/12  gap:11ms  lo:0  clip:0
--> PWTT: 225
ECG:2509/2113  HR p/e:67.9/67.9  env:142.9  dc:17548  R/P:13/13  gap:9ms  lo:0  clip:0
ECG:2539/2115  HR p/e:67.9/67.9  env:128.5  dc:17557  R/P:14/14  gap:14ms  lo:0  clip:0
ECG:2620/2126  HR p/e:67.9/67.9  env:123.6  dc:17561  R/P:15/15  gap:10ms  lo:0  clip:0
ECG:2681/2126  HR p/e:64.9/65.1  env:119.9  dc:17592  R/P:16/16  gap:10ms  lo:0  clip:0
ECG:2534/2125  HR p/e:64.9/65.1  env:116.5  dc:17609  R/P:17/17  gap:10ms  lo:0  clip:0
--> PWTT: 230
ECG:2491/2124  HR p/e:64.9/65.1  env:110.9  dc:17633  R/P:19/18  gap:10ms  lo:0  clip:0
ECG:2599/2133  HR p/e:64.9/65.1  env:105.4  dc:17657  R/P:20/19  gap:13ms  lo:0  clip:0
ECG:2594/2127  HR p/e:64.9/66.1  env:103.9  dc:17693  R/P:21/20  gap:13ms  lo:0  clip:0
ECG:2809/2184  HR p/e:66.2/66.1  env:118.5  dc:17608  R/P:22/22  gap:13ms  lo:0  clip:0
ECG:2147/2103  HR p/e:66.2/66.1  env:132.3  dc:17540  R/P:23/23  gap:13ms  lo:0  clip:0
--> PWTT: 234
ECG:2777/2130  HR p/e:66.2/66.1  env:129.7  dc:17536  R/P:24/24  gap:14ms  lo:0  clip:0
ECG:2700/2143  HR p/e:66.2/66.1  env:115.8  dc:17513  R/P:25/25  gap:13ms  lo:0  clip:0
ECG:2588/2138  HR p/e:68.4/68.4  env:114.1  dc:17536  R/P:26/26  gap:11ms  lo:0  clip:0
ECG:2598/2133  HR p/e:68.4/68.4  env:113.6  dc:17600  R/P:28/27  gap:14ms  lo:0  clip:0
ECG:2581/2125  HR p/e:68.4/68.4  env:107.8  dc:17664  R/P:29/28  gap:9ms  lo:0  clip:0
--> PWTT: 234
ECG:2512/2124  HR p/e:68.4/68.4  env:114.7  dc:17633  R/P:30/30  gap:12ms  lo:0  clip:0
ECG:2482/2113  HR p/e:67.9/68.0  env:139.2  dc:17588  R/P:31/31  gap:13ms  lo:0  clip:0
ECG:2640/2112  HR p/e:67.9/68.0  env:126.4  dc:17564  R/P:32/32  gap:13ms  lo:0  clip:0
ECG:2723/2109  HR p/e:67.9/68.0  env:121.3  dc:17499  R/P:33/33  gap:10ms  lo:0  clip:0
--> PWTT: 234
ECG:2475/2131  HR p/e:67.9/68.0  env:112.8  dc:17519  R/P:35/34  gap:11ms  lo:0  clip:0
ECG:2950/2142  HR p/e:67.9/69.1  env:112.2  dc:17551  R/P:36/35  gap:13ms  lo:0  clip:0
ECG:2584/2123  HR p/e:69.2/69.1  env:112.3  dc:17606  R/P:37/36  gap:14ms  lo:0  clip:0
ECG:2701/2119  HR p/e:69.2/69.1  env:144.1  dc:17534  R/P:38/38  gap:12ms  lo:0  clip:0
--> PWTT: 235
ECG:2655/2106  HR p/e:69.2/69.1  env:127.1  dc:17500  R/P:39/39  gap:10ms  lo:0  clip:0
ECG:2605/2122  HR p/e:69.2/69.1  env:110.8  dc:17582  R/P:40/40  gap:11ms  lo:0  clip:0
ECG:2672/2126  HR p/e:72.0/72.1  env:108.5  dc:17650  R/P:42/41  gap:13ms  lo:0  clip:0
ECG:2582/2112  HR p/e:72.0/72.1  env:111.9  dc:17633  R/P:43/43  gap:13ms  lo:0  clip:0
--> PWTT: 234
ECG:2599/2120  HR p/e:72.0/72.1  env:131.3  dc:17590  R/P:44/44  gap:14ms  lo:0  clip:0
ECG:2612/2122  HR p/e:72.0/72.1  env:114.6  dc:17552  R/P:45/45  gap:17ms  lo:0  clip:0
"""
