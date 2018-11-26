//
// Created by Krzysztof Lichocki on 16.11.2018.
//

#ifndef AIRSOFTCOUNTER_PROGMEMLCD_H
#define AIRSOFTCOUNTER_PROGMEMLCD_H
#include <LiquidCrystal_I2C.h>
#include <Arduino.h>

class ProgmemLcd {
public:
    ProgmemLcd(LiquidCrystal_I2C* lcd);

    void print(const __FlashStringHelper * str);
    void printFromArray(char** str, uint8_t index);

private:
    LiquidCrystal_I2C* lcd;
};


#endif //AIRSOFTCOUNTER_PROGMEMLCD_H
