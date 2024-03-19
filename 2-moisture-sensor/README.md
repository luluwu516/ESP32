# LM393 Soil Moisture Detect Sensor

The LM393 soil moisture detection sensor serves the purpose of detecting the moisture level in soil, providing crucial data for automated irrigation systems, plant health monitoring, and other applications where soil moisture content is a critical factor.

When I return to Taiwan for a few weeks, I always ask my friends to take care of my plants. When I first learned ESP32, I aimed to build an automated watering system. Here is my first step.

<img width="400" alt="image" src="https://github.com/luluwu516/ESP32/assets/98475122/25824f1c-aec8-4ee4-8b8d-030eeea63d6c">

<br />

<br />

## Connection Table

For Soil Moisture Detect Sensor:

| Sensor      | Meaning        | ESP32         |
| :---        |    :----      |          ---: |
| VCC         | Power          | 3V            |
| GND         | Ground         | GND           |
| DO          | Digital Output | -             |
| AO          | Analog Output  | VP 36         |

For OLED display:

| OLED        | Meaning     | ESP32         |
| :---        |    :----   |          ---: |
| VCC         | Power       | 3V            |
| GND         | Ground      | GND           |
| SCL         | Clock line  | 22 SCL        |
| SDA         | Data line   | 21 SDA        |

<img width="400" alt="image" src="https://github.com/luluwu516/ESP32/assets/98475122/37b5347e-630b-4d3e-9cd9-d75617f20d3f">

<br />


## Result

The sensor operates on the principle of electrical conductivity. It measures the resistance between two electrodes inserted into the soil. Moist soil conducts electricity better, resulting in lower resistance. Conversely, dry soil has higher resistance. The sensor detects these resistance changes and translates them into moisture levels.

Air has a higher resistance. The display showed 511 Ohm (Ω), the maximum value (see the left figure). On the other hand, the display showed 148 Ohm (Ω) when I plugged the sensor into the soil since the wet soil has lower resistance than air (see the right figure).

<img height="400" alt="air" src="https://github.com/luluwu516/ESP32/assets/98475122/c6f067f3-d52d-4e0e-97c1-7d30d84650f0">

<img height="400" alt="Watered plant" src="https://github.com/luluwu516/ESP32/assets/98475122/93ec9f96-5299-40a1-b09c-ce203e1c5144">

<br />

<br />

I can use the analog output value to control the water pump and build an automated watering system. Wish me luck!
