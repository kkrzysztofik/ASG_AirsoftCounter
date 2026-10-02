"""Battery runtime estimate for the carrier + Heltec V4 (duty-cycle model, not a circuit sim).

Every figure is battery-side mA at ~3.6 V (the 35E's nominal). Sources: Heltec V4 datasheet Rev 1.4
table 3.4 (RX, TX, WiFi, sleep; measured on USB, and the V4's 3V3 is a CE6260B33M linear LDO, so
battery current is about the same); game.rs (beep timing); design.py (two button LED rings, gate
divider); fab/PARTS_REVIEW.md (5.1 V rail); design doc (PN532 polling ~20 mA). Everything
marked EST is a guess: replace it with a measurement once the board exists (USB meter or INA219 in
the J_PWR1 lead). Measure LCD_IDLE_5V and HELTEC_RX first.

    /usr/bin/python3 power_budget.py [--tme]
"""
import sys
from math import ceil

TME = "--tme" in sys.argv[1:]   # hand-build boards: L072 + 4x INA228 + PCM5100A/PAM8302A

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
# Optimized firmware targets (power-efficiency design, table 2). EST until measured.
HELTEC_RX_OPT = 20.0  # 80 MHz + automatic light sleep, SX1262 RX duty cycle
GNSS_OPT = 1.0  # one fix at boot, then VGNSS off (backup domain only)
NFC_POLL_OPT = 5.0  # PN532 PowerDown between polls, polls only when a card is expected
# Carrier and off-board loads
GNSS = 29.0  # Quectel L76K hardware design: 29 mA acquisition and tracking, on the Heltec's
             # switched GNSS 3V3 (VGNSS_Ctrl: GPIO34 on R2, GPIO42 on R8). 41 mA with an active antenna (Seeed's L76K).
NFC_POLL = 20.0  # design doc: PN532 RF bursts ~50 ms on / 300 ms, average. Datasheet is ~91 mA
                 # field-on and ~20-30 mA idle, so one of the two is under-counted.
NFC_IDLE = 3.0  # EST: module power LED + PN532 PowerDown command (45 uA). A chip left running
                # idles ~20 mA, which makes the parked figure ~19 days instead of ~47.
LCD_ON_5V = 32.0  # Newhaven NHD-0420D3Z-FL-GBW-V3, LCD + backlight at level 8: 21/32/44 mA
                  # min/typ/max (datasheet). Its PIC PWMs the backlight (0xFE 0x53, levels 1-8).
LCD_IDLE_5V = 5.0  # EST: PIC16F690 + ST7066U with the backlight at level 1 (off). Measure it
                   # (fab/OFFBOARD_PARTS.md item 5).
BACKLIGHT_DUTY = 0.05  # EST: firmware lights it for a button, card or game event, then times out.
                       # Transflective panel, so it reads in daylight with the backlight off.
LED_RING_5V = 15.0  # one ONPOW 6 V ring run at 5 V; design.py's figure, ONPOW publishes none.
                    # Two rings are fitted (LR + LB), so scenario() counts this twice (once with opt).
BUZZER_5V = 8.0  # BZ-38: TME's spec page, piezo with generator, 3-28 V, 8 mA
GATE_PD = 3.0 / 11e3 * 1e3  # 10k gate pull-down + 1k: 0.27 mA per driver that is on
AMP_ON = 4.0 if TME else 13.0  # PAM8302A quiescent no-load vs NS4168 quiescent with CTRL high;
                               # firmware holds the amp SD low between clips (1 uA off)
