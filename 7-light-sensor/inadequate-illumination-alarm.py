import bh1750
from machine import Pin, PWM, SoftI2C
from ssd1306 import SSD1306_I2C

# i2c
i2c = SoftI2C(scl=Pin(22), sda=Pin(21))

# oled
oled_width = 128
oled_height = 64
oled = SSD1306_I2C(oled_width, oled_height, i2c)

# buzzer
buzzer = PWM(Pin(16, Pin.OUT), freq=110, duty=0)

while True:
    light_level = bh1750.sample(i2c, mode=0x23)
    
    oled.fill(0)
    oled.text("Light level: ", 0, 0)
    oled.text(str(light_level) + " lux", 0, 16)
    
    if 30 < light_level < 300: # it should not buzz if we turn off the light
        oled.text("!! WARNING !!", 0, 32)
        oled.text("IT'S TOO DARK: ", 0, 48)
        buzzer.duty(512)
    else:
        buzzer.duty(0)
    
    oled.show()
