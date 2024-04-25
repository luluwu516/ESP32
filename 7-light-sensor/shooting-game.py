import bh1750, utime
from machine import Pin, PWM, SoftI2C
from ssd1306 import SSD1306_I2C

score = 0

# i2c
i2c = SoftI2C(scl=Pin(22), sda=Pin(21))

# oled
oled_width = 128
oled_height = 64
oled = SSD1306_I2C(oled_width, oled_height, i2c)

# buzzer
buzzer = PWM(Pin(16, Pin.OUT), freq=110, duty=0)

while score < 10:
    light_level = bh1750.sample(i2c, mode=0x23)
    
    oled.fill(0)
    
    if light_level > 1000:
        oled.text("!! HIT !!", 0, 32)
        oled.text("One point", 0, 48)
        score += 1
        
        buzzer.freq(784)
        buzzer.duty(512)
        utime.sleep_ms(100)
        buzzer.freq(988)
        utime.sleep_ms(300)
        buzzer.duty(0)
        
    oled.text("Score: " + str(score), 0, 0)
    oled.show()
    
    utime.sleep_ms(10)

oled.fill(0)
oled.text("Score: " + str(score), 0, 0)
oled.text("YOU WIN!", 0, 32)

buzzer.freq(784)
buzzer.duty(512)
utime.sleep_ms(100)
buzzer.freq(659)
utime.sleep_ms(100)
buzzer.duty(523)
utime.sleep_ms(300)
buzzer.duty(0)

