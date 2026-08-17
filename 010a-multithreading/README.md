# PPG over WiFi, on Two Threads

> Note: this is a learning project. Nothing here is calibrated or validated for clinical use.

<br />

This is [010-pulse-oximeter](../010-pulse-oximeter) with the trace moved off the serial cable and into a browser. The ESP32 keeps sampling the MAX30102 at 50 Hz while a second thread serves a web page, so the waveform and heart rate can be watched from a phone on the same network.

The signal path is unchanged, and the filtering is documented there: a 0.5 to 5 Hz band-pass, automatic gain control, and beat detection against an adaptive threshold. What this folder adds is the concurrency and the transport, which is where all of its own bugs came from.

<br />

## Mechanism: how the two threads split

MicroPython's `_thread` gives one extra thread. That is enough, because the work divides cleanly:

```
main thread                          web thread
-----------                          ----------
sensor.check()                       ESPWebServer.handleClient()
band-pass, AGC, beat detect            -> /hr    reads state.heart_rate
write state.heart_rate                 -> /line  drains state.ppg_buffer
append state.ppg_buffer
```

Neither thread waits on the other. The sensor loop never blocks on the network, and a slow or absent browser costs it nothing.

`handleClient()` polls its socket with a 1 ms timeout, so that call doubles as the web thread's yield. No sleep is needed there, and the sensor loop keeps its share of the CPU.

<br />

### What is shared, and why there is no lock

| Shared | Written by | Read by |
| :--- | :--- | :--- |
| `state.heart_rate` | main | web |
| `state.ppg_buffer` | main | web |
| `state.running` | either | both |

MicroPython holds a GIL, so an integer read or write cannot be interrupted half way. `heart_rate` and `running` need nothing further.

The buffer does, because two statements are involved rather than one:

```python
buf = state.ppg_buffer          # bind once
buf.append(ppg)
if len(buf) > PPG_BUFFER_LEN:
    del buf[0]
```

`send_ppg` hands the whole list to the response and puts a fresh one in `state.ppg_buffer`. Without the local binding, the length check and the delete can land on two different lists: the check sees 51 items, the swap arrives, and the delete hits the new empty one. That is problem 4 below. Binding once makes the pair operate on the same object no matter when the swap happens, at the cost of losing at most one sample.

The web thread only rebinds the name, it never mutates the list it took, so the main thread owns that object outright and a lock would buy nothing.

<br />

## Connection Table

Same wiring as 010, plus an LED that flashes on each detected beat.

| Device | Meaning | ESP32 |
| :--- | :--- | ---: |
| MAX30102 GND | Ground | GND |
| MAX30102 SCL | Clock line | 22 SCL |
| MAX30102 SDA | Data line | 21 SDA |
| MAX30102 VIN | Power | 3V |
| LED anode | Beat indicator, active low | 5 |

<br />

## Web API

| Path | Returns | Polled by The Page Every |
| :--- | :--- | :--- |
| `/hr` | One number, beats per minute | 2 s |
| `/line` | Comma separated samples since the last request | 500 ms |
| `/` | `index.html` | once |

`/line` returns a **batch**, not the latest value. The first version answered with one sample per request, polled every 100 ms, which is 10 Hz. The systolic upstroke is 80 ms wide, so at 10 Hz it was never in the data at all and the page drew a plausible looking line that was mostly interpolation. Returning everything since the last request gives the full 50 Hz and cuts the request count by five at the same time.

It also **drains** the buffer rather than copying it, so nothing is sent twice. Serving the same 1 s window every 500 ms would replay half its samples and draw the waveform at half speed.

`PPG_BUFFER_LEN` is 50, one second at 50 Hz. That is headroom for a missed poll, not the normal payload: at a 500 ms interval each response carries about 25 samples.

<br />

## Debugging

Every one of these ran without an error message.

