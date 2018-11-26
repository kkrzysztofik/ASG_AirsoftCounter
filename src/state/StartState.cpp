
#include "StartState.h"
#include "../System.h"
#include "../GameType.h"
#include "../GameGlobalState.h"
#include "../config/Config.h"

long startMillis;



void StartState::onEnter() {
    startMillis = millis();
    System::lcd.clear();
    System::lcd.setCursor(0,0);
    System::greenLed.repeating(300,300);
    System::redLed.repeating(300,300);


    switch (System::config.gameType) {
        case AIRSOFTCOIN:
            System::lcd.print(F("Tryb Airsoftcoin"));
            break;
        case DOMINATION:
            System::lcd.print(F("Tryb Dominacji"));
            break;
        case RESPAWN:
            System::lcd.print(F("Tryb respawn"));
            break;
    }
};

void StartState::update() {
    if(millis()-startMillis>3000) {
        switch (System::config.gameType) {
            case 0: //tryb prosty;
                GameGlobalState::pointsLeft = System::config.airsoftCoinBlockSize;
                System::stateManager.enterAirsoftcoinMined();
                return;
            case 1: //kable proste
            case 2: //kable kodowane
               // System::stateManager.enterCheckWires();
                System::stateManager.enterModeConfig();
                return;
        }
    }
}

void StartState::onExit() {};
