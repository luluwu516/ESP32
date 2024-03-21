from machine import Pin, SoftI2C
from ssd1306 import SSD1306_I2C
from hcsr04 import HCSR04
import utime

# oled
i2c = SoftI2C(scl=Pin(22), sda=Pin(21))
oled_width = 128
oled_height = 64
oled = SSD1306_I2C(oled_width, oled_height, i2c)

# sonar
sonar = HCSR04(trigger_pin=5, echo_pin=18, echo_timeout_us=10000)


while True:
    distance = sonar.distance_cm()
    oled.fill(0)
    oled.text("Distance: ", 0, 0)
    if distance > 400 or distance < 2:
        oled.text("Out of range!", 0, 16)
    else:
        oled.text(str(distance) + " cm", 0, 16)
    oled.show()
    
    utime.sleep_ms(25)
    