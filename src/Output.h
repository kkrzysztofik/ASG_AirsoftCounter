#ifndef ASGBOMB_ARDUINO_OUTPUT_H
#define ASGBOMB_ARDUINO_OUTPUT_H
#include <stdint.h>
#include <Arduino.h>
class Output {
public:
    Output(int pin, uint8_t negated);

    void disable();
    void constantly();
    void single(int duration);
    void repeating(int duration, int breakDuration);
    void repeatingTimes(int duration, int breakDuration, uint8_t times);
    void repeatingToSecond(int duration);

    void update();

private:
    int pin;
    uint8_t negated;
    uint8_t currentState;

    uint8_t times;
    uint8_t lastLevel;
    long startMillis;
    int duration;
    int breakDuration;

    void setState(uint8_t);

    enum Mode {
        CONSTANTLY,
        SINGLE,
        REPEATING,
        REPEATING_TIMES,
        REPEATING_TO_SECOND
    };
    Mode currentMode;
};
#endif //ASGBOMB_ARDUINO_OUTPUT_H
