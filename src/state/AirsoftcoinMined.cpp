//
// Created by Krzysztof Lichocki on 15.11.2018.
//

#include "AirsoftcoinMined.h"
#include "../GameGlobalState.h"
#include "../System.h"

#define BUZZER_TIME_SPACE 15000

void AirsoftcoinMined::onEnter() {
    buzzerMillis = millis();
    System::lcd.clear();

    sprintf(System::buffer, "Ziel%3d Czer %3d", GameGlobalState::greenPoints, GameGlobalState::redPoints);
    System::lcd.setCursor(0, 0);
    System::lcd.print(System::buffer);
    sprintf(System::buffer, "GOTOWY  Resz %3d", GameGlobalState::pointsLeft);
    System::lcd.setCursor(0, 1);
    System::lcd.print(System::buffer);


    System::greenLed.constantly();
    System::redLed.constantly();

};

void AirsoftcoinMined::update() {
 //   System::irController.decode();

    if (millis() >= buzzerMillis + BUZZER_TIME_SPACE) {
        buzzerMillis += BUZZER_TIME_SPACE;
        System::buzzer.repeatingTimes(200, 100, 3);
    }
    if (System::greenButton.state()) {
        GameGlobalState::greenPoints += 1;
        GameGlobalState::pointsLeft -= 1;
        nextState();
    } else if (System::redButton.state()) {
        GameGlobalState::redPoints += 1;
        GameGlobalState::pointsLeft -= 1;
        nextState();
    }
    NecValue key = System::irController.decode();
    if (key == EQ) {
        System::stateManager.enterModeConfig();
    }



}

void AirsoftcoinMined::onExit() {}

void AirsoftcoinMined::nextState() {
    if(GameGlobalState::pointsLeft<=0){
        System::stateManager.enterAirsoftcoinEnd();
    } else {
        System::stateManager.enterAirsoftcoinMining();
    }
}