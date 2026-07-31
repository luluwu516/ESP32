#ifndef HAL_OLED_H
#define HAL_OLED_H

#include <Arduino.h>

constexpr uint8_t OLED_WIDTH = 128;
constexpr uint8_t OLED_HEIGHT = 64;
constexpr uint8_t OLED_I2C_ADDR = 0x3C;

void hal_oled_init();
void hal_oled_show_status(uint16_t lux, bool alarm_active);

#endif