from machine import Pin, SoftI2C
from ssd1306 import SSD1306_I2C
import utime

# Constants
OLED_WIDTH = 128
OLED_HEIGHT = 64

# Pin
I2C_SCL_PIN = 22
I2C_SDA_PIN = 21


def setup():
    try:
        # oled
        i2c = SoftI2C(scl=Pin(I2C_SCL_PIN), sda=Pin(I2C_SDA_PIN))
        oled = SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c)
        return oled
    except Exception as e:
        print("Error initializing OLED:", e)
        return None


def display_time(oled):
    try:
        local_time = utime.localtime()
        oled.fill(0)
        oled.text("Local time: ", 0, 0)
        oled.text("{}/{}/{}".format(local_time[0], local_time[1], local_time[2]), 0, 16)
        oled.text("{}:{}:{}".format(local_time[3], local_time[4], local_time[5]), 0, 32)
        oled.show()
    except Exception as e:
        print("Error displaying time on OLED:", e)


def main():
    oled = setup()
    if oled:
        while True:
            display_time(oled)
            utime.sleep_ms(100)


if __name__ == "__main__":
    main()
