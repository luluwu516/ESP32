from machine import Pin, SoftI2C, PWM
from ssd1306 import SSD1306_I2C
from hcsr04 import HCSR04
import utime

# Constants
OLED_WIDTH = 128
OLED_HEIGHT = 64
NOTE_MIN = 220  # Lowest frequency
NOTE_MAX = 880  # Highest frequency
DIST_MIN = 40  # Minimum distance


# Pins
TRIGGER_PIN = 5  # Sonar trigger pin
ECHO_PIN = 18  # Sonar echo pin
BUZZER_PIN = 16
I2C_SCL_PIN = 22
I2C_SDA_PIN = 21


# oled
i2c = SoftI2C(scl=Pin(I2C_SCL_PIN), sda=Pin(I2C_SDA_PIN))
oled = SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c)

# sonar
sonar = HCSR04(trigger_pin=TRIGGER_PIN, echo_pin=ECHO_PIN)

# buzzer
buzzer = PWM(Pin(BUZZER_PIN, Pin.OUT), freq=40, duty=0)  # Lowest freq: 40


def update_display(distance, key):
    oled.fill(0)
    oled.text("Distance: ", 0, 0)
    if 2 <= distance <= 400:
        oled.text(str(distance) + " mm", 0, 16)
        oled.text("Note: ", 0, 32)
        oled.text(str(key) + " Hz", 0, 48)
    else:
        oled.text("Out of range", 0, 16)
    oled.show()


def map_distance_to_frequency(distance):
    if DIST_MIN <= distance <= DIST_MIN + (NOTE_MAX - NOTE_MIN):
        return NOTE_MIN + (distance - DIST_MIN)
    else:
        return 0


def main():
    while True:
        distance = sonar.distance_mm()
        key = map_distance_to_frequency(distance)
        if key:
            buzzer.freq(key)
            buzzer.duty(512)
        else:
            buzzer.duty(0)
        update_display(distance, key)
        utime.sleep_ms(10)


if __name__ == "__main__":
    main()
