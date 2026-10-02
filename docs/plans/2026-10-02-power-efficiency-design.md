# AirsoftCounter power efficiency: a weekend on the 18650 pack

Date: 2026-10-02
Status: docs and model done (E1-E3); firmware C2-C8 and validation wait for the hardware. No board changes.

## Goal

One charge of the 18650 pack (4x Samsung 35E, variant A or B) lasts a **weekend**: 2 game days of
10 h plus a 12 h night with the key left on, at 0 °C, on cells aged to 80 % capacity. A player's
LiPo (LiPo board) is a one-day battery and is swapped like a gun battery; it is out of scope.

## Where the energy goes (`hardware/power_budget.py`, Deluxe, game running)

| Load | mA (battery side) |
|---|---|
| 5 V rail via MT3608 (100 mA backlight planning value) | 209 |
| Heltec awake, LoRa RX (240 MHz, no light sleep) | 75 |
| GNSS | 29 |
| PN532 polling | 20 |
| LoRa TX + amp | 13 |
| **Total** | **346** |

Weekend budget: 13400 mAh x 0.84 usable x 0.8 (0 °C) x 0.8 (aged), minus 12 h parked at ~7 mA,
over 20 h of game = **~350 mA**. Today's estimate passes with no margin, and the backlight figure
is still a guess.

Modelled after the display change (E1, `power_budget.py` weekend block, budget 353 mA): today's
firmware with the backlight always on 236 mA (+50 % margin), backlight on a timeout 196 mA (+80 %),
optimized firmware 74 mA (+377 %). The Newhaven alone meets the goal; the firmware work is margin.

## Decisions

### 1. Display: Newhaven NHD-0420D3Z-FL-GBW-V3 replaces the blue 2004A + HW-61

One display for the Deluxe and Budget builds.

- Transflective STN(+), yellow-green: readable in daylight with the **backlight off**. The blue
  2004A is a negative panel and unreadable without its backlight.
- Backlight brightness 1-8 over I2C (`0xFE 0x53 n`, 1 = off, 100 us); the module PWMs it.
- 5 V, 21-44 mA total with the backlight on (datasheet), -20..+70 °C.
- I2C address 0x28 (7-bit), no clash (TCA9534 0x20/0x21, PN532 0x24, PAC1934 0x10, pack MCU
  0x30, ADS1115 0x48). **I2C max 50 kHz**: the shared bus runs at 50 kHz.
- 10k pull-ups on the module, so `R_SDA5/R_SCL5` stay DNP. Same 4 wires to `J_LCD1`
  (GND 5V SDA SCL): **no carrier change**.
- Ships in RS-232 mode: **bridge jumper R1** for I2C. 100 ms power-up delay before the first
  command. Its own command set (not HD44780), so C3 writes one small driver and the PCF8574 path
  is not needed.
- About $17 (Mouser 763-0420D3ZFLGBW-V3, Newhaven direct); TME has none.

Rejected: generic yellow-green 2004A + PCF8574 (on/off only, transmissive, backlight current
undocumented); SparkFun SerLCD RGB (3.3 V logic, not transflective); PWM from an ESP32 GPIO (only
GPIO43/44 are free and they are UART0); PWM by toggling PCF8574 P3 (keeps the CPU awake).

### 2. Firmware power requirements (added to the C-tasks, implemented with the hardware)

| Task | Requirement | Target |
|---|---|---|
| C2 | I2C at 50 kHz (Newhaven limit) | - |
| C3 | Backlight off after a timeout; on (level from config) for a button, card or game event | backlight ~5 % duty |
| C1/C4 | CPU 80 MHz + automatic light sleep | Heltec 75 -> ~20 mA |
| C4 | Light only the ring that carries information | rings 2x -> 1x |
| C6 | PN532 PowerDown between polls; poll only when a card is expected | 20 -> ~5 mA |
| GNSS | One fix at boot, then VGNSS off | 29 -> ~1 mA |
| LoRa | SX1262 RX duty cycle; HQ sends a preamble longer than the sleep window | protocol note |

`R_LLR1/R_LLB1` (0R today) stay the ring brightness knob if the rings are too bright.

### 3. Power model (`power_budget.py`)

- Backlight duty parameter (default 5 %) and the Newhaven current.
- An "optimized firmware" scenario with the targets above.
- A weekend check that prints PASS/FAIL against the budget for today's and the optimized
  firmware, and asserts in the self-check that the optimized one passes.

### 4. Validation (once the hardware exists)

- Instrument: pack variant A's PAC1934 energy accumulators (per-cell Wh); USB meter on `J_PWR1`
  as a cross-check.
- Run each `power_budget.py` scenario for 30 min, replace every EST figure with the measured one,
  re-run the weekend check.
- Pass: measured Deluxe game current fits the weekend budget (~350 mA) with at least 30 % margin.
- Soak: full charge, game-loop firmware until the pack MCU cuts off; compare with the model.

## Not doing (add if the measurements miss)

- +5V load switch: parked drain is ~90 mAh per night, under 1 % of the pack.
- Hardware backlight PWM, LiPo-board changes, lower LoRa TX power.
