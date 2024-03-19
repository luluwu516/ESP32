import network, urequests, utime
from ssd1306 import SSD1306_I2C
from machine import Pin, ADC, SoftI2C

# OLED
i2c = SoftI2C(scl=Pin(22), sda=Pin(21))
oled_width = 128
oled_height = 64
oled = SSD1306_I2C(oled_width, oled_height, i2c)


# Sensor
adc_pin = Pin(36)          # VP pin
adc = ADC(adc_pin)         # set input
adc.width(ADC.WIDTH_9BIT)  # set resolutions
adc.atten(ADC.ATTN_11DB)   # set attenuation

    
# Network
ssid = "REPLACE_WITH_YOUR_SSID"
pw = "REPLACE_WITH_YOUR_PASSWORD"
key = "REPLACE_WITH_YOUR_KEY"
url = "https://maker.ifttt.com.com/trigger/YOUR_EVENT_NAME/with/key/" + key

print("Connecting to WiFi " + ssid + "...")
sta = network.WLAN(network.STA_IF)
sta.active(True)
sta.connect(ssid, pw)

while not sta.isconnected():  # check connection
    pass

print("Connected.")

while True:
    gsr = adc.read()
    
    if gsr > 200:
        response = urequests.get(url)
        if response.status_code == 200:
            print("IFTTT Success: Sending messages on Line")
        else:
            print("IFTTT Failed")
        utime.sleep(5)
    
    oled.fill(0)
    oled.text("Resistance: ", 0, 0)
    oled.text(str(gsr) + " Ohm", 0, 16)
    oled.show()
    
    utime.sleep_ms(100)
