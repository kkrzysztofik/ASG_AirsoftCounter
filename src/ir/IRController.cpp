//
// Created by Krzysztof Lichocki on 16.11.2018.
//

#include "IRController.h"

IRController::IRController(IRrecv* irrecv){
    this->irrecv = irrecv;
}

NecValue IRController::decode() {
    decode_results results;
    if (irrecv->decode(&results)) {
        uint16_t value = results.value;
        irrecv->resume();
        if(!(value==0xFFFF && (last==NEXT || last==PREVIOUS))){
            last = value;
        }
        return last;
    } else return NONE;
}
