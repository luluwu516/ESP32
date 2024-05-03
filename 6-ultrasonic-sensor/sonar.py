from machine import Pin, SoftI2C
from ssd1306 import SSD1306_I2C
from hcsr04 import HCSR04
import utime

# Constants
OLED_WIDTH = 128
OLED_HEIGHT = 64
ECHO_TIMEOUT_US = 10000

# Pins
SCL_PIN = 22
SDA_PIN = 21
TRIGGER_PIN = 5
ECHO_PIN = 18

# oled
i2c = SoftI2C(scl=Pin(SCL_PIN), sda=Pin(SDA_PIN))
oled = SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c)

# sonar
sonar = HCSR04(
    trigger_pin=TRIGGER_PIN, echo_pin=ECHO_PIN, echo_timeout_us=ECHO_TIMEOUT_US
)


def update_display(distance):
    oled.fill(0)
    oled.text("Distance: ", 0, 0)
    if 2 <= distance <= 400:
        oled.text(str(distance) + " cm", 0, 16)
    else:
        oled.text("Out of range!", 0, 16)
    oled.show()


def main():
    while True:
        try:
            distance = sonar.distance_cm()
            update_display(distance)
        except Exception as e:
            print("Error:", e)  # Handle the exception gracefully
        utime.sleep_ms(25)


if __name__ == "__main__":
    main()
