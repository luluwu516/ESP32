from utime import ticks_ms, ticks_diff
from machine import Pin, ADC

# PIN
ADC_PIN = 36

SAMPLE_INTVAL = 300

# Same envelope and floor the detector uses, so what this prints is a
# preview of whether rsp_led.py will find anything
ENVELOPE_DECAY = 0.97
MIN_AMPLITUDE = 25


def setup():
    try:
        adc_pin = Pin(ADC_PIN)
        adc = ADC(adc_pin)
        adc.atten(ADC.ATTN_11DB)

        return adc

    except Exception as e:
        print("Setup error:", e)
        return None


def main():
    adc = setup()

    if adc is None:
        print("Failed...")
        return

    peak = trough = adc.read()

    last_sample = ticks_ms()
    was_weak = True
    acc = 0
    n_acc = 0

    try:
        while True:
            # average the whole window, as the detector does. A single read
            # is several times noisier and would misrepresent the signal.
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

                # three series at the same scale: the signal with its
                # envelope drawn around it
                print("RSP:", rsp, peak, trough)

                weak = (peak - trough) < MIN_AMPLITUDE
                if weak != was_weak:
                    print("!!" if weak else "--", "amplitude:", peak - trough)
                    was_weak = weak

    except KeyboardInterrupt:
        pass

    finally:
        print("Stopped...")


if __name__ == "__main__":
    main()
