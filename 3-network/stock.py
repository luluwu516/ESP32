from wifi import *
import network, urequests
from machine import Pin, SoftI2C
from ssd1306 import SSD1306_I2C


# Constants
OLED_WIDTH = 128
OLED_HEIGHT = 64
SSID = REPLACE_WITH_YOUR_SSID
PASSWORD = REPLACE_WITH_YOUR_PASSWORD
API_ACCESS_KEY = REPLACE_WITH_YOUR_STOCK_API_ACCESS_KEY

STOCK_NAME = "TSM"
API_URL = "http://api.marketstack.com/v1/eod?access_key={}&limit=1&symbols={}".format(
    API_ACCESS_KEY, STOCK_NAME
)


# Pins
I2C_SCL_PIN = 22
I2C_SDA_PIN = 21


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


def display_info(oled, name, price, trade_time):
    oled.fill(0)
    oled.text("Stock: {}".format(name), 0, 0)
    oled.text("Price: ${}".format(price), 0, 16)
    oled.text("Last Trade Time:", 0, 32)
    oled.text(trade_time[:10], 0, 48)  # 2024-05-03T00:00:00+0000 is too long
    oled.show()


def get_stock_data(api_url):
    try:
        response = urequests.get(api_url)
        if response.status_code == 200:
            print("\nJSON data query successful.")
            parsed_data = response.json()
            if "data" in parsed_data and parsed_data["data"]:
                stock = parsed_data["data"][0]
                name = stock.get("symbol", "")
                price = "{:.2f}".format(stock.get("close", 0))
                trade_time = stock.get("date", "")
                print("\nJSON:", stock, sep="\n")
                return name, price, trade_time
            else:
                print("No data found for the stock.")
        else:
            print("Failed to fetch data. Status code:", response.status_code)
    except Exception as e:
        print("Error:", e)
    return None, None, None


def main():
    try:
        oled = setup()
        connect_wifi(SSID, PASSWORD)
        name, price, trade_time = get_stock_data(API_URL)
        if name and price and trade_time:
            display_info(oled, name, price, trade_time)
    except Exception as e:
        print("An error occurred:", e)


if __name__ == "__main__":
    main()
