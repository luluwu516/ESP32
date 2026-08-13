# Thermistor Nasal-Airflow Respiration Monitor

> Note: this is a learning project. It counts breaths by watching air temperature change under the nose. It measures nothing about how much air moves, and a held breath through the mouth reads the same as no breathing at all. Use certified equipment for anything health-related.

<br />

A thermistor is a resistor whose resistance changes with temperature. Held in the airflow under the nostrils, it sits in warm air on the way out and cool room air on the way in, and its resistance follows. Wired as one arm of a voltage divider, that becomes a voltage the ESP32 can read: a slow wave, one cycle per breath, riding on a much larger DC level.

Nothing amplifies it. The entire breathing signal is **2–3 % of the ADC's range**, and the other 97 % is a constant that carries no information. Pulling that few percent out is the firmware's whole job.

> This is an AI-assisted project. The code was straightforward; getting it to produce a number was not. Almost every fix in the Debugging section came from pasting a capture and having it traced sample by sample against the detection logic, which is a much faster loop than re-running the board and guessing.

<br />

## Mechanism: How does it work?

### From temperature to a voltage

Exhaled air leaves the body near 34 °C and room air arrives at 22–25 °C. The bead does not reach either temperature — it has thermal mass, and a breath cycle only lasts a few seconds — so it oscillates over a fraction of that range.

An NTC thermistor loses resistance as it warms. In a divider it produces a voltage that rises on exhalation and falls on inhalation, which is the polarity the firmware assumes: **a rising edge is the start of an exhalation.** Swapping the two divider arms inverts this and the detector will lock onto inhalations instead. Nothing breaks, but the phase reported is no longer what the variable names say.

<br />

### What the signal actually looks like

Every number below comes from captures in this folder, not from a datasheet.

| Property | Measured |
| :--- | :--- |
| Baseline | 1760–2110 counts of 4095, different every sitting |
| Peak-to-trough swing, good contact | 87–131 counts |
| Swing as a fraction of full scale | 2–3 % |
| Noise after averaging | 3–5 counts |
| Rising edge | ~30 counts per sample |
| Breath period | 3.0–3.9 s (15–20 brpm) |

Two consequences follow from that table, and they set every constant in the firmware.

**The signal is small, so the sampling has to earn back the noise.** The loop reads the ADC continuously and reports the **average** over each 300 ms window rather than a single sample. Averaging every read in the window brings the noise down to 3–5 counts, which is what makes a 20-count trigger margin usable. The ECG project in `011-ecg` uses peak-hold over its window instead, because there the feature of interest is a 100 ms spike; here it is a 3.5 s wave, and averaging is strictly better.

**The signal is slow, so 300 ms sampling is plenty.** At $f_s = 3.33$ Hz against a breathing rate near 0.28 Hz, there are about 12 samples per cycle. That is comfortable for Nyquist and coarse for timing — see Results.

Because everything the firmware does is a *difference* between nearby samples, the ESP32 ADC's well-known nonlinearity does not matter here. The absolute value of the baseline is never used for anything.

<br />

### From a waveform to a respiration rate

Everything the detector needs comes from one structure: an **envelope**. Two bounds shrink toward their midpoint on every sample and get pushed back out by the real extremes once per breath.

```python
if rsp > peak:
    peak = rsp
else:
    mid = (peak + trough) / 2
    peak = mid + (peak - mid) * ENVELOPE_DECAY
```

$$\mathrm{amplitude} = \mathrm{peak} - \mathrm{trough}, \qquad \mathrm{mid} = \frac{\mathrm{peak} + \mathrm{trough}}{2}$$

The relaxation is a fixed *fraction*, not a fixed number of counts, and that is the whole point: $0.97^{12} \approx 0.69$, so the envelope gives up about 30 % per breath **at any amplitude**. A capture reading 130 counts and one reading 30 are described the same way.

From those two numbers come the baseline, the threshold, and the health check:

$$\mathrm{trigger} = \mathrm{mid} + 0.25 \cdot \mathrm{amplitude}, \qquad \mathrm{re\text{-}arm} = \mathrm{mid} + 0.10 \cdot \mathrm{amplitude}$$

