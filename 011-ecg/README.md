# AD8232 Single-Lead ECG Heart-Rate Monitor

> Note: this is a learning project. The circuit reads one lead through three adhesive electrodes, and nothing isolates the amplifier from a USB-powered board. You can see a QRS complex and count beats with it. Do not read a rhythm from it, and keep it off anyone while the board connects to mains-powered equipment. Use certified equipment for anything health-related.

<br />

The AD8232 is an integrated front end for measuring the heart's electrical activity. A heartbeat starts as a wave of electrical depolarization through the cardiac muscle, and that wave leaves a potential difference of about one millivolt on the skin. The AD8232 amplifies that difference a hundredfold, filters out the much larger interference riding on top of it, and hands the ESP32 an analog voltage that swings with each beat.

> This is an AI-assisted project. I used it to learn more in detail.

<img width="400" alt="AD8232 front" src="https://github.com/user-attachments/assets/e578062e-818c-4632-bb04-ea82185d5b93" />

<img width="400" alt="AD8232 back" src="https://github.com/user-attachments/assets/b01f9156-ac00-4600-a38c-a85ae479ae04" />

<br />

<br />

## Mechanism: How does it work?

<img width="400" alt="wikipedia ecg" src="https://github.com/user-attachments/assets/3ad3c23f-d1dd-4827-bc8d-6603a7657346" />


An electrical conduction system drives the heart. Each cycle produces three features that a single lead can resolve:

| Feature | Event | Relative size |
| :--- | :--- | :--- |
| P wave | The atria depolarize | Small |
| QRS complex | The ventricles depolarize | Largest, ~1 mV at the skin |
| T wave | The ventricles repolarize | Middling |

The **R** peak, the tall spike in the middle of the QRS complex, is the only feature this project needs. Timing the gap between consecutive R peaks gives the heart rate.

<br />

### Sources of interference

One millivolt is not much to work with, and it does not arrive alone:

* **Electrode half-cell potential.** The junction between gel and skin is an electrochemical cell, and it contributes a DC offset of up to ±300 mV, three hundred times the signal. A high-pass filter integrated into the amplifier's feedback loop blocks it, so the gain stage never sees it.
* **Mains interference.** Both electrodes pick up 50/60 Hz from the room almost identically. Because that interference is *common* to both inputs, an instrumentation amplifier rejects it: the AD8232 specifies 80 dB of common-mode rejection from DC to 60 Hz.
* **Motion.** Moving an electrode changes the half-cell potential it sits on. The chip cannot filter this one, because a motion artifact looks like a large, slow heartbeat.

The third electrode, on the right leg, carries a **right leg drive**. The AD8232 senses the common-mode voltage on the body and drives the inverse back in, holding the body where the amplifier can resolve the difference between the other two electrodes.

<br />

### From a voltage to a heart rate

The firmware samples the amplifier output as fast as the loop runs and reports the **maximum** seen in each 50 ms window. A QRS complex is 80–100 ms wide, so a plain 20 Hz sample would miss the peak on most beats; peak-hold puts the R wave in one or two windows. The output is an envelope rather than a waveform: the trace sits above the true baseline, and the P wave does not survive.

A beat registers when the reported value crosses a threshold set above the baseline. A single-pole IIR filter tracks that baseline across the reported values:

$$b_n = \alpha \cdot b_{n-1} + (1 - \alpha) \cdot x_n, \qquad \alpha = 0.99$$

At 20 Hz an $\alpha$ of 0.99 gives a time constant near five seconds, slow enough to follow electrode drift and too slow to follow the heartbeat. The trigger level is then

$$\mathrm{trigger} = b_n + \mathtt{BEAT\_MARGIN}$$

and the heart rate is the average over five intervals:

$$\mathrm{HR}\ (\mathrm{bpm}) = \frac{60000 \cdot N}{\sum_{i=1}^{N} \Delta t_i}, \qquad N = 5$$

Two guards bound the interval. A **refractory period** discards any crossing within 400 ms of the previous beat, and an upper bound of 2000 ms discards intervals too long to be a beat, resetting the average instead of corrupting it.

<br />

