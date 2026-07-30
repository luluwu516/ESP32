#include "hal_bh1750.h"
#include <Wire.h>

namespace {
  uint8_t s_addr = BH1750_ADDR;  // static address (static storage duration)
  constexpr uint16_t DELAY_HMODE_MS = 180;
  constexpr uint16_t DELAY_LMODE_MS = 24;
}

void hal_bh1750_init(uint8_t addr) {
  s_addr = addr;
}

uint16_t hal_bh1750_read_lux(uint8_t mode) {
  // clear and power down
  Wire.beginTransmission(s_addr);
  Wire.write(0x00);
  Wire.endTransmission();

  // power up
  Wire.beginTransmission(s_addr);
  Wire.write(0x01);
  Wire.endTransmission();

  // measurement
  Wire.beginTransmission(s_addr);
  Wire.write(mode);
  Wire.endTransmission();

  uint16_t delay_ms = (mode == BH1750_MODE_LRES) ? DELAY_LMODE_MS : DELAY_HMODE_MS;
  delay(delay_ms);

  Wire.requestFrom(s_addr, (uint8_t)2);
  uint8_t high_byte = Wire.read();  // i2c smallest uint = 1 byte
  uint8_t low_byte = Wire.read();

  // power down again
  Wire.beginTransmission(s_addr);
  Wire.write(0x00);
  Wire.endTransmission();

  uint32_t raw = ((uint32_t)high_byte << 24) | ((uint32_t)low_byte << 16);  // avoid overflow
  return (uint16_t)(raw / 78642);
}