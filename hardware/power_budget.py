"""Battery runtime estimate for the carrier + Heltec V4 (duty-cycle model, not a circuit sim).

Every figure is battery-side mA at ~3.6 V (the 35E's nominal). Sources: Heltec V4 datasheet Rev 1.4
table 3.4 (RX, TX, WiFi, sleep; measured on USB, and the V4's 3V3 is a CE6260B33M linear LDO, so
battery current is about the same); game.rs (beep timing); design.py (two button LED rings, gate
divider); fab/PARTS_REVIEW.md (5.1 V rail, XB8089D); design doc (PN532 polling ~20 mA). Everything
marked EST is a guess: replace it with a measurement once the board exists (USB meter or INA219 in
the J_PWR1 lead). The one worth measuring first is LCD_BACKLIGHT_5V.

    /usr/bin/python3 power_budget.py
"""
from math import ceil

CELLS_MAH = 4 * 3350  # 4x Samsung INR18650-35E in parallel (the pack board). 3350 mAh is the
                      # datasheet minimum (rated 3250 at 0.2 C to 2.65 V); 3400 is only the typical
                      # number.
USABLE = 0.84  # EST: share of capacity above a ~3.5 V firmware shutdown. Heltec's own V4 test:
               # "below 3.45 V operation becomes erratic", ESP32 reboot at 3.40 V, and a 2x3000 mAh
               # pack delivered 4429 mAh before that. Do not plan on a 3.3 V cutoff.
BOOST_EFF = 0.90  # MT3608, 3.7 V in / 5 V out / <= 100 mA: 92-93 % in the datasheet graph; 0.90
                  # leaves margin for light-load PFM losses
VBAT = 3.6  # 35E nominal; a better mean over a discharge than 3.7


def lora_airtime_s(payload, sf=9, bw=125e3, cr=1, preamble=8, crc=True, implicit=False):
    """Semtech SX126x time-on-air formula (cr=1 means 4/5)."""
    tsym = 2 ** sf / bw
    de = 1 if tsym > 0.016 else 0
    n = 8 + max(ceil((8 * payload - 4 * sf + 28 + 16 * crc - 20 * implicit) / (4 * (sf - 2 * de))) * (cr + 4), 0)
    return (preamble + 4.25) * tsym + n * tsym


def from_5v(ma_5v):
    """Battery current for a load on the +5.1 V boost rail (D1 + the 75k/10k divider)."""
    return ma_5v * 5.1 / (VBAT * BOOST_EFF)


# Heltec board (ESP32-S3 awake, CPU clock as shipped, no light sleep)
HELTEC_RX = 75.0  # datasheet: LoRa RX on, TX off
HELTEC_TX_27DBM = 750.0  # datasheet 27 dBm row; an upper bound on the TX setpoint, not a target.
                         # 27 dBm conducted + the 3.6 dBi antenna (OFFBOARD_PARTS #15) is ~0.6 W ERP,
                         # over the g3 500 mW ERP limit, so cap the setpoint at ~26 dBm (the datasheet
                         # has no 26 dBm row; Heltec's own V4 test measured ~1 A peaks at 27 dBm).
HELTEC_WIFI_AP = 170.0  # datasheet
HELTEC_SLEEP = 0.020  # datasheet: 20 uA, battery powered
# Carrier and off-board loads
GNSS = 29.0  # Quectel L76K hardware design: 29 mA acquisition and tracking, on the Heltec's
             # switched GNSS 3V3 (VGNSS_Ctrl/GPIO34). 41 mA with an active antenna (Seeed's L76K).
NFC_POLL = 20.0  # design doc: PN532 RF bursts ~50 ms on / 300 ms, average. Datasheet is ~91 mA
                 # field-on and ~20-30 mA idle, so one of the two is under-counted.
NFC_IDLE = 3.0  # EST: module power LED + PN532 PowerDown command (45 uA). A chip left running
                # idles ~20 mA, which makes the parked figure 12 days instead of 44.
LCD_LOGIC_5V = 2.0  # 1.2 mA typ HD44780 logic (Crystalfontz 20x4) + contrast pot + PCF8574
LCD_BACKLIGHT_5V = 100.0  # PLANNING value until it is measured: the largest single load in the
                          # game scenarios, and the one figure that still decides the answer.
                          # The module is a generic 2004A panel on an HW-61 backpack, and the HW-61
                          # only switches it with a transistor from P3, so the panel's own resistor
                          # sets the current: 48-60 mA typ for a white LED array (Raystar
                          # RC2004A-GHW), 120 mA for the blue 4.2 V flavour, 200+ if unprotected.
                          # Measure it (fab/OFFBOARD_PARTS.md item 5) and put the real number here.
LED_RING_5V = 15.0  # one ONPOW 6 V ring run at 5 V; design.py's figure, ONPOW publishes none.
                    # Two rings are fitted (LR + LB), so scenario() counts this twice.
