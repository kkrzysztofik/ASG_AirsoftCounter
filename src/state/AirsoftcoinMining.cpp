//
// Created by Krzysztof Lichocki on 15.11.2018.
//

#include "AirsoftcoinMining.h"
#include "../GameGlobalState.h"
#include "../System.h"

void AirsoftcoinMining::onEnter() {
    lastChangeMillis = millis();
    System::lcd.clear();
    timer = System::config.airsoftCoinMiningTime;

    sprintf(System::buffer, "Ziel%3d Czer %3d", GameGlobalState::greenPoints, GameGlobalState::redPoints);
    System::lcd.setCursor(0, 0);
    System::lcd.print(System::buffer);
    printState();

    System::greenLed.disable();
    System::redLed.disable();

};

void AirsoftcoinMining::update() {
    long currentMillis = millis();
    if (currentMillis - lastChangeMillis >= 1000) {
        lastChangeMillis += 1000;

        if (timer == 0) {
            System::buzzer.repeatingTimes(200, 200, 5);
            System::stateManager.enterAirsoftcoinMined();
        } else {
            //System::buzzer.single(200);
            timer -= 1;
            printState();
        }
    }

}

void AirsoftcoinMining::onExit() {};

void AirsoftcoinMining::printState() {
    uint8_t min = timer / 60;
    uint8_t sec = timer % 60;

    sprintf(System::buffer, " %02d:%02d  Resz %3d", min, sec, GameGlobalState::pointsLeft);
    System::lcd.setCursor(0, 1);
    System::lcd.print(System::buffer);
};