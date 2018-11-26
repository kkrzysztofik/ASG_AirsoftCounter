//
// Created by Krzysztof Lichocki on 15.11.2018.
//

#ifndef AIRSOFTCOUNTER_GAMEGLOBALSTATE_H
#define AIRSOFTCOUNTER_GAMEGLOBALSTATE_H

#include <Arduino.h>
struct GameGlobalState {
    static uint16_t greenPoints;
    static uint16_t redPoints;
    static uint16_t pointsLeft;
};


#endif //AIRSOFTCOUNTER_GAMEGLOBALSTATE_H
