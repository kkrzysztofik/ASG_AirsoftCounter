#include <Arduino.h>
#include "System.h"
//Wyświetlacz w wersji V1
LiquidCrystal_I2C System::lcd(0x3F, 2, 1, 0, 4, 5, 6, 7, 3, POSITIVE);
//Wyświetlacz w wersji V2
//LiquidCrystal_I2C System::lcd(0x27, 2, 1, 0, 4, 5, 6, 7, 3, POSITIVE);
ProgmemLcd System::progmemLcd(&System::lcd);
IRrecv System::irrecv(5);
IRController System::irController(&System::irrecv);

Input System::greenButton(6, 1);
Input System::redButton(7, 1);
Output System::greenLed(8, 0);
Output System::redLed(9, 0);
Output System::buzzer(10, 1);

char System::buffer[17];

Config System::config;
StateManager System::stateManager;



void System::init() {
    System::lcd.begin(16, 2);
    System::lcd.backlight();
   // System::config.save();
    System::config.load();

    System::redLed.repeating(2200,200);
    stateManager.init();
    System::irrecv.enableIRIn(); // Start the receiver
    System::irrecv.blink13(true);
}

void System::update() {
    stateManager.update();
    System::greenLed.update();
    System::redLed.update();
    System::buzzer.update();
}
