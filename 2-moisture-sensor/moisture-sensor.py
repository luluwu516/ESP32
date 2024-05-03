import utime
from ssd1306 import SSD1306_I2C
from machine import Pin, ADC, SoftI2C

# Constants
OLED_WIDTH = 128
OLED_HEIGHT = 64

# Pin
I2C_SCL_PIN = 22
I2C_SDA_PIN = 21
SENSOR_PIN = 36

# oled
i2c = SoftI2C(scl=Pin(I2C_SCL_PIN), sda=Pin(I2C_SDA_PIN))
oled = SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c)

# sensor
adc = ADC(Pin(SENSOR_PIN))
adc.width(ADC.WIDTH_9BIT)
adc.atten(ADC.ATTN_11DB)


def read_moisture():
    resistance = adc.read()
    moisture_value = (511 - resistance) * 100 // 511
    return moisture_value, resistance


def display_moisture(moisture_value, resistance):
    oled.fill(0)
    oled.text("Moisture Value:", 0, 0)
    oled.text(str(moisture_value) + " %", 0, 16)
    oled.text(str(resistance) + " Ohm", 0, 32)
    oled.show()


def main():
    while True:
        moisture_value, resistance = read_moisture()
        display_moisture(moisture_value, resistance)
        utime.sleep_ms(100)


if __name__ == "__main__":
    main()
