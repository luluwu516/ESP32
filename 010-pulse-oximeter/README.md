# MAX30102 Pulse Oximeter and Heart-Rate Sensor

The MAX30102 is an advanced, integrated biosensor module for pulse oximetry and heart-rate monitoring. It accurately measures oxygen saturation (SpO2) and pulse rate by emitting red and infrared light through the skin and analyzing the blood's absorption of these light wavelengths. This difference in light absorption is then used to calculate precise SpO2 and pulse rate readings, making the MAX30102 an essential component in various health and fitness monitoring devices.

<img width="400" alt="MAX30102 front" src="https://github.com/luluwu516/ESP32/assets/98475122/67f35e36-b3d3-42fd-a0cd-11aa7681943a">

<img width="400" alt="MAX30102 back" src="https://github.com/luluwu516/ESP32/assets/98475122/b6bd5c30-4e26-4192-b06a-7b2aeb9c916a">

<br />

<br />

## Mechanism: How does it work?



<img width="400" alt="Sensor" src="https://github.com/luluwu516/ESP32/assets/98475122/b8650d37-13f1-4536-a92e-f2c72fbeec1a">

<br />

<br />

## MAX30102 Features

* Heart-rate monitor and Pulse Oximeter Biosensor in LED Reflective Solution
* Tiny 5.6 mm x 3.3 mm x 1.55 mm 14-Pin Optical Module
  * Integrated Cover Glass for Optimal, Robust Performance
* Ultra-Low Power Operation for Mobile Devices
  * Programmable Sample Rate and LED Current for Power Savings
  * Low-Power Heart-Rate Monitor (< 1mW)
  * Ultra-Low Shutdown Current (0.7µA, typ)
* Fast Data Output Capability
  * High Sample Rates
* Robust Motion Artifact Resilience
  * High SNR
* -40°C to +85°C Operating Temperature Range

<br />

## Connection Tables

For MAX30102 Biosensor:

| MAX30102 Biosensor  | Meaning     | ESP32         |
| :---                |    :----    |          ---: |
| GND                 | Ground      | GND           |
| SCL                 | Clock line  | 22 SCL        |
| SDA                 | Data line   | 21 SDA        |
| VIN                 | Power       | 3V            |

<br />

For OLED display:

| OLED        | Meaning     | ESP32         |
| :---        |    :----    |          ---: |
| VCC         | Power       | 3V            |
| GND         | Ground      | GND           |
| SCL         | Clock line  | 22 SCL        |
| SDA         | Data line   | 21 SDA        |

<br />

<br />

## Results

<br />

<br />

## Brief Summary

<br />

## References

* [Analog Devices](https://www.analog.com/en/products/max30102.html)
* [FLAG](https://www.flag.com.tw/maker/FM636A)
