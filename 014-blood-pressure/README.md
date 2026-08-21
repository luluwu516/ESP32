# Cuffless Blood Pressure by Pulse Wave Transit Time

> Note: this is a learning project. It reports a number in mmHg that has never been checked against a cuff, so that number is not your blood pressure. It measures *pulse wave transit time*, and it can show that transit time moving when your circulation does. Use certified equipment for anything health-related.

<br />

A heartbeat is one event that reaches two sensors at two different times. The ECG electrodes see the ventricles depolarize; a few hundred milliseconds later the photoplethysmograph on a fingertip sees the pressure wave arrive. That gap is the **pulse wave transit time (PWTT)**. It shortens as arteries stiffen, which rising blood pressure does.

The measurement is a subtraction between two clocks. Signal amplitude never enters it; only arrival time does. That constraint drives the firmware design choices, and each fault in the Debugging section turned out to be a timing fault in disguise.

> This is an AI-assisted project. The signal chain came together in an afternoon, then produced a number that wouldn't move for a week. Each fix below came from adding one measurement to the status line and reading it. Three confident diagnoses along the way were wrong, and the working pattern was to stop reasoning and print the number.

<img width="800" alt="MAX30102 and AD8232" src="https://github.com/user-attachments/assets/8d30f663-4ee8-44c8-addc-9b2c148cac96" />

<br />

## Mechanism: How does it work?

### Why timing is the whole problem

A linear fit over `pwtt_bp.txt`, the 61-row training set that ships with the model:

$$\mathrm{BP} \approx 216 - 0.41 \cdot \mathrm{PWTT}$$

| Property | Value |
| :--- | :--- |
| Samples | 61 |
| PWTT range | 130–275 ms |
| Systolic range | 104–150 mmHg |
| Slope | **−0.41 mmHg per ms** |

**One millisecond of timing error is 0.41 mmHg.** That number is the budget the rest of the design spends against:

| Error source | Cost | Fix |
| :--- | :--- | :--- |
| Quantizing the R-wave timestamp to a 50 ms window | ±20 mmHg | detect R on every loop iteration, not on the window |
| PPG sampled at 50 Hz | ±8 mmHg | run the sensor at 100 Hz |
| Band-pass group delay at 5 Hz | 18 mmHg, one-sided | move the corner to 8 Hz, subtract the rest |
| One dropped FIFO sample batch | tens of mmHg | see Debugging |

<br />

### The three cadences

The loop does three things at three rates, and keeping them separate is what makes the timing work.

| Rate | Work | Why |
| :--- | :--- | :--- |
| Every iteration, ~800 Hz | read the ADC, compare against the R threshold | the R upstroke is ~30 ms wide and its timestamp *is* the measurement |
| 100 Hz | poll the I2C FIFO, filter, detect the pulse | the sensor's own rate |
| 50 ms | update the ECG baseline | a five-second time constant needs no faster feed |
| 1 s | print the status line | see below |

`011-ecg` reports the **maximum** of each 50 ms window. That peak-hold survives here, feeding the baseline and nothing else; the trigger comparison runs on the instantaneous sample. Quantizing the R timestamp to the display window would have cost more than the other three error sources combined.

`011-ecg` also printed one line per window, twenty a second, and that loop held a single `adc.read()` and could afford it. Here the loop is the measurement. One status line costs 6–35 ms, so twenty of them spend up to 700 ms of every second not looking at the ADC, and any R found on the far side of a print carries a timestamp that late. The baseline kept its 50 ms tick; the print moved to its own.

The 100 Hz row is a throttle, not a schedule. `sensor.check()` reads two FIFO pointers before it knows whether anything is waiting, and on SoftI2C that question costs four bus transactions, about 3 ms. Asking it at loop rate caps the loop and blinds the ADC for those 3 ms, so it asks at the rate the chip can answer.

<br />

### Finding the R wave

Unchanged from `011-ecg`: a single-pole IIR tracks the baseline of the peak-held values, and a beat registers when a raw sample crosses it by a fixed margin.

