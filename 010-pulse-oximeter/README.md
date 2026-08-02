# MAX30102 Pulse Oximeter and Heart-Rate Sensor

> Note: this is a learning project. The formula converting the ratio to a percentage is a generic empirical curve, not one calibrated for this sensor or this board, so the numbers look plausible without being accurate. Use certified equipment for anything health-related.

<br />

The MAX30102 is an integrated biosensor module for pulse oximetry and heart-rate monitoring. It shines red and infrared light into the fingertip and measures how much of each color comes back, using the difference in absorption between oxygenated and deoxygenated hemoglobin to estimate blood oxygen saturation (SpO2) and pulse rate. The same kind of sensor sits inside fitness bands and clip-on finger oximeters.

> This is an AI-assisted project. I followed the FLAG instructions but kept getting `SpO2: 0 %` with no errors. I searched Google to see if anyone else had encountered the same issue, read the MAX30102 document, and checked the hardware. Everything looks fine, and I can't find the problem with my limited knowledge. I never suspected the library would have issues. <br/>
Thanks to AI, I learned that the provided library, ported from SparkFun's MAX3010x library, had some bugs (see <a href="#debugging">Debugging</a>). I really appreciate that we live in an AI era, so I can ask an LLM agent for help anytime.

<img width="400" alt="MAX30102 front" src="https://github.com/luluwu516/ESP32/assets/98475122/67f35e36-b3d3-42fd-a0cd-11aa7681943a">

<img width="400" alt="MAX30102 back" src="https://github.com/luluwu516/ESP32/assets/98475122/b6bd5c30-4e26-4192-b06a-7b2aeb9c916a">

<br />

<br />

## Mechanism: How does it work?

The MAX30102 carries two LEDs, red and infrared, and a photodetector on the same side. Light from the LEDs scatters through the tissue under the skin, and some of it reflects back into the detector. The sensor detects only reflected light, so **finger placement and contact pressure dominate the result** (see Debugging).

Hemoglobin changes color when it carries oxygen. The two LEDs sit either side of that change:

| LED | Wavelength | Absorbed more by |
| :--- | :--- | :--- |
| Red | ~660 nm | Deoxygenated hemoglobin |
| Infrared | ~880 nm | Oxygenated hemoglobin |

Comparing how much red the tissue absorbs against how much infrared it absorbs gives a number that tracks oxygen saturation. 
> Finger thickness and LED brightness drop out of the ratio, so neither has to be known.

<br />

### The two components of the signal

* Skin, fat, bone, and venous blood block most of the light reaching the detector, and the amount they block holds steady through a heartbeat. That constant part is the **DC** component.

* Only the **arteries** pulse. Each beat expands them, they block a little more light, then they relax. That periodic wobble is the **AC** component, and it carries the information about freshly oxygenated blood.

Across the captures in this project the AC component ran between 0.3 % and 1.6 % of the DC: a reading near 16000 with a heartbeat wobble of 50 to 260 counts riding on top. Pulling that 1 % out of the rest is the firmware's whole job, which is why a small mistake drops the output to zero instead of shifting it by a few percent.

<br />

### From raw counts to a percentage

For each channel, the firmware separates the two components, then forms a ratio-of-ratios. Dividing each AC by its corresponding DC cancels out the effects of LED brightness and tissue thickness:

$$ R = \frac{\frac{\mathrm{AC\_red}} {\mathrm{DC\_red}}}{\frac{\mathrm{AC\_ir}}{\mathrm{DC\_ir}}} = \frac{\mathrm{AC\_red} \cdot \mathrm{DC\_ir}}{\mathrm{DC\_red} \cdot \mathrm{AC\_ir}}$$
$$\mathrm{SpO}_2 = -45.060 \cdot R^2 + 30.354 \cdot R + 94.845$$

Code:
```
R = (AC_red / DC_red) / (AC_ir / DC_ir)

SpO2 = -45.060 * R^2 + 30.354 * R + 94.845
```

The firmware measures heart rate on its own, by timing the interval between pulse peaks.

<br />

## MAX30102 Features

* Heart-rate monitor and pulse oximeter biosensor in an LED reflective solution
* Tiny 5.6 mm x 3.3 mm x 1.55 mm 14-pin optical module
  * Integrated cover glass for optimal, robust performance
* Ultra-low power operation for mobile devices
  * Programmable sample rate and LED current for power savings
  * Low-power heart-rate monitor (< 1 mW)
  * Ultra-low shutdown current (0.7 µA, typ)
* Fast data output capability
  * High sample rates
* Robust motion artifact resilience
  * High SNR
* -40°C to +85°C operating temperature range

<br />

## Connection Tables

The MAX30102 operates at 3.3 V. Both SDA and SCL require pull-up resistors, which most breakout boards already include.

| MAX30102 Biosensor  | Meaning     | ESP32         |
| :---                |    :----    |          ---: |
| GND                 | Ground      | GND           |
| SCL                 | Clock line  | 22 SCL        |
| SDA                 | Data line   | 21 SDA        |
| VIN                 | Power       | 3V            |

<br />


Sensor configuration, read back from the chip to confirm it applied:

