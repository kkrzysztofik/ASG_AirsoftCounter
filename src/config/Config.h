
//

#ifndef ASG_ARDUINO_CONFIG_H
#define ASG_ARDUINO_CONFIG_H
#include <stdint.h>
#include "../GameType.h"

struct Config {
    GameType gameType = 0;

    uint16_t airsoftCoinMiningTime = 1*5;
    uint16_t airsoftCoinBlockSize = 3;

    void save();
    void load();
};

#endif //ASG_ARDUINO_CONFIG_H
