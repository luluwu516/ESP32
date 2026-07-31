#ifndef TASKS_H
#define TASKS_H

#include <Arduino.h>

extern QueueHandle_t luxQueue;

void SensorTask(void *pvParameters);
void DisplayAlarmTask(void *pvParameters);

#endif