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

## Signal Filtering

Problem 7 above was fixed by retuning the one-pole DC tracker from alpha 0.99 to 0.95. That worked, and it was still a patch. This section is the durable version, which lives in `filters.py`.

Splitting the code out came first. `IIR_filter` used to live in `pulse_oximeter.py`, so three other sketches were importing a general purpose filter from a module named after blood oxygen. The classes now sit in two files by what they do: `filters.py` maps one sample to one sample, `detectors.py` tracks where you are inside a cycle. Nothing in either knows about SpO2, so the period window and the corner frequencies are constructor arguments and the same code serves a pulse, a breath, or an R wave.

<br />

### Alpha is a frequency in disguise

`IIR_filter(0.95)` says nothing about what it does. The same filter written as a corner frequency does:

$$f_c = -\frac{\ln \alpha \cdot f_s}{2\pi}$$

| alpha | corner frequency | in cycles per minute |
| :--- | :--- | :--- |
| 0.99 | 0.08 Hz | 4.8 |
| 0.95 | 0.41 Hz | 24.5 |

A resting heart is 60 cycles per minute. A tracker that corners at 4.8 was never going to follow a finger settling onto the sensor, and reading it as 0.99 gives no hint of that. `IIR_filter.from_cutoff(50, 0.41)` returns alpha 0.9498, so the two forms agree and the frequency one explains itself.

<br />

### The band-pass

A one-pole rolls off at 6 dB per octave, which is gentle enough that a 0.25 Hz drift still gets through at half strength. `Biquad` is a second order section at 12 dB per octave, and `BandPass` puts a high-pass at 0.5 Hz in front of a low-pass at 5 Hz. That band is 30 to 300 bpm.

Two sections rather than the cookbook band-pass biquad, which is built around a centre frequency and a Q. That suits a narrow band. Ours spans more than three octaves, and one section stretched that wide develops a peak instead of a flat top. Measured response of the cascade:

| frequency | gain | |
| :--- | ---: | :--- |
| 0.05 Hz | 0.010 | drift, rejected |
| 0.25 Hz | 0.242 | |
| 0.50 Hz | 0.707 | corner, -3 dB |
| 1.00 Hz | 0.969 | 60 bpm |
| 2.00 Hz | 0.987 | |
| 5.00 Hz | 0.700 | corner, -3 dB |
| 15.0 Hz | 0.056 | noise, rejected |

The passband sits between 0.97 and 0.99, so **the band-pass does not amplify anything**. It removes what is not the pulse. That distinction took a while to land, because the obvious expectation of a filter is that the signal gets stronger.

Second order sections have to be started carefully. From zero state a 16000 count input makes the filter ring for seconds, which is bug 2 all over again. `Biquad._prime()` solves the steady state equations for the first sample and loads the result, so a constant input produces exactly zero output from the first sample with no warm-up at all.

<br />

### What it bought

Energy in each band, before and after, as a percentage of the total:

| capture | drift, pulse, noise before | after |
| :--- | :--- | :--- |
| trace1, poor contact | 10.2 / 84.0 / 5.8 | 4.0 / **94.0** / 1.9 |
| trace2, good contact | 3.0 / 88.2 / 8.7 | 1.3 / **95.6** / 3.1 |
| trace3, worst drift | 31.4 / 64.0 / 4.6 | 20.2 / **78.1** / 1.7 |

The gain is largest where contact is worst, and on a good capture there is nearly nothing left to remove. That is why the change is invisible on a clean recording.

Where it matters more is beat detection, because `AC_extractor` needs the signal to cross zero in both directions:

| capture | one-pole, alpha 0.95 | band-pass |
| :--- | :--- | :--- |
| trace1 | r = 0.47, **+16 / -104** | r = 0.50, +74 / -46 |
| trace2 | r = 0.66, +60 / -60 | r = 0.67, +77 / -43 |
| trace3 | **r = 0.18**, +92 / -28 | **r = 0.38**, +64 / -56 |

trace1 sat almost entirely on one side of zero, which is exactly the condition that stalls the beat detector. Both marginal captures come back into balance, and the good one is untouched.

On an auto-scaling plot the visible effect is the pulse taking up more of the height, since drift no longer eats the vertical range: 79 to 83 % before, 92 to 102 % after.

**A note on precision.** ESP32 MicroPython uses single precision floats, and biquads lose accuracy as the corner frequency approaches DC. Running the same capture in float32 and float64 differs by 0.035 counts on a 32 count signal, about 0.1 %, so 0.5 Hz at 50 Hz is comfortable. Keep `fc / fs` above roughly 0.001. Respiration at 0.1 Hz would need a lower sample rate, not a lower corner.

<br />

### Automatic gain control (AGC)

`AGC` is the part that does make the trace taller, by dividing out a running estimate of the current amplitude. Across the three captures, perfusion spanning 6.3x comes out within 1.3x:

| capture | PI | without AGC | with AGC |
| :--- | ---: | ---: | ---: |
| trace1 | 0.195 % | 31.7 | 189.6 |
| trace2 | 1.228 % | 200.2 | 152.2 |
| trace3 | 0.440 % | 71.7 | 200.0 |

A weak pulse then fills the plot the same as a strong one. Two things this costs, both worth knowing before using it anywhere but a display. Amplitude information is gone, so the trace height no longer tells you anything about contact quality and it must never feed a perfusion or SpO2 calculation. And with no finger on the sensor the envelope collapses and noise gets the full gain, which is what the `floor` argument caps.

The first version of this had an instant attack: any sample above the envelope became the envelope. That makes the output land on exactly the target, so every systolic peak came out as a flat plateau. Replaying captures measured 20 to 36 samples of flat top, 0.4 to 0.7 s, which erases the peak the ECG comparison needs a landmark from.

The fix is an attack that is fast but not instant. At `attack_hz=0.5`, half the pulse fundamental, the 0.32 s time constant cannot follow an 80 ms upstroke:

| attack | flat top | normalisation | recovery after the pulse weakens |
| :--- | :--- | :--- | :--- |
| instant | 20 to 36 samples | 1.04x | 1.6 s |
| 0.5 Hz | 4 samples | 1.13x | **1.0 s** |

Four samples is what the band-passed waveform's own peak measures, so nothing is being flattened. The slower attack also recovers faster and works over a wider range of beat thresholds.

<br />

## PPG Waveform

`ppg.py` skips the SpO2 arithmetic and prints the pulse waveform instead, one value per sample at 50 Hz. Thonny's Plotter draws it live, and the on-board LED flashes on each detected beat. The point is to have a signal that can later be lined up against an ECG trace.

It talks to the driver directly rather than through `Pulse_oximeter`. That class runs the whole SpO2 chain, a second DC filter, both AC extractors and the rate calculator, and this file would read one number out of it. Going direct halves the per sample work and keeps `detectors.py` out of memory.

Three decisions are hiding in the following three lines:

```python
ir = sensor.pop_ir_from_storage()
ac, dc = ppg_channel.step(ir)           # 0.5 to 5 Hz, plus a slow baseline
ppg = int(agc.step(-ac) + AGC_TARGET)   # negated, then lifted clear of zero
```

* **Infrared, not red.** On the two captures where both channels show a detectable pulse, band-passed infrared measures 2.6x and 1.9x the red channel. On the worst capture, red carries more energy than infrared, but none of it is a heartbeat: its autocorrelation peaks at the 200 bpm edge of the search range with r = 0.20, while infrared lands on 75 bpm at r = 0.38. Red loses first as contact degrades, which is the case worth designing around.
* **Negate the AC, do not plot it as it comes.** In reflectance, the artery blocks more light at systole, so the raw count *drops* on each beat. Without the minus sign the waveform is upside down against every published PPG trace.
* **The offset only moves the trace, it does not clip it.** Band-passed output is centred on zero, and `AGC_TARGET` lifts it to a readable place. The trough still goes negative, around -40 against a target of 100, and that is left alone. Clamping it with `max(..., 0)` would flatten the diastolic trough the same way the instant attack flattened the peak.

**Note**: `set_led_mode(2)`, not 1. The driver calls mode 1 "IR only", but `MAX30102_MODE_IR_ONLY = 0x02` is the chip's heart rate mode, which lights LED1, the red one. Mode 2 is the only setting that fills the infrared buffer this file reads. The same mislabelling caused problem 4.

<br />

### What a real trace looks like

Six seconds of output, 302 samples. This capture predates the band-pass and the AGC, so the numbers describe the plain `dc * 1.01 - ir` trace:

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

The filtering came after the device already worked, and it is the part that generalises. `filters.py` and `detectors.py` are described by sample rates and corner frequencies rather than by tuned constants, so the respiration and ECG sketches in the neighbouring folders use the same code. The measurement that took longest to accept is that a band-pass has a gain of one: it decides what reaches the output, not how loud it is.

| file | holds |
| :--- | :--- |
| `filters.py` | `IIR_filter`, `Biquad`, `BandPass`, `Channel`, `AGC` |
| `detectors.py` | `AC_extractor`, `Rate_calculator` |
| `pulse_oximeter.py` | the SpO2 chain, used by `spo2.py` |
| `max30102.py`, `circular_buffer.py` | the driver, ported from SparkFun |
| `sim/` | the off-device harness, `python3 sim.py` |

<br />

## References

* [Analog Devices, MAX30102 product page](https://www.analog.com/en/products/max30102.html)
* [FLAG FM636A](https://www.flag.com.tw/maker/FM636A)
* [SparkFun MAX3010x Sensor Library](https://github.com/sparkfun/SparkFun_MAX3010x_Sensor_Library), the origin of this driver
