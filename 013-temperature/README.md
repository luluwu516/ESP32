# NTC Thermistor Temperature Regression

> Note: this is a learning project. A thermistor taped to skin is not a clinical thermometer, and I trained the model on a water-bath sweep instead of on body temperature. Use certified equipment for anything health-related.

<br />

A thermistor's resistance changes with temperature along a steep, repeatable curve. This project reads one with the ESP32's ADC, converts the reading into degrees Celsius with a small neural network, and serves the result over Wi-Fi as a web page.

The network earns its place because the path from temperature to ADC count bends in three places: the thermistor's own curve, component tolerances, and the ADC. Calibrating the whole path at once means I model none of them.

> This is an AI-assisted project. I used it to learn more in detail.

<img width="400" alt="NTC Thermistor" src="https://github.com/user-attachments/assets/d7847539-0bb6-4470-acdd-f0157d70aac2" />

<br />

<br />

## Mechanism: How does it work?

### From temperature to resistance

An NTC thermistor has a **negative temperature coefficient**: its resistance falls as it warms. Over a moderate span, the relationship follows the B-parameter equation,

$$R(T) = R_{25}\exp\left[B\left(\frac{1}{T}-\frac{1}{T_{25}}\right)\right]$$

with $T$ in kelvin and $T_{25} = 298.15\ \mathrm{K}$. For a 10 kΩ NTC with $B = 3950$:

| Temperature | Resistance |
| :--- | ---: |
| 20 °C | 12.5 kΩ |
| 25 °C | 10.0 kΩ |
| 37 °C | 6.0 kΩ |
| 60 °C | 2.5 kΩ |
| 100 °C | 0.70 kΩ |

The steep curve makes the thermistor sensitive. The exponent in it keeps ADC counts from tracking temperature in a straight line.

<br />

### From resistance to a voltage

The ESP32 reads voltage, so the thermistor forms one half of a divider:

$$V_{ADC} = V_{CC}\cdot\frac{R_{fixed}}{R_{NTC}(T)+R_{fixed}}$$

Put the thermistor on the **high side**, between 3V3 and the ADC node, with the fixed resistor to ground. The ADC reading then rises with temperature. Wire it the other way, and the curve inverts; a model trained on one arrangement is useless on the other.

The recorded data fits a 10 kΩ NTC against a 10 kΩ fixed resistor, centering the divider near 25 °C.

<br />

### Why a neural network instead of the equation

Inverting the two equations gives temperature from a voltage, so a network looks like overkill. The equation and the hardware disagree in several places:

* **The B-parameter equation approximates.** It fits near $T_{25}$ and drifts at the ends of a wide sweep. Manufacturers publish correction tables for this reason.
* **Component tolerance.** A 5% thermistor and a 1% resistor shift the whole curve. Each board needs its own constants.
* **The ESP32's ADC bends.** It carries a known integral nonlinearity, and it gets worse below about 150 mV, where the hot end of a sweep lands.

Fitting the raw ADC count against a reference thermometer folds all three into one learned curve, and the constants come out specific to the board that produced the data. The Results section below shows how far apart two boards built to the same schematic drift.

<br />

### Resolution

Set `adc.width(ADC.WIDTH_10BIT)` in both the collection script and the inference script. The 12-bit default will not do.

This is a compatibility requirement. The stored dataset tops out at 975, and only a 1023 full scale explains that. Collect new data at 12-bit on the same hardware, and every reading comes out four times larger. Mix the two scales in one file, and you train a model that is wrong across its whole range, with no error to warn you.

Near body temperature, the divider moves about 39 counts per °C at 12-bit, so 10-bit gives about 0.1 °C per count. The thermistor's own noise is larger than that.

<br />

## Connection Table

| Component | Meaning | ESP32 |
| :--- | :---- | ---: |
| NTC, one leg | Supply | 3V3 |
| NTC, other leg + resistor | Divider midpoint | 36 (ADC1_CH0) |
| Fixed resistor, other leg | Ground | GND |

<img width="400" alt="Connection" src="https://github.com/user-attachments/assets/f8d2cf90-aed1-405b-b7f5-1c5900ef5bb4" />

To check the orientation, warm the thermistor with your fingers and watch the raw value. It should **rise**. A falling value means the divider is inverted.

<br />

## The Pipeline

This project runs in two places, unlike the others in this repository. Sorting out which file executes where takes most of the setup:

| File | Runs on | Purpose |
| :--- | :--- | :--- |
| `temperature-write.py` | ESP32 | Confirms the ADC reads and the filesystem writes |
| `temperature-collect-data.py` | ESP32 | Pairs averaged ADC readings with a reference thermometer |
| `temperature-model.py` | Computer | Trains the network and exports it as JSON |
| `temperature-web.py` | ESP32 | Loads the model, measures, serves the web page |
| `index.html` | Browser | Polls `/measure` and displays the reading |

The data moves one way: the board writes `temperature.txt`, the computer turns it into `temperature_model.json`, and the board loads that back.

I keep `wifi.py` out of the repository. Create it next to the scripts with two variables:

```python
WIFI_SSID = "your network"
WIFI_PASSWORD = "your password"
```

<br />

### Toolchain Constraints

Two version mismatches will stop this pipeline, and neither prints a message that points at the cause.

**On the board**, `import ulab` and `from keras_lite import Model` both need the textbook's custom MicroPython build (`esp32-v1.16.bin`). `ulab` is a C module, so you cannot upload it as a file, and stock MicroPython will not run the inference script. Flash it with:

```bash
python3 -m esptool --chip esp32 --port /dev/cu.usbserial-110 erase_flash
python3 -m esptool --chip esp32 --port /dev/cu.usbserial-110 --baud 460800 \
  write_flash -z 0x1000 esp32-v1.16.bin
```

`erase_flash` wipes the filesystem, so back up any collected data first.

**On the computer**, `keras_lite_convertor.save()` reads `config['batch_input_shape']` out of the serialized model. That key exists only in **Keras 2**. TensorFlow 2.16 and later ship Keras 3, where training runs to completion and the export then raises `KeyError`. That constrains the whole environment:

| Requirement | Consequence |
| :--- | :--- |
| `kc.save()` needs Keras 2 | TensorFlow ≤ 2.15 |
| TF 2.15 publishes no newer wheels | Python ≤ 3.11 |

```bash
conda create -n tf215 python=3.11 -y
conda activate tf215
pip install "tensorflow==2.15.1" "numpy<2"
```

Verify with `python -c "import tensorflow as tf, keras; print(tf.__version__, keras.__version__)"`. Keras must report **2.x**.

<br />

## Training

`Data_reader.read()` shuffles by default and takes a `random_seed`. Pass one. The split decides the normalization constants, and you paste those constants into the inference script by hand, so leaving the seed unset hands you different numbers on every run than the ones already sitting on the board.

The script standardizes inputs against the training split alone, and scales labels to about 0–1:

$$x = \frac{\mathrm{raw}-\mu}{\sigma}, \qquad \hat{T} = 100\cdot f(x)$$

The network is three ReLU layers of 20 units and a linear output, about 900 parameters for a smooth one-dimensional curve. That is generous for the job, though a monotonic target this simple costs little to overfit.

Undo both transforms on the board, in `cal_temp()`. Get one of them wrong, and the board reports temperatures that look plausible and sit at a constant offset, with nothing in the output to show it.

<img width="400" alt="Training" src="https://github.com/user-attachments/assets/63a7c13d-7d8f-44b0-b722-6cad6bd6ecc4" />

<br />

## Debugging: the page that loaded halfway

The measurement loop printed a stable room temperature over USB while the browser showed nothing. One `curl` found where it broke:

```
< HTTP/1.1 200 OK
<
<!DOCTYPE html>
...
      background-color: #dd
* Closing connection
```

A 200, then the response cut off mid-CSS after about 1.3 kB of a 4 kB file. The server was running, the file was on the board, and the transfer died partway through. The REPL carried one line to go with it: `[Errno 104] ECONNRESET`.

**Memory was the first hypothesis**, since the board holds a 19.5 kB JSON model, Wi-Fi buffers, a second thread stack, and a 4 kB file at once. I printed `gc.mem_free()` next to each reading:

```
24.2 96896
24.4 89328
24.5 89232
24.5 89616
24.3 89616
...
24.3 89584
```

One 7 kB drop for warm-up, then 89 kB free, oscillating inside a 600-byte band with no downward trend. The board had memory to spare and was leaking none of it.

**The GIL caused it.** `model.predict()` chains `ulab` operations, and `ulab` is a C module: each call holds the interpreter lock until it returns, where `time.sleep_ms()` yields. The measurement loop ran back to back with no pause, so it spent most of its time inside C code. The web thread got slivers, and so did lwIP, which needs CPU time to drain the TCP send buffer. Pushing 4 kB in 64-byte writes under those conditions ran slow enough that the client gave up first, and the server then wrote to a closed socket and got `ECONNRESET`.