$$b_n = \alpha b_{n-1} + (1-\alpha) x_n, \qquad \alpha = 0.99, \qquad \mathrm{trigger} = b_n + \mathtt{BEAT\_MARGIN}$$

Fed at 20 Hz, $\alpha = 0.99$ gives a five-second time constant. A 500 ms refractory period rejects the T wave, which lands 250–300 ms after R.

`BEAT_MARGIN` came from `011-ecg` at 330 and had to come down to 200. Electrode signal strength is a property of the sitting, not of the code, and on this hardware the second-best peak often landed below a 330 threshold: 2109 against 2301, 2070 against 2303, 2087 against 2301. Watch the two numbers in `ECG:peak/threshold` converge and lower it further.

The five-second time constant also sets how long the warm-up has to be, and that took two runs to get right. See Debugging.

<br />

### Finding the pulse

The project departs from the book's version here for repeatability.

The book detects a pulse when a DC-removed signal crosses a **fixed threshold of 20 counts**. Perfusion varies more than sixfold between people and between sittings, so that threshold lands at a different height on the upstroke each sitting. The upstroke height sets the timestamp.

Instead, the signal passes through an automatic gain control (`AGC` in `filters.py`, shared with `010a`) that divides out a running amplitude estimate, and the trigger sits at **50 % of the normalized height**. Simulated against the same synthetic pulse:

| AC amplitude | Book: one-pole DC, +20 counts | Here: AGC, 50 % |
| :--- | :--- | :--- |
| 300 counts | 33.6 ms after the foot | **83.6 ms** |
| 500 counts | 25.7 ms | **83.6 ms** |
| 800 counts | 18.6 ms | **83.6 ms** |

The AGC trigger holds still. The book's slides show 15 ms across that range, 6 mmHg of scatter produced by how hard you press your finger.

Two consequences:

* 50 % of amplitude sits on the steepest part of the upstroke, where noise moves the crossing least.
* This pipeline reports a PWTT about **58 ms longer** than the one `bp_model.json` was trained on. `PPG_DELAY_MS` carries that difference, and the code subtracts it before the model sees the number.

That 58 belongs to one filter chain, so both programs have to run that chain. Ahead of the AGC sits a one-pole DC estimate subtracted from the raw IR, then a second-order low pass at 8 Hz. `blood-pressure.py` used to run `filters.Channel` instead, whose second-order high pass triggers 10 ms earlier on the same synthetic pulse at any amplitude:

| Chain | Foot to trigger, 100 Hz | Grid removed |
| :--- | :--- | :--- |
| `Channel`, two biquads | 80.0 ms | 71.25 ms |
| One-pole DC subtract plus low pass | 90.0 ms | 83.75 ms |

Two programs, one heartbeat, PWTTs 10 ms apart. Four mmHg of disagreement for nothing, and the cheaper chain is the one that stayed: subtracting a one-pole DC estimate *is* a high pass, 6 dB per octave against 12, and the AGC behind it cannot tell the difference.

<br />

### From PWTT to a number

`bp_model.json` is a 1→20→20→20→1 dense network trained by `bp_model.py`, normalized as `pwtt/200` in and `bp/100` out. Evaluating the shipped weights:

| PWTT | Model output |
| :--- | :--- |
| 130 ms | 122.3 mmHg |
| 180 ms | 147.9 mmHg |
| 218 ms | 125.7 mmHg |
| 250 ms | 109.2 mmHg |
| 275 ms | 109.4 mmHg |

That table shows two problems. Below 180 ms, the curve runs **backward**, against physiology, because 55 of the 61 training rows sit in 180–275 and the low end rests on one contradictory point at (130, 114) that three layers of twenty units memorized. Above 250 ms, the curve goes **flat**, so any longer measurement returns the same 109.4.

`cal_bp()` clamps its input to **180–275 ms**, the region the data supports, and says so when it does:

```
!! pwtt 282 over training range, BP is a floor
```

The code collects five beats and takes the **median**. One mispaired beat drags a mean of five by tens of milliseconds.

<br />

