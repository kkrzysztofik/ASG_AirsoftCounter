//
// Created by Krzysztof Lichocki on 16.11.2018.
//

#include "ProgmemLcd.h"
#include "System.h"
ProgmemLcd::ProgmemLcd(LiquidCrystal_I2C* lcd) {
    this->lcd = lcd;
}

void ProgmemLcd::print(const __FlashStringHelper * str ){
    System::lcd.print(str);
}

void ProgmemLcd::printFromArray(char **str, uint8_t index) {
    strcpy_P(System::buffer, (char*)pgm_read_word(&(str[index])));
    System::lcd.print(System::buffer);
}