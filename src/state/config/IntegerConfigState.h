//
// Created by Krzysztof Lichocki on 16.11.2018.
//

#ifndef AIRSOFTCOUNTER_INTEGERCONFIGSTATE_H
#define AIRSOFTCOUNTER_INTEGERCONFIGSTATE_H

#include "../State.h"
#include "Arduino.h"
#include "../../System.h"
#include "../../ProgmemLcd.h"
#include <avr/pgmspace.h>

enum IntegerConfigStateState {
    NORMAL,
    NUMBER
};

class IntegerConfigState : public State {
public:

    IntegerConfigState(State *previousState,
                       State *nextState,
                       const __FlashStringHelper *name,
                       uint16_t *currentValue,
                       uint16_t min,
                       uint16_t max);

    virtual void update();

    virtual void onEnter();

    virtual void onExit();

protected:
    State *previousState;
    State *nextState;
    const __FlashStringHelper *name;
    uint16_t *currentValue;
    uint16_t min;
    uint16_t max;
    uint16_t tmpNumber = 0;
    IntegerConfigStateState state = NORMAL;

    virtual void printValue();
    virtual void printState();
    void trySetNumber();
    void numberPushed(uint8_t num);
};




#endif //AIRSOFTCOUNTER_INTEGERCONFIGSTATE_H
