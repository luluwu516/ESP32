from wifi import *
from machine import Pin, SoftI2C, RTC
from ssd1306 import SSD1306_I2C
import network
import urequests
import utime

# Constants
OLED_WIDTH = 128
OLED_HEIGHT = 64
SSID = REPLACE_WITH_YOUR_SSID
PASSWORD = REPLACE_WITH_YOUR_PASSWORD
API_ACCESS_KEY = REPLACE_WITH_YOUR_STOCK_API_ACCESS_KEY

API_URL = "http://worldtimeapi.org/api/timezone/America/Los_Angeles"
WEB_QUERY_DELAY = 600000

WEEKDAY_NAMES = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]

# Pins
I2C_SCL_PIN = 22
I2C_SDA_PIN = 21

# RTC: Real Time Clock
rtc = RTC()


def setup():
    i2c = SoftI2C(scl=Pin(I2C_SCL_PIN), sda=Pin(I2C_SDA_PIN))
    oled = SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c)
    return oled


def connect_wifi(ssid, password):
    print("Connecting to WiFi " + SSID + "...")
    wifi = network.WLAN(network.STA_IF)
    wifi.active(True)
    wifi.connect(ssid, password)
    while not wifi.isconnected():
        pass
    print("Connected to WiFi:", wifi.ifconfig())
    return wifi


def update_rtc_from_api():
    response = urequests.get(API_URL)
    if response.status_code == 200:
        print("\nJSON data query successful.")
        data = response.json()
        time_str = data["datetime"]
        year, month, day = map(int, time_str.split("T")[0].split("-"))
        time_str = data["datetime"].split("T")[1].split(".")[0]
        hour, minute, second = map(int, time_str.split(":"))
        weekday = data["day_of_week"] - 1
        rtc.datetime((year, month, day, weekday, hour, minute, second, 0))
        print("RTC updated successfully.")
    else:
        print("Failed to update RTC from API.")


def display_info(oled, weekday, date, time):
    oled.fill(0)
    oled.text("Day: {}".format(weekday), 0, 0)
    oled.text("Date: {}".format(date), 0, 16)
    oled.text("Time: {}".format(time), 0, 32)
    oled.show()


def main():
    oled = setup()
    connect_wifi(SSID, PASSWORD)
    update_time = utime.ticks_ms() - WEB_QUERY_DELAY

    while True:
        current_time = utime.ticks_ms()
        if current_time - update_time >= WEB_QUERY_DELAY:
            update_rtc_from_api()
            update_time = current_time

        rtc_time = rtc.datetime()
        weekday = WEEKDAY_NAMES[rtc_time[3]]
        date_str = "{:02}/{:02}/{:4}".format(rtc_time[1], rtc_time[2], rtc_time[0])
        time_str = "{:02}:{:02}:{:02}".format(rtc_time[4], rtc_time[5], rtc_time[6])
        display_info(oled, weekday, date_str, time_str)
        utime.sleep(1)


if __name__ == "__main__":
    main()
