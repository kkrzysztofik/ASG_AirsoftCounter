
//

#ifndef ASGBOMB_ARDUINO_STATE_H
#define ASGBOMB_ARDUINO_STATE_H
class State {
public:
    virtual void update();
    virtual void onEnter();
    virtual void onExit();
};
#endif //ASGBOMB_ARDUINO_STATE_H
