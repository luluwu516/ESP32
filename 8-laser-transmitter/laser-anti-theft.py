import bh1750
import utime
from machine import Pin, PWM, SoftI2C
from ssd1306 import SSD1306_I2C

# Constants
OLED_WIDTH = 128
OLED_HEIGHT = 64
LIGHT_THRESHOLD = 10000
WATCH_INTERVAL = 1

# Pins
BUZZER_PIN = 16
SCL_PIN = 22
SDA_PIN = 21


def setup():
    i2c = SoftI2C(scl=Pin(SCL_PIN), sda=Pin(SDA_PIN))
    oled = SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c)

    return i2c, oled


def turn_on_buzzer(buzzer, level):
    if level < LIGHT_THRESHOLD:
        buzzer.duty(512)
    else:
        buzzer.duty(0)


def main():
    # buzzer
    buzzer = PWM(Pin(BUZZER_PIN, Pin.OUT), freq=110, duty=0)

    i2c, oled = setup()

    count = 0
    while count < 5:
        light_level = bh1750.sample(i2c, mode=0x23)

        oled.fill(0)
        oled.text("Setting...", 0, 0)

        if light_level > LIGHT_THRESHOLD:
            count += 1
            oled.text(str(count) + " second(s)", 0, 16)
        else:
            count = 0

        oled.show()
        utime.sleep(WATCH_INTERVAL)

    oled.fill(0)
    oled.text("Device on!", 0, 0)
    oled.show()
    utime.sleep(2)

    # The anti-theft is on
    while True:
        light_level = bh1750.sample(i2c, mode=0x23)

        oled.fill(0)
        oled.text("Watching...", 0, 0)

        turn_on_buzzer(buzzer, light_level)

        if light_level < LIGHT_THRESHOLD:
            oled.fill(0)
            oled.text("!! WARNING !!", 0, 0)
            oled.text("!! WARNING !!", 0, 16)
            oled.text("!! WARNING !!", 0, 32)
            oled.show()
            utime.sleep(1)

        else:
            oled.show()

        utime.sleep(WATCH_INTERVAL)


if __name__ == "__main__":
    main()
