import utime
from ssd1306 import SSD1306_I2C
from machine import Pin, ADC, SoftI2C

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
    resistance = adc.read()
    moisture_value = (511 - resistance) * 100 // 511
    oled.fill(0)
    oled.text("Moisture Value: ", 0, 0)
    oled.text(str(moisture_value) + " %", 0, 16)
    oled.text(str(resistance) + " Ohm", 0, 32)

    utime.sleep_ms(100)
