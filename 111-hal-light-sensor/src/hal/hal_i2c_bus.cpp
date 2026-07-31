#include "hal_i2c_bus.h"
#include <Wire.h>

void hal_i2c_init() {
  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);
}





