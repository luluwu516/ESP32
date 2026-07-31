import utime
from ssd1306 import SSD1306_I2C
from machine import Pin, ADC, SoftI2C

# pump
pump = Pin(26)
pump.value(0)

# OLED
i2c = SoftI2C(scl=Pin(22), sda=Pin(21))
oled_width = 128
oled_height = 64
oled = SSD1306_I2C(oled_width, oled_height, i2c)

# Sensor
adc_pin = Pin(36)  # VP pin
adc = ADC(adc_pin)  # set input
adc.width(ADC.WIDTH_9BIT)  # set resolutions
adc.atten(ADC.ATTN_11DB)  # set attenuation

while True:
    gsr = adc.read()
    oled.fill(0)
    oled.text("Resistance: ", 0, 0)
    oled.text(str(gsr) + " Ohm", 0, 16)
    oled.show()

    if gsr > 200:
        pump.value(1)
        utime.sleep(2)
        pump.value(0)

    utime.sleep_ms(100)
