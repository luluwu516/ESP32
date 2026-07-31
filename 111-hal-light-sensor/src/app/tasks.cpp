// References:
// RTOS Fundamentals by FreeRTOS (https://freertos.org/Documentation/01-FreeRTOS-quick-start/01-Beginners-guide/01-RTOS-fundamentals)
// ESP32 with FreeRTOS (Arduino IDE) – Getting Started: Create Tasks by Random Nerd Tutorials (https://randomnerdtutorials.com/esp32-freertos-arduino-tasks/)

#include "tasks.h"
#include "../hal/hal_bh1750.h"
#include "../hal/hal_oled.h"
#include "../hal/hal_buzzer.h"
#include "light_alarm_logic.h"

QueueHandle_t luxQueue;

// read the sensor and publishes the latest value to the queue
void SensorTask(void *pvParameters) {
  // infinite loop
  // a FreeRTOS task must never return
  for (;;) { 
    uint16_t lux = hal_bh1750_read_lux();
    xQueueOverwrite(luxQueue, &lux);
    // give up the CPU for 20ms
    vTaskDelay(pdMS_TO_TICKS(20)); // vTaskDelay() expects a tick count -> call the pdMS_TO_TICKS()
  }
}

// wait for a new lux value and drive outputs
void DisplayAlarmTask(void *pvParameters) {
  uint16_t lux;
  for(;;) {
    if (xQueueReceive(luxQueue, &lux, portMAX_DELAY) == pdTRUE) {
      bool alarm = decide_alarm(lux, LOW_LIGHT_THRESHOLD, HIGH_LIGHT_THRESHOLD);
      hal_oled_show_status(lux, alarm);
      hal_buzzer_set(alarm);
    }
  }
}