import _thread

from utime import ticks_ms, ticks_diff, sleep_ms
from machine import SoftI2C, Pin
import network, ESPWebServer
from wifi import WIFI_SSID, WIFI_PASSWORD

from max30102 import MAX30102
from filters import IIR_filter, Channel, AGC
from detectors import Rate_calculator

# Pin Definitions
LED_PIN = 5
SDA_PIN = 21
SCL_PIN = 22

SAMPLE_RATE = 50  # 400 Hz internally, 8 averaged by the chip

PPG_LOW_HZ = 0.5
PPG_HIGH_HZ = 5.0

USE_AGC = True
AGC_TARGET = 100.0

TARGET_N_BEATS = 5

BEAT_THRESHOLD = AGC_TARGET * 0.5 if USE_AGC else 10
PPG_BUFFER_LEN = 50


class Shared(object):
    def __init__(self):
        self.heart_rate = 0
        self.ppg_buffer = []
        self.running = True


state = Shared()


def send_heart_rate(socket, args):
    ESPWebServer.ok(socket, "200", str(state.heart_rate))


def send_ppg(socket, args):
    buffer = state.ppg_buffer
    state.ppg_buffer = []
    ESPWebServer.ok(socket, "200", ",".join(str(v) for v in buffer))


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
    except BaseException as e:
        print("Web thread stopping:", e)
    finally:
        state.running = False
        ESPWebServer.close()
        print("Web server closed")


def start_web_server(routes, port=80):
    ESPWebServer.begin(port)
    for path, handler in routes.items():
        ESPWebServer.onPath(path, handler)
    _thread.start_new_thread(web_loop, ())


def setup():
    try:
        led = Pin(LED_PIN, Pin.OUT)
        led.value(1)

        i2c = SoftI2C(sda=Pin(SDA_PIN), scl=Pin(SCL_PIN))
        sensor = MAX30102(i2c=i2c)
        sensor.setup_sensor()

        # Mode 2 is the chip's heart rate mode,
        # which lights LED1, the red one and
        # fills the infrared buffer.
        sensor.set_led_mode(2)

        return (led, sensor)

    except Exception as e:
        print("Setup error:", e)
        return None


def main():
    sensors = setup()

    if sensors is None:
        print("Failed...")
        return

    led, sensor = sensors

    ppg_channel = Channel(SAMPLE_RATE, PPG_LOW_HZ, PPG_HIGH_HZ)
    agc = AGC(SAMPLE_RATE, AGC_TARGET) if USE_AGC else None

    thresh_gen_pulse = IIR_filter(0.9)
    rate = Rate_calculator(target_n_cycles=TARGET_N_BEATS)
    is_beating = False

    try:
        ip = connect_wifi(WIFI_SSID, WIFI_PASSWORD)
        print("Connected, open http://%s/" % ip)

        start_web_server({"/hr": send_heart_rate, "/line": send_ppg})

        while state.running:
            sensor.check()

            if sensor.available():
                ir = sensor.pop_ir_from_storage()
                ac, dc = ppg_channel.step(ir)
                if agc:
                    ppg = int(agc.step(-ac) + AGC_TARGET)
                else:
                    ppg = max(int(-ac + 0.01 * dc), 0)

                buf = state.ppg_buffer
                buf.append(ppg)
                if len(buf) > PPG_BUFFER_LEN:
                    del buf[0]

                thresh = thresh_gen_pulse.step(ppg)

                if ppg > (thresh + BEAT_THRESHOLD) and not is_beating:
                    is_beating = True
                    led.value(0)
                elif ppg < thresh:
                    is_beating = False
                    led.value(1)

                rate.update(is_beating)
                state.heart_rate = round(rate.get_rate(), 1)

    except KeyboardInterrupt:
        pass

    finally:
        state.running = False
        try:
            sensor.shutdown()
            print("Sensor shut down")
        except Exception as e:
            print("Shutdown error:", e)
        led.value(1)
        sleep_ms(200)


if __name__ == "__main__":
    main()
