#include "hal_buzzer.h"

void hal_buzzer_init() {
  ledcAttach(BUZZER_PIN, BUZZER_FREQ_HZ, BUZZER_RESOLUTION_BITS);
}

void hal_buzzer_set(bool on) {
  ledcWrite(BUZZER_PIN, on ? BUZZER_DUTY_ON : 0);
}