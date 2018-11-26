//
// Created by Krzysztof Lichocki on 15.11.2018.
//

#ifndef AIRSOFTCOUNTER_AIRSOFTCOINMINED_H
#define AIRSOFTCOUNTER_AIRSOFTCOINMINED_H

#include "State.h"
class AirsoftcoinMined : public State {

    virtual void update();
    virtual void onEnter();
    virtual void onExit();

private:
    long buzzerMillis;

    void nextState();
};


#endif //AIRSOFTCOUNTER_AIRSOFTCOINMINED_H
