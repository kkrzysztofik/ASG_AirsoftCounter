
#include "Config.h"
#include <HardwareSerial.h>
#include "../System.h"
#include <EEPROM.h>

void Config::save() {
    EEPROM.put(0, System::config);
}

void Config::load() {
    EEPROM.get(0, System::config);

}