BUZZER_5V = 8.0  # BZ-38: TME's spec page, piezo with generator, 3-28 V, 8 mA
GATE_PD = 3.0 / 11e3 * 1e3  # 10k gate pull-down + 1k: 0.27 mA per driver that is on
AMP_ON = 13.0  # NS4168 quiescent with CTRL high; firmware holds CTRL low between clips (1 uA off)
AMP_PLAYING = 0.4 / VBAT * 1e3  # EST: ~0.4 W average electrical while a clip plays
BOOST_IDLE = 1.0  # EST: MT3608 switching at near-zero load
PROT = 0.006  # XB8089D operating current
# Pack board with the key off (the carrier is unpowered; only the pack's own electronics drain the
# cells). EST from the P0 datasheets: STM32C071 Stop with RTC/LSI is 85 uA typical, so the design
# doc's "tens of uA" target is unreachable; 2x INA3221 power-down ~1 uA each, BQ25601 battery-only
# ~4.5 uA, XC6206 Iq ~1 uA, plus the 4 x 1M gate resistors (4.2 V / 1M = 4.2 uA each) while the
# switches are on. Cell self-discharge (~1-3 %/month) dominates this after about a year.
PACK_IQ_MA = 0.085 + 2 * 0.001 + 0.0045 + 0.001 + 4 * 0.0042
# Cell branch series resistance (5 A fuse + 20 mOhm shunt + back-to-back AO3401A + track) ~150 mOhm
# EST. Deliberately not modelled: it drops < 0.3 V at these currents, well inside the 0.84 USABLE
# derate that already covers the 3.5 V shutdown.
BRANCH_MOHM = 150

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
        five += 2 * LED_RING_5V + BUZZER_5V * READY_BUZZ_DUTY  # both panel rings are lit
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
    show("WiFi setup (AP on, backlight on)", {"Heltec WiFi AP": HELTEC_WIFI_AP,
                                             "5 V rail": from_5v(LCD_LOGIC_5V + LCD_BACKLIGHT_5V) + BOOST_IDLE})
    # The backlight is the one unknown that can still move the answer by 20 %. from_5v() is linear,
    # so add the difference rather than rebuilding the scenario.
    base = sum(scenario(True, True, True).values())
    print(f"  backlight unknown ({LCD_BACKLIGHT_5V:.0f} mA assumed): 32 mA -> "
          f"{hours(base + from_5v(32 - LCD_BACKLIGHT_5V)):.0f} h, {LCD_BACKLIGHT_5V:.0f} mA -> "
          f"{hours(base):.0f} h, 120 mA -> {hours(base + from_5v(120 - LCD_BACKLIGHT_5V)):.0f} h"
          " (Deluxe, game, backlight on)")
    # Key left on after the game, firmware in deep sleep: what still draws from the cells
    parked = {"Heltec deep sleep": HELTEC_SLEEP, "PN532 module idle": NFC_IDLE,
              "LCD logic via boost": from_5v(LCD_LOGIC_5V) + BOOST_IDLE, "XB8089D": PROT}
    total = sum(parked.values())
    days = CELLS_MAH / total / 24  # full pack down to the pack's 2.5 V protector cutoff
    print(f"\nKey left on, firmware asleep: {total:.1f} mA -> about {days:.0f} days until the pack "
          "cuts off at 2.5 V")
    print("  (cut this with the key; firmware cannot switch off the boost or the PN532 module)")
    print("  Optimistic on purpose: this needs the radio off (a live V4 node sits at a 12 mA floor)")
    print("  and the PN532 in PowerDown. Miss either and it is days, not weeks.")
    # Key off: the carrier is unpowered, so this is the pack's own drain (storage life, not runtime)
    years = CELLS_MAH * USABLE / PACK_IQ_MA / 24 / 365
    print(f"\nPack quiescent, key off (carrier unpowered): {PACK_IQ_MA * 1000:.0f} uA -> "
          f"{years:.0f} years of pack electronics ({BRANCH_MOHM} mOhm branch drop not modelled)")
    print("  Cell self-discharge (~1-3 %/month) is the larger term over a season.")


if __name__ == "__main__":
    # Self-check against Semtech's calculator and the published airtime table (125 kHz, CR 4/5,
    # 8-symbol preamble): 56.6 ms at SF7/20 B, 144 ms at SF9/10 B, 991 ms at SF12/10 B.
    assert abs(lora_airtime_s(20, 7) - 0.05658) < 1e-4, lora_airtime_s(20, 7)
    assert abs(lora_airtime_s(10, 9) - 0.144) < 2e-3, lora_airtime_s(10, 9)
    assert abs(lora_airtime_s(10, 12) - 0.991) < 2e-3, lora_airtime_s(10, 12)
    assert hours(100) > hours(200)
    assert hours(100, 0.8) < hours(100)  # the cold derate must not raise the runtime
    assert from_5v(60) > 60  # a 5 V load always costs more than its own current from the pack
    main()
