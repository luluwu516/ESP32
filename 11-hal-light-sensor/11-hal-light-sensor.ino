#include "src/hal/hal_i2c_bus.h"
#include "src/hal/hal_bh1750.h"
#include "src/hal/hal_oled.h"
#include "src/hal/hal_buzzer.h"

#include "src/app/light_alarm_logic.h"
#include "src/app/tasks.h"

void setup() {
  // put your setup code here, to run once:
  Serial.begin(115200);

  hal_i2c_init();
  hal_bh1750_init();
  hal_oled_init();
  hal_buzzer_init();

  luxQueue = xQueueCreate(1, sizeof(uint16_t));

  // Core 0
  xTaskCreatePinnedToCore(SensorTask, "SensorTask", 2048, NULL, 1, NULL, 0); 
  // Core 1
  xTaskCreatePinnedToCore(DisplayAlarmTask, "DisplayAlarmTask", 4096, NULL, 1, NULL, 1); 
}

void loop() {
  // put your main code here, to run repeatedly:
  vTaskDelete(NULL);

  // Testing
  // hal_oled_show_status(123, false);
  // hal_buzzer_set(true);
}
