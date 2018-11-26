#include "StateManager.h"
#include "StartState.h"
#include "AirsoftcoinMined.h"
#include "AirsoftcoinMining.h"
#include "AirsoftcoinEnd.h"
#include "./config/ModeConfigState.h"
#include "./config/IntegerConfigState.h"
#include "./config/TimeConfigState.h"

StartState startState;
AirsoftcoinMined airsoftcoinMined;
AirsoftcoinMining airsoftcoinMining;
AirsoftcoinEnd airsoftcoinEnd;

ModeConfigState modeConfig;

extern IntegerConfigState airsoftCoinBlockSize;
extern TimeConfigState airsoftCoinMiningTime;

const char airsoftCoinBlockSizeText[] PROGMEM = "Block AC:";
IntegerConfigState airsoftCoinBlockSize(&modeConfig, &airsoftCoinMiningTime, (const __FlashStringHelper *)airsoftCoinBlockSizeText,
            &System::config.airsoftCoinBlockSize,1,1000);

const char airsoftCoinMiningTimeText[] PROGMEM = "Czas kopania AC:";
TimeConfigState airsoftCoinMiningTime(&airsoftCoinBlockSize, &modeConfig, (const __FlashStringHelper *)airsoftCoinMiningTimeText,
                                        &System::config.airsoftCoinMiningTime,5,30000);


void StateManager::init() {
    this->currentState = 0;
    changeState(&startState);
}

void StateManager::update() {
    this->currentState->update();
}

void StateManager::changeState(State *newState) {
    if (currentState != 0) {
        currentState->onExit();
    }
    currentState = newState;
    currentState->onEnter();
}

void StateManager::enterStart() {
    changeState(&startState);
}

void StateManager::enterAirsoftcoinMined() {
    changeState(&airsoftcoinMined);
}

void StateManager::enterAirsoftcoinMining() {
    changeState(&airsoftcoinMining);
}

void StateManager::enterAirsoftcoinEnd() {
    changeState(&airsoftcoinEnd);
}

void StateManager::enterModeConfig() {
    changeState(&modeConfig);
}