//
// Created by Krzysztof Lichocki on 15.11.2018.
//

#include "AirsoftcoinEnd.h"
#include "../System.h"
#include "../GameGlobalState.h"

#define BACKLIGHT_BLINK_DELAY 1000

void AirsoftcoinEnd::onEnter() {
    lastChangeMillis = millis();

    System::greenLed.disable();
    System::redLed.disable();

    System::lcd.clear();
    sprintf(System::buffer,"Ziel%3d Czer %3d", GameGlobalState::greenPoints, GameGlobalState::redPoints);
    System::lcd.setCursor(0,0);
    System::lcd.print(System::buffer);
    sprintf(System::buffer,"PUNKT WYCZERPANY");
    System::lcd.setCursor(0,1);
    System::lcd.print(System::buffer);
    lcdBacklightState = false;
};

void AirsoftcoinEnd::update() {
    if( millis()>=lastChangeMillis + BACKLIGHT_BLINK_DELAY ){
        lastChangeMillis+=BACKLIGHT_BLINK_DELAY;
        lcdBacklightState = !lcdBacklightState;
        if(lcdBacklightState)System::lcd.backlight();
        else System::lcd.noBacklight();
    }
}

void AirsoftcoinEnd::onExit() {};