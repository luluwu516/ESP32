import bh1750
import utime
from machine import Pin, PWM, SoftI2C
from ssd1306 import SSD1306_I2C

# Constants
LIGHT_THRESHOLD = 10000
SCORE_LIMIT = 10
OLED_WIDTH = 128
OLED_HEIGHT = 64
BUZZER_FREQ_HIT = 784
BUZZER_FREQ_WIN = 659
BUZZER_FREQ_LOSE = 523
BUZZER_DUTY_CYCLE = 512
HIT_DELAY = 100
WIN_DELAY = 100
LOSE_DELAY = 300
LOOP_DELAY = 10

# Pins
BUZZER_PIN = 16
SCL_PIN = 22
SDA_PIN = 21


def setup():
    i2c = SoftI2C(scl=Pin(SCL_PIN), sda=Pin(SDA_PIN))
    oled = SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c)
    buzzer = PWM(Pin(BUZZER_PIN, Pin.OUT), freq=BUZZER_FREQ_HIT, duty=0)

    return i2c, oled, buzzer


def hit_buzzer(buzzer, frequency, duty_cycle, duration):
    buzzer.freq(frequency)
    buzzer.duty(duty_cycle)
    utime.sleep_ms(duration)
    buzzer.duty(0)


def main():
    # setup
    i2c, oled, buzzer = setup()

    # Game loop
    score = 0
    while score < SCORE_LIMIT:
        light_level = bh1750.sample(i2c, mode=0x23)

        oled.fill(0)
        oled.text("Score: " + str(score), 0, 0)

        if light_level > LIGHT_THRESHOLD:
            score += 1
            oled.text("!! HIT !!", 0, 32)
            oled.text("One point", 0, 48)
            oled.show()

            hit_buzzer(buzzer, BUZZER_FREQ_HIT, BUZZER_DUTY_CYCLE, HIT_DELAY)

        oled.show()

        utime.sleep_ms(LOOP_DELAY)

    # Game over
    oled.fill(0)
    oled.text("Score: " + str(score), 0, 0)
    oled.text("YOU WIN!", 0, 32)
    oled.show()

    # Win sound
    hit_buzzer(buzzer, BUZZER_FREQ_WIN, BUZZER_DUTY_CYCLE, WIN_DELAY)
    utime.sleep_ms(LOSE_DELAY)  # Pause for effect


if __name__ == "__main__":
    main()
