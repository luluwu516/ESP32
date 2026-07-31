import bh1750
from machine import Pin, SoftI2C
from ssd1306 import SSD1306_I2C

# Constants
OLED_WIDTH = 128
OLED_HEIGHT = 64
LOW_LIGHT_THRESHOLD = 30
HIGH_LIGHT_THRESHOLD = 300

# Pin Definitions
SCL_PIN = 22
SDA_PIN = 21
BUZZER_PIN = 16


def setup():
    i2c = SoftI2C(scl=Pin(SCL_PIN), sda=Pin(SDA_PIN))
    oled = SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c)

    return i2c, oled


def main():
    i2c, oled = setup()

    while True:
        try:
            light_level = bh1750.sample(i2c, mode=0x23)
        except Exception as e:
            print("Error reading light level:", e)
            continue

        oled.fill(0)
        oled.text("Light level: ", 0, 0)
        oled.text(str(light_level) + " lux", 0, 16)
        oled.show()


if __name__ == "__main__":
    main()
