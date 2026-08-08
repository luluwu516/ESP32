from utime import ticks_ms, ticks_diff
from machine import Pin, ADC

# Pin Definitions
ADC_PIN = 36
LO_POSITIVE_PIN = 32
LO_NEGATIVE_PIN = 33


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

        return (adc, lo_p, lo_n)

    except Exception as e:
        print("Setup error:", e)
        return None


def main():
    sensors = setup()
    if sensors is None:
        print("Failed...")
        return

    adc, lo_p, lo_n = sensors

    last_print = ticks_ms()
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
                else:
                    print("ECG:", ecg)

                max_val = 0
                last_print = ticks_ms()
                leads_off = False

    except KeyboardInterrupt:
        pass

    finally:
        print("Stopped...")


if __name__ == "__main__":
    main()
