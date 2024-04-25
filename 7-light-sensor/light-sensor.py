import bh1750
from machine import Pin, SoftI2C
from ssd1306 import SSD1306_I2C

# Pin Definitions
SCL_PIN = 22
SDA_PIN = 21

# OLED Display Dimensions
OLEDC_WIDTH = 128
OLEDC_HEIGHT = 64


def setup():
    # Initialize I2C
    try:
        i2c = SoftI2C(scl=Pin(SCL_PIN), sda=Pin(SDA_PIN))
    except Exception as e:
        print("Error initializing I2C:", e)
        return None

    # Initialize OLED Display
    oled = SSD1306_I2C(OLEDC_WIDTH, OLEDC_HEIGHT, i2c)
    return i2c, oled


def main():
    # Setup I2C and OLED
    i2c_oled = setup()
    if not i2c_oled:
        return

    i2c, oled = i2c_oled

    # Main loop
    while True:
        try:
            light_level = bh1750.sample(i2c, mode=0x23)
        except Exception as e:
            print("Error reading light level:", e)
            continue

        oled.fill(0)
        oled.text("Light level: ", 0, 0)
        oled.text(str(light_level) + " lux", 0, 16)
        oled.show()


if __name__ == "__main__":
    main()
