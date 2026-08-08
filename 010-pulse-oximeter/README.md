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

Across the captures in this project the AC component ran between 0.2 % and 1.6 % of the DC: a reading near 16000 with a heartbeat wobble of 30 to 260 counts riding on top. Pulling that 1 % out of the rest is the firmware's whole job, which is why a small mistake drops the output to zero instead of shifting it by a few percent.

That ratio has a name, and it is used throughout this file:

$$\mathrm{PI} = \frac{\mathrm{AC}}{\mathrm{DC}} \times 100\ \%$$

**Perfusion index (PI)** is a property of the optical signal, not a physiological measurement. Perfusion in physiology means blood flow per unit of tissue, measured in mL/min per 100 g. PI is unitless, and it only correlates with that. Nothing in this project measures blood flow.

What PI does measure is how much of the returning light carries a heartbeat. Dividing by DC is what makes the number portable: LED current, finger thickness, skin tone, and contact pressure scale AC and DC together, so they cancel, and the same finger reads the same PI at any light level.

Two things to keep in mind when reading the PI figures later on. Commercial oximeters display PI down to about 0.02 % and treat anything below 0.4 % as low perfusion, but those instruments shine light through the whole finger, while the MAX30102 collects only what reflects off the surface layers. Reflectance gives a lower PI for the same finger, so the clinical thresholds do not carry over. Separately, a high PI does not prove a pulse is there. PI measures how large the fluctuation is, not whether it repeats. In `sim/trace1.py` the red channel has the higher PI of the two and no heartbeat in it at all.

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

The firmware measures heart rate on its own by timing the interval between successive downward zero crossings of the AC signal.

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
| `SPO2_CONFIG` 0x0A | `0x6F` | ADC range 16384 nA, 400 Hz sample rate, 411 µs pulse width |
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
| 4 | Code | Red and infrared channels swapped in the driver | Inverted the ratio: 38.3 % instead of 95.1 % on identical input |
| 5 | Code | A duplicated calculation block missing its guard clause | `0 / 0` on the first update, introduced while fixing the others |
| 6 | Measurement | Poor finger contact | PI 0.34 %, a fifth of what good contact gives |
| 7 | Code | The DC tracker could not keep up with baseline drift | Its lag exceeded the pulse amplitude, so the beat detector saw no zero crossing and stalled |
| 8 | Environment | MicroPython kept the previously imported module in memory | The board still ran an older file after upload |


Problem 4 is worth flagging for anyone using the same driver. The port mislabels the two LEDs. On the MAX30102, LED1 is red and LED2 is infrared, and SpO2 mode packs the FIFO in that order. The MAX30105 uses the same LED1/LED2 assignment and adds a green LED3, so the difference between chip variants has nothing to do with it. Swapping the byte offsets and buffer names together cancels out and changes nothing, which is worth knowing before you "fix" it.

Rather than guessing, the AI split the signal path and tested each piece against a known answer. It simulated the firmware in the laptop environment (see `sim/`). A controllable clock stands in for the hardware timer, so a 30-second experiment completes in about a second, and every run repeats identically.

The purpose of the layers is fault localization. An end-to-end failure only indicates that something broke. Splitting the path narrows it down: if layer 2 fails while layer 1 passes, the issue points to registers, the FIFO, or byte handling; the reverse points to filtering and arithmetic. If both pass, the code is cleared, and the search shifts to the signal or the environment.

| Layer | Fakes | Tests | Known answer |
| :--- | :--- | :--- | :--- |
| 1 | The sensor object | `pulse_oximeter.py` | Synthetic waveform built with an infrared PI of 1.5 % and a red PI of 1.0 %, so SpO2 must read 95.05 %, HR 75 bpm |
| 2 | The I2C bus | `max30102.py` | Two dissimilar probe values, which must land in the right channels (5497 and 582) |
| 3 | The sensor object | Whole chain | None. Replays real captures for comparison |

Besides, contact quality mattered more than any code change for getting a good reading. The same finger in two positions produced a fivefold difference in pulse strength.