and the rate is the average over two intervals:

$$\mathrm{RSP}\ (\mathrm{brpm}) = \frac{60000 \cdot N}{\sum_{i=1}^{N} \Delta t_i}, \qquad N = 2$$

**A threshold at a fixed number of counts above a baseline does not work here**, and most of the Debugging section is the evidence. Measured peak-to-trough amplitude has ranged from 26 to 131 counts across captures of the same person on the same hardware. A margin large enough to clear noise at 131 rejects every breath at 30; a margin small enough for 30 fires on noise at 131. A fraction of the measured amplitude has no such range to span.

Three guards remain, each answering a question the threshold cannot:

| Guard | Value | Rejects |
| :--- | :--- | :--- |
| `MIN_AMPLITUDE` | 25 | Detection at all, when the trigger would land inside the noise |
| `BREATH_REFRACTORY` | 1500 ms | A second crossing during one breath; caps detection at 40 brpm |
| `MAX_INTVAL` | 10000 ms | A gap too long to be breathing — the sensor came off |
| First-breath discard | — | The first crossing after start-up, whose interval would be timed from boot |

That last one is worth stating plainly, because `010-pulse-oximeter` shipped without it and its first heart-rate reading is wrong by 12 % as a result. Here the first detected breath only stores a timestamp; it contributes no interval.

<br />

### One number, reported honestly

`MIN_AMPLITUDE` does double duty, and the two jobs are deliberately the same test:

```python
weak = amplitude < MIN_AMPLITUDE
if weak != was_weak:
    print("!!" if weak else "--", "amplitude:", amplitude)
    was_weak = weak
```

Below it the firmware **stops detecting and says so**; above it, it works and stays quiet. So `!! amplitude: 19` does not mean "the signal is a bit poor" — it means "this is why you are getting no rate." The message is printed on the transition only, so a steady state produces no noise in the log and a recovery shows up as `--`.

This exists because the failure it reports is otherwise silent. A weak signal and a broken detector produce the same output: nothing at all.

The envelope under-reads a little — it is always mid-relaxation when sampled — so 25 here corresponds to a real peak-to-trough swing near 30. That was measured, not assumed: on the capture where the real swing was 31–38, the tracker reported 28–29.

<br />

### What the envelope replaced

An earlier version tracked the baseline with a single-pole IIR filter, $\alpha = 0.99$ at 300 ms, giving $\tau \approx 30$ s, and triggered at a fixed 20 counts above it. That approach is still the right one in `011-ecg`, where the feature is a 1 mV spike of roughly constant size. It failed here for reasons specific to this signal, and removing it deleted five constants and two guard blocks:

| Removed | Why it is no longer needed |
| :--- | :--- |
| `THRESH_ALPHA`, `IIR_filter` | `mid` is already a baseline estimate, and a faster one |
| `WARMUP_MS` and its 7 s block | Existed only because the IIR seeded on a single sample and needed ~70 s to converge. The amplitude gate is the warm-up: detection simply does not start until the envelope has opened |
| `LATCH_TIMEOUT` and its block | A backstop for the IIR lagging a baseline step. The envelope midpoint moves with the signal, so the latch cannot stick that way |
| `MIN_INTVAL` | Identical to `BREATH_REFRACTORY`, which already guarantees the same bound. The check was dead from the first version |
| `BREATH_MARGIN`, `BREATH_RESET` | Replaced by the two fractions |

Deleting the warm-up also halved the time to a first reading, from 14.5 s to 7.5 s, because the seven seconds were never buying anything the amplitude gate did not already provide.

<br />

## Connection Tables

The divider runs from 3.3 V. Feeding it 5 V puts the ADC node above the ESP32's input range at one end of the swing.

| Divider | Position | ESP32 |
| :--- | :---- | ---: |
| NTC thermistor | Between 3.3 V and the ADC node | 3V |
| Fixed resistor | Between the ADC node and ground | GND |
| ADC node | The junction of the two | 36 (ADC1_CH0) |