## AD8232 Features

* Fully integrated single-lead ECG front end
* High signal gain (G = 100) with DC blocking capability
* Two- or three-electrode configurations
* Common-mode rejection ratio: 80 dB (DC to 60 Hz)
* Low supply current: 170 µA (typ)
* Operating voltage: 2.0 V to 3.5 V
* Accepts up to ±300 mV of electrode half-cell potential
* Integrated right leg drive (RLD) amplifier
* 2-pole adjustable high-pass filter, 3-pole adjustable low-pass filter
* Fast restore feature improves filter settling
* Leads-off detection, AC or DC
* Shutdown pin
* −40°C to +85°C operating temperature range

<br />

## Connection Tables

The AD8232 operates at 3.3 V. Do not feed it 5 V, since the maximum operating supply is 3.5 V.

| AD8232 | Meaning | ESP32 |
| :--- | :---- | ---: |
| GND | Ground | GND |
| 3.3V | Power | 3V |
| OUTPUT | Amplified ECG signal | 36 (ADC1_CH0) |
| LO+ | Leads-off detect | 32 |
| LO− | Leads-off detect | 33 |
| SDN | Shutdown, active low | not connected |

<br />

| Buzzer | Meaning | ESP32 |
| :--- | :---- | ---: |
| − | Ground | GND |
| + | PWM drive, 2 kHz | 2 |

<br />

I left `SDN` unconnected on purpose. Pulling it low sleeps the chip and switches off the board's LED, which otherwise stays lit whenever the electrodes lose contact. Safety depends on the breakout: a pull-up resistor between `SDN` and VCC makes GPIO control fine, while a hard-wired connection to VCC turns a low output into a short across the supply. Measure the resistance between `SDN` and `3.3V` with the board unpowered to tell the two apart. A few tens of kΩ is safe, near zero is not, and a 1 kΩ resistor in series with the GPIO removes the risk either way. `LO+` and `LO−` already report what the LED reports, so I dropped the feature.

<img width="400" alt="connection" src="https://github.com/user-attachments/assets/e46d6055-f3f5-4d0d-9586-950a19c4f2b8" />

<br />

<br />

### Electrode placement

Three electrodes, in the standard Lead I arrangement. Colors follow the SparkFun sensor cable; verify yours before trusting them.

| Electrode | Color | Position |
| :--- | :--- | :--- |
| RA | Red | Right side of the chest, below the collarbone |
| LA | Yellow | Left side of the chest, below the collarbone |
| RL | Green | Lower right abdomen, or the right hip |

Torso placement gives a larger R wave than the wrists, and it moves less. Sitting still with your arms supported matters more than any constant in the code.

Run `ecg.py` while you position the electrodes. It prints the same 50 ms peak-hold values without beat detection, which is what you need to pick a value for `BEAT_MARGIN`. `ecg-with-buzzer.py` adds the detection, the beep, and the heart rate.

<br />

## Debugging: the double beep

Solving this one took real data. With `BEAT_MARGIN = 230`, most beats produced one beep and some produced two, with no pattern I could see.

I guessed first that the T wave was crossing the threshold, and added a 350 ms refractory period to cover the window where T waves land. The double beeps grew rarer without stopping, which turned out to be the useful clue: an intermittent failure after a timing fix points at timing that is marginal instead of wrong.

Working through a 120-sample capture by hand settled it. The mean of that capture, which is what the IIR baseline converges to, was **2032**. A margin of 230 put the trigger at **2262**:

| R wave (sample / value) | T wave that follows | Delay |
| :--- | :--- | :--- |
| 4 / 2634 | 10 / **2279** | 6 samples |
| 23 / 2559 | 29 / 2192 | 6 samples |
| 42 / 2489 | 47 / 2261 | 5 samples |
| 62 / 2525 | 67 / **2304** | 5 samples |
| 81 / 2642 | 87 / **2276** | 6 samples |
| 100 / 2414 | 106 / 2234 | 6 samples |

Three of the six T waves already sat above the trigger. Amplitude was rejecting none of them, and the refractory period was the only thing stopping them. At 5–6 samples they land 258–309 ms after the R wave, against a 350 ms window, leaving about 40 ms of room.

