//
// Created by Krzysztof Lichocki on 15.11.2018.
//

#ifndef AIRSOFTCOUNTER_AIRSOFTCOINEND_H
#define AIRSOFTCOUNTER_AIRSOFTCOINEND_H
#include "State.h"

class AirsoftcoinEnd : public State {

    virtual void update();
    virtual void onEnter();
    virtual void onExit();

private:
    long lastChangeMillis;
    bool lcdBacklightState;

};


#endif //AIRSOFTCOUNTER_AIRSOFTCOINEND_H
