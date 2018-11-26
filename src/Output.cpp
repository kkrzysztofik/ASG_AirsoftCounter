#include "Output.h"

Output::Output(int pin, uint8_t negated) {
    this->pin = pin;
    this->negated = negated;
    pinMode(pin, OUTPUT);
    disable();
}

void Output::disable() {
    setState(0);
    this->currentMode = CONSTANTLY;
}

void Output::constantly() {
    setState(1);
    this->currentMode = CONSTANTLY;
}

void Output::single(int duration) {
    this->duration = duration;
    this->currentMode = SINGLE;
    this->startMillis = millis();
    setState(1);
}

void Output::repeating(int duration, int breakDuration) {
    this->duration = duration;
    this->breakDuration = breakDuration;
    this->currentMode = REPEATING;
    this->startMillis = millis();
    setState(1);
}

void Output::repeatingTimes(int duration, int breakDuration, uint8_t times) {
    this->duration = duration;
    this->breakDuration = breakDuration;
    this->currentMode = REPEATING_TIMES;
    this->times = times;
    this->startMillis = millis();
    setState(1);
}

void Output::repeatingToSecond(int duration) {
    this->duration = duration;
    this->currentMode = REPEATING_TO_SECOND;
    setState( 1);
}

void Output::update() {
    switch(currentMode){
        case CONSTANTLY:
            break;
        case SINGLE:
            if(millis()-startMillis>duration){
                this->currentMode = CONSTANTLY;
                setState(0);
            }
            break;
        case REPEATING:
            if((millis()-startMillis) % (duration+breakDuration) < duration){
                setState(1);
            } else {
                setState(0);
            }
            break;
        case REPEATING_TIMES:
            if(times<=0){
                this->disable();
            }
            if((millis()-startMillis) % (duration+breakDuration) < duration){
                setState(1);
                lastLevel = 1;
            } else {
                setState(0);
                if(lastLevel!=0){
                    times-=1;
                }
                lastLevel = 0;
            }
            break;
        case REPEATING_TO_SECOND:
            if(millis()%1000 < duration){
                setState(1);
            } else {
                setState(0);
            }
    }
}

void Output::setState(uint8_t state) {
    if(negated) state = !state;
    digitalWrite(pin, state);
}