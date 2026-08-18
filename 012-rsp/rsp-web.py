import _thread

from utime import ticks_ms, ticks_diff, sleep_ms
from machine import Pin, ADC

import network, ESPWebServer
from wifi import WIFI_SSID, WIFI_PASSWORD

# PIN
ADC_PIN = 36
LED_PIN = 5

SAMPLE_INTVAL = 300

# Peak and trough shrink toward their midpoint each sample and get pushed
# back out by the real extremes once per breath. 0.97 ** 12 ~= 0.69, so the
# envelope gives up ~30% per breath at any amplitude.
ENVELOPE_DECAY = 0.97

# Trigger and re-arm as a fraction of the measured amplitude above the
# midpoint. Fixed counts do not work: amplitude has ranged 26-131 across
# captures, and no single margin spans that.
THRESH_FRACTION = 0.25
RESET_FRACTION = 0.1

# Below this the trigger would sit inside the noise, so do not guess.
# The envelope under-reads by ~20%, so 25 here means a real swing near 30.
MIN_AMPLITUDE = 25

BREATH_REFRACTORY = 1500  # caps at 40 brpm, blocks double-triggering
MAX_INTVAL = 10000  # 6 brpm
TARGET_N_BREATH = 2


class Shared(object):
    def __init__(self):
        self.rsp = 0
        self.rsp_rate = 0
        self.running = True


state = Shared()


def send_rsp(socket, args):
    ESPWebServer.ok(socket, "200", str(state.rsp))


def send_rsp_rate(socket, args):
    ESPWebServer.ok(socket, "200", str(state.rsp_rate))


def connect_wifi(ssid, password, timeout_ms=15000):
    sta = network.WLAN(network.STA_IF)
    sta.active(True)

    if not sta.isconnected():
        sta.connect(ssid, password)
        start = ticks_ms()

        while not sta.isconnected():
            if ticks_diff(ticks_ms(), start) > timeout_ms:
                raise OSError("wifi connect timed out after %d ms" % timeout_ms)
            sleep_ms(100)

    return sta.ifconfig()[0]


def web_loop():
    try:
        while state.running:
            ESPWebServer.handleClient()
    except Exception as e:
        print("Web thread error:", e)
    finally:
        ESPWebServer.close()
        print("Web server closed")


def start_web_server(routes, port=80):
    ESPWebServer.begin(port)
    for path, handler in routes.items():
        ESPWebServer.onPath(path, handler)
    _thread.start_new_thread(web_loop, ())


def setup():
    try:
        adc_pin = Pin(ADC_PIN)
        adc = ADC(adc_pin)
        adc.atten(ADC.ATTN_11DB)

        led = Pin(LED_PIN, Pin.OUT)
        led.value(1)

        return (adc, led)

    except Exception as e:
        print("Setup error:", e)
        return None


def cal_rsp_rate(intval, target_n_breath=TARGET_N_BREATH):
    intval /= 1000
    rsp_rate = target_n_breath / (intval / 60)
    rsp_rate = round(rsp_rate, 1)
    return rsp_rate


def main():
    sensors = setup()

    if sensors is None:
        print("Failed...")
        return

    adc, led = sensors

    peak = trough = adc.read()

    last_sample = ticks_ms()
    last_breath = None
    is_breathing = False
    was_weak = True
    num_breath = 0
    total_intval = 0
    acc = 0
    n_acc = 0

    try:
        ip = connect_wifi(WIFI_SSID, WIFI_PASSWORD)
        print("Connected, open http://%s" % ip)
        start_web_server({"/sendata": send_rsp_rate, "/line": send_rsp})

        while True:
            acc += adc.read()
            n_acc += 1
            sleep_ms(1)

            if ticks_diff(ticks_ms(), last_sample) > SAMPLE_INTVAL:
                rsp = acc // n_acc
                acc = 0
                n_acc = 0
                last_sample = ticks_ms()

                state.rsp = rsp

                if rsp > peak:
                    peak = rsp
                else:
                    mid = (peak + trough) / 2
                    peak = mid + (peak - mid) * ENVELOPE_DECAY

                if rsp < trough:
                    trough = rsp
                else:
                    mid = (peak + trough) / 2
                    trough = mid + (trough - mid) * ENVELOPE_DECAY

                amplitude = peak - trough
                mid = (peak + trough) / 2
                trigger = mid + amplitude * THRESH_FRACTION
                rearm = mid + amplitude * RESET_FRACTION

                print("RSP:", rsp, trigger)

                # only on a change, so a steady state stays quiet
                weak = amplitude < MIN_AMPLITUDE
                if weak != was_weak:
                    print("!!" if weak else "--", "amplitude:", amplitude)
                    was_weak = weak

                now = ticks_ms()

                if weak:
                    is_breathing = False
                    led.value(1)

                elif rsp > trigger and not is_breathing:
                    if (
                        last_breath is None
                        or ticks_diff(now, last_breath) > BREATH_REFRACTORY
                    ):
                        is_breathing = True
                        led.value(0)

                        if last_breath is not None:
                            intval = ticks_diff(now, last_breath)

                            if intval < MAX_INTVAL:
                                total_intval += intval
                                num_breath += 1
                                if num_breath == TARGET_N_BREATH:
                                    state.rsp_rate = cal_rsp_rate(total_intval)
                                    print("---> RSP rate:", state.rsp_rate)
                                    total_intval = 0
                                    num_breath = 0
                            else:
                                print("!! gap:", intval)
                                total_intval = 0
                                num_breath = 0

                        last_breath = now

                elif rsp < rearm:
                    is_breathing = False
                    led.value(1)

    except KeyboardInterrupt:
        pass

    finally:
        led.value(1)
        state.running = False
        sleep_ms(200)
        print("Stopped...")


if __name__ == "__main__":
    main()