## Connection Tables

| MAX30102 | Meaning | ESP32 |
| :--- | :---- | ---: |
| VIN | Power | 3V |
| GND | Ground | GND |
| SCL | I2C clock | 22 |
| SDA | I2C data | 21 |

<br />

| AD8232 | Meaning | ESP32 |
| :--- | :---- | ---: |
| 3.3V | Power | 3V |
| GND | Ground | GND |
| OUTPUT | Amplified ECG signal | 36 (ADC1_CH0) |
| LO+ | Leads-off detect | 32 |
| LO− | Leads-off detect | 33 |

<img width="400" alt="Connection" src="https://github.com/user-attachments/assets/cdcf2823-cdc0-46d2-bab5-1082f68d044b" />

<br />

Electrodes follow the Lead I placement from `011-ecg`: RA below the right collarbone, LA below the left, RL on the lower right abdomen. Rest your finger on the MAX30102 without pressing. Pressure flattens the capillaries and takes the perfusion signal with them.

The onboard LED on pin 5 flashes on each accepted pulse, so you can see whether the PPG side is alive without reading the log.

<br />

## Firmware

| File | Role |
| :--- | :--- |
| `blood-pressure.py` | serial version, prints PWTT. The reference for signal work |
| `bp-web.py` | adds Wi-Fi, the model, and the web page |
| `index.html` | systolic reading and heart rate, one request every 5 s |
| `filters.py` | `IIR_filter`, `Biquad`, `AGC`, shared with `010a` and `012` |
| `detectors.py` | `Rate_calculator`, shared with `010a` |
| `max30102.py` | sensor driver, shared with `010` and `010a` |
| `bp_model.json` | the trained network, from `CH10/模型/` |
| `bp_model.py` | desktop training script, needs TensorFlow. **Do not upload** |

The two programs share their measurement path line for line. `bp-web.py` adds timing instrumentation, the model call, and a `Shared` object the web handlers read; the ECG block and the 50 ms tick are identical text. Anything that changes how a beat is timed has to land in both, and a diff of those blocks is the check.

`index.html` belongs to `bp-web.py`, not beside it. Upload one without the other, and the page requests a route the board does not serve.

Two driver notes, both found the hard way:

* **LED mode 1 is broken.** It files its single channel into `sense.red` while `available()` counts `sense.ir`, so `available()` returns zero forever. Stay on mode 2.
* **`dc` full scale is 32767**, not 262143. `fifo_bytes_to_int` right-shifts the 18-bit value by 3 at `pulse_width=411`.

<br />

## Debugging

Nine faults, in the order I found them. Each one hid the next.

### The heart rate that stayed at zero

PWTT printed 237, 245, 243, 241 while the heart rate read `0.0`. Both come from the same pulse detector, so one of them was lying.

`Rate_calculator` counts rising edges. The contact-quality gate cleared its flag and then hit `continue`, skipping the `rate.update()` call that would have passed the change on:

```python
if agc.env < PPG_MIN_ENV:
    pulse_is_beating = False
    pulse_accepted = False
    continue            # <- is_cycling latches True, and never sees another edge
```

`is_cycling` latched high, and no later beat registered as an edge. Simulating a weak signal against the real `filters.py` reproduced it:

| Signal | env range | triggers | rate, as written | rate, fixed |
| :--- | :--- | :--- | :--- | :--- |
| strong | 130–182 | 77 | 76.9 | 76.9 |
| medium | 21–29 | 76 | 76.9 | 76.9 |
| **weak** | **14–20** | **71** | **0.0** | **76.9** |

Detection held in all three rows. The rate died in one, when the envelope grazed the gate.

<br />

### The gate I put inside the signal

`PPG_MIN_ENV` was supposed to mean "no finger". I had set it to 20, and a live but weak finger produced an envelope of 14–20, so the gate fired thousands of times a minute on live data.

The AGC's own `floor` of 16 already caps the gain: with nothing on the sensor, the output tops out near 12, under the trigger. The gate has to catch a dead signal and nothing else, so it moved to 5.

