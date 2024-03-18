from machine import Pin, SoftI2C
from ssd1306 import SSD1306_I2C
import utime

i2c = SoftI2C(scl=Pin(22), sda=Pin(21))

oled_width = 128
oled_height = 64
oled = SSD1306_I2C(oled_width, oled_height, i2c)

while True:
    system_time = utime.ticks_ms()
    oled.fill(0)
    oled.text("System time: ", 0, 0)
    oled.text(str(system_time), 0, 20)
    oled.show()

