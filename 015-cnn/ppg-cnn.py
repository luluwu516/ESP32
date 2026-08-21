from utime import ticks_ms, ticks_diff
from machine import SoftI2C, Pin

from max30102 import MAX30102
from filters import IIR_filter, Channel, AGC
from keras_lite import Model
import ulab as np

mean = -15.054416666666667
std = 1257.0903909745286

MODEL_FILE = "ppg_model.json"
model = Model(MODEL_FILE)
label_name = ["others", "ppg"]

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
DC_ON = 15000
DC_OFF = 9000


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


def get_label(data):
    data = trim(data)
    data = np.array([data])
    data = (data - mean) / std
    pred_class = model.predict_classes(data)
    label = label_name[pred_class[0]]
    return label


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
    beat_time_mark = ticks_ms()
    heart_rate = 0
    num_beats = 0
    total_intval = 0
    finger_on = True

    data = []

    try:
        while True:
            sensor.check()

            while sensor.available():
                ir = sensor.pop_ir_from_storage()
                ac, dc = ppg_channel.step(ir)
                # print("dc:", dc)

                ppg_raw = int(-ac)
                if agc:
                    ppg = int(agc.step(-ac) + AGC_TARGET)
                else:
                    ppg = max(int(-ac + 0.01 * dc), 0)

                thresh = thresh_gen.step(ppg)

                if finger_on and dc < DC_OFF:
                    print("Class: others (no finger)")
                    finger_on = False
                    led.value(1)
                elif not finger_on and dc > DC_ON:
                    print("Finger on!")
                    finger_on = True

                if not finger_on:
                    data = []
                    num_beats = 0
                    total_intval = 0
                    beat_time_mark = ticks_ms()
                    is_beating = False
                    continue

                data.append(ppg_raw)
                if len(data) > 600:
                    data = []
                    total_intval = 0
                    num_beats = 0
                    beat_time_mark = ticks_ms()

                if ppg > (thresh + BEAT_THRESHOLD) and not is_beating:
                    is_beating = True
                    led.value(0)

                    rr_intval = ticks_diff(ticks_ms(), beat_time_mark)
                    if 2000 > rr_intval > 270:
                        total_intval += rr_intval
                        num_beats += 1

                        if num_beats == TARGET_N_BEATS:
                            label = get_label(data)
                            # print("Class:", label)
                            print(
                                "Class:",
                                label,
                                "| dc:",
                                int(dc),
                                "| amp:",
                                max(data) - min(data),
                            )
                            if label == "ppg":
                                heart_rate = cal_heart_rate(total_intval)
                                print("HR:", heart_rate)
                            total_intval = 0
                            num_beats = 0
                            data = []
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
            sensor.shutdown()
            print("Sensor shut down")
        except Exception as e:
            print("Shutdown error:", e)
        led.value(1)


if __name__ == "__main__":
    main()
