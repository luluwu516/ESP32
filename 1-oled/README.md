# OLED Display with ESP32
The 0.96-inch SSD1306 OLED display is a compact and versatile display module that utilizes OLED (Organic Light Emitting Diode) technology to provide clear, bright, and high-contrast visuals. The SSD1306 controller chip, integrated within the display, enables seamless communication with microcontrollers and other devices.

<img width="400" alt="OLED" src="https://github.com/luluwu516/ESP32/assets/98475122/7f94f895-4b66-448e-934f-dc1c7b27d4d6">

</br>

## SSD1306 Library
The library for writing to the OLED display isn't included in the standard MicroPython library, so we must upload the specific library designed for interfacing with the SSD1306 OLED display over I2C in a MicroPython environment. 

I am using Thonny IDE here.
1. Create a new file or download the ssd1306.py (I copied from [here](https://randomnerdtutorials.com/micropython-oled-display-esp32-esp8266/))
2. Save to "MicroPython device"

<img width="600" alt="Save to" src="https://github.com/luluwu516/ESP32/assets/98475122/3663e064-0f31-4ec6-aef6-baedb9daf7f7">

4. Name the file ssd1306.py and click OK to save the file on the device

<img width="600" alt="ssd1306.py" src="https://github.com/luluwu516/ESP32/assets/98475122/813ae6bd-41de-4f05-b0a5-f4a82de4ca5f">

</br>

## OLED Pinout

| OLED        | Meaning     | ESP32         |
| :---        |    :----:   |          ---: |
| VCC         | Power       | 3V            |
| GND         | Ground      | GND           |
| SCL         | Clock line  | 22 SCL        |
| SDA         | Data line   | 21 SDA        |

</br>

## Result

<img width="600" alt="OLED display with ESP32" src="https://github.com/luluwu516/ESP32/assets/98475122/af039bbd-91ac-465b-a94c-a5bd4a107c81">

After uploading the library to the ESP32 and connecting to the correct pin, we can simply print the "Hello, World!" message on the display.


</br>

## Reference
* [Randomner Tutorials](https://randomnerdtutorials.com/micropython-oled-display-esp32-esp8266/)
