//
// Created by Krzysztof Lichocki on 15.11.2018.
//

#ifndef AIRSOFTCOUNTER_AIRSOFTCOINMINING_H
#define AIRSOFTCOUNTER_AIRSOFTCOINMINING_H
#include "State.h"
#include <Arduino.h>

class AirsoftcoinMining : public State {

    virtual void update();
    virtual void onEnter();
    virtual void onExit();

private:
    long lastChangeMillis;
    uint16_t timer;

    void printState();




};


#endif //AIRSOFTCOUNTER_AIRSOFTCOINMINING_H
