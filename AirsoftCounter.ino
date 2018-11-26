#include "src/System.h"
void setup()
{
 // Serial.begin(9600);
  System::init();
}

void loop() {
  System::update();
}
