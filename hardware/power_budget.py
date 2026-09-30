"""Battery runtime estimate for the carrier + Heltec V4 (duty-cycle model, not a circuit sim).

Every figure is battery-side mA at ~3.7 V. Sources: Heltec V4 datasheet Rev 1.4 table 3.4 (RX, TX,
WiFi, sleep; measured on USB, and the V4's 3V3 is a linear LDO, so battery current is about the
same); game.rs (beep timing); design doc (PN532 polling ~20 mA). Everything marked EST is a guess:
replace it with a measurement once the board exists (USB meter or INA219 in the J_BAT lead).

    /usr/bin/python3 power_budget.py
"""
from math import ceil

CELLS_MAH = 2 * 3400  # 2x Samsung INR18650-35E in parallel
USABLE = 0.90  # EST: share of capacity above a ~3.3 V firmware shutdown at these currents
BOOST_EFF = 0.85  # EST: MT3608 at 5-100 mA out from ~3.7 V
VBAT = 3.7


def lora_airtime_s(payload, sf=9, bw=125e3, cr=1, preamble=8, crc=True, implicit=False):
    """Semtech SX126x time-on-air formula (cr=1 means 4/5)."""
    tsym = 2 ** sf / bw
    de = 1 if tsym > 0.016 else 0
    n = 8 + max(ceil((8 * payload - 4 * sf + 28 + 16 * crc - 20 * implicit) / (4 * (sf - 2 * de))) * (cr + 4), 0)
    return (preamble + 4.25) * tsym + n * tsym


def from_5v(ma_5v):
    """Battery current for a load on the +5V boost rail."""
    return ma_5v * 5.0 / (VBAT * BOOST_EFF)


# Heltec board (ESP32-S3 awake, CPU clock as shipped, no light sleep)
HELTEC_RX = 75.0  # datasheet: LoRa RX on, TX off
HELTEC_TX_27DBM = 750.0  # datasheet: 27 dBm, 868 MHz (EU g3 sub-band limit is 500 mW ERP)
HELTEC_WIFI_AP = 170.0  # datasheet
HELTEC_SLEEP = 0.020  # datasheet: 20 uA, battery powered
# Carrier and off-board loads
GNSS = 25.0  # EST: L76K tracking, on Heltec Ve (3V3)
NFC_POLL = 20.0  # design doc: PN532 RF bursts ~50 ms on / 300 ms, average
NFC_IDLE = 3.0  # EST: module power LED + PN532 power-down
LCD_LOGIC_5V = 1.5  # EST: HD44780 + PCF8574 backpack
LCD_BACKLIGHT_5V = 60.0  # EST: 20x4 backlight; the biggest unknown on the 5 V side
LED_RING_5V = 10.0  # EST: one ONPOW 6 V ring run at 5 V
BUZZER_5V = 8.0  # BZ-38 (web figure)
GATE_PD = 3.0 / 11e3 * 1e3  # 10k gate pull-down + 1k: 0.27 mA per driver that is on
AMP_ON = 13.0  # NS4168 quiescent with CTRL high; firmware holds CTRL low between clips (1 uA off)
AMP_PLAYING = 0.4 / VBAT * 1e3  # EST: ~0.4 W average electrical while a clip plays
BOOST_IDLE = 1.0  # EST: MT3608 switching at near-zero load
PROT = 0.006  # XB8089D operating current

READY_BUZZ_DUTY = 3 * 0.2 / 15  # game.rs READY_BEEP: 3 x 200 ms every 15 s


def lora_avg(period_s, payload=40, sf=9):
    """Average extra current of one STATUS packet every period_s (TX replaces RX while sending)."""
    t = lora_airtime_s(payload, sf)
    return (HELTEC_TX_27DBM - HELTEC_RX) * t / period_s, t / period_s


def scenario(deluxe, game, backlight, status_s=30, clip_duty=0.05):
    ma = {"Heltec awake, LoRa RX": HELTEC_RX}
    ma["LoRa STATUS TX"], _ = lora_avg(status_s)
    if deluxe:
        ma["GNSS"] = GNSS
        ma["PN532"] = NFC_POLL if game else NFC_IDLE
        ma["Amp (on only for clips)"] = (AMP_ON + AMP_PLAYING) * clip_duty if game else 0.0
    five = LCD_LOGIC_5V + (LCD_BACKLIGHT_5V if backlight else 0)
    if game:
        five += LED_RING_5V + BUZZER_5V * READY_BUZZ_DUTY
        ma["Gate pull-downs"] = GATE_PD
    ma["5 V rail via boost"] = from_5v(five) + BOOST_IDLE
    ma["XB8089D"] = PROT
    return ma


def hours(total_ma, derate=1.0):
    return CELLS_MAH * USABLE * derate / total_ma


def show(name, ma):
    total = sum(ma.values())
    print(f"\n{name}: {total:.0f} mA -> {hours(total):.0f} h (20 C), {hours(total, 0.8):.0f} h (0 C, -20 %)")
    for k, v in sorted(ma.items(), key=lambda kv: -kv[1]):
        print(f"  {k:24} {v:7.1f} mA  {100 * v / total:4.0f} %")


def main():
    t = lora_airtime_s(40, 9)
    _, duty = lora_avg(30)
    print(f"STATUS 40 B at SF9/125 kHz: {t * 1000:.0f} ms on air, {100 * duty:.1f} % duty at 30 s "
          f"(sub-band limit 10 %)")
    show("Deluxe, game running, backlight on", scenario(True, True, True))
    show("Deluxe, game running, backlight off", scenario(True, True, False))
    show("Budget, game running, backlight on", scenario(False, True, True))
    show("Deluxe, key on, waiting for HQ (no game, backlight off)", scenario(True, False, False, status_s=60))
    show("WiFi setup (AP on, backlight on)", {"Heltec WiFi AP": HELTEC_WIFI_AP, "5 V rail": from_5v(61.5) + BOOST_IDLE})
    # Key left on after the game, firmware in deep sleep: what still draws from the cells
    parked = {"Heltec deep sleep": HELTEC_SLEEP, "PN532 module idle": NFC_IDLE,
              "LCD logic via boost": from_5v(LCD_LOGIC_5V) + BOOST_IDLE, "XB8089D": PROT}
    total = sum(parked.values())
    days = CELLS_MAH / total / 24  # full pack down to U4's 2.5 V cutoff
    print(f"\nKey left on, firmware asleep: {total:.1f} mA -> about {days:.0f} days until U4 cuts off at 2.5 V")
    print("  (cut this with the key; firmware cannot switch off the boost or the PN532 module)")


if __name__ == "__main__":
    # Self-check against Semtech's calculator: 20 B, SF7, 125 kHz, CR 4/5, 8-symbol preamble -> 56.6 ms
    assert abs(lora_airtime_s(20, 7) - 0.05658) < 1e-4, lora_airtime_s(20, 7)
    assert hours(100) > hours(200)
    main()
