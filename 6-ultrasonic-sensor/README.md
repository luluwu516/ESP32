# HC-SR04 Ultrasonic Sensor

The HC-SR04 Ultrasonic utilizes ultrasonic waves to measure distances accurately. Employing ultrasonic waves, it adeptly gauges distances with precision. Through the transmission of straightforward digital signals, the sensor seamlessly interfaces with microcontrollers and allied devices, facilitating smooth integration into diverse projects.

Operating within a range from 2 cm to 400 cm, the HC-SR04 Ultrasonic Sensor consistently furnishes reliable distance readings with an impressive accuracy of 0.3cm (0.1 inches). Its utility extends across various applications, encompassing robotics, security systems, industrial automation, and many other endeavors necessitating robust distance-sensing capabilities.

<br />

<img width="400" alt="image" src="https://github.com/luluwu516/ESP32/assets/98475122/2b31f610-ab58-4668-8b06-f27cbecaff5d">

<br />

<br />

## Mechanism: How does it work?

The HC-SR04 ultrasonic sensor operates based on the principle of ultrasonic waves to measure distance. Here is how it works:

1. The ultrasound transmitter (trig pin) emits a high-frequency sound, typically at 40 kHz.

2. This emitted sound travels through the air, and upon encountering an object, it reflects back towards the module.

3. The echo pin, serving as the ultrasound receiver, picks up the reflected sound, also known as the echo.

<br />

<img width="599" alt="image" src="https://github.com/luluwu516/ESP32/assets/98475122/f86518d1-c793-419e-b255-18b7a246e207">

<br />

<br />

<br />

Since the speed of sound in air is known (approximately 343 meters per second or 0.0343 centimeters per microsecond at room temperature), the microcontroller can calculate the round-trip distance traveled by the ultrasonic waves using the formula:

> Distance = (Time taken for echo to return * Speed of sound) / 2

Dividing by 2 accounts for the measured time representing the total round-trip distance traveled by the ultrasonic waves.

<br />

<br />

## Features

* Working Voltage: DC 5V
* Working Current: 15 mA
* Working Frequency: 40 Hz
* Max Range: 4 m
* Min Range: 2 cm
* MeasuringAngle: 15 degree
* Trigger Input Signal: 10uS TTL pulse
* Echo Output Signal: Input TTL lever signal and the range in proportion
* Dimension: 45 × 20 × 15 mm 

For more information, check out [the HC-SR04 Ultrasonic Sensor datasheet](https://cdn.sparkfun.com/datasheets/Sensors/Proximity/HCSR04.pdf).

<br />

<br />

## Connection Table

For Ultrasonic Sensor:

| Ultrasonic Sensor   | Meaning     | ESP32         |
| :---                |    :----    |          ---: |
| Vcc                 | Power       | 3V            |
| Trig                | Ground      | 5 SS          |
| Echo                | Clock line  | 18 SCK        |
| Gnd                 | Data line   | GND           |

For OLED display:

| OLED        | Meaning     | ESP32         |
| :---        |    :----    |          ---: |
| VCC         | Power       | 3V            |
| GND         | Ground      | GND           |
| SCL         | Clock line  | 22 SCL        |
| SDA         | Data line   | 21 SDA        |

For Buzzer:

| OLED        | Meaning     | ESP32         |
| :---        |    :----    |          ---: |
| +           | Power       | 16            |
| -           | Ground      | GND           |

<br />

<img width="406" alt="image" src="https://github.com/luluwu516/ESP32/assets/98475122/6f9166cb-260e-4d87-8939-92c7f499b3bd">

<br />

<br />

## HC-SR04 Library

The library for HC-SR04 isn't included in the standard MicroPython library, so we must upload the specific library to the ESP32.

I am using Thonny IDE here.

1. Create a new file or download the ssd1306.py (I copied from [here](https://randomnerdtutorials.com/micropython-hc-sr04-ultrasonic-esp32-esp8266/))
2. Save to "MicroPython device"
3. Name the file hcsr04.py and click OK to save the file on the device

<img width="613" alt="image" src="https://github.com/luluwu516/ESP32/assets/98475122/d6fb60f1-317e-4d49-82d0-1a82361c9a70">

<br />

<br />

## Results

The HC-SR04 ultrasonic sensor offers a versatile range, enabling distance measurements from as close as 2 centimeters to as far as 4 meters (sonar.py). Personally, I found it remarkably precise when gauging the depth of my MacBook Air (shown in the figure). Moreover, its adaptability extends to diverse applications such as crafting anti-theft mechanisms (anti-theft.py), assisting in parking (parking-sensor.py), and even constructing an air piano (air-piano.py). 

<img width="406" alt="image" src="https://github.com/luluwu516/ESP32/assets/98475122/d13ba43f-61ca-40d3-9a78-0dddfdaccc91">

<br />

<br />

## Brief Summary

These are just a few examples of the many applications of HC-SR04 ultrasonic sensors. They can also applied to obstacle avoidance in robotics, monitoring liquid levels in fish tanks, implementing automatic trash bins, and much more.

<br />

## Reference
* [Random Nerd Tutorials](https://randomnerdtutorials.com/micropython-hc-sr04-ultrasonic-esp32-esp8266/)
* [FLAG](https://www.flag.com.tw/maker/FM622A)
