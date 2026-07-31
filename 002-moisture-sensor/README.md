# LM393 Soil Moisture Detect Sensor

The LM393 soil moisture detection sensor is a simple yet effective electronic device to measure soil moisture content. It typically consists of two main components: the LM393 comparator chip and the moisture-sensing probe. 
* The LM393 comparator chip includes two voltage comparator integrated circuits. It compares two voltage inputs and determines which one is greater. The soil moisture sensor compares the resistance of the soil with a reference voltage.
* The moisture-sensing probe usually comprises two electrodes inserted into the soil. As the moisture content in the soil changes, so does its electrical conductivity. The probe measures this conductivity, which is then converted into a voltage signal.

<br />

<img width="400" alt="image" src="https://github.com/luluwu516/ESP32/assets/98475122/25824f1c-aec8-4ee4-8b8d-030eeea63d6c">

<br />

<br />

## Features

* Operating Voltage: 3.3V to 5V DC
* Operating Current: 15mA
* Output Digital - 0V to 5V, Adjustable trigger level from preset
* Output Analog - 0V to 5V based on infrared radiation from fire flame falling on the sensor
* LEDs indicating output and power
* PCB Size: 3.2cm x 1.4cm
* Easy to use with Microcontrollers or even with normal Digital/Analog IC

For more information, check out [the LM393 Soil Moisture Detect Sensor datasheet](https://www.smart-prototyping.com/image/data/SKU%20Photos/10100012/lm393-n.pdf).

<br />

## Connection Table

For Soil Moisture Detect Sensor:

| Sensor      | Meaning        | ESP32         |
| :---        |    :----      |          ---: |
| VCC         | Power          | 3V            |
| GND         | Ground         | GND           |
| DO          | Digital Output | -             |
| AO          | Analog Output  | VP 36         |

<br />

For OLED display:

| OLED        | Meaning     | ESP32         |
| :---        |    :----    |          ---: |
| VCC         | Power       | 3V            |
| GND         | Ground      | GND           |
| SCL         | Clock line  | 22 SCL        |
| SDA         | Data line   | 21 SDA        |

<br />

<img width="400" alt="image" src="https://github.com/luluwu516/ESP32/assets/98475122/37b5347e-630b-4d3e-9cd9-d75617f20d3f">

<br />

<br />

## ADC (analog to digital conversion)

> On the ESP32, ADC functionality is available on pins 32-39 (ADC block 1) and pins 0, 2, 4, 12-15, and 25-27 (ADC block 2).

To read voltages above the reference voltage, apply input attenuation with the atten keyword argument.

### Input Attenuation

| Constant         | Input Attenuation                   | 
| :---             |    :----                            | 
| ADC.ATTN_0DB     | No attenuation (100mV - 950mV)      |
| ADC.ATTN_2_5DB   | 2.5dB attenuation (100mV - 1250mV)  |
| ADC.ATTN_6DB     | 6dB attenuation (150mV - 1750mV)    |
| ADC.ATTN_11DB    | 11dB attenuation (150mV - 2450mV)   |

<br />

### Resolutions

| Constant         | Resolutions         | 
| :---             |    :----            | 
| ADC.WIDTH_9BIT   | 9 bits (0-511)      |
| ADC.WIDTH_10BIT  | 10 bits (0-1023)    |
| ADC.WIDTH_11BIT  | 11 bits (0-2047)    |
| ADC.WIDTH_12BIT  | 12 bits (0-4095)    |

<br />

## Results

The sensor operates on the principle of electrical conductivity. It measures the resistance between two electrodes inserted into the soil. Moist soil conducts electricity better, resulting in lower resistance. Conversely, dry soil has higher resistance. The sensor detects these resistance changes and translates them into moisture levels.

Air has a higher resistance. The display showed 511 Ohm (Ω), the maximum value (see the left figure). On the other hand, the display showed 148 Ohm (Ω) when I plugged the sensor into the soil since the wet soil has lower resistance than air (see the right figure).

<img height="400" alt="air" src="https://github.com/luluwu516/ESP32/assets/98475122/c6f067f3-d52d-4e0e-97c1-7d30d84650f0">

<img height="400" alt="Watered plant" src="https://github.com/luluwu516/ESP32/assets/98475122/93ec9f96-5299-40a1-b09c-ce203e1c5144">

<br />

<br />

## Brief Summary

The LM393 soil moisture detection sensor is fundamental in discerning soil moisture levels, offering indispensable insights for automated irrigation systems, plant vitality assessment, and various applications reliant on precise soil moisture analysis.

<br />

## Reference
* [FLAG](https://www.flag.com.tw/maker/FM636A)
* [Components 101](https://components101.com/modules/soil-moisture-sensor-module)
* [MicroPyhon](https://docs.micropython.org/en/latest/esp32/quickref.html)

