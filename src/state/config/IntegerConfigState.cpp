//
// Created by Krzysztof Lichocki on 16.11.2018.
//

#include "IntegerConfigState.h"

IntegerConfigState::IntegerConfigState(State *previousState, State *nextState, const __FlashStringHelper *name,
                                       uint16_t *currentValue, uint16_t min, uint16_t max) {
    this->previousState = previousState;
    this->nextState = nextState;
    this->name = name;
    this->currentValue = currentValue;
    this->min = min;
    this->max = max;
}

void IntegerConfigState::onEnter() {
    printState();
}

void IntegerConfigState::update() {
    NecValue key = System::irController.decode();
    if (key == PREVIOUS) {
        if (*currentValue > min) {
            (*this->currentValue)--;
            printState();
        }
    } else if (key == NEXT) {
        if (*currentValue < max) {
            (*this->currentValue)++;
            printState();
        }
    } else if (key == EQ) {
        System::config.save();
        System::stateManager.enterStart();
    } else if (key == CH_PLUS) {
        System::config.save();
        System::stateManager.changeState(nextState);
    } else if (key == CH_MINUS) {
        System::config.save();
        System::stateManager.changeState(previousState);
    } else if (key == N0) {
        numberPushed(0);
    } else if (key == N1) {
        numberPushed(1);
    } else if (key == N2) {
        numberPushed(2);
    } else if (key == N3) {
        numberPushed(3);
    } else if (key == N4) {
        numberPushed(4);
    } else if (key == N5) {
        numberPushed(5);
    } else if (key == N6) {
        numberPushed(6);
    } else if (key == N7) {
        numberPushed(7);
    } else if (key == N8) {
        numberPushed(8);
    } else if (key == N9) {
        numberPushed(9);
    } else if (key == PLAY_PAUSE) {
        trySetNumber();
    }
}

void IntegerConfigState::onExit() {}

void IntegerConfigState::numberPushed(uint8_t num) {
    if(this->state!=NUMBER) {
        this->state = NUMBER;
        tmpNumber = 0;
    }
    if(this->tmpNumber <3000) {
        this->tmpNumber = tmpNumber * 10 + num;
        printState();
    }
}

void IntegerConfigState::trySetNumber() {
    if(this->state==NUMBER) {
        if (tmpNumber < min || tmpNumber > max) {
            System::lcd.clear();
            System::lcd.print(F("Poza zakresem"));
            System::lcd.setCursor(0, 1);
            sprintf(System::buffer, "[%d-%d]", min, max);
            System::lcd.print(System::buffer);
        } else {
            *this->currentValue = tmpNumber;
        }
        this->state = NORMAL;
    } else {
        printState();
    }
}
void IntegerConfigState::printValue() {
    System::lcd.print(*this->currentValue);
}

void IntegerConfigState::printState() {
    System::lcd.clear();
    System::progmemLcd.print(this->name);
    System::lcd.setCursor(0, 1);
    if (this->state == NORMAL) {
        printValue();
    } else {
        sprintf(System::buffer, "-(%d)-", tmpNumber);
        System::lcd.print(System::buffer);
    }
}