<br />

### More light made it worse

With the envelope small, raising the LED current from MEDIUM to HIGH looked obvious. It produced `dc:32766`, pinned at full scale. The waveform clipped flat, `env` fell to 0.4, and the detector found one beat in ninety seconds.

Past saturation, more light causes a small envelope. `dc` belongs in the middle of the range, and MEDIUM puts it at 16500–18300 on this hardware.

<br />

### The ECG threshold that chased itself

`ECG:4095` appeared thirteen times in one run, the AD8232 railing. The peak-held value feeds the baseline, so those 4095s dragged the threshold from its usual 2218–2331 up to 2328–2555, and the five-second time constant held it there. The normal R waves behind the clipping then sat below threshold, costing 56 % of the beats.

A clipped window carries no amplitude information, so it no longer updates the baseline. A `clip:` counter reports it, since the fault is in the hardware and no constant will fix it.

<br />

### The driver that threw away 16 % of the signal

```python
# max30102.py
STORAGE_QUEUE_SIZE = 4
```

`check()` moves each pending sample out of the chip's 32-deep FIFO into that buffer, and `CircularBuffer.append` drops the **oldest** when full. With the loop stalling ~240 ms once a second at 50 Hz:

| | |
| :--- | :--- |
| Samples the chip produced during the stall | 12 |
| Buffer capacity | 4 |
| Silently discarded | **8, oldest first** |

The discarded samples included pulse upstrokes, so the trigger fired on a later survivor. I raised the buffer to 32 to match the chip's own FIFO, at a cost of a few hundred bytes.

This also broke something upstream. `available()` saturates at `STORAGE_QUEUE_SIZE`, so an earlier attempt to use it as a stall detector read a constant 4 and measured nothing.

<br />

### The second thread that cost 90 % of the CPU

The book runs the web server in a `_thread`. I measured it against identical code, with the radio associated in both runs:

| | with `_thread` | polled from the loop | no server at all |
| :--- | :--- | :--- | :--- |
| Loop rate | 100/s | 450/s | 1300/s |
| Stalls per second | 12 × up to 234 ms | 3–6 × ~320 ms | 0–2 × under 23 ms |
| R vs P beat counts | 20 % apart | 50 % apart | **equal** |
| PWTT | 271–365 | not measured | 247–268 |

The GIL handoff between two MicroPython threads costs an order of magnitude, and it lands on the loop whose timing is the measurement. Before running this comparison, I blamed garbage collection, then the status print. A `mem:` field showed 43–70 kB free and a `pr:` field showed the print costing 6–35 ms, so both guesses died, one run each.

<br />

### The poll that took 100 ms

Removing the thread left 3–6 stalls a second, with `handleClient()` running five times a second. Timing that call:

```
web:507ms/0
```

507 ms out of each second, and zero connections accepted. The cost sits in `poller.poll(1)`, whose 1 ms timeout is not 1 ms on this port. Swapping it for a non-blocking `accept()` that returns at once when no client is waiting:

```
web:5ms/0
```

`loop` went to 1300/s, matching a run with no web server at all.

<br />

### Five seconds was one time constant

$\alpha = 0.99$ fed at 20 Hz gives a time constant of five seconds, and `WARMUP_MS` was 5000. One time constant is 63 % of the way there.

The AD8232 spends most of that settling itself, so the baseline seeds on the transient and climbs out of it. From a soft reboot, the first window it sees is around 300 counts against a steady state near 1950:

| `WARMUP_MS` | Predicted threshold | Measured |
| :--- | :--- | :--- |
| 5000 | 1550 | 1467 |
| 10000 | 1931 | 2000 |
| 15000 | 2070 | 2119 |

I expected a threshold 600 counts low to produce extra triggers. It produced the opposite. `ecg_rearm` is the baseline itself, so a baseline sitting under the signal's own trough never gets crossed downward and `r_is_high` latches on: R stuck at 1 for three seconds while the PPG counted 4, then tracking at the right rate for the rest of the run and three beats behind.