AMP_PLAYING = 0.4 / VBAT * 1e3  # EST: ~0.4 W average electrical while a clip plays
DAC_STANDBY = 0.5 if TME else 0.0  # PCM5100A standby with clocks stopped (clocks low > 1 s)
BOOST_IDLE = 1.0  # EST: MT3608/MCP1640 switching at near-zero load
# Pack board with the key off (the carrier is unpowered; only the pack's own electronics drain the
# cells). EST from the P0 datasheets: STM32C071 Stop with RTC/LSI is 85 uA typical, so the design
# doc's "tens of uA" target is unreachable; PAC1934 SLEEP 5 uA (DS20005850E; its PWRDN state is
# 0.1 uA but loses the configuration and accumulators), BQ25601 battery-only
# ~4.5 uA, XC6206 Iq ~1 uA, plus the 4 x 1M gate resistors (4.2 V / 1M = 4.2 uA each) while the
# switches are on. Cell self-discharge (~1-3 %/month) dominates this after about a year.
# TME: the L072's Stop IDD is 0.43 uA typ (DS10690 Table 37) and each INA228 2.8 uA in shutdown.
MCU_STOP_MA = 0.00043 if TME else 0.085
MON_IQ_MA = 4 * 0.0028 if TME else 0.005
PACK_IQ_MA = MCU_STOP_MA + MON_IQ_MA + 0.0045 + 0.001 + 4 * 0.0042
# Cell branch series resistance (5 A fuse + 20 mOhm shunt + back-to-back AO3401A + track) ~150 mOhm
# EST. Deliberately not modelled: it drops < 0.3 V at these currents, well inside the 0.84 USABLE
# derate that already covers the 3.5 V shutdown.
BRANCH_MOHM = 150

READY_BUZZ_DUTY = 3 * 0.2 / 15  # game.rs READY_BEEP: 3 x 200 ms every 15 s


def lora_avg(period_s, payload=40, sf=9):
    """Average extra current of one STATUS packet every period_s (TX replaces RX while sending)."""
    t = lora_airtime_s(payload, sf)
    return (HELTEC_TX_27DBM - HELTEC_RX) * t / period_s, t / period_s


def scenario(deluxe, game, backlight, status_s=30, clip_duty=0.05, opt=False):
    """backlight: share of time the LCD backlight is on (0..1). opt: optimized firmware targets."""
    ma = {"Heltec awake, LoRa RX": HELTEC_RX_OPT if opt else HELTEC_RX}
    ma["LoRa STATUS TX"], _ = lora_avg(status_s)
    if deluxe:
        ma["GNSS"] = GNSS_OPT if opt else GNSS
        ma["PN532"] = (NFC_POLL_OPT if opt else NFC_POLL) if game else NFC_IDLE
        ma["Amp (on only for clips)"] = (AMP_ON + AMP_PLAYING) * clip_duty if game else 0.0
        if TME:
            ma["DAC standby"] = DAC_STANDBY
    five = LCD_IDLE_5V + (LCD_ON_5V - LCD_IDLE_5V) * backlight
    if game:
        five += (1 if opt else 2) * LED_RING_5V + BUZZER_5V * READY_BUZZ_DUTY  # opt: one ring lit
        ma["Gate pull-downs"] = GATE_PD
    ma["5 V rail via boost"] = from_5v(five) + BOOST_IDLE
    return ma


# Key left on, firmware asleep: what still draws from the cells
PARKED = {"Heltec deep sleep": HELTEC_SLEEP, "PN532 module idle": NFC_IDLE,
          "LCD idle via boost": from_5v(LCD_IDLE_5V) + BOOST_IDLE}
if TME:
    PARKED["DAC standby"] = DAC_STANDBY
GAME_H, DAYS = 10, 2  # a weekend: two 10 h game days and the night between them parked
NIGHT_H = 12
AGED = 0.8  # cells at 80 % of rated capacity (end of the 35E's rated cycle life)