That room does not hold. Each pass of the loop includes a `print()` over USB serial, and how long it blocks depends on how fast the host drains the buffer, so the window runs 50–60 ms instead of a fixed 50. A few slow windows in a row push the T wave past 350 ms and it triggers.

The fix was to stop asking the refractory period to do the threshold's job:

* Highest T wave in the capture: **2304**, so the margin must exceed 2304 − 2032 = **272**
* Lowest R wave in the capture: **2414**, so the margin must stay below 2414 − 2032 = **382**

`BEAT_MARGIN = 330` sits in the middle of that band. Re-checked against the same 120 samples, it catches all seven R waves and rejects all six T waves. I raised the refractory period to 400 ms as a backstop, which costs nothing at rest and caps detectable heart rate at 150 bpm.

A fixed offset above a drifting baseline stays fragile. Across three captures taken minutes apart, the baseline moved between 1953 and 2034 and the R-wave amplitude moved with it, so the safe band for `BEAT_MARGIN` shifted each time: 175–285, then 271–431, then 272–382. Setting the threshold as a fraction of the measured R-wave height would track that drift on its own, and that is the next change to make.

<br />

## Results

A capture from `ecg-with-buzzer.py`, printing every 50 ms. I derived the thresholds above from this run, so it still shows the problem. The values are real, taken at rest with electrodes on the torso.

```
ECG: 1982
ECG: 1997
ECG: 1911
ECG: 2634     <- R wave
ECG: 2167
ECG: 1591
ECG: 1857
ECG: 2143
ECG: 2231
ECG: 2279     <- T wave, above the old trigger level of 2262
ECG: 2002
...
ECG: 2054
ECG: 2233
ECG: 2525     <- R wave
--> HR: 61.3
```

Three things to read from it:

* **The R waves are unambiguous.** Seven of them across the capture, at 2414–2642 against a baseline near 2032. Signal quality limited nothing here; each failure came from a threshold or a timer.
* **The intervals hold steady** at 19, 19, 20, 19, 19, 19 samples. Those 19 samples span one beat, and the code timed that beat at 61.3 bpm from real `ticks_ms()` values, which puts one sample at 979 / 19 = about 51.5 ms. Nothing in the code sets that period, so this is the only place it can be read from.
* **The highest T wave sits 110 counts below the lowest R wave**, 2304 against 2414. That gap is the whole discrimination problem. A single global threshold has to fit inside it, which is why the working band for `BEAT_MARGIN` spans a few hundred counts instead of a few thousand.

Heart rate averages five intervals before reporting, so the first reading takes about five seconds and later ones arrive every five beats.

<img width="800" alt="Screenshot 2026-08-06 at 5 04 17 PM" src="https://github.com/user-attachments/assets/614f5052-d202-44b8-a91d-4bd7b21e258a" />


<br />

## Brief Summary

A single-lead ECG on an ESP32: the AD8232 amplifies the potential difference between two chest electrodes, the ESP32 samples it with peak-hold windows, and a threshold above a drifting baseline picks out R waves to drive a beep and a heart rate.

Acquiring the signal worked early and well. Separating the R wave from the T wave took the rest of the project. In the worst case those two features differ by 110 counts out of 4096, and the constants governing that separation all interact: the baseline filter's time constant, the trigger margin, the refractory period, the sample window. I got the final values by measuring a capture instead of reasoning about one.

<br />

## References

* [Wikipedia - Electrocardiography](https://en.wikipedia.org/wiki/Electrocardiography)
* [Analog Devices, AD8232 product page](https://www.analog.com/en/products/ad8232.html)
* [AD8232 datasheet](https://www.analog.com/media/en/technical-documentation/data-sheets/ad8232.pdf)
* [SparkFun Single Lead Heart Rate Monitor hookup guide](https://learn.sparkfun.com/tutorials/ad8232-heart-rate-monitor-hookup-guide)
* [MicroPython `machine.ADC`, ESP32 port](https://docs.micropython.org/en/latest/esp32/quickref.html#adc-analog-to-digital-conversion)
