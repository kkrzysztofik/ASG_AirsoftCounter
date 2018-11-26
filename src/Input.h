#ifndef ASGBOMB_ARDUINO_INPUT_H
#define ASGBOMB_ARDUINO_INPUT_H
#include <stdint.h>
#include <Arduino.h>
class Input {
public:
    Input(uint8_t pin, uint8_t negate);
    uint8_t state();
private:
    uint8_t pin;
    uint8_t negate;
};

#endif //ASGBOMB_ARDUINO_INPUT_H
