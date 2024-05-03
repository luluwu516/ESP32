# SSD1306 OLED Display

The 0.96-inch SSD1306 OLED display is a compact and versatile module that utilizes OLED (Organic Light Emitting Diode) technology to provide clear, bright, high-contrast visuals. The SSD1306 controller chip, integrated within the display, enables seamless communication with microcontrollers and other devices.

<img width="400" alt="OLED" src="https://github.com/luluwu516/ESP32/assets/98475122/3fece805-0f28-4363-ba9e-b1b84571edba">

</br>

</br>

## Features

* Monochrome 7-pin SSD1306 0.96” OLED display.
* 128×64 pixel resolution with 160° viewing angle.
* Supply voltage 3V – 5V (supports both 5V and 3.31v logic devices).
* Uses SSD1306 for interfacing hence can communicate through SPI or IIC.
* Multiple SPI or IIC devices are supported
* Can be easily interfaced with Arduino (Library available).
* Supports decent graphics of bitmap images.
* Available in different colors and sizes as discussed below.

</br>

## Connection Table

| OLED |  Meaning   |  ESP32 |
| :--- | :--------: | -----: |
| VCC  |   Power    |     3V |
| GND  |   Ground   |    GND |
| SCL  | Clock line | 22 SCL |
| SDA  | Data line  | 21 SDA |

</br>

## SSD1306 Library

The library for writing to the OLED display isn't included in the standard MicroPython library, so we must upload the specific library designed for interfacing with the SSD1306 OLED display over I2C in a MicroPython environment.

I use Thonny IDE here.

1. Create a new file or download the ssd1306.py (I copied it from [here](https://randomnerdtutorials.com/micropython-oled-display-esp32-esp8266/))
2. Save to "MicroPython device"

<img width="600" alt="Save to" src="https://github.com/luluwu516/ESP32/assets/98475122/3663e064-0f31-4ec6-aef6-baedb9daf7f7">

3. Name the file ssd1306.py and click OK to save the file on the device

<img width="600" alt="ssd1306.py" src="https://github.com/luluwu516/ESP32/assets/98475122/813ae6bd-41de-4f05-b0a5-f4a82de4ca5f">

</br>

</br>

## Results

After uploading the library to the ESP32 and connecting to the correct pin, we can print the "Hello, World!" message or the values of other variables, such as time on the display.

<img width="600" alt="OLED display with ESP32" src="https://github.com/luluwu516/ESP32/assets/98475122/af039bbd-91ac-465b-a94c-a5bd4a107c81">

</br>

</br>

## Reference

* [Components 101](https://components101.com/displays/oled-display-ssd1306)
* [Random Nerd Tutorials](https://randomnerdtutorials.com/micropython-oled-display-esp32-esp8266/)

