#ifndef LIGHT_ALARM_LOGIC_H
#define LIGHT_ALARM_LOGIC_H

#include <Arduino.h>

constexpr uint16_t LOW_LIGHT_THRESHOLD = 30;
constexpr uint16_t HIGH_LIGHT_THRESHOLD = 300;

bool decide_alarm(uint16_t lux, uint16_t low_threshold, uint16_t high_threshold);

#endif