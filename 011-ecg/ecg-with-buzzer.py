from utime import ticks_ms, ticks_diff
from machine import Pin, ADC, PWM
from pulse_oximeter import IIR_filter

# Pin Definitions
ADC_PIN = 36
LO_POSITIVE_PIN = 32
LO_NEGATIVE_PIN = 33
BUZZER_PIN = 2

# Find R
BEAT_MARGIN = 330
# T-waves land ~250-300 ms after R, ignore that window
BEAT_REFRACTORY = 400

TARGET_N_BEATS = 5
VOLUME = 128  # duty 0-1023


def setup():
    try:
        adc_pin = Pin(ADC_PIN)
        adc = ADC(adc_pin)

        # 10-bit resolution (0-1023); classic-ESP32 only,
        # and the default 12-bit gives 4x the resolution for free
        # adc.width(ADC.WIDTH_10BIT)

        # widest input range (~0-3.3V), required for AD8232
        adc.atten(ADC.ATTN_11DB)

        lo_p = Pin(LO_POSITIVE_PIN, Pin.IN)
        lo_n = Pin(LO_NEGATIVE_PIN, Pin.IN)

        buzzer = PWM(Pin(BUZZER_PIN), freq=2000, duty=0)

        return (adc, lo_p, lo_n, buzzer)

    except Exception as e:
        print("Setup error:", e)
        return None


def cal_heart_rate(intval, target_n_beats=TARGET_N_BEATS):
    intval /= 1000
    heart_rate = target_n_beats / (intval / 60)
    heart_rate = round(heart_rate, 1)

    return heart_rate


def main():
    sensors = setup()

    if sensors is None:
        print("Failed...")
        return

    adc, lo_p, lo_n, buzzer = sensors

    thresh_generator = IIR_filter(0.99)

    last_print = ticks_ms()
    last_beat = ticks_ms()

    is_beating = False
    heart_rate = 0
    num_beats = 0
    total_intval = 0
    max_val = 0
    leads_off = False

    try:
        while True:
            # check if leads off
            if lo_p.value() or lo_n.value():
                leads_off = True

            raw = adc.read()
            if raw > max_val:
                max_val = raw

            # output every 50 ms
            if ticks_diff(ticks_ms(), last_print) > 50:
                ecg = max_val

                if leads_off:
                    print("!")
                    buzzer.duty(0)
                    is_beating = False
                else:
                    print("ECG:", ecg)
                    thresh = thresh_generator.step(ecg)

                    now = ticks_ms()
                    if (
                        ecg > (thresh + BEAT_MARGIN)
                        and not is_beating
                        and ticks_diff(now, last_beat) > BEAT_REFRACTORY
                    ):
                        is_beating = True
                        buzzer.duty(VOLUME)

                        intval = ticks_diff(now, last_beat)
                        last_beat = now

                        if intval < 2000:  # lower bound is BEAT_REFRACTORY
                            total_intval += intval
                            num_beats += 1
                            if num_beats == TARGET_N_BEATS:
                                heart_rate = cal_heart_rate(total_intval)
                                print("--> HR:", heart_rate)
                                total_intval = 0
                                num_beats = 0
                        else:
                            total_intval = 0
                            num_beats = 0

                    elif ecg < thresh:
                        is_beating = False
                        buzzer.duty(0)

                max_val = 0
                last_print = ticks_ms()
                leads_off = False

    except KeyboardInterrupt:
        pass

    finally:
        buzzer.duty(0)
        buzzer.deinit()  # release the PWM channel
        print("Stopped...")


if __name__ == "__main__":
    main()
