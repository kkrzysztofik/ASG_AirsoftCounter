//
// Created by Krzysztof Lichocki on 16.11.2018.
//

#include "ModeConfigState.h"
#include "IntegerConfigState.h"
const char modeConfig_mode[] PROGMEM = "Tryb:";
const char mode_airsoftcoin[] PROGMEM = "AirsoftCoin";
const char mode_domination[] PROGMEM = "Dominacja";
const char mode_respawn[] PROGMEM = "Respawn";

const char *const _EnumConfigState_values[] PROGMEM = {mode_airsoftcoin, mode_domination, mode_respawn};

extern IntegerConfigState airsoftCoinBlockSize;

void ModeConfigState::onEnter() {
    currentSelection = System::config.gameType;
    printState();
    System::redLed.disable();
    System::greenLed.disable();
}

void ModeConfigState::update() {
    NecValue key = System::irController.decode();
    if (key == PREVIOUS) {
        currentSelection = (currentSelection + 2) % 3;
        System::config.gameType = currentSelection;
        printState();
    } else if (key == NEXT) {
        currentSelection = (currentSelection + 1) % 3;
        System::config.gameType = currentSelection;
        printState();
    } else if(key == EQ) {
        System::config.save();
        System::stateManager.enterStart();
    } else if(key == CH_PLUS) {
        System::config.save();
        System::stateManager.changeState(&airsoftCoinBlockSize);
    }
}

void ModeConfigState::onExit() {}


void ModeConfigState::printState() {
    System::lcd.clear();
    System::progmemLcd.print((const __FlashStringHelper *) modeConfig_mode);
    System::lcd.setCursor(0, 1);
    System::progmemLcd.printFromArray( _EnumConfigState_values, currentSelection);
}
