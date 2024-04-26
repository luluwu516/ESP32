import bh1750
import utime
from machine import Pin, PWM, SoftI2C
from ssd1306 import SSD1306_I2C

# Constants
LIGHT_THRESHOLD = 10000
SCORE_LIMIT = 10
BUZZER_PIN = 16
SCL_PIN = 22
SDA_PIN = 21
OLEDC_WIDTH = 128
OLEDC_HEIGHT = 64
BUZZER_FREQ_HIT = 784
BUZZER_FREQ_WIN = 659
BUZZER_FREQ_LOSE = 523
BUZZER_DUTY_CYCLE = 512
HIT_DELAY = 100
WIN_DELAY = 100
LOSE_DELAY = 300
LOOP_DELAY = 10


def setup():
    # Initialize I2C
    i2c = SoftI2C(scl=Pin(SCL_PIN), sda=Pin(SDA_PIN))

    # Initialize OLED Display
    oled = SSD1306_I2C(OLEDC_WIDTH, OLEDC_HEIGHT, i2c)
    return i2c, oled


def hit_buzzer(buzzer, frequency, duty_cycle, duration):
    buzzer.freq(frequency)
    buzzer.duty(duty_cycle)
    utime.sleep_ms(duration)
    buzzer.duty(0)


def main():
    # Initialize buzzer
    buzzer = PWM(Pin(BUZZER_PIN, Pin.OUT), freq=BUZZER_FREQ_HIT, duty=0)

    # Setup I2C and OLED
    i2c, oled = setup()

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
