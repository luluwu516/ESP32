from machine import Pin, SoftI2C, PWM
from ssd1306 import SSD1306_I2C
from hcsr04 import HCSR04
import utime

note_min = 220  # lowest frequency
note_max = 880  # highest frequency
dist_min = 40   # set the minimum distance 
dist_max = dist_min + note_max - note_min  # 660 mm

# oled
i2c = SoftI2C(scl=Pin(22), sda=Pin(21))
oled_width = 128
oled_height = 64
oled = SSD1306_I2C(oled_width, oled_height, i2c)

# sonar
sonar = HCSR04(trigger_pin=5, echo_pin=18)

# buzzer
buzzer = PWM(Pin(16, Pin.OUT), freq=40, duty=0)  # the lowest freq 40

while True:
    distance = sonar.distance_mm()
    if dist_min <= distance <= dist_max:
        key = note_min + (distance - dist_min)
        buzzer.freq(key)
        buzzer.duty(512)
    else:
        key = 0
        buzzer.duty(0)
    
    oled.fill(0)
    oled.text("Distance: ", 0, 0)
    if 2 <= distance <= 400:
        oled.text(str(distance) + " mm", 0, 16)
        oled.text("Note: ", 0, 32)
        oled.text(str(key) + " Hz", 0, 48)
    else:
        oled.text("Out of range", 0, 16)
    
    oled.show()
    
    utime.sleep_ms(10)