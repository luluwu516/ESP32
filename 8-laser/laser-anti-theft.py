import bh1750
from machine import Pin, PWM, SoftI2C
from ssd1306 import SSD1306_I2C

count = 0

# i2c
i2c = SoftI2C(scl=Pin(22), sda=Pin(21))

# oled
oled_width = 128
oled_height = 64
oled = SSD1306_I2C(oled_width, oled_height, i2c)

# buzzer
buzzer = PWM(Pin(16, Pin.OUT), freq=110, duty=0)

# Turn on the anti-theft laser
while count < 5:
    light_level = bh1750.sample(i2c, mode=0x23)
    
    oled.fill(0)
    oled.text("Setting...", 0, 0)
    
    if light_level > 10000:
        count += 1
        oled.text(str(count) + " second(s)", 0, 16)
        buzzer.duty(512)
    else:
        count = 0
    
    oled.show()
    utime.sleep(1)
    

# The anti-theft is on
while True:
    light_level = bh1750.sample(i2c, mode=0x23)
    
    oled.fill(0)
    oled.text("Watching...", 0, 0)
    
    if light_level < 10000:
        buzzer.duty(512)
        oled.fill(0)
        oled.text("!! WARNING !!", 0, 0)
        oled.text("!! WARNING !!", 0, 16)
        oled.text("!! WARNING !!", 0, 32)
        utime.sleep(1)
        
    else:
        buzzer.duty(0)


