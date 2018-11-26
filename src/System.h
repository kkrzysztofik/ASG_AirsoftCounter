
//

#ifndef ASG_ARDUINO_SYSTEM_H
#define ASG_ARDUINO_SYSTEM_H

#include <Arduino.h>
#include <LiquidCrystal_I2C.h>
#include "state/StateManager.h"
#include "./config/Config.h"
#include "Output.h"
#include "Input.h"
#include "ProgmemLcd.h"
#include "./ir/IRController.h"
#include <IRremote.h>

class System {

public:
    static LiquidCrystal_I2C lcd;
    static IRController irController;
    static ProgmemLcd progmemLcd;

    static Input greenButton;
    static Input redButton;

    static Output greenLed;
    static Output redLed;
    static Output buzzer;
    static Output explosiveLed;


    static Config config;
    static StateManager stateManager;

    static char buffer[17];

    static void init();

    static void update();

private:
    static IRrecv irrecv;

};

#endif //ASG_ARDUINO_SYSTEM_H