Pick the fixed resistor to match the thermistor's resistance at room temperature. That puts the node near mid-rail, where the divider is most sensitive and the swing has room in both directions.

`adc.atten(ADC.ATTN_11DB)` selects the widest input range. GPIO 36 is input-only and belongs to ADC1, which stays usable while WiFi is on — ADC2 does not, which matters for `rsp_web.py`.

<br />

| LED | Meaning | ESP32 |
| :--- | :---- | ---: |
| Onboard LED | Lit during exhalation | 5 |

On the Lolin D32 the onboard LED on GPIO 5 is **active low**, which is why `setup()` writes `1` to turn it off and the detector writes `0` to light it.

<br />

## Firmware

| File | Purpose |
| :--- | :--- |
| `rsp.py` | Prints the raw trace and nothing else. Run this first, while positioning the sensor, to see the peak-to-trough swing you are actually getting |
| `rsp_led.py` | Detection, LED, and respiration rate on the serial console |
| `rsp_web.py` | The same detection, serving the rate and the waveform over WiFi on a second thread |
| `index.html` | Browser-side canvas plot, polls `/line` and `/sendata` |
| `filters.py` | The single-pole IIR. No longer used here — kept because `011-ecg` imports the same file |
| `wifi.py` | SSID and password, gitignored |

`rsp_web.py` also needs `ESPWebServer.py` on the board; a copy lives in `010a-multithreading`.

Neither detecting version needs a warm-up. They start printing immediately and start detecting as soon as the envelope has opened past `MIN_AMPLITUDE`, which the log marks with a `--` line.

<br />

## Debugging

Nine problems, in the order they surfaced. Ordinary typos and slips are left out; what follows is the set that came from the signal itself or from a constant chosen on a bad assumption.

Every one except 5 and 7 belongs to the IIR-plus-fixed-margin design that the envelope later replaced. They are kept here rather than deleted, because they are the evidence that forced the replacement — the argument for the current design is that each of these failures has no counterpart in it. Problem 5 is mechanical and still open; problem 7 is the one lesson that carried across, since the envelope survived the rewrite and only its decay rule changed.

| # | Kind | Problem | Effect |
| :--- | :--- | :--- | :--- |
| 1 | Signal | Baseline filter at $\alpha = 0.9$, giving $\tau = 2.9$ s against a 3.3 s breath | The baseline followed the breathing and flattened the peaks it was there to measure |
| 2 | Signal | Trigger margin of 3 counts | Under the noise floor. Trigger position jittered across 10–13 samples on a rhythm that was steady to within one sample |
| 3 | Design | Baseline filter seeded on a single sample | Seeded at a trough, it needed ~70 s to reach the true mean; until then the latch stuck on for 10 s at a time |
| 4 | Signal | Baseline stepped ~50 counts mid-capture | Outran the 30 s tracker, latch stuck for 11.6 s, detection dead for the rest of the run |
| 5 | Measurement | Sensor coupling varied between runs | Peak-to-trough amplitude ranged from 5 to 131 counts across eight captures |
| 6 | Design | `MAX_INTVAL` of 10000 ms accepted an interval that spanned two breaths | A missed crossing produced 7500 ms, which passed validation and would have reported **half the true rate** as a plausible number |
| 7 | Design | The envelope relaxed by a fixed 2 counts per sample | Under-read worse as the signal got weaker, reporting an amplitude of 6 where the real swing was 26 |
| 8 | Design | `LATCH_TIMEOUT` was written as `MAX_INTVAL // 2` | Tightening `MAX_INTVAL` for problem 6 silently halved the timeout to 3000 ms, close enough to a real latch at slow breathing to start discarding valid runs |
| 9 | Design | A fixed `BREATH_MARGIN` of 20 counts, on a capture whose peaks reached only 16–23 above the baseline | One trigger in 52 samples, and that one discarded as the first breath. **Zero output on a signal that was breathing steadily at 15–18 brpm** — the failure that ended the fixed-threshold design |

