from machine import Pin, SoftI2C
from ssd1306 import SSD1306_I2C

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


def display_message(oled, message, x=0, y=0):
    try:
        oled.text(message, x, y)
        oled.show()

    except Exception as e:
        print("Error displaying message on OLED:", e)


def main():
    oled = setup()
    if oled:
        display_message(oled, "Hello, world!")


if __name__ == "__main__":
    main()
