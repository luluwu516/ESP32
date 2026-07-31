#ifndef HAL_I2C_BUS_H
#define HAL_I2C_BUS_H

#include <Arduino.h>

constexpr uint8_t I2C_SCL_PIN = 22;
constexpr uint8_t I2C_SDA_PIN = 21;

void hal_i2c_init();

#endif