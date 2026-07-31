from machine import Pin, SoftI2C, PWM
from ssd1306 import SSD1306_I2C
from hcsr04 import HCSR04
import utime

# Constants
OLED_WIDTH = 128
OLED_HEIGHT = 64
ALARM_DISTANCE = 10
BUZZER_FREQ = 440
BUZZER_DUTY = 512
DISPLAY_UPDATE_INTERVAL = 25  # milliseconds

# Pins
I2C_SCL_PIN = 22
I2C_SDA_PIN = 21
TRIGGER_PIN = 5
ECHO_PIN = 18
BUZZER_PIN = 16

# oled
i2c = SoftI2C(scl=Pin(I2C_SCL_PIN), sda=Pin(I2C_SDA_PIN))
oled = SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c)

# sonar
sonar = HCSR04(trigger_pin=TRIGGER_PIN, echo_pin=ECHO_PIN)

# buzzer
buzzer = PWM(Pin(BUZZER_PIN, Pin.OUT), freq=BUZZER_FREQ, duty=0)


def display_distance(distance):
    oled.fill(0)
    oled.text("Distance: ", 0, 0)
    if 2 <= distance <= 400:
        oled.text(str(distance) + " cm", 0, 16)
        if distance <= ALARM_DISTANCE:
            oled.text("!!! ALARM !!!", 0, 32)
            buzzer.duty(BUZZER_DUTY)
        else:
            oled.text("No alarm", 0, 32)
            buzzer.duty(0)
    else:
        oled.text("Out of range", 0, 16)
    oled.show()


def main():
    while True:
        try:
            distance = sonar.distance_cm()
            display_distance(distance)
            utime.sleep_ms(DISPLAY_UPDATE_INTERVAL)

        except Exception as e:
            print("Error:", e)


if __name__ == "__main__":
    main()
