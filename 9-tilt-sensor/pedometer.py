from machine import Pin, SoftI2C, PWM
from ssd1306 import SSD1306_I2C
import utime

# Constants
OLED_WIDTH = 128
OLED_HEIGHT = 64
BUZZER_FREQ = 392
BUZZER_DUTY = 512
SWITCH_DEBOUNCE_TIME = 50  # milliseconds

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
    buzzer = PWM(Pin(BUZZER_PIN, Pin.OUT), freq=BUZZER_FREQ, duty=0)

    return sw520d, oled, buzzer


def display_steps(oled, count):
    oled.fill(0)
    oled.text("Count:", 0, 0)
    oled.text(str(count) + " step(s)", 0, 16)
    oled.show()


def debounce(sw520d):
    current_state = sw520d.value()
    if current_state == 1:
        utime.sleep_ms(SWITCH_DEBOUNCE_TIME)
        return current_state == sw520d.value()
    else:
        return False


def main():
    count = 0
    sw520d, oled, buzzer = setup()

    while True:
        display_steps(oled, count)
        if debounce(sw520d):
            count += 1
            buzzer.duty(BUZZER_DUTY)
            utime.sleep_ms(50)
            buzzer.duty(0)

        utime.sleep_ms(100)


if __name__ == "__main__":
    main()
