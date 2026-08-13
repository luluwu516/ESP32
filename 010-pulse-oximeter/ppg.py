from machine import SoftI2C, Pin
from max30102 import MAX30102
from filters import IIR_filter, Channel, AGC

# Pin Definitions
LED_PIN = 5
SDA_PIN = 21
SCL_PIN = 22

SAMPLE_RATE = 50  # 400 Hz internally, 8 averaged by the chip

# Pulse band: 0.5 Hz is 30 bpm, 5 Hz is 300 bpm.
PPG_LOW_HZ = 0.5
PPG_HIGH_HZ = 5.0

# The band-pass has a gain of about 1, so it cleans the trace without making
# it any taller. AGC is what makes it taller. Set this False to see the real
# amplitude again, which is the only version that shows contact quality.
USE_AGC = True
AGC_TARGET = 100.0

# Counts the trace must rise above its running mean to count as a beat.
# Without AGC: measured on a real 302 sample capture, the peaks sit 18 to 20
# counts above the mean, so 20 found 2 beats out of 6 while 10 found all 6.
# With AGC the amplitude is normalised, so a fixed fraction of the target
# works at any perfusion. Both settings find 3 of 3 on the recorded captures,
# and with AGC anything from 35 to 70 gives the same answer.
BEAT_THRESHOLD = AGC_TARGET * 0.5 if USE_AGC else 10


def setup():
    try:
        led = Pin(LED_PIN, Pin.OUT)
        led.value(1)  # active low, so 1 is off

        i2c = SoftI2C(sda=Pin(SDA_PIN), scl=Pin(SCL_PIN))
        sensor = MAX30102(i2c=i2c)
        sensor.setup_sensor()

        # Pulse_oximeter used to do this. Mode 2 and not 1: the driver calls
        # mode 1 "IR only", but 0x02 is the chip's heart rate mode, which
        # lights LED1, the red one. Mode 2 is the only one that fills the
        # infrared buffer this file reads.
        sensor.set_led_mode(2)

        return (led, sensor)

    except Exception as e:
        print("Setup error:", e)
        return None


def main():
    devices = setup()

    if devices is None:
        print("Failed...")
        return

    led, sensor = devices

    ppg_channel = Channel(SAMPLE_RATE, PPG_LOW_HZ, PPG_HIGH_HZ)
    agc = AGC(SAMPLE_RATE, AGC_TARGET) if USE_AGC else None

    thresh_gen = IIR_filter(0.9)
    is_beating = False

    try:
        while True:
            sensor.check()

            # while, not if: check() can bring back several samples at once,
            # and the red buffer fills in step with this one either way.
            while sensor.available():
                ir = sensor.pop_ir_from_storage()

                # Negated because reflectance drops at systole. The offset
                # is what keeps the trace positive around a sensible centre.
                ac, dc = ppg_channel.step(ir)
                if agc:
                    ppg = int(agc.step(-ac) + AGC_TARGET)
                else:
                    ppg = max(int(-ac + 0.01 * dc), 0)

                thresh = thresh_gen.step(ppg)

                if ppg > (thresh + BEAT_THRESHOLD) and not is_beating:
                    is_beating = True
                    led.value(0)

                elif ppg < thresh:
                    is_beating = False
                    led.value(1)

                print(ppg)

    except KeyboardInterrupt:
        pass

    finally:
        try:
            sensor.shutdown()
            print("Sensor shut down")
        except Exception as e:
            print("Shutdown error:", e)
        led.value(1)


if __name__ == "__main__":
    main()
