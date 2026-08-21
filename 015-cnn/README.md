# PPG Waveform Classification with a 1D CNN

> Note: this is a learning project. The classifier decides whether a captured waveform looks like a pulse, and it does that well enough to demonstrate. It does not decide whether the heart rate printed next to it is correct. Use certified equipment for anything health-related.

<br />

`010-pulse-oximeter` prints a heart rate whenever three beats arrive within the interval it accepts. It prints one for a finger. It prints one for a finger being wiggled, and on the serial line the two look the same. This project puts a 453-parameter convolutional network on the board to separate them, trained on waveforms the same firmware collected.

A classifier is a function of its input distribution. Here that distribution comes from four things: the sensor, a band-pass, an automatic gain control, and a padding rule. Change any one of them and the trained weights answer a different question without saying so.

> This is an AI-assisted project. None of the four faults below raised an exception, and none of them showed on the serial line. A network that has learned the wrong feature looks like one that has learned the right feature. I found each of them by re-implementing the forward pass in NumPy and running the shipped weights against the collected `.txt` files on the desktop.

<br />

## Mechanism: How does it work?

### The window the model sees

The capture rule comes from the book: accumulate the filtered waveform until **three beats** arrive with plausible intervals, then hand it over. The network takes 300 samples, so `trim()` truncates or zero-pads to that length.

At 50 Hz and a resting rate near 70 bpm, three beats take about 2.4 s.

| | |
| :--- | :--- |
| Sample rate | 50 Hz (chip runs at 400 Hz, averages 8) |
| Input length | 300 samples, 6 s |
| Real samples per capture, median | **120** |
| Zero padding, median | **60 %** |

Most of every training row is padding, and the padding grows as heart rate falls. The network can read that. The book's design puts it there, and it means part of the decision rests on how long three beats took rather than on their shape. Collecting a fixed 300-sample window would remove it, at the cost of counting beats separately.

<br />

### What goes into the window

The model and the beat detector read different signals. `ppg.py` in `010-pulse-oximeter` runs a band-pass into an AGC, and the AGC divides amplitude out. Amplitude is most of what separates a pulse from an artifact, so the loop builds two signals from each sample:

```python
ac, dc = ppg_channel.step(ir)

ppg_raw = int(-ac)                        # to the model: signed, real amplitude
ppg = int(agc.step(-ac) + AGC_TARGET)     # to the beat detector: normalised
```

The detector keeps the AGC, which lets one threshold work across a sixfold range of perfusion. The model reads the band-pass output. Both negate `ac`, because reflectance falls at systole.

Normalisation before inference uses the dataset's own statistics, computed on the training split:

$$x' = \frac{x - \mu}{\sigma}, \qquad \mu = -15.05, \qquad \sigma = 1257.09$$

Those two constants join the two programs, and they hold for one signal chain. Change the LED current, a filter corner, the AGC, or the sign, and they stop describing what the sensor now produces. `ppg_model.py` prints them at the end of every training run, and nothing else records them.

<br />

### The network

Unchanged from `CH11/ppg_model.py`, trained by TensorFlow on the desktop and converted to JSON by `keras_lite_convertor`:

| Layer | Output | Parameters |
| :--- | :--- | ---: |
| Reshape | 300 × 1 | |
| Conv1D, 4 filters, width 3, ReLU | 298 × 4 | 16 |
| MaxPooling1D | 149 × 4 | |
| Conv1D, 4 filters, width 3, ReLU | 147 × 4 | 52 |
| MaxPooling1D | 73 × 4 | |
| Conv1D, 8 filters, width 3, ReLU | 71 × 8 | 104 |
| MaxPooling1D | 35 × 8 | |
| Flatten | 280 | |
| Dense, sigmoid | 1 | 281 |
| | | **453** |

453 parameters and 10.9 kB of JSON. Inference on the ESP32 costs a pause too short to see between the third beat and the printed class. `keras_lite` is frozen into the FLAG firmware, so the board needs no installation.

<br />

### Three layers of judgement

