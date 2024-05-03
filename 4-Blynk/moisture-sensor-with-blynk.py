from wifi import *  # the module store my wifi info
import BlynkLib
import network
import utime
from ssd1306 import SSD1306_I2C
from machine import Pin, ADC, SoftI2C

# Constants
WIFI_SSID = REPLACE_WITH_YOUR_SSID
WIFI_PASS = REPLACE_WITH_YOUR_PASSWORD
BLYNK_AUTH = REPLACE_WITH_YOUR_BLYNK_AUTH
OLED_WIDTH = 128
OLED_HEIGHT = 64

# Pin
ADC_PIN = 36
SCL_PIN = 22
SDA_PIN = 21


def connect_to_wifi():
    wifi = network.WLAN(network.STA_IF)
    if not wifi.isconnected():
        print("Connecting to WiFi...")
        wifi.active(True)
        wifi.connect(WIFI_SSID, WIFI_PASS)
        while not wifi.isconnected():
            pass
        print("IP:", wifi.ifconfig()[0])


def blynk_setup():
    blynk = BlynkLib.Blynk(BLYNK_AUTH)

    @blynk.on("connected")
    def blynk_connected(ping):
        print("Blynk ready. Ping:", ping, "ms")

    @blynk.on("disconnected")
    def blynk_disconnected():
        print("Blynk disconnected")

    return blynk


def setup():
    i2c = SoftI2C(scl=Pin(SCL_PIN), sda=Pin(SDA_PIN))
    oled = SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c)

    adc = ADC(Pin(ADC_PIN))
    adc.width(ADC.WIDTH_9BIT)
    adc.atten(ADC.ATTN_11DB)
    return oled, adc


def main():
    connect_to_wifi()
    blynk = blynk_setup()
    oled, adc = setup()

    while True:
        resistance = adc.read()
        moisture_value = (511 - resistance) * 100 // 511

        oled.fill(0)
        oled.text("Moisture Value: ", 0, 0)
        oled.text(str(moisture_value) + " %", 0, 16)
        oled.text(str(resistance) + " Ohm", 0, 32)
        oled.show()

        blynk.run()
        blynk.virtual_write(0, str(moisture_value))

        utime.sleep(1)


if __name__ == "__main__":
    main()
