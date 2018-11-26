
//

#ifndef ASGBOMB_ARDUINO_STARTSTATE_H
#define ASGBOMB_ARDUINO_STARTSTATE_H

#include "State.h"

//Stan wejściowy do wyboru trybu gry
class StartState : public State {

    virtual void update();
    virtual void onEnter();
    virtual void onExit();
};

#endif //ASGBOMB_ARDUINO_STARTSTATE_H
