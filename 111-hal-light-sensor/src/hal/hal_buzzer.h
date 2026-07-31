#ifndef HAL_BUZZER_H
#define HAL_BUZZER_H

#include <Arduino.h>

constexpr uint8_t BUZZER_PIN = 16;
constexpr uint16_t BUZZER_FREQ_HZ = 110;
constexpr uint8_t BUZZER_RESOLUTION_BITS = 8;
constexpr uint8_t BUZZER_DUTY_ON = 128;

void hal_buzzer_init();
void hal_buzzer_set(bool on);

#endif