Three time constants. `BASELINE_MIN_FEEDS` counts the windows the filter received and the seconds that passed, since `ECG_CLIP` skips the railed ones and a clipping front end can reach 15 s while feeding the filter far less.

<br />

### The zero I did not read

`web:5ms/0` sat on the status line for three sessions while I read it as "serving is cheap". The second number counts accepted connections. It was zero because no browser was attached.

With the page open:

| Connections that second | Web time |
| :--- | :--- |
| 0 | 5 ms |
| 2, both served | 444–462 ms |
| 1, timing out | 308–316 ms |

One request cost **228 ms** of the sampling loop, and the page asked for two every three seconds, plus one the browser opened and never used. A quarter of the loop was spent blind to the ECG. `R/P` ran 29/35, and the ECG heart rate read 49–55 against the PPG's 65–70.

I blamed Nagle's algorithm. `ESPWebServer.ok()` writes the status line and the body as two segments, and a second segment waiting on a client's delayed ACK is a textbook 200 ms. Rewriting it as one write with `Content-Length` took a request from 243 ms to 228 ms, so that theory died too. Whatever the 200 ms is, it sits below HTTP.

Asking for less worked. `/hr` and `/bp` became a single `/data`, and the page polls every 5 s:

| | Before | After |
| :--- | :--- | :--- |
| Connections | 3 per 3 s | 1 per 5 s |
| Web time | 256 ms/s, 26 % | **37 ms/s, 3.7 %** |
| `[Errno 116] ETIMEDOUT` | every 3 s | gone |
| `gap` | 300–380 ms | 10–16 ms |
| `R/P` | 29/35 | **16/16** |

The rewrite earned its place anyway: `Connection: close` stopped the browser from holding a spare socket open until it timed out.

Two guards cover what is left. `R_MAX_GAP` refuses a PWTT whose R was found on the first iteration after a stall, because that timestamp is late by the stall length. `PPG_MAX_AGE_MS` refuses one whose pulse came out of a FIFO left to fill for longer than its 32 samples hold, because `CircularBuffer` drops the oldest and backdating assumes none went missing. Between them they caught every bad pairing in the logs above: −44, −27, −13, and one memorable 1072.

228 ms per connection is still there. Wi-Fi modem sleep fits it: two beacon intervals at 100 ms each, but this firmware answers `sta.config(pm=...)` with `unknown config param`, so the hypothesis stays untested.

<br />

## Results

`blood-pressure.py`, at rest, after the fixes above:

```
ECG:2582/2112  HR p/e:72.0/72.1  env:111.9  dc:17633  R/P:43/43  gap:13ms  lo:0  clip:0
--> PWTT: 234
ECG:2599/2120  HR p/e:72.0/72.1  env:131.3  dc:17590  R/P:44/44  gap:14ms  lo:0  clip:0
ECG:2612/2122  HR p/e:72.0/72.1  env:114.6  dc:17552  R/P:45/45  gap:17ms  lo:0  clip:0
```

Reading the line: the ECG peak against the threshold it had to clear, the two heart rates, the perfusion envelope and DC level, the two beat counts, the worst loop gap of the second, leads-off and clipping counts. A converging first pair or a drifting fourth pair both mean R waves are going missing. Those two comparisons diagnose most of the faults above.

Two independent sensors, two independent rate calculators, **0.1 bpm apart**, and beat counts that stayed equal for 45 beats. Nothing in the code couples them.

`bp-web.py`, a different session, with the page open:

```
ECG:2483/2133  HR p/e:74.9/68.9  env:113.1  dc:17966  R/P:8/8   gap:244ms  web:233ms/1  PWTT:243  BP:110.9
ECG:2777/2181  HR p/e:69.1/77.2  env:129.1  dc:17995  R/P:11/12 gap:10ms   web:5ms/0    PWTT:243  BP:110.9
ECG:2618/2169  HR p/e:69.1/77.2  env:97.9   dc:17872  R/P:15/15 gap:15ms   web:4ms/0    PWTT:240  BP:112.7
ECG:2496/2151  HR p/e:71.9/65.5  env:103.8  dc:17894  R/P:16/16 gap:12ms   web:8ms/0    PWTT:240  BP:112.7
```