Eight of the nine share a shape: **they produce no output rather than a wrong one.** A latch that never releases, a threshold the peaks never reach, an interval that fails validation — none of them raise anything, and the console looks the same as a working run with the sensor unplugged. On a board whose only output is `print()`, that ambiguity costs more time than the arithmetic ever did, and it is why the current firmware spends a constant and four lines on saying *which* of those cases it is in.

<br />

### The latch that would not release

Problems 3 and 4 are the same bug reached two different ways, and it is the one worth understanding.

The detector holds a flag, `is_breathing`, set when the signal crosses `baseline + 20` and cleared when it falls back under `baseline + 10`. That works as long as the tracked baseline is close to the true one. When it is not, the re-arm level can sit **below the signal's own floor**, and then nothing ever clears the flag.

The first time, the cause was start-up. `IIR_filter` seeds itself with its first input, and that sample happened to land on a trough at 1767 while the true mean was 1826. With $\tau = 30$ s, closing a 59-count gap to within 5 counts takes about 70 seconds:

```
sample 3     1814 > 1767.98 + 40    trigger
sample 4-35  ...                    never falls below thresh, latch held
sample 36    1774 < 1775.37         released, 9.9 s later
```

The fix is to average the first 7 seconds and seed the filter with that. It is not an optimization; without it the detector is blind for the first minute.

The second time, the cause was the signal. A capture with a good warm-up still failed, because the baseline itself stepped up ~50 counts partway through:

```
sample 114   1785 > 1762.34 + 20    trigger
sample 191   1803 vs 1778.30 + 10   still latched, 11.6 s later
```

No seeding fixes that one — a 30 second tracker cannot follow a step, by construction. So the second fix is a backstop rather than a cure: if the latch is held longer than `LATCH_TIMEOUT`, drop it *and* discard the run in progress by setting `last_breath = None`.

Discarding matters as much as releasing. Releasing the latch alone left a 5000 ms gap behind, which fell inside the valid interval window and would have been recorded as a real breath at 12 brpm. Setting `last_breath = None` routes the next crossing through the first-breath discard instead.

**None of this survives into the current firmware, and that is the argument for the envelope.** The failure needs a baseline estimator that can fall below the signal's own floor and stay there. The envelope midpoint cannot: `peak` refreshes the moment the signal makes a new high, so a step of +50 counts raises `mid` immediately, while `trough` — still sitting at the old low — inflates the measured amplitude. Working it through, `re-arm` ends up about 40 counts above the old trough while the signal's new floor is 50 above it, so the re-arm still fires. The 60 lines of warm-up, timeout, and discard logic were all scaffolding around a baseline that could not keep up.

<br />

### The wrong answer is worse than no answer

Every other problem above fails empty. Problem 6 is the only one that fails *plausibly*, and it is the one to be most careful about.

Once the amplitude fell far enough that some peaks stopped reaching `baseline + 20`, the detector began skipping breaths. A skipped breath does not announce itself — it merges two cycles into one interval:

```
sample 24   trigger
sample 36   peak reached only baseline + 15, no trigger
sample 49   trigger        interval = 7500 ms, spanning two breaths
```

7500 ms passed `MAX_INTVAL = 10000`, so it was recorded as one breath. That capture stopped before a second such interval arrived, but had it continued, the firmware would have printed roughly **8 brpm** for someone breathing at 16 — not an error, not a zero, just a wrong number in the normal range with nothing to mark it as wrong.

The obvious fix was to tighten `MAX_INTVAL` to 6000 ms, and that was the wrong move — it treats the symptom and creates a new failure. Work the numbers:

* A missed breath at 17 brpm produces **7000 ms**
* Genuine slow, deep breathing at 8 brpm produces **7500 ms**

**No fixed limit separates those two.** Set it below 7000 and real slow breathing is rejected; set it above 7500 and missed breaths sail through. The 6000 ms limit duly turned "occasionally reports half the rate" into "reports nothing at all below 10 brpm", which is a different bug, not a fix. And it dragged problem 8 along with it, because `LATCH_TIMEOUT` was written as `MAX_INTVAL // 2` and silently halved to a value a real latch could reach.

The absolute length of an interval simply does not carry the information. Only a comparison does — against its neighbours, or against the amplitude that produced it.

