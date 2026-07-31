from machine import Pin, SoftI2C, PWM
from ssd1306 import SSD1306_I2C
import utime

# Constants
OLED_WIDTH = 128
OLED_HEIGHT = 64

# Pins
SW520D_PIN = 17
BUZZER_PIN = 16
I2C_SCL_PIN = 22
I2C_SDA_PIN = 21


def setup():
    # tilt sensor
    sw520d = Pin(SW520D_PIN, Pin.IN, Pin.PULL_UP)

    # oled
    i2c = SoftI2C(scl=Pin(I2C_SCL_PIN), sda=Pin(I2C_SDA_PIN))
    oled = SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c)

    # buzzer
    buzzer = PWM(Pin(BUZZER_PIN, Pin.OUT), freq=880, duty=0)

    return sw520d, oled, buzzer


def display_shake_status(oled, sw520d, buzzer):
    oled.fill(0)
    oled.text("Shake status:", 0, 0)
    if sw520d.value() == 1:
        buzzer.duty(512)
        oled.text("!!! TIPPED !!!", 0, 16)
    else:
        buzzer.duty(0)
        oled.text("- Standby -", 0, 16)
    oled.show()


def main():
    sw520d, oled, buzzer = setup()

    while True:
        display_shake_status(oled, sw520d, buzzer)
        utime.sleep_ms(100)


if __name__ == "__main__":
    main()