The network answers one of three questions, and separating them is what makes each one work.

| Question | Method | Evidence it uses |
| :--- | :--- | :--- |
| Is a finger present? | DC threshold with hysteresis | how much light comes back at all |
| Is this waveform a pulse or an artifact? | the CNN | amplitude and shape |
| Is the contact pressure right? | *not implemented*, see below | upstroke/downstroke asymmetry |

The first question does not belong in the network, though that is where the original design put it. With no finger, the AGC's `floor` caps gain at `target/floor` = 6.25, so a 2 to 4 count noise signal reaches about 25 against a `BEAT_THRESHOLD` of 50. The detector almost never fires, three beats almost never accumulate, and the program stays quiet for a minute or more. A DC test needs no beats at all. It runs on every sample and reports within about 20 ms.

$$\text{finger on} \rightarrow \text{off at } dc < 9000, \qquad \text{off} \rightarrow \text{on at } dc > 15000$$

Two thresholds rather than one. With a finger present, DC sits at 16 300 to 17 500 and falls by about 9 counts per second as the LED warms. A single threshold placed just under the working value would cross it within the minute and chatter.

<br />

## Connection Table

| MAX30102 | Meaning | ESP32 |
| :--- | :---- | ---: |
| VIN | Power | 3V |
| GND | Ground | GND |
| SCL | I2C clock | 22 |
| SDA | I2C data | 21 |

<br />

Rest the finger on the sensor without pressing. The onboard LED on pin 5 flashes on each detected beat.

<br />

## Firmware

| File | Role | Upload |
| :--- | :--- | :---: |
| `ppg-collect-data.py` | capture and label training waveforms to a `.txt` on flash | yes |
| `ppg-cnn.py` | live classification | yes |
| `max30102.py` | sensor driver, shared with `010` and `014` | yes |
| `circular_buffer.py` | the driver's sample queue | yes |
| `filters.py` | `IIR_filter`, `Biquad`, `Channel`, `AGC`, shared with `010a`, `012`, `014` | yes |
| `ppg_model.json` | the trained network | yes |
| `ppg_model.py` | desktop training script, needs TensorFlow | **no** |
| `keras_lite_convertor.py` | desktop dataset reader and JSON writer | **no** |

The two bottom rows import `numpy` and `tensorflow` and target CPython. MicroPython v1.16 cannot parse them at all, since `keras_lite_convertor.py` uses an f-string and f-strings arrive in v1.17.

`ppg-collect-data.py` and `ppg-cnn.py` share their signal chain line for line, from `ppg_channel.step(ir)` down to `data.append(ppg_raw)`. Change one without the other and nothing raises an error. The model answers about a distribution it never saw.

<br />

## Workflow

```
1.  LABEL = "ppg"     ->  ppg-collect-data.py   ->  50 captures, finger resting
2.  LABEL = "others"  ->  ppg-collect-data.py   ->  50 captures, finger moving
3.  copy ppg.txt and others.txt off the board into ppg_classification/
4.  python3 ppg_model.py                        (desktop, not the board)
5.  copy the printed mean and std into ppg-cnn.py
6.  upload the new ppg_model.json
7.  ppg-cnn.py
```

`FILE_MODE = "a"` appends, so a second session adds to the first. A leftover file from an earlier signal chain also mixes two distributions without complaint, so delete the board's copies before starting a fresh collection.

Step 5 carries the workflow. `ppg-cnn.py` cannot tell a stale `mean` and `std` from a fresh pair, and a stale pair describes a signal chain the sensor no longer produces.

<br />

## Debugging

Four faults. None of them raised an exception, and none showed on the serial line. I found each one by evaluating the network's own weights offline against the `.txt` files on disk.

