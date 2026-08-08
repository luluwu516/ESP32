from machine import SoftI2C, Pin
from max30102 import MAX30102
from pulse_oximeter import Pulse_oximeter

# Pin Definitions
SDA_PIN = 21
SCL_PIN = 22


def setup():
    try:
        i2c = SoftI2C(sda=Pin(SDA_PIN), scl=Pin(SCL_PIN))
        sensor = MAX30102(i2c=i2c)
        sensor.setup_sensor()
        return sensor

    except Exception as e:
        print("Setup error:", e)
        return None


def main():
    sensor = setup()

    if sensor is None:
        print("Failed...")
        return

    pox = Pulse_oximeter(sensor)
    # dc_extractor = IIR_filter(0.99)

    try:
        while True:
            pox.update()

            if pox.available():
                ir = pox.get_raw_ir()
                dc = pox.dc_remover_ir.old_value
                ppg = int(dc * 1.01 - ir)
                print("PPG:", ppg)

                # red_val = pox.get_raw_red()
                # red_dc = dc_extractor.step(red_val)
                # ppg = int(red_dc * 1.01 - red_val)
                # print("PPG:", ppg)

    except KeyboardInterrupt:
        pass

    finally:
        sensor.shutdown()
        print("Sensor shut down")


if __name__ == "__main__":
    main()
