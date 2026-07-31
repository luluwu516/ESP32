# HAL + FreeRTOS Light Sensor (Arduino C++ rewrite of 7-light-sensor)

This project reimplements the light and alarm system from [7-light-sensor](../7-light-sensor): a BH1750 ambient light sensor, an SSD1306 OLED display, and a buzzer alarm, rewritten in Arduino C++ with FreeRTOS instead of MicroPython. The hardware and the alarm behavior match the original. The language and the software architecture changed, to demonstrate C++, RTOS task design, and Hardware Abstraction Layer (HAL) concepts for embedded software roles.

<br />

## Key Differences from 7-light-sensor

| Aspect | 7-light-sensor (original) | 11-hal-light-sensor (this project) |
| :--- | :--- | :--- |
| Language | MicroPython | Arduino C++ |
| Execution model | Single-threaded `while True` loop | Two FreeRTOS tasks running concurrently, pinned to separate CPU cores |
| Code organization | Flat script — sensor I/O, display, and alarm logic all mixed together in one file | Layered: a Hardware Abstraction Layer (`src/hal/`) isolates all register/pin/I2C access; application logic (`src/app/`) contains only the alarm decision, with zero hardware dependencies |
| Sensor ↔ display communication | N/A (single loop, shared local variables) | FreeRTOS queue used as a depth-1 "mailbox" (`xQueueOverwrite` / `xQueueReceive`), a producer-consumer pattern |
| Sensor read blocking | The ~180ms BH1750 conversion delay blocks the entire loop every cycle, including the display/buzzer update | `SensorTask` (Core 0) isolates the blocking read; `DisplayAlarmTask` (Core 1) never blocks |
| I2C driver | `i2c.writeto()` / `i2c.readfrom()` (MicroPython high-level API) | `Wire.beginTransmission()` / `Wire.write()` / `Wire.endTransmission()` / `Wire.requestFrom()` (Arduino's transaction-level I2C API) |

<br />

## Folder Structure

```
11-hal-light-sensor/
├── 11-hal-light-sensor.ino   # setup()/task creation only 
|                             # no hardware or business logic
└── src/
    ├── hal/                  # Hardware Abstraction Layer — anything that touches
    │   │                     # registers, pins, or I2C addresses lives here
    │   ├── hal_i2c_bus.h/.cpp
    │   ├── hal_bh1750.h/.cpp
    │   ├── hal_oled.h/.cpp
    │   └── hal_buzzer.h/.cpp
    └── app/                  # Application layer — pure logic + task orchestration,
        │                     # no direct hardware access
        ├── light_alarm_logic.h/.cpp
        └── tasks.h/.cpp
```

> **Note**: Arduino IDE only auto-discovers files sitting directly in the sketch's top-level folder; arbitrary subfolders are silently ignored. The special `src/` folder is the one exception — it's compiled recursively like a library, which is what makes the `hal/`/`app/` split possible here.

<br />

## Task Design

Two FreeRTOS tasks, pinned to different ESP32 cores via `xTaskCreatePinnedToCore()`:

- **`SensorTask`** (Core 0): reads the BH1750 sensor (a call that blocks for ~180ms during conversion) and pushes the latest lux value into `luxQueue`.
- **`DisplayAlarmTask`** (Core 1): blocks on the queue. On every new reading, it evaluates the alarm condition and updates the OLED and buzzer.

The two tasks communicate through a depth-1 queue used as a mailbox (`xQueueOverwrite` / `xQueueReceive`). The queue carries the lux value itself, so a semaphore would not work here: a semaphore signals an event, not a value. This is a producer-consumer pattern built on message passing. No shared mutable state exists between the two tasks, so no manual mutex is needed.

<br />

## Connection Tables

Same wiring as [7-light-sensor](../7-light-sensor#connection-tables):

For BH1750 Light Sensor:

| Sensor | Meaning | ESP32 |
| :--- | :--- | ---: |
| VCC | Power | 3V |
| GND | Ground | GND |
| SCL | Clock line | 22 SCL |
| SDA | Data line | 21 SDA |

For OLED display:

| OLED | Meaning | ESP32 |
| :--- | :--- | ---: |
| VCC | Power | 3V |
| GND | Ground | GND |
| SCL | Clock line | 22 SCL |
| SDA | Data line | 21 SDA |

For Buzzer:

| Buzzer | Meaning | ESP32 |
| :--- | :--- | ---: |
| + | Power | - |
| - | Ground | GND |
| S | Signal | 16 |

<br />

## Build Environment

- **Board**: WEMOS LOLIN D32 (ESP32-WROOM-32)
- **Toolchain**: Arduino IDE
- **Libraries**: `Adafruit SSD1306` + `Adafruit GFX Library` (OLED); `Wire` and FreeRTOS APIs (`xTaskCreatePinnedToCore`, `QueueHandle_t`, etc.) are built into the ESP32 Arduino core, no extra install needed.

<br />

## Results

The firmware compiles and runs on the LOLIN D32. The OLED updates with the live lux reading, and the buzzer activates when ambient light falls within the alarm range, matching the behavior of the original MicroPython version. Two concurrent, decoupled FreeRTOS tasks now replace the single blocking loop.

<br />

## Brief Summary

This project turns a single-threaded MicroPython sensor script into layered, concurrent C++ firmware. A Hardware Abstraction Layer separates register-level I2C access from the alarm decision logic, and two FreeRTOS tasks split sensing and display work across the ESP32's two cores, communicating through a queue instead of shared variables. The BH1750 sensor, OLED display, and buzzer alarm behave exactly as before; the software behind them now follows patterns used in production embedded systems.

<br />

## References

* [Random Nerd Tutorials - ESP32 with BH1750 Ambient Light Sensor](https://randomnerdtutorials.com/esp32-bh1750-ambient-light-sensor/)
* [Random Nerd Tutorials - ESP32 with FreeRTOS (Arduino IDE)](https://randomnerdtutorials.com/esp32-freertos-arduino-tasks/)
* [RTOS Fundamentals](https://freertos.org/Documentation/01-FreeRTOS-quick-start/01-Beginners-guide/01-RTOS-fundamentals)