| # | Kind | Problem | Effect |
| :--- | :--- | :--- | :--- |
| 1 | Signal | The AGC divides amplitude out, and amplitude is most of what separates the two classes | The model reads the one representation with the discriminating feature removed |
| 2 | Model | The network learned amplitude and little else | Perfect on high-amplitude motion, 10 errors in 32 where amplitude cannot separate |
| 3 | Design | Three detected beats gated every report | With no finger the AGC floor holds noise under the beat threshold, so the program stayed quiet for a minute or more |
| 4 | Model | Dropping the ambiguous low-amplitude rows left `others` almost all high-amplitude | 300 zeros now score 0.971 as `ppg`, and the DC gate is the only remaining defence |

Fault 1 sits at the boundary between training and inference. Faults 2 through 4 are about which feature the network settled on.

<br />

### 1. The gain control that erased the answer

The book's two classes differ mostly in size: `others` spans ±14512, `ppg` spans ±588. Any classifier will find that.

The AGC from `010-pulse-oximeter` divides it out. Its docstring says as much, *"Amplitude information is gone"*, while forbidding the AGC to feed an SpO2 calculation. The same sentence rules it out here. Feed the AGC output to the model and only shape remains, for a network with 453 parameters and 100 examples per class.

Splitting the signal in two, `ppg_raw` for the model and `ppg` for the detector, costs one line and gives the classification its feature back.

<br />

### 2. Amplitude was the whole model

The trained weights scored 91 % against the collected dataset, with every error in one place:

| `others` captures | Count | Wrong |
| :--- | ---: | ---: |
| Amplitude ≥ 470 (motion) | 68 | **0** |
| Amplitude < 470 (pressed too hard) | 32 | **10** |

All ten errors ran `others → ppg`, all ten at low amplitude. So I ran a controlled test on those 32 rows against the 100 `ppg` rows, five-fold cross-validated:

| Features given to a logistic regression | Balanced accuracy | Pressed-tight caught |
| :--- | ---: | ---: |
| Amplitude alone | **51.6 %** | 1 / 32 |
| Whole waveform, per-row normalised | 74.0 % | 16 / 32 |
| Three shape descriptors | **86.5 %** | 24 / 32 |

51.6 % against a 50 % chance line. Amplitude cannot see pressing too hard, so no volume of extra training data repairs it in a network that has learned amplitude. Adding that data teaches "small means artifact", which condemns every weak pulse.

Shape carries it, for a physiological reason. A pulse is an arterial pressure wave: fast upstroke, slow decay, peak skewed early. Occlude the capillaries and a passive damped oscillation remains, closer to a symmetric sinusoid.

| Descriptor | Normal pulse | Pressed too hard |
| :--- | ---: | ---: |
| Mean rising slope ÷ mean falling slope | **2.005** | **1.076** |
| Fraction of samples rising | 0.286 | 0.424 |
| Skewness | 0.634 | −0.027 |

The three descriptors agree. A linear rule over them runs on the board in about ten lines with no model file, separating 24 of 32 pressed-tight captures while losing 2 of 100 normal ones. The rule is written down and not yet in `ppg-cnn.py`.

<br />

### 3. The silence that took a minute to report

With the finger removed, the program printed nothing for a minute, sometimes longer, then printed `ppg` with a plausible heart rate.

The AGC floor causes the silence: noise cannot reach `BEAT_THRESHOLD`, so three beats never accumulate. No code path reported anything without beats.

Moving the DC test out of the post-capture branch and onto every sample fixed both halves. The filters have to step before the test runs, or they freeze while the finger is away and the AGC envelope needs seconds to recover:

```python
thresh = thresh_gen.step(ppg)          # always, even with no finger

if finger_on and dc < DC_OFF:
    print("Class: others (no finger)")
    ...
if not finger_on:
    data = []
    ...
    continue
```

<br />

### 4. The model that learned silence is a pulse

Dropping the 32 ambiguous pressed-tight rows from `others.txt` and retraining stops the network learning that small means artifact. It costs something in return.

| Input | Before | After |
| :--- | :--- | :--- |
| 300 zeros | 0.404 → others | **0.971 → ppg** |
| ±2 count noise, 200 trials | 0 % ppg | **100 % ppg** |
| ±20 count noise, 200 trials | 0 % ppg | **100 % ppg** |

