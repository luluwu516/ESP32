from machine import Pin, SoftI2C, PWM
from ssd1306 import SSD1306_I2C
from hcsr04 import HCSR04
import utime

alarm_distance = 10

# oled
i2c = SoftI2C(scl=Pin(22), sda=Pin(21))
oled_width = 128
oled_height = 64
oled = SSD1306_I2C(oled_width, oled_height, i2c)

# sonar
sonar = HCSR04(trigger_pin=5, echo_pin=18)

# buzzer
buzzer = PWM(Pin(16, Pin.OUT), freq=440, duty=0)


while True:
    distance = sonar.distance_cm()
    oled.fill(0)
    oled.text("Distance: ", 0, 0)
    if 2 <= distance <= 400:
        oled.text(str(distance) + " cm", 0, 16)
        if distance <= alarm_distance:
            oled.text("!!! ALARM !!!", 0, 32)
            buzzer.duty(512)
        else:
            oled.text("No alarm", 0, 32)
            buzzer.duty(0)
    else:
        oled.text("Out of range", 0, 16)
    
    oled.show()
    
    utime.sleep_ms(25)
    