* Cover both LEDs and the detector window, edge to edge
* Press light and steady; hard pressure collapses the capillaries and *reduces* the signal
* Hold still, with the arm resting on something
* Warm cold hands first, since poor circulation leaves almost no pulse to measure
* Wait about 10 seconds after placing the finger, until the tissue stops compressing
* Shield the sensor from bright ambient light

Heart rate needs five consecutive intervals before it reports, so the first few seconds show `HR: 0.0`.

<br />

## Results

<img width="400" alt="image" src="https://github.com/user-attachments/assets/fdaa4e3e-7c82-4aef-a084-8c2982aa1b15" />

A full run of `spo2.py`, printing once a second, from soft reboot to `Ctrl-C`:

```
MPY: soft reboot
SpO2: 0 % HR: 0.0
SpO2: 0 % HR: 0.0
SpO2: 0 % HR: 0.0
SpO2: 99.09847 % HR: 0.0
SpO2: 98.41518 % HR: 0.0
SpO2: 98.97713 % HR: 57.94862
SpO2: 98.87823 % HR: 57.94862
SpO2: 98.98921 % HR: 57.94862
SpO2: 99.04211 % HR: 57.94862
SpO2: 98.73403 % HR: 71.94244
SpO2: 99.05496 % HR: 71.94244
SpO2: 98.91346 % HR: 71.94244
SpO2: 98.93148 % HR: 71.94244
Sensor shut down
```

Three things to read from that trace:

* The first three seconds report `0 %` as the finger settles. The tissue is still compressing, and the baseline drifts faster than the DC tracker can follow, so the beat detector has nothing stable to lock onto.
* SpO2 arrives about two seconds before heart rate. SpO2 requires one complete pulse cycle; heart rate first averages five intervals.
* Heart rate steps from 57.9 to 71.9 bpm partway through, and the first of the two is wrong. The average covers five intervals, but the first interval is timed from start-up rather than from a heartbeat, so whatever gap happens to fall between power-on and the first detected beat is averaged in as though it were a real one. Reversing the arithmetic, the two windows span 5.178 s and 4.170 s, and the difference is 1.008 s, one whole beat. 71.9 bpm is the real rate. SpO2 over the same window stays within 98.4 to 99.1 %, which is the steadier of the two readings.

Before and after, using the same synthetic test signal:

| | Before | After |
| :--- | :--- | :--- |
| SpO2 reading | 0 % always | 95.14 % (expected 95.05 %) |
| Heart rate | 0.0 | 75.0 bpm (expected 75.0) |
| Useful readings | 0.08 % of updates | 97.4 % |
| Time to first SpO2 reading | 12.0 s | 0.8 s (1 heartbeat) |
| Time to first heart rate | 12.4 s | 3.6 s (4.5 heartbeats) |
| PI (good contact) | 0.34 % | 1.62 % |

Timings come from the 75 bpm synthetic signal, where one beat is 800 ms. SpO2 needs a single complete pulse cycle, so it appears after one beat. Heart rate averages `target_n_beats = 5` intervals before it reports, which is why the first few seconds always show `HR: 0.0`.

Five intervals should take five beats, but the first reading lands at 3.6 s, which is 4.5 beats. `HR_calculator` timestamps itself when it is constructed, so its first interval runs from start-up to the first detected beat rather than between two beats. In the simulation that gap was 360 ms against a true 800 ms, and the first reported value came out **84.3 bpm instead of 75.0**, off by 12 %. The second reading, four beats later, is correct. Treat the first heart-rate number the firmware prints as a throwaway, on the bench and on the device alike. At a slower resting rate the wait grows in proportion: roughly 4.5 s at 60 bpm, 4.7 s at 57 bpm.

On real hardware, the wait runs longer than these figures, as the trace above shows. The synthetic signal has a steady baseline from the first sample, while a real finger keeps compressing for several seconds after it lands on the sensor.

<br />

## PPG Waveform

`ppg.py` skips the SpO2 arithmetic and prints the raw pulse waveform instead, one value per sample at 50 Hz. Thonny's Plotter draws it live. The point is to have a signal that can later be lined up against an ECG trace.

Three decisions are hiding in the following three lines:

