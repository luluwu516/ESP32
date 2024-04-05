import BlynkLib, utime, network
from ssd1306 import SSD1306_I2C
from machine import Pin, ADC, SoftI2C

WIFI_SSID = "REPLACE_WITH_YOUR_SSID"
WIFI_PASS = "REPLACE_WITH_YOUR_PASSWORD"

BLYNK_AUTH = "REPLACE_WITH_YOUR_AUTH_TOKEN"

OLED_WIDTH = 128
OLED_HEIGHT = 64

# network
wifi = network.WLAN(network.STA_IF)

if not wifi.isconnected():
    print("Connecting to WiFi...")
    wifi.active(True)
    wifi.connect(WIFI_SSID, WIFI_PASS)
    while not wifi.isconnected():
        pass

print('IP:', wifi.ifconfig()[0])

# Blynk
blynk = BlynkLib.Blynk(BLYNK_AUTH)
@blynk.on("connected")
def blynk_connected(ping):
    print('Blynk ready. Ping:', ping, 'ms')

@blynk.on("disconnected")
def blynk_disconnected():
    print('Blynk disconnected')

@blynk.on("V1")  # water pump
def blynk_handle_vpins(value):
    print(f"Current button value: {value}") 


# OLED
i2c = SoftI2C(scl=Pin(22), sda=Pin(21))
oled = SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c)


# Sensor
adc_pin = Pin(36)          # VP pin
adc = ADC(adc_pin)         # set input
adc.width(ADC.WIDTH_9BIT)  # set resolutions
adc.atten(ADC.ATTN_11DB)   # set attenuation


while True:
    resistance = adc.read()
    moisture_value = (511 - resistance) * 100 // 511
    oled.fill(0)
    oled.text("Moisture Value: ", 0, 0)
    oled.text(str(moisture_value) + " %", 0, 16)
    oled.text(str(resistance) + " Ohm", 0, 32)
    
    oled.show()
    
    blynk.run()
    # write the moisture_value to the 
    blynk.virtual_write(0, str(moisture_value))
    
    utime.sleep(1)

