from utime import ticks_ms, ticks_diff
from machine import Pin, ADC

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
        while True:
            acc += adc.read()
            n_acc += 1

            if ticks_diff(ticks_ms(), last_sample) > SAMPLE_INTVAL:
                rsp = acc // n_acc
                acc = 0
                n_acc = 0
                last_sample = ticks_ms()

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
                                    print("---> RSP rate:", cal_rsp_rate(total_intval))
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
        print("Stopped...")


if __name__ == "__main__":
    main()

"""
Output: second column is the trigger level, not a baseline.
Peak-to-trough amplitude ran 33-69 here, the range the previous
fixed-threshold version produced nothing at all on.

MPY: soft reboot
RSP: 1995 1992.537
RSP: 2012 2005.388
-- amplitude: 26.44727      <- detector armed, first trigger discarded
RSP: 2029 2018.301
RSP: 2056 2038.813
RSP: 2078 2055.653
RSP: 2090 2065.033          <- peak
RSP: 2069 2064.279
RSP: 2040 2063.547
RSP: 2026 2062.836
RSP: 2022 2062.147
RSP: 2021 2061.478          <- trough
RSP: 2029 2060.83
RSP: 2048 2060.2
RSP: 2068 2059.589          <- trigger, interval 1 (12 samples)
...
RSP: 2082 2071.453          <- trigger, interval 2 (12 samples)
---> RSP rate: 16.6
...
RSP: 2087 2079.963
---> RSP rate: 18.1
...
RSP: 2094 2087.118
---> RSP rate: 18.1
...
RSP: 2102 2097.409
---> RSP rate: 16.6

Triggers on samples 1, 13, 25, 36, 47, 59, 69, 80, 93: eight intervals of
12, 12, 11, 11, 12, 10, 11, 13 samples, mean 3460 ms = 17.3 brpm.
The trough drifted up 52 counts across the capture and the trigger level
followed it, from 2005 to 2097.
"""