```python
ir = pox.get_raw_ir()
dc = pox.dc_remover_ir.old_value     # read the DC estimate, do not advance it
ppg = int(dc * 1.01 - ir)
```

* **Infrared, not red.** On the two captures where both channels show a detectable pulse, band-passed infrared measures 2.6x and 1.9x the red channel. On the worst capture, red carries more energy than infrared, but none of it is a heartbeat: its autocorrelation peaks at the 200 bpm edge of the search range with r = 0.20, while infrared lands on 75 bpm at r = 0.38. Red loses first as contact degrades, which is the case worth designing around.
* **Subtract the sample from the baseline, not the other way round.** In reflectance, the artery blocks more light at systole, so the raw count *drops* on each beat. Flipping the subtraction puts the pulse the way a reader expects it.
* **The 1 % offset keeps the trace positive.** `ppg` can only go negative when the raw reading rises more than `dc * 0.01` above the baseline, about 163 counts at an infrared baseline of 16300. The pulse swings mostly downward, so although peak-to-peak reaches 285 counts, the largest upward excursion in any capture is 55. That leaves a factor of three in hand.

**Note**: Reading `old_value` matters. Calling `step()` here would push the same sample through the filter a second time and disturb the DC estimate that `Pulse_oximeter` is using for SpO2.

<br />

### What a real trace looks like

Six seconds of output, 302 samples:

```
peaks at samples : 20, 68, 117, 166, 211, 258
intervals        : 960, 980, 980, 900, 940 ms
beat-to-beat rate : 62.5, 61.2, 61.2, 66.7, 63.8 bpm
mean 63.1 bpm, standard deviation 2.0 bpm
```

Averaging the six beats with their systolic peaks aligned gives the pulse shape:

```
 -200 ms  165.8  ##
 -160 ms  166.0  ##
 -120 ms  164.7
  -80 ms  166.3  ###
  -40 ms  183.2  ##########################
   +0 ms  193.3  ########################################   <- systolic peak
  +40 ms  190.8  #####################################
  +80 ms  187.3  ################################
 +120 ms  186.7  ###############################
 +160 ms  185.2  #############################
 +200 ms  181.2  #######################
 +240 ms  178.2  ###################
 +280 ms  177.5  ##################
 +320 ms  176.7  #################
 +360 ms  175.2  ###############
 +400 ms  173.2  ############
 +440 ms  171.5  ##########
 +480 ms  170.3  ########
 +520 ms  169.8  ########
 +560 ms  168.8  ######
 +600 ms  167.8  #####
```

The asymmetry is what makes this a real pulse rather than noise. The upstroke takes 80 ms as the heart ejects blood toward the fingertip; the decay is still running at +600 ms, the end of the window above, and reaches baseline near +680 ms. Noise and interference rise and fall symmetrically.

The decay hesitates twice. The later pause, near +260 ms, is the dicrotic notch, the pressure wave that bounces back when the aortic valve closes. The earlier one near +120 ms is a separate reflection returning from the peripheral vessels. At this amplitude both stay hesitations rather than resolved dips.

This capture ran at 0.21 % PI, well below the 1.62 % of the best SpO2 recording, yet the waveform is clean. A low PI on its own is survivable; what kills the signal is baseline drift, which stayed small here. It also explains why SpO2 stalls more readily than the waveform does: SpO2 needs both channels working at once, and red carries a third to a half of the pulse strength of infrared.

<br />

## Brief Summary

This is a working reflectance pulse oximeter on an ESP32 that reads SpO2 and heart rate from a MAX30102 over I2C. Debugging was the main focus of the project. The sensor's useful signal is about 1 % of what it reads, and that ratio is unforgiving: all eight problems produced the same flat `0 %`, regardless of the stage. A layered test harness turned that single ambiguous symptom into a specific answer and caught fixes that were themselves broken.

<br />

## References

* [Analog Devices, MAX30102 product page](https://www.analog.com/en/products/max30102.html)
* [FLAG FM636A](https://www.flag.com.tw/maker/FM636A)
* [SparkFun MAX3010x Sensor Library](https://github.com/sparkfun/SparkFun_MAX3010x_Sensor_Library), the origin of this driver
