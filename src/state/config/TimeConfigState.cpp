//
// Created by Krzysztof Lichocki on 26.11.2018.
//

#include "TimeConfigState.h"

TimeConfigState::TimeConfigState(State *previousState, State *nextState, const __FlashStringHelper *name,
                                 uint16_t *currentValue, uint16_t min, uint16_t max)
                                 : IntegerConfigState(previousState, nextState, name, currentValue, min, max){}

void TimeConfigState::printValue() {
    uint8_t min = *currentValue / 60;
    uint8_t sec = *currentValue % 60;

    sprintf(System::buffer, "%d (%03d:%02d)", *currentValue, min, sec);
    System::lcd.print(System::buffer);
}