A second bug turned an intermittent failure into a permanent one. The web thread wrapped its `try` around the loop instead of inside it:

```python
def web_loop():
    try:
        while state.running:
            ESPWebServer.handleClient()
    except Exception as e:
        print("Web thread error:", e)
    finally:
        ESPWebServer.close()        # one bad request ends the server
```

`ECONNRESET` arrives during normal use, whenever someone closes a tab mid-load. Here, one occurrence shut the server down for good while the measurement loop carried on printing healthy readings, so the board looked fine from the REPL and answered nothing over the network.

Both fixes are small:

```python
def web_loop():
    while state.running:
        try:
            ESPWebServer.handleClient()
        except Exception as e:
            print("Web thread error:", e)

    ESPWebServer.close()
    print("Web server closed")
```

and a `time.sleep_ms(500)` at the end of the measurement loop. Body temperature does not need updating five times a second.

One process note. The sleep and a `gc.collect()` went in together, the page started working, and I gave the credit to `gc.collect()`. Removing them one at a time showed the sleep doing all the work. The memory log had already ruled memory out, and I read it as supporting my hypothesis rather than contradicting it.

<br />

## Results

I collected 112 records across two cooling runs, spanning 17 °C to 74 °C, with 23 of them inside the 34–42 °C band that matters for body temperature. The reference was a dial thermometer read to whole degrees, so every label carries about ±0.5 °C of rounding.

Against the textbook's dataset, this board reads 25 to 47 counts lower at the same temperature:

| °C | This board | Textbook | Difference |
| ---: | ---: | ---: | ---: |
| 25 | 433 | 473 | −40 |
| 30 | 498 | 522 | −25 |
| 37 | 568 | 594 | −26 |
| 45 | 640 | 676 | −37 |
| 60 | 757 | 789 | −32 |
| 70 | 810 | 857 | −47 |

The divider moves 9.0 counts per °C in the 34–42 °C band, so the 26-count gap at 37 °C works out to **2.9 °C**. That is what the textbook's model reports on this hardware, and it is why I collected the data again.

Error of the trained model, on the same split used for training:

| Split | Records | MAE | Worst |
| :--- | ---: | ---: | ---: |
| Train | 95 | 0.278 °C | 1.132 °C |
| Validation | 12 | 0.249 °C | 0.774 °C |
| Test | 5 | 0.402 °C | 0.619 °C |
| 34–42 °C band | 23 | 0.173 °C | 0.461 °C |

Validation error sits below training error, so the network has not overfitted, though 12 records is a thin sample to read that from.

Weigh those figures against the reference that produced them. A dial thermometer resolved to whole degrees puts ±0.5 °C of quantization into every label, which is larger than the model's MAE. The table shows a fitted curve passing through rounded labels, and it cannot show accuracy finer than the instrument behind it. Held next to the dial thermometer at room temperature, the board agrees at every reading I can resolve.

Normalization constants for this model (`random_seed=12`):

```
mean = 622.2105263157895
std  = 113.19846518736738
```

Both go into `temperature-web.py` by hand, and retraining changes them.

<!-- TODO: screenshot of the web page -->

<br />

## Brief Summary

An NTC thermistor in a divider, read by the ESP32's ADC, converted to degrees by a small network trained on paired readings, and served over Wi-Fi.

Calibrating end to end paid off for reasons visible only in the data: a second board built to the same schematic sits 2.9 °C away at body temperature, and no amount of care with the divider would have closed that gap. Fit the whole path at once, and you cover the thermistor's curve, the component tolerances, and the ADC's nonlinearity together.

The failures came from the plumbing. A silent 4× scale change between 10-bit and 12-bit, an export format tied to a Keras version two years old, and a C extension holding the interpreter lock long enough to starve a web server. None of the three raises an error when the mistake happens.

<br />

## References

* [Wikipedia, Thermistor](https://en.wikipedia.org/wiki/Thermistor)
* [Wikipedia, Steinhart–Hart equation](https://en.wikipedia.org/wiki/Steinhart%E2%80%93Hart_equation)
* [MicroPython `machine.ADC`, ESP32 port](https://docs.micropython.org/en/latest/esp32/quickref.html#adc-analog-to-digital-conversion)
* [ESP-IDF, ADC calibration and accuracy](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/peripherals/adc_calibration.html)
* [ulab documentation](https://micropython-ulab.readthedocs.io/)
* [esptool documentation](https://docs.espressif.com/projects/esptool/en/latest/esp32/)
* [FLAG](https://www.flag.com.tw/maker/FM636A)
