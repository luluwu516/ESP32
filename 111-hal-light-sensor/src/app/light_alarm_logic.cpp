#include "light_alarm_logic.h"

bool decide_alarm(uint16_t lux, uint16_t low_threshold, uint16_t high_threshold) {
  return (lux > low_threshold) && (lux < high_threshold);
}