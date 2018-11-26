#ifndef ASGBOMB_ARDUINO_STATEMANAGER_H
#define ASGBOMB_ARDUINO_STATEMANAGER_H

#include "State.h"

class StateManager {
public:
    void init();
    void update();

    void changeState(State* newState);

    void enterStart();
    void enterAirsoftcoinMined();
    void enterAirsoftcoinMining();
    void enterAirsoftcoinEnd();
    void enterModeConfig();

private:
    State* currentState;





};

#endif //ASGBOMB_ARDUINO_STATEMANAGER_H
