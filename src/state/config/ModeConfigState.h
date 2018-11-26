//
// Created by Krzysztof Lichocki on 16.11.2018.
//

#ifndef AIRSOFTCOUNTER_MODECONFIGSTATE_H
#define AIRSOFTCOUNTER_MODECONFIGSTATE_H

#include "../State.h"
#include "Arduino.h"
#include "../../System.h"
#include "../../ProgmemLcd.h"
#include <avr/pgmspace.h>
class ModeConfigState : public State {
public:

    virtual void update();

    virtual void onEnter();

    virtual void onExit();

private:
    uint8_t currentSelection;

    void printState();
};

#endif //AIRSOFTCOUNTER_MODECONFIGSTATE_H
