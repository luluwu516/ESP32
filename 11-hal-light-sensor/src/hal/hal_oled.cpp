#include "hal_oled.h"
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

namespace {
  Adafruit_SSD1306 s_display(OLED_WIDTH, OLED_HEIGHT, &Wire, -1);
}

void hal_oled_init() {
  if(!s_display.begin(SSD1306_SWITCHCAPVCC, OLED_I2C_ADDR)) {
    Serial.println("OLED init failed");
    while(true) {
      delay(1000);
    }
  }
  s_display.setTextColor(SSD1306_WHITE);
  s_display.setTextSize(1);
}

void hal_oled_show_status(uint16_t lux, bool alarm_active) {
  s_display.clearDisplay();

  s_display.setCursor(0, 0);
  s_display.print("Light level:");
  s_display.setCursor(0, 16);
  s_display.print(lux);
  s_display.print(" lux");

  if (alarm_active) {
    s_display.setCursor(0, 32);
    s_display.print("!! WARNING !!");
    s_display.setCursor(0, 48);
    s_display.print("IT'S TOO DARK");
  }

  s_display.display();
}