| Register           | Value  | Meaning |
| :---               | :---   | :---    |
| `MODE_CONFIG` 0x09 | `0x03` | SpO2 mode, both LEDs active |
| `SPO2_CONFIG` 0x0A | `0x6F` | ADC range 16384, 400 Hz sample rate, 411 µs pulse width |
| `FIFO_CONFIG` 0x08 | `0x7F` | Average 8 samples, rollover enabled |
| `LED1_PA` 0x0C     | `0x7F` | Red LED, 25.4 mA pulse current |
| `LED2_PA` 0x0D     | `0x7F` | Infrared LED, 25.4 mA pulse current |

<br />

## Debugging

The first build ran without errors and reported `SpO2: 0 %` forever. With the help of AI, I traced it to eight separate problems, and each one hid the next, so they came out one at a time.

| # | Kind | Problem | Effect |
| :--- | :--- | :--- | :--- |
| 1 | Code | `update()` reset `spo2` to 0 at the top of every call | The code produces a value once per heartbeat, but the function runs ~976 times a second, so 99.9 % of printed values were 0 |
| 2 | Code | The DC estimator started from 0 while the signal sat near 16000 | 12 seconds of garbage before the first usable reading |
| 3 | Code | `return True` sat one indent too deep, inside the FIFO read loop | Each poll collected one sample instead of all pending ones |
| 4 | Code | Red and infrared channels swapped in the driver | Inverted the ratio: 38.5 % instead of 95.1 % on identical input |
| 5 | Code | A duplicated calculation block missing its guard clause | `0 / 0` on the first update, introduced while fixing the others |
| 6 | Measurement | Poor finger contact | Pulse strength 0.34 % of baseline, with drift 8x larger than the pulse |
| 7 | Code | The DC tracker could not keep up with baseline drift | Its lag exceeded the pulse amplitude, so the beat detector saw no zero crossing and stalled |
| 8 | Environment | MicroPython kept the previously imported module in memory | The board still ran an older file after upload |


Problem 4 is worth flagging for anyone using the same driver. The port mislabels the two LEDs. On the MAX30102, LED1 is red and LED2 is infrared, and SpO2 mode packs the FIFO in that order. The MAX30105 uses the same LED1/LED2 assignment and adds a green LED3, so the difference between chip variants has nothing to do with it. Swapping the byte offsets and buffer names together cancels out and changes nothing, which is worth knowing before you "fix" it.

Rather than guessing, the AI split the signal path and tested each piece against a known answer. It simulated the firmware in the laptop environment (see `sim/`). A controllable clock stands in for the hardware timer, so a 30-second experiment completes in about a second, and every run repeats identically.

The purpose of the layers is fault localization. An end-to-end failure only indicates that something broke. Splitting the path narrows it down: if layer 2 fails while layer 1 passes, the issue points to registers, the FIFO, or byte handling; the reverse points to filtering and arithmetic. If both pass, the code is cleared, and the search shifts to the signal or the environment.

| Layer | Fakes | Tests | Known answer |
| :--- | :--- | :--- | :--- |
| 1 | The sensor object | `pulse_oximeter.py` | Synthetic waveform built with 1.5 % / 1.0 % perfusion, so SpO2 must read 95.05 %, HR 75 bpm |
| 2 | The I2C bus | `max30102.py` | Two dissimilar probe values, which must land in the right channels (5497 and 582) |
| 3 | The sensor object | Whole chain | None. Replays real captures for comparison |

Besides, contact quality mattered more than any code change for getting a good reading. The same finger in two positions produced a fivefold difference in pulse strength.

* Cover both LEDs and the detector window, edge to edge
* Press light and steady; hard pressure collapses the capillaries and *reduces* the signal
* Hold still, with the arm resting on something
* Warm cold hands first, since poor circulation leaves almost no pulse to measure
* Wait about 10 seconds after placing the finger, until the tissue stops compressing
* Shield the sensor from bright ambient light

Heart rate needs five consecutive beats before it reports, so the first few seconds show `HR: 0.0`.

<br />

## Results

Working output from the device, once a second:

```
SpO2: 94.5 %   HR: 0.0
SpO2: 99.0 %   HR: 57.1
SpO2: 99.0 %   HR: 57.1
```

Before and after, using the same synthetic test signal:

| | Before | After |
| :--- | :--- | :--- |
| SpO2 reading | 0 % always | 95.14 % (expected 95.05 %) |
| Heart rate | 0.0 | 75.0 bpm (expected 75.0) |
| Useful readings | 0.08 % of updates | 97.4 % |
| Time to first reading | 12 seconds | ~1 heartbeat |
| Pulse strength (good contact) | 0.34 % | 1.62 % |

<br />

## Brief Summary

This is a working reflectance pulse oximeter on an ESP32 that reads SpO2 and heart rate from a MAX30102 over I2C. Debugging was the main focus of the project. The sensor's useful signal is about 1 % of what it reads, and that ratio is unforgiving: all eight problems produced the same flat `0 %`, regardless of the stage. A layered test harness turned that single ambiguous symptom into a specific answer and caught two fixes that were themselves broken.

<br />

## References

* [Analog Devices, MAX30102 product page](https://www.analog.com/en/products/max30102.html)
* [FLAG FM636A](https://www.flag.com.tw/maker/FM636A)
* [SparkFun MAX3010x Sensor Library](https://github.com/sparkfun/SparkFun_MAX3010x_Sensor_Library), the origin of this driver