That is why the real fix was upstream. Breaths were being missed because a fixed margin sat too close to the peaks; scaling the threshold to the measured amplitude removes the cause, and `MAX_INTVAL` goes back to 10000 ms doing the only job it is suited for — noticing that the sensor came off.

<br />

### Coupling beat every constant

Problem 5 is the one no code change addresses, and it is what eventually decided the design. Eight captures of the same person on the same hardware, in order:

| Capture | Threshold | Peak-to-trough | Rates produced |
| :--- | :--- | :--- | :--- |
| 1 | — | 78 – 102 | raw trace only |
| 2 | fixed | 89, decaying to 5 | 0 |
| 3 | fixed | 85 – 105 | 2 |
| 4 | fixed | 10 – 25, later 25 – 71 | 0 |
| 5 | fixed | 53, decaying to 26 | 1 |
| 6 | fixed | **87 – 131** | 3 |
| 7 | fixed | 31 – 38 | **0** |
| 8 | **adaptive** | 33 – 69 | **4** |

Capture 2 is the clearest mechanical failure: amplitude fell 89 → 17 → 15 → 11 → 5 over five consecutive breaths while the DC level drifted down 49 counts. Falling amplitude with a drifting baseline is the sensor relaxing out of the airflow, not an electrical fault. The rhythm stayed visible in capture 4 at the right period and the right rate; there was simply not enough of it to cross a threshold that also cleared the noise.

For a long time the plan was to fix the mounting and keep the fixed threshold — an adaptive threshold on a weak signal tracks noise instead of breathing, and does it without complaining, which trades a visible failure for an invisible one. Captures 3 and 6 seemed to confirm it: mount the bead well and everything works.

**Six sittings settled it the other way.** The amplitude went 102 → 5 → 105 → 25 → 53 → 131 → 38 with no sign of converging. Waiting for a repeatable mount was a bet that had now lost six times, so the condition was met in the only sense that matters: it had been tested.

Captures 7 and 8 are the comparison that justifies the switch. Amplitudes of 31–38 and 33–69 are the same regime — the weak end, roughly a third of capture 6. The fixed threshold produced **nothing at all** on the first. The adaptive one produced **four readings in 28 seconds** on the second, one every 7.1 s, which is the same cadence capture 6 managed on triple the amplitude.

The objection about tracking noise is answered by `MIN_AMPLITUDE` rather than by avoiding the approach: below the floor the detector stops and says so, so the invisible failure never gets the chance to happen.

<br />

## Results

Capture 8 from `rsp_led.py`. The second column is the **trigger level**, not a baseline — plotting the signal against the actual decision boundary is more useful than plotting it against an intermediate. 95 samples, 28.5 seconds, trimmed:

```
MPY: soft reboot
RSP: 1995 1992.537
RSP: 2012 2005.388
-- amplitude: 26.44727      <- detector armed; this crossing is the discarded first breath
RSP: 2029 2018.301
RSP: 2056 2038.813
RSP: 2078 2055.653
RSP: 2090 2065.033          <- peak
RSP: 2069 2064.279
RSP: 2040 2063.547
RSP: 2026 2062.836
RSP: 2022 2062.147
RSP: 2021 2061.478          <- trough
RSP: 2029 2060.83
RSP: 2048 2060.2
RSP: 2068 2059.589          <- trigger, interval 1 (12 samples)
...
RSP: 2082 2071.453          <- trigger, interval 2 (12 samples)
---> RSP rate: 16.6
...
RSP: 2087 2079.963
---> RSP rate: 18.1
...
RSP: 2094 2087.118
---> RSP rate: 18.1
...
RSP: 2102 2097.409
---> RSP rate: 16.6
```

Triggers landed on samples **1, 13, 25, 36, 47, 59, 69, 80 and 93**: eight intervals of 12, 12, 11, 11, 12, 10, 11 and 13 samples, mean 3460 ms, or 17.3 brpm. Four things to read from it:

* **This is the amplitude that broke the previous version.** Peak-to-trough ran 33–69 counts. Capture 7, at 31–38, produced zero readings under a fixed margin. Four readings here, one every 7.1 s, matching the cadence capture 6 achieved on 87–131.

