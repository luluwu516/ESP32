from wifi import *  # the module store my wifi info
import network
import urequests
import utime
from ssd1306 import SSD1306_I2C
from machine import Pin, ADC, SoftI2C

# Constants
OLED_WIDTH = 128
OLED_HEIGHT = 64
SSID = REPLACE_WITH_YOUR_SSID
PASSWORD = REPLACE_WITH_YOUR_PASSWORD
KEY = REPLACE_WITH_YOUR_KEY
EVENT_NAME = REPLACE_WITH_YOUR_EVENT_NAME
IFTTT_URL = "https://maker.ifttt.com/trigger/{}/with/key/{}".format(EVENT_NAME, KEY)

# Pin
ADC_PIN = 36
I2C_SCL_PIN = 22
I2C_SDA_PIN = 21

# oled
i2c = SoftI2C(scl=Pin(I2C_SCL_PIN), sda=Pin(I2C_SDA_PIN))
oled = SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c)

# sensor
adc_pin = Pin(ADC_PIN)
adc = ADC(adc_pin)
adc.width(ADC.WIDTH_9BIT)
adc.atten(ADC.ATTN_11DB)


def connect_to_wifi():
    print("Connecting to WiFi " + SSID + "...")
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    sta.connect(SSID, PASSWORD)

    while not sta.isconnected():  # Check connection
        pass
    print("Connected.")


def send_to_ifttt(data):
    try:
        response = urequests.get(IFTTT_URL, params={"value": data})
        if response.status_code == 200:
            print("IFTTT Success: Sending messages on Line")
        else:
            print("IFTTT Failed")
    except Exception as e:
        print("Exception occurred while sending data to IFTTT:", e)


def main():
    connect_to_wifi()

    while True:
        resistance = adc.read()

        if resistance > 200:
            send_to_ifttt(gsr)
            utime.sleep(5)

        oled.fill(0)
        oled.text("Resistance: ", 0, 0)
        oled.text(str(gsr) + " Ohm", 0, 16)
        oled.show()

        utime.sleep_ms(100)


if __name__ == "__main__":
    main()
