import _thread
from utime import ticks_ms, ticks_diff, sleep_ms

# import gc
from machine import Pin, ADC

import network, ESPWebServer
from wifi import WIFI_SSID, WIFI_PASSWORD

from keras_lite import Model
import ulab as np  # micropython's numpy

# Pin
ADC_PIN = 36

MODEL_FILE = "temperature_model.json"
NUM_SAMPLES = 20

mean = 622.2105263157895
std = 113.19846518736738

model = Model(MODEL_FILE)


class Shared(object):
    def __init__(self):
        self.temp = 0
        self.running = True


state = Shared()


def setup():
    try:
        adc_pin = Pin(ADC_PIN)
        adc = ADC(adc_pin)
        adc.width(ADC.WIDTH_10BIT)  # to match the data in temperature.txt
        adc.atten(ADC.ATTN_11DB)

        return adc

    except Exception as e:
        print("Setup error:", e)
        return None


def read_average(adc):
    total = 0

    for i in range(NUM_SAMPLES):
        total += adc.read()
        sleep_ms(10)

    return int(total / NUM_SAMPLES)


def cal_temp(data):
    data = np.array([data])
    data = data - mean
    data = data / std

    temp = model.predict(data)
    temp = round(temp[0] * 100, 1)

    return temp


def send_temp(socket, args):
    ESPWebServer.ok(socket, "200", str(state.temp))


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
    errors = 0

    while state.running:
        try:
            ESPWebServer.handleClient()
            errors = 0
        except Exception as e:
            errors += 1
            print("Web thread error:", e)

            if errors >= 10:
                print("Too many consecutive errors")
                break

    ESPWebServer.close()
    print("Web server closed")


def start_web_server(routes, port=80):
    ESPWebServer.begin(port)
    for path, handler in routes.items():
        ESPWebServer.onPath(path, handler)
    _thread.start_new_thread(web_loop, ())


def main():
    adc = setup()

    if adc is None:
        print("Failed...")
        return

    try:
        ip = connect_wifi(WIFI_SSID, WIFI_PASSWORD)
        print("Connected, open http://%s" % ip)
        start_web_server({"/measure": send_temp})

        while True:
            raw = read_average(adc)
            state.temp = cal_temp(raw)
            print(state.temp)
            # print(state.temp, gc.mem_free())
            # gc.collect()
            sleep_ms(500)

    except KeyboardInterrupt:
        pass

    finally:
        state.running = False
        sleep_ms(200)
        print("Stopped...")


if __name__ == "__main__":
    main()
