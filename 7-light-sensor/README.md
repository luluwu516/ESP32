# BH1750 Light Sensor

The BH1750 is a digital ambient light sensor renowned for its precise measurement of light intensity. Operating as a 16-bit ambient light sensor, the BH1750 communicates seamlessly via the I2C protocol. Its output is expressed in lux, the standardized unit of illuminance in the International System of Units (SI). It boasts a measurement range from a minimum of 1 lux to a maximum of 65535 lux, ensuring precise and reliable data capture across various lighting conditions.

<br />

<img width="800" alt="image" src="https://github.com/luluwu516/ESP32/assets/98475122/fcbb6ab2-8819-4de5-b220-1acab0ea555b">

<br />

<br />

## BH1750 Features

* I2C bus Interface (f/s Mode Support)
* Spectral responsibility is approximately human eye response
* Illuminance to Digital Converter
* Wide range and High resolution. (1 - 65535 lux)
* Low Current by power down function
* 50Hz/60Hz Light noise reject-function
* 1.8V Logic input interface
* No need any external parts
* Light source dependency is little. (ex. Incandescent Lamp. Fluorescent Lamp. Halogen Lamp. White LED. Sun Light)
* It is possible to select 2 types of I2C slave-address.
* Adjustable measurement result for the influence of optical window (It is possible to detect min. 0.11 lux, max. 100000 lux by using this function.)
* Small measurement variation (+/- 20%)
* The influence of infrared is very small. 

<br />

Here is where BH1750 sensors the light.

<img width="400" alt="image" src="https://github.com/luluwu516/ESP32/assets/98475122/cd24b8b8-869c-4975-b596-9be1382405fc">

<br />

<br />

For more information, check out [the BH1750 sensor datasheet](https://datasheet.octopart.com/BH1750FVI-TR-Rohm-datasheet-25365051.pdf).

<br />

<br />

## Measurement Modes

In MicroPython, the BH1750 light sensor library provides different measurement modes for various application needs. These modes allow us to configure the sensor to provide measurements with different resolutions and measurement times. 

<br />

| Code      | Mode                    | Precision    | Measurement Time   |
| :---      |    :----                |         ---: |               ---: |
| 0x20      | High Resolution Mode 1  | 1 lux        | 120 ms             |
| 0x21      | High Resolution Mode 2  | 0.5 lux      | 120 ms             |
| 0x23      | Low Resolution Mode     | 4 lux        | 16 ms              |

<br />

<br />

## Connection Table

For BH1750 Light Sensor:

| Sensor      | Meaning         | ESP32         |
| :---        |    :----        |          ---: |
| VCC         | Power           | 3V            |
| GND         | Ground          | GND           |
| SCL         | Clock line      | 22 SCL        |
| SDA         | Data line       | 21 SDA        |
| ADDR        | Selects Address | -             |

<br />

For OLED display:

| OLED        | Meaning     | ESP32         |
| :---        |    :----    |          ---: |
| VCC         | Power       | 3V            |
| GND         | Ground      | GND           |
| SCL         | Clock line  | 22 SCL        |
| SDA         | Data line   | 21 SDA        |

<br />

<img width="400" alt="image" src="https://github.com/luluwu516/ESP32/assets/98475122/b3810501-3904-4ef5-9ba4-e9247dff3355">

<br />

<br />

For Buzzer:

| Buzzer    | Meaning     | ESP32      |
| :---      |    :----    |       ---: |
| +         | Power       | -          |
| -         | Ground      | GND        |
| S         | Clock line  | 16         |

<br />

<br />

## Result

First, I applied the BH1750 library and created a light sensor that detects the illumination (light-sensor.py). It worked perfectly. 

<br />

Then, I added a buzzer in my light sensor system to create an inadequate illumination alarm (inadequate-illumination-alarm.py). The alarm only displays the light level when the room is bright enough. 

<img width="400" alt="image" src="https://github.com/luluwu516/ESP32/assets/98475122/0a8d2339-b349-4c10-8cd0-6adad8d14c3d">

<br />

<br />

If the room is too dark, the buzzer alarms to alert the user to get more light. 

<img width="400" alt="image" src="https://github.com/luluwu516/ESP32/assets/98475122/dad016e6-0eb0-4b52-bcc2-b53b6885ae36">

<br />

<br />

We set the alarm condition to be 30 < light_level < 300, so when the user turns off the light, the buzzer will not alarm. 

(I used my flashlight to cover the sensor, pretending the user turned off the light.)

<img width="400" alt="image" src="https://github.com/luluwu516/ESP32/assets/98475122/28671c2d-ac48-4b54-bf4a-d9a3c0e970f7">

<br />

<br />

## Brief Summary

The BH1750 light sensor's precision in measuring ambient light intensity finds widespread application across various fields, including Automatic Brightness Adjustment, Smart Lighting Systems, and IoT. Its exacting measurement capabilities render it indispensable in contemporary electronic devices and systems.

<br />

<br />

## Reference
* [FLAG](https://www.flag.com.tw/maker/FM636A)
* [Random Nerd Tutorials](https://randomnerdtutorials.com/esp32-bh1750-ambient-light-sensor/)
