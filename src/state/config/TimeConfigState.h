//
// Created by Krzysztof Lichocki on 26.11.2018.
//

#ifndef AIRSOFTCOUNTER_TIMCONFIGSTATE_H
#define AIRSOFTCOUNTER_TIMCONFIGSTATE_H

#include "IntegerConfigState.h"

class TimeConfigState : public IntegerConfigState {
public:
    TimeConfigState(State *previousState,
                   State *nextState,
                   const __FlashStringHelper *name,
                   uint16_t *currentValue,
                   uint16_t min,
                   uint16_t max);

protected:
    virtual void printValue();
};


#endif //AIRSOFTCOUNTER_TIMCONFIGSTATE_H
