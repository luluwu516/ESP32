import bh1750
from machine import Pin, SoftI2C
from ssd1306 import SSD1306_I2C

# i2c
i2c = SoftI2C(scl=Pin(22), sda=Pin(21))

# oled
oled_width = 128
oled_height = 64
oled = SSD1306_I2C(oled_width, oled_height, i2c)

while True:
    light_level = bh1750.sample(i2c, mode=0x23)
    
    oled.fill(0)
    oled.text("Light level: ", 0, 0)
    oled.text(str(light_level) + " lux", 0, 16)
    oled.show()