* **The threshold tracked a 52-count baseline drift.** The troughs climbed from 2021 to 2073 across the capture and the trigger level followed, 2005 → 2097. That is the same drift pattern that left the IIR version latched for 11.6 seconds; here it does not register as an event at all.

* **The spread is quantization, not instability.** 16.6, 18.1, 18.1, 16.6 is ±4.3 % around 17.35, and one sample of trigger position is worth 4.8 %. The intervals behind those numbers — 12, 12, 11, 11, 12, 10, 11, 13 — are real breath-to-breath variation plus that ±1 sample. Only the triggers at the **edges** of a reported pair move the answer; a shift in the middle one changes how the total splits but not the total itself.

* **The log is quiet when nothing is wrong.** One `--` line at start-up, then nothing but data for 28 seconds. No `!!`, no `gap`. Every diagnostic in the firmware is edge-triggered or exceptional, so an uneventful run reads as uneventful.

Raising `TARGET_N_BREATH` to 3 would cut that ±4.3 % to ±2.9 % and smooth the real variation, at the cost of a reading every 10 s instead of 7. That trade only became worth considering once detection was reliable; while breaths were being missed, a higher target just meant waiting longer for a number that never came.

Halving `SAMPLE_INTVAL` to 150 ms halves the quantization directly. It was tried once and abandoned — the capture that failed under it failed on amplitude, and would have failed identically at 300 ms — but the option stands. Note that `ENVELOPE_DECAY` would have to move with it, to $0.985$, since 24 samples per breath instead of 12 would otherwise double the relaxation per cycle. Constants defined per sample are meaningless without the sample interval; this project learned that once already, with $\alpha$.

Timing from reset to the first number:

| Stage | Duration |
| :--- | :--- |
| Envelope opens past `MIN_AMPLITUDE` | 0.3 s here, up to one breath in general |
| First crossing, discarded | same sample |
| Two intervals at `TARGET_N_BREATH = 2` | 7.2 s |
| **First `RSP rate`** | **7.5 s** |

The previous version took 14.5 s to the same point, seven of which were a warm-up that existed only to seed a filter that no longer exists.

<br />

## Brief Summary

A thermistor under the nose, a two-resistor divider, and one ADC pin, reading respiration rate on an ESP32 at 17.3 brpm — on a signal weak enough that the previous version of the same firmware reported nothing at all.

Acquisition was never the hard part. Detection was, and for most of the project it failed silently. A baseline seeded on the wrong sample, a filter too fast to be a baseline, a threshold the peaks no longer reached — each produced an empty console rather than an error, and the only way through was to capture real output and walk it against the logic by hand. Every constant in the file came out of that; none came from reasoning about a waveform in the abstract.

The turn came from a measurement, not an idea. Across eight sittings with the same sensor on the same person, peak-to-trough amplitude ranged from 5 to 131 counts and never converged. A threshold set a fixed number of counts above a baseline cannot span 20x, so half the constants in the firmware existed to prop up an approach that was mismatched to the signal — a warm-up to seed the baseline, a timeout for when the baseline fell behind, an interval limit patching the breaths the margin missed. Scaling the threshold to a measured envelope instead deleted five constants and two guard blocks, halved the time to a first reading, and turned the weakest usable capture from zero readings into four.

What is left is honest about its own limits. `MIN_AMPLITUDE` is one number serving as both the detection floor and the warning, so `!! amplitude: 19` does not mean the signal is poor — it means *this is why there is no rate*. On a board whose only output is `print()`, that distinction was worth more than any of the signal processing.

<br />

## References

* [MicroPython `machine.ADC`, ESP32 port](https://docs.micropython.org/en/latest/esp32/quickref.html#adc-analog-to-digital-conversion)
* [Espressif, ADC characteristics and attenuation ranges](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/peripherals/adc_oneshot.html)
* [Vishay, NTC thermistors: application notes](https://www.vishay.com/docs/29053/ntcappnote.pdf)
* `011-ecg`, which shares `filters.py` and the same threshold-above-a-drifting-baseline approach