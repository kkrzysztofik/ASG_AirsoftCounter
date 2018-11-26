#include "Input.h"

Input::Input(uint8_t pin, uint8_t negate) {
    this->pin = pin;
    this->negate = negate;
    pinMode(pin, INPUT_PULLUP);

}

uint8_t Input::state() {
    return negate ? !digitalRead(pin) : digitalRead(pin);
}
