#ifndef HAL_BH1750_H
#define HAL_BH1750_H

#include <Arduino.h>

constexpr uint8_t BH1750_ADDR = 0x23;
constexpr uint8_t BH1750_MODE_HRES1 = 0x20;
constexpr uint8_t BH1750_MODE_HRES2 = 0x21;
constexpr uint8_t BH1750_MODE_LRES = 0x23;

void     hal_bh1750_init(uint8_t addr = BH1750_ADDR);
uint16_t hal_bh1750_read_lux(uint8_t mode = BH1750_MODE_HRES1);

#endif