def weekend_ma():
    """Highest mean game-time current that lasts the weekend at 0 C (-20 %) on aged cells."""
    night = sum(PARKED.values()) * NIGHT_H * (DAYS - 1)
    return (CELLS_MAH * USABLE * 0.8 * AGED - night) / (DAYS * GAME_H)


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
    print(f"model: {'TME hand-build (L072 + INA228 + PCM5100A/PAM8302A)' if TME else 'JLC (C071 + PAC1934 + NS4168)'}")
    print(f"STATUS 40 B at SF9/125 kHz: {t * 1000:.0f} ms on air, {100 * duty:.1f} % duty at 30 s "
          f"(sub-band limit 10 %)")
    show("Deluxe, game running, backlight on", scenario(True, True, 1.0))
    show("Deluxe, game running, backlight off", scenario(True, True, 0.0))
    show("Budget, game running, backlight on", scenario(False, True, 1.0))
    show("Deluxe, key on, waiting for HQ (no game, backlight off)", scenario(True, False, 0.0, status_s=60))
    show("Deluxe, game, optimized firmware, backlight on a timeout",
         scenario(True, True, BACKLIGHT_DUTY, opt=True))
    show("WiFi setup (AP on, backlight on)", {"Heltec WiFi AP": HELTEC_WIFI_AP,
                                             "5 V rail": from_5v(LCD_ON_5V) + BOOST_IDLE})
    total = sum(PARKED.values())
    days = CELLS_MAH / total / 24  # full pack down to the pack MCU's undervoltage disconnect
    print(f"\nKey left on, firmware asleep: {total:.1f} mA -> about {days:.0f} days until the pack "
          "MCU disconnects the cells")
    print("  (cut this with the key; firmware cannot switch off the boost or the PN532 module)")
    print("  Optimistic on purpose: this needs the radio off (a live V4 node sits at a 12 mA floor)")
    print("  and the PN532 in PowerDown. Miss either and it is days, not weeks.")
    # Key off: the carrier is unpowered, so this is the pack's own drain (storage life, not runtime)
    years = CELLS_MAH * USABLE / PACK_IQ_MA / 24 / 365
    print(f"\nPack quiescent, key off (carrier unpowered): {PACK_IQ_MA * 1000:.0f} uA -> "
          f"{years:.0f} years of pack electronics ({BRANCH_MOHM} mOhm branch drop not modelled)")
    print("  Cell self-discharge (~1-3 %/month) is the larger term over a season.")
    budget = weekend_ma()
    print(f"\nWeekend ({DAYS} x {GAME_H} h game + {NIGHT_H} h parked, 0 C, cells at {AGED:.0%}): "
          f"game current must stay under {budget:.0f} mA")
    for name, backlight, opt in (("today's firmware, backlight on", 1.0, False),
                                 ("today's firmware, backlight on a timeout", BACKLIGHT_DUTY, False),
                                 ("optimized firmware, backlight on a timeout", BACKLIGHT_DUTY, True)):
        total = sum(scenario(True, True, backlight, opt=opt).values())
        print(f"  {name:44} {total:4.0f} mA  {'PASS' if total < budget else 'FAIL'}"
              f"  ({100 * (budget / total - 1):+.0f} % margin)")


if __name__ == "__main__":
    # Self-check against Semtech's calculator and the published airtime table (125 kHz, CR 4/5,
    # 8-symbol preamble): 56.6 ms at SF7/20 B, 144 ms at SF9/10 B, 991 ms at SF12/10 B.
    assert abs(lora_airtime_s(20, 7) - 0.05658) < 1e-4, lora_airtime_s(20, 7)
    assert abs(lora_airtime_s(10, 9) - 0.144) < 2e-3, lora_airtime_s(10, 9)
    assert abs(lora_airtime_s(10, 12) - 0.991) < 2e-3, lora_airtime_s(10, 12)
    assert hours(100) > hours(200)
    assert hours(100, 0.8) < hours(100)  # the cold derate must not raise the runtime
    assert from_5v(60) > 60  # a 5 V load always costs more than its own current from the pack
    # Weekend budget: 2 x 10 h games + 1 night parked, 0 C, cells aged to 80 %. ~350 mA.
    assert 300 < weekend_ma() < 400, weekend_ma()
    # The optimized firmware (design doc table 2) must pass with 30 % margin, backlight duty included.
    assert sum(scenario(True, True, BACKLIGHT_DUTY, opt=True).values()) * 1.3 < weekend_ma()
    # A backlight left on must cost more than one on a timeout.
    assert sum(scenario(True, True, 1.0).values()) > sum(scenario(True, True, BACKLIGHT_DUTY).values())
    main()