One second in five carries the page's request and shows a 230 ms gap. The other four cost 5 ms, and `gap` sits where `blood-pressure.py` sits.

Three things worth reading from these:

* **The two heart rates agree.** 0.1 bpm on the serial run, a few bpm on the web run where a request lands every fifth second. They arrive from different sensors through different filters and nothing in the code couples them.
* **PWTT does not track heart rate.** Two `blood-pressure.py` sessions minutes apart, with identical constants, sat at 72 bpm and 94 bpm and both reported 219–232 ms. Transit time should be independent of rate, and it was, which argues the number measures what it claims to. (Those two are not comparable to the 234 above: `PPG_DELAY_MS` was 30 then and is 58 now, so the raw intervals differ by 28 ms.)
* **The spread is about 10 ms**, or 4 mmHg. That is the short-term repeatability of this method on this hardware. Averaging harder in the firmware will not shrink it, since it comes from physiology plus a 10 ms sample period.

The two programs land 10 ms apart across these sittings, 225–235 against 240–243. They run the same chain and the same `PPG_DELAY_MS`, so that gap isn't systematic, and the sample is too small to call it anything else. Deciding would take one sitting of swapping the two programs back and forth, which nobody has done.

<img width="400" alt="Result" src="https://github.com/user-attachments/assets/47c0f29c-fa47-40ef-8f1b-6f1ffc2fb3d9" />

<br />

## What is not verified

Nobody has compared the mmHg figure against a cuff. `PPG_DELAY_MS = 58` aligns this pipeline with the one the model was trained on, a geometric quantity you can simulate, and neither of them is aligned with real pressure.

The **trend** is demonstrable today: hold your breath, stand up, or come back from a walk, and the transit time moves in the direction it should. The 123.4 itself carries no claim.

Two ways forward, in increasing order of honesty:

1. Take one cuff reading, invert $\mathrm{BP} = 216 - 0.41\,\mathrm{PWTT}$ for the PWTT the model expects, then fold the difference into `PPG_DELAY_MS`.
2. Re-collect `pwtt_bp.txt` through this signal chain against cuff readings and retrain with `bp_model.py`. That also repairs the model's two defects: a usable input range of 180–250 ms, and an output range of 109–148 mmHg.

<br />

## Brief Summary

Two sensors, one heartbeat, and the few hundred milliseconds between them. The ECG side is `011-ecg` with its detection moved off the display window and onto each sample. The PPG side is `010a`'s filter chain plus an AGC that holds the trigger point still while perfusion varies.

The signal processing was the easy half. A PWTT measurement tolerates nothing that pauses the loop, and MicroPython on an ESP32 offers several ways to pause it: a four-deep driver buffer, a second thread, a socket poll with a misleading timeout, twenty status prints a second, one HTTP request. None of the five looks like a timing bug in the source. All five surfaced as a blood pressure that would not move.

Adding a counter to the status line found each one, and the counters that mattered most were the ones I already had and had misread. `web:5ms/0` looked like a cheap web server for three sessions. The zero was the connection count.

<br />

## References

* [Wikipedia, Pulse wave velocity](https://en.wikipedia.org/wiki/Pulse_wave_velocity)
* [Wikipedia, Photoplethysmogram](https://en.wikipedia.org/wiki/Photoplethysmogram)
* [Analog Devices, AD8232 datasheet](https://www.analog.com/media/en/technical-documentation/data-sheets/ad8232.pdf)
* [Maxim MAX30102 datasheet](https://www.analog.com/media/en/technical-documentation/data-sheets/max30102.pdf)
* [Robert Bristow-Johnson, Audio EQ Cookbook](https://www.w3.org/TR/audio-eq-cookbook/), the biquad coefficients in `filters.py`
* [MicroPython `_thread`](https://docs.micropython.org/en/latest/library/_thread.html)
* [FLAG](https://www.flag.com.tw/maker/FM636A)
