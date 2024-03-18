from machine import Pin, SoftI2C
from ssd1306 import SSD1306_I2C
import utime

i2c = SoftI2C(scl=Pin(22), sda=Pin(21))

oled_width = 128
oled_height = 64
oled = SSD1306_I2C(oled_width, oled_height, i2c)

while True:
    # utime.localtime() return an 8-tuple
    # (year, month, mday, hour, minute, second, weekday, yearday)
    local_time = utime.localtime()
    oled.fill(0)
    oled.text("Local time: ", 0, 0)
    oled.text(f"{local_time[0]}/{local_time[1]}/{local_time[2]}", 0, 16)
    oled.text(f"{local_time[3]}:{local_time[4]}:{local_time[5]}", 0, 32)
    oled.show()
    
    utime.sleep_ms(100)