| # | Where | Problem | Effect |
| :--- | :--- | :--- | :--- |
| 1 | Python | Beat threshold of 20 counts | Found 2 of 6 beats on a real capture. The peaks sit 18 to 20 counts above the running mean, so 20 was the ceiling |
| 2 | Python | Heart rate timed inline instead of through `Rate_calculator` | Reintroduced the start-up interval bug from 010, inflating the first reading by 12 % |
| 3 | Python | `except Exception` in the web thread | `KeyboardInterrupt` derives from `BaseException`, so Ctrl-C escaped, killed the thread, and left the sensor running |
| 4 | Python | `del state.ppg_buffer[0]` racing the swap in `send_ppg` | `IndexError: pop from empty list`, only when the page was polling and the buffer was full |
| 5 | Python | Cleanup ordered `sleep_ms(200)` before `sensor.shutdown()` | A second Ctrl-C landed in the sleep and skipped the shutdown, leaving the LED lit |
| 6 | Python | `while True` in the web thread, no stop flag | The socket stayed bound after Ctrl-C, so the next run failed with `EADDRINUSE` |
| 7 | Python | `while not sta.isconnected(): pass` | A wrong password hung forever, spinning the CPU against the other thread |
| 8 | JS | `scaler()` divided by `in_max - in_min` unguarded | A flat signal produced `NaN` and the trace vanished with nothing in the console |

<br />

**Problems 3 and 5 are the same lesson from opposite ends.** `finally` guarantees that a block *starts*, not that it finishes. An exception arriving inside it skips whatever is left. Thonny's Stop button sends several interrupts in a row, so the window is not theoretical. The fix is to do the irreversible thing first, before anything that can block:

```python
finally:
    state.running = False
    try:
        sensor.shutdown()          # first, and it does not block
        print("Sensor shut down")
    except Exception as e:
        print("Shutdown error:", e)
    led.value(1)
    sleep_ms(200)                  # then wait for the web thread
```

<br />

## Results

Replaying a recorded capture through the whole file, with the web thread running:

```
Connected, open http://192.168.0.42/
heart rate reported      : 73.9 bpm
LED on-transitions       : 18 over 14.4 s  ->  75 bpm
/line returned           : 50 samples, range 18..297
/hr returned             : '73.9'
buffer drained after read: 0
Sensor shut down
Web server closed
```

The trace values run from about -40 to 360 rather than the small positive numbers 010 produced. AGC normalises the amplitude, and the offset only shifts the trace: the diastolic trough is allowed to go negative. `scaler()` in the page is auto-ranging and `parseInt` accepts a minus sign, so nothing on the browser side cares.

<br />

## Brief Summary

The measurement side of this folder is a straight copy of 010 and gave no trouble. Everything that broke came from the two additions: a second thread, and a browser reading state that another thread is writing.

None of those eight problems raised anything on the console at the point of failure, and several left the page looking like it was working. The first heart rate was 12 % high, the beat detector found two of every six beats, and the sensor stayed lit after what looked like a clean exit.

| File | Holds |
| :--- | :--- |
| `ppg-multithreading.py` | The sensor loop, the shared state, the web routes |
| `index.html` | The canvas, the polling, the auto-ranging |
| `ESPWebServer.py` | The HTTP server, unmodified |
| `wifi.py` | `WIFI_SSID` and `WIFI_PASSWORD`, not committed |
| `filters.py`, `detectors.py`, `max30102.py`, `circular_buffer.py` | Copies of 010's |

There is no `pulse_oximeter.py` here. `ppg-multithreading.py` reads infrared only and drives the sensor directly, because going through that class would have run the whole SpO2 chain, a second DC filter and both AC extractors, to use one number out of it. Heart rate comes from `Rate_calculator` in `detectors.py` instead.

<br />

## References

* [010-pulse-oximeter](../010-pulse-oximeter), where the sensor and the filtering are documented
* [MicroPython `_thread`](https://docs.micropython.org/en/latest/library/_thread.html)
* [FLAG](https://www.flag.com.tw/maker/FM636A)