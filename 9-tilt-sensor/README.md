# SW-520D Tilt Sensor

The SW-520D is a small, cost-effective ball-type tilt and vibration sensor commonly used in electronics projects to detect an object's tilt or orientation. Ideal for activating low-current circuits, this unidirectional trigger is widely applied in electronic devices, small household appliances, sports equipment, and anti-theft systems.

<br />

<img width="301" alt="SW-520D Tilt Sensor" src="https://github.com/luluwu516/ESP32/assets/98475122/4503dddc-e5df-423c-b326-5dcdafac3509">

<br />

<br />

## Mechanism: How does it work?

The SW-520D operates by housing a small metal ball that moves freely inside a cylindrical case. Depending on the sensor's tilt, the ball either makes contact with the conductive pins, closing the circuit, or moves away from them, opening the circuit. This movement enables simple tilt detection.

Specifically, when the sensor tilts to the conductive terminal more than 15 degrees, it enters an open circuit (OFF) state. Conversely, when the trigger end (gold-plated pin) tilts below the horizontal gradient by more than 15 degrees, it closes the circuit (ON state). Shaking easily triggers the sensor in the horizontal position, whereas with the gold-plated pin facing up, it is less sensitive to shaking.

<img width="400" alt="Tilt Sensor SW-520D" src="https://github.com/luluwu516/ESP32/assets/98475122/edb980ed-72d9-4420-b358-08fe7d1a2d14">

<br />

<br />

## SW-520D Features

* Conduction Time: 20 ms
* Max.Voltage: 12V
* Rated Thermal Current: 20 mA
* Insulation Resistance: 10M ohm

## Connection Table

For SW-520D Tilt Sensor:

| Sensor      | Meaning         | ESP32         |
| :---        |    :----        |          ---: |
| VCC         | Power           | 17            |
| GND         | Ground          | GND           |

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

<img width="400" alt="image" src="https://github.com/luluwu516/ESP32/assets/98475122/8109b510-8e4d-4327-b3af-0d0f7de38726">

<br />

<br />

## Results

### Tilt sensor

When the device is horizontal, the metal ball inside the SW-520D tilt sensor remains in contact with the conductive pins. It keeps the circuit's default state (In my case, the circuit is closed and `sw520d.value() == 0`). In the state, no action is triggered.

<img width="400" alt="The sensor in the horizontal position" src="https://github.com/luluwu516/ESP32/assets/98475122/b13673ad-d312-47f1-aa4f-93d03c936d87">

<br />

<br />

Conversely, when the sensor is tilted, the two balls roll inside the case. The balls move away from them (opening the circuit). This change in the circuit state triggers a response: a buzzer sounds, and an OLED display shows a message indicating that the device has been tilted. This mechanism allows for simple yet effective tilt detection, providing immediate feedback when the device's orientation changes.

<img width="400" alt="The sensor tilted" src="https://github.com/luluwu516/ESP32/assets/98475122/0463342a-8fdc-4cbe-aa02-393e4acab4ec">

<br />

<br />

<br />

### Pedometer

We can apply the same concept to build a pedometer. However, due to the sensor's sensitivity to vibrations, it may overcount steps. To address this, we implemented a function to check the duration between circuit changes. If the duration is more than 50 milliseconds, it is considered a true walking vibration, thereby reducing the chances of overcounting.

![pedometer](https://github.com/luluwu516/ESP32/assets/98475122/0e8e5d5f-6b7a-46a9-8060-3cd9ed91deb2)

<br />

<br />

## Brief Summary

The SW-520D tilt sensor is not suitable for precise angle measurement and is sensitive to vibrations, which might cause false triggering. However, it is a practical choice for projects requiring basic tilt or vibration detection. Its simplicity and affordability make it ideal for many hobbyist and professional electronics applications.

## Reference

* [FLAG](https://www.flag.com.tw/maker/FM636A)
