from machine import Pin, SoftI2C
from ssd1306 import SSD1306_I2C
import utime

i2c = SoftI2C(scl=Pin(22), sda=Pin(21))

oled_width = 128
oled_height = 64
oled = SSD1306_I2C(oled_width, oled_height, i2c)

oled.text("Hello, world!", 0, 0)
oled.show()

