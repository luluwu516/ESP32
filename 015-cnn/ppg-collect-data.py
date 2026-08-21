from utime import ticks_ms, ticks_diff
from machine import SoftI2C, Pin

from max30102 import MAX30102
from filters import IIR_filter, Channel, AGC

LED_PIN = 5
SDA_PIN = 21
SCL_PIN = 22

SAMPLE_RATE = 50
PPG_LOW_HZ = 0.5
PPG_HIGH_HZ = 5.0
USE_AGC = True
AGC_TARGET = 100.0
BEAT_THRESHOLD = AGC_TARGET * 0.5 if USE_AGC else 10
TARGET_N_BEATS = 3

LABEL = "other"
FILE_NAME = LABEL + ".txt"
FILE_MODE = "a"


def setup():
    try:
        led = Pin(LED_PIN, Pin.OUT)
        led.value(1)

        i2c = SoftI2C(sda=Pin(SDA_PIN), scl=Pin(SCL_PIN))
        sensor = MAX30102(i2c=i2c)
        sensor.setup_sensor()

        sensor.set_led_mode(2)

        return (led, sensor)

    except Exception as e:
        print("Setup error:", e)
        return None


def cal_heart_rate(intval, target_n_beats=TARGET_N_BEATS):
    intval /= 1000
    heart_rate = target_n_beats / (intval / 60)
    heart_rate = round(heart_rate, 1)
    return heart_rate


def trim(data, length=300):
    if len(data) > length:
        data = data[:length]
    else:
        data = data + [0 for _ in range(length - len(data))]
    return data


def drain(sensor, ppg_channel, agc, thresh_gen, settle=50):
    for i in range(4):
        sensor.check()
        while sensor.available():
            sensor.pop_ir_from_storage()
    n = 0
    while n < settle:
        sensor.check()
        while sensor.available() and n < settle:
            ac, dc = ppg_channel.step(sensor.pop_ir_from_storage())
            if agc:
                thresh_gen.step(int(agc.step(-ac) + AGC_TARGET))
            else:
                thresh_gen.step(max(int(-ac + 0.01 * dc), 0))
            n += 1


def main():
    devices = setup()
    if devices is None:
        print("Failed...")
        return
    led, sensor = devices

    try:
        f = open(FILE_NAME, FILE_MODE)
    except Exception as e:
        print("Open file error:", e)
        sensor.shutdown()
        return

    ppg_channel = Channel(SAMPLE_RATE, PPG_LOW_HZ, PPG_HIGH_HZ)
    agc = AGC(SAMPLE_RATE, AGC_TARGET) if USE_AGC else None
    thresh_gen = IIR_filter(0.9)

    is_beating = False
    beat_time_mark = ticks_ms()
    num_beats = 0
    total_intval = 0

    num_completed = 0
    target_num = 50

    data = []
    done = False

    try:
        while not done:
            sensor.check()

            while sensor.available():
                ir = sensor.pop_ir_from_storage()
                ac, dc = ppg_channel.step(ir)

                ppg_raw = int(-ac)
                if agc:
                    ppg = int(agc.step(-ac) + AGC_TARGET)
                else:
                    ppg = max(int(-ac + 0.01 * dc), 0)

                data.append(ppg_raw)
                if len(data) > 600:
                    total_intval = 0
                    num_beats = 0
                    data = []
                    beat_time_mark = ticks_ms()

                thresh = thresh_gen.step(ppg)

                if ppg > (thresh + BEAT_THRESHOLD) and not is_beating:
                    is_beating = True
                    led.value(0)

                    rr_intval = ticks_diff(ticks_ms(), beat_time_mark)
                    if 2000 > rr_intval > 270:
                        total_intval += rr_intval
                        num_beats += 1

                        if num_beats == TARGET_N_BEATS:
                            heart_rate = cal_heart_rate(total_intval)
                            data = trim(data)

                            for point in data:
                                print(point)
                            print("HR:", heart_rate)

                            if input("Save(Y/N)? ").lower() in ("y", "yes"):
                                f.write(str(data)[1:-1])
                                f.write("\n")
                                num_completed += 1
                                print("Saved: %s/%s" % (num_completed, target_num))
                                if num_completed == target_num:
                                    print("Finish!")
                                    done = True
                            else:
                                print("Abandon.")

                            total_intval = 0
                            num_beats = 0
                            data = []
                            if done:
                                break
                            drain(sensor, ppg_channel, agc, thresh_gen)
                    else:
                        total_intval = 0
                        num_beats = 0
                        data = []

                    beat_time_mark = ticks_ms()

                elif ppg < thresh:
                    is_beating = False
                    led.value(1)

    except KeyboardInterrupt:
        pass

    finally:
        try:
            f.close()
        except Exception:
            pass
        try:
            sensor.shutdown()
            print("Sensor shut down")
        except Exception as e:
            print("Shutdown error:", e)
        led.value(1)


if __name__ == "__main__":
    main()