With `others` now almost all high-amplitude, the network has learned *large means artifact, everything else is a pulse*. It is wrong about silence, and confident.

The DC gate reaches that case first, which is what makes this workable, and no second line of defence remains behind it. What survives is a finger present but not pulsating, pressed too hard or resting without contact: the DC gate passes it, the network returns `ppg` at 0.89, and the program computes a heart rate from noise-triggered beats.

<br />

## Results

`ppg-cnn.py`, finger placed, removed, replaced, removed:

```
Class: others | dc: 16298 | amp: 2759
Class: ppg | dc: 16363 | amp: 298
HR: 70.7
Class: ppg | dc: 16381 | amp: 318
HR: 70.3
Class: ppg | dc: 16281 | amp: 308
HR: 70.7
Class: others (no finger)
Finger on!
Class: ppg | dc: 16640 | amp: 439
HR: 72.1
Class: ppg | dc: 16619 | amp: 435
HR: 71.8
Class: others (no finger)
Finger on!
Class: ppg | dc: 16918 | amp: 324
HR: 72.6
Class: ppg | dc: 16951 | amp: 254
HR: 72.0
Class: others (no finger)
```

The first line shows the network working: amplitude 2759 while the finger settles, called an artifact. `others (no finger)` and `Finger on!` arrive within one sample of the physical event rather than after three beats. Heart rate holds within 2 bpm across three placements, and `amp` stays between 254 and 469, inside the interquartile range of the `ppg` training set at 163 to 251. That last comparison is the check that the live distribution still matches the trained one.

Evaluating the shipped weights against the whole dataset:

| | |
| :--- | :--- |
| Overall | 95.5 % (191/200) |
| `ppg` recall | 100/100 |
| `others` recall | 91/100 |
| Outputs in 0.3–0.7 | 8/200, down from 27 |

<br />

## What is not verified

**That 95.5 % is in-sample.** 80 % of those rows trained the network. `ppg_model.py` holds out 15 rows for validation and 5 for test, too few to mean anything. The honest figure is lower and nobody has measured it. A 70/30 split with a fixed `random_seed` would produce a number worth quoting.

**Both classes come from one person, one sitting, one sensor.** Perfusion varies more than sixfold between people, and perfusion is the feature the network leans on.

**Pressed-tight contact goes undetected.** I measured it, characterised it, and kept it out of the training data, since it asks about contact quality rather than waveform class. The shape rule that handles it lives in this README and not in the firmware.

**Nothing checks the heart rate.** The classifier gates whether a rate prints. Whether that rate is right belongs to `010-pulse-oximeter`.

<br />

## Brief Summary

A 453-parameter network on a microcontroller, deciding whether 300 samples look like a pulse. It works. What went wrong along the way was about which feature the network picked up, never about its size or its training.

The AGC is the clearest case. It exists to make a weak pulse and a strong pulse reach the same height, which is what the beat detector wants and the reverse of what the classifier needs. One line splits the signal so each of them gets what it wants.

Accuracy hid the rest. Ninety-one percent covered a network that had learned one feature, and cross-validating that single scalar on its own returned 51.6 % where chance is 50. That number said more than the accuracy ever did. A DC threshold answers whether a finger is there. Three lines of arithmetic about waveform asymmetry answer whether the contact is right. The network answers what is left, which is the part worth spending 453 parameters on.

<br />

## References

* [Wikipedia, Photoplethysmogram](https://en.wikipedia.org/wiki/Photoplethysmogram)
* [Maxim MAX30102 datasheet](https://www.analog.com/media/en/technical-documentation/data-sheets/max30102.pdf)
* [Robert Bristow-Johnson, Audio EQ Cookbook](https://www.w3.org/TR/audio-eq-cookbook/), the biquad coefficients in `filters.py`
* [Keras, Conv1D](https://keras.io/api/layers/convolution_layers/convolution1d/)
* [MicroPython v1.17 release notes](https://github.com/micropython/micropython/releases/tag/v1.17), where f-strings arrive
* [FLAG](https://www.flag.com.tw/maker/FM636A)
