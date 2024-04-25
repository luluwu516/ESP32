import bh1750
from machine import Pin, PWM, SoftI2C
from ssd1306 import SSD1306_I2C

# Pin Definitions
SCL_PIN = 22
SDA_PIN = 21
BUZZER_PIN = 16

# OLED Display Dimensions
OLEDC_WIDTH = 128
OLEDC_HEIGHT = 64

# Light Level Thresholds
LOW_LIGHT_THRESHOLD = 30
HIGH_LIGHT_THRESHOLD = 300


def setup():
    # Initialize I2C
    i2c = SoftI2C(scl=Pin(SCL_PIN), sda=Pin(SDA_PIN))

    # Initialize OLED Display
    oled = SSD1306_I2C(OLEDC_WIDTH, OLEDC_HEIGHT, i2c)

    # Initialize Buzzer
    buzzer = PWM(Pin(BUZZER_PIN, Pin.OUT), freq=110, duty=0)

    return i2c, oled, buzzer


def main():
    i2c, oled, buzzer = setup()

    while True:
        light_level = bh1750.sample(i2c, mode=0x23)

        oled.fill(0)
        oled.text("Light level: ", 0, 0)
        oled.text(str(light_level) + " lux", 0, 16)

        if LOW_LIGHT_THRESHOLD < light_level < HIGH_LIGHT_THRESHOLD:
            oled.text("!! WARNING !!", 0, 32)
            oled.text("IT'S TOO DARK ", 0, 48)
            buzzer.duty(512)
        else:
            buzzer.duty(0)

        oled.show()


if __name__ == "__main__":
    main()
