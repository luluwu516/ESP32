from machine import Pin, SoftI2C, PWM
from ssd1306 import SSD1306_I2C
from hcsr04 import HCSR04
import utime

# Constants
OLED_WIDTH = 128
OLED_HEIGHT = 64
ALARM_DISTANCE = 50
INITIAL_FREQ = 784
INITIAL_DELAY = 500

# Pins
SCL_PIN = 22
SDA_PIN = 21
TRIGGER_PIN = 5
ECHO_PIN = 18
BUZZER_PIN = 16

# oled
i2c = SoftI2C(scl=Pin(SCL_PIN), sda=Pin(SDA_PIN))
oled = SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c)

# sonar
sonar = HCSR04(trigger_pin=TRIGGER_PIN, echo_pin=ECHO_PIN)

# buzzer
buzzer = PWM(Pin(BUZZER_PIN, Pin.OUT), freq=INITIAL_FREQ, duty=0)


def update_display(distance):
    oled.fill(0)
    oled.text("Distance: ", 0, 0)
    if 2 <= distance <= 400:
        oled.text(str(distance) + " cm", 0, 16)
    else:
        oled.text("Out of range", 0, 16)
    oled.show()


def main():
    sound_delay = INITIAL_DELAY
    while True:
        try:
            distance = sonar.distance_cm()
            update_display(distance)
            if distance <= ALARM_DISTANCE:
                buzzer.duty(512)
                utime.sleep_ms(10)
                buzzer.duty(0)
                sound_delay = int(distance) * 10
            else:
                sound_delay = INITIAL_DELAY
            utime.sleep_ms(sound_delay)
        except Exception as e:
            print("Error:", e)


if __name__ == "__main__":
    main()
