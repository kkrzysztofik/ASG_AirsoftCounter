//
// Created by Krzysztof Lichocki on 16.11.2018.
//

#ifndef AIRSOFTCOUNTER_IRCONTROLLER_H
#define AIRSOFTCOUNTER_IRCONTROLLER_H

#include <IRremote.h>
#include "NecValue.h"


class IRController {
public:
    IRController(IRrecv* irrecv);

    NecValue decode();
private:
    const IRrecv* irrecv;
    uint16_t last;
};


#endif //AIRSOFTCOUNTER_IRCONTROLLER_H
