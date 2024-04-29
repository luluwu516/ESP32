# KY-008 Laser Transmitter

The KY-008 Laser Transmitter is a small module commonly used in hobbyist electronics projects for transmitting laser beams. It features a small, low-power laser diode that emits a visible red light. This module is popular among Arduino enthusiasts due to its ease of use and versatility.

<img width="400" alt="KY-008 Laser Transmitter" src="https://github.com/luluwu516/ESP32/assets/98475122/1439a1a3-3635-4856-a6f0-9657b81911c6">

<br />

<br />

## Features

* Operating Voltage: 5V
* Output Power: 5mW
* Wavelenght: 650nm
* Operating Current: < 40mA
* Working Temperature: -10°C ~ 40°C
* Board Dimensions: 18.5mm x 15mm

<br />

<br />

## Connection Table

For KY-008 Laser Transmitter

| Laser     | Meaning       | ESP32      |
| :---      |    :----      |       ---: |
| Signal    | Power/Signal  | 3V         |
| +         | Power         | -          |
| -         | Ground        | GND        |

<br />

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

For Buzzer:

| Buzzer    | Meaning     | ESP32      |
| :---      |    :----    |       ---: |
| +         | Power       | -          |
| -         | Ground      | GND        |
| S         | Clock line  | 16         |

<br />

<img width="612" alt="image" src="https://github.com/luluwu516/ESP32/assets/98475122/2115376e-a0f6-46e8-ad0f-ad503cd9e1ae">

<br />

<br />

## Result

### Shooting Game

We employ a KY-008 laser transmitter for a shooting game, using the BH170 light sensor as a designated target. Each successful hit on the target accrues one point for the user. 

![shooting-game-hit](https://github.com/luluwu516/ESP32/assets/98475122/2dc4aeeb-e233-42be-911f-6d6975c4653f)

Victory in the game is achieved upon reaching a score of ten points.

![shooting-game-win](https://github.com/luluwu516/ESP32/assets/98475122/50e44a17-4405-45cd-832a-6721a6030dba)

<br />

### Anti-Theft Device

The KY-008 laser transmitter can be effectively integrated into an anti-theft system. Activation of the device is initiated by directing the laser toward the light sensor.

![anti-theft-setting](https://github.com/luluwu516/ESP32/assets/98475122/53d0083f-9297-46a2-9e05-9650fab2c263)

Following configuration, reminiscent of scenes from the movie "Mission: Impossible," any obstruction of the laser beam triggers the alarm, signaling a potential security breach.

![anti-theft-on](https://github.com/luluwu516/ESP32/assets/98475122/4a5e87ed-0f12-483a-9c57-436303bef72a)

<br />

<br />

## Reference
* [FLAG](https://www.flag.com.tw/maker/FM636A)
* [Arduino Modules](https://arduinomodules.info/ky-008-laser-transmitter-module/)
