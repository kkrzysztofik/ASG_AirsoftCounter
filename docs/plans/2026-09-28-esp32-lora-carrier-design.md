# AirsoftCounter v2: Heltec V4 + LoRa carrier board and Rust firmware

Date: 2026-09-28
Status: design approved, implementation not started

## Goal

Replace the hand-wired Arduino Nano build (soldered point-to-point, hot glue,
per-unit LCD address tweaks, not waterproof) with:

- a KiCad carrier PCB for a **Heltec WiFi LoRa 32 V4 (no-display build, R2 or R8)**,
- LoRa **remote control from HQ** (start/stop/configure + status reports),
- **GPS** position in status reports,
- phone configuration over **WiFi AP + web page** (IR remote dropped),
- a **20x4 I2C LCD**,
- **RFID/NFC cards**: player cards (score + per-player stats) and admin cards,
- a **loudspeaker** (I2S class-D amp) in addition to the buzzer, with GPIOs freed by an **I2C GPIO expander** (Part 6),
- a **weatherproof enclosure** (Kradex ZP240.190.105SJp, clear PC lid, IP67),
- firmware rewritten in **Rust** (esp-hal + Embassy).

Existing Nano units are left as they are; no Nano carrier is planned.

## Part 1: MCU board, pins, power

### Heltec V4 facts (verified from Heltec pin maps and Meshtastic variants)

- J2 and J3 are 1x18 2.54 mm headers, identical physical layout on V3/V4.
  V4 adds a separate 4-pin strip (GPIO15-18) at the antenna end: not used.
- Native USB (no USB-UART chip). 5V pin is powered **only from USB** (max 500 mA).
- Battery: SH1.25 2-pin socket, onboard charger. VBAT sense on GPIO1 via
  100k/390k divider (R2 needs ADC_Ctrl GPIO37 HIGH; R8 has no ADC_Ctrl).
- Internally used GPIOs:
  - 2, 5, 7: LoRa front end (KCT8103L CSD, CTX, LDO power) on V4.3
  - 8-14: SX1262 (NSS, SCK, MOSI, MISO, RST, BUSY, DIO1)
  - 38-42: GNSS connector (TX 38, RX 39, PPS 41; EN 34/RST 42/STANDBY 40 on R2, EN 42 on R8)
  - 33-37: octal PSRAM on R8
  - 35/36 (R2) or 46/40 (R8): LED / Vext
  - 0, 45, 46: strapping; 19/20: USB; 26: PSRAM CS
- All EU868 V4s are the 28 dBm high-power version.

### GPIO assignment (valid on both no-display V4-R2 and V4-R8)

| Signal | GPIO | Header pin |
|---|---|---|
| I2C SDA (LCD) | 4 | J3-15 |
| I2C SCL (LCD) | 3 | J3-14 |
| Red button in | 6 | J3-17 |
| Blue button in | 44 | J2-5 (U0RXD; firmware must not use UART0) |
| Red LED out | 47 | J2-13 |
| Blue LED out | 48 | J2-14 |
| Buzzer out | 21 | J2-16 |
| Battery sense | 1 | onboard |
| GPS | 38/39/41/42 (+40 R2) | Heltec GNSS connector, no carrier involvement |

Spare: GPIO43 and the top 4-pin strip. Left unconnected.

### Power path

```
1S Li-ion (2x18650 parallel) ─J_BAT─ PTC 1A ─ key switch (J_KEY) ─ VBAT_SW ─┬─ J_HBAT ─> Heltec SH1.25 battery socket
                                                                            ├─ 220 µF bulk
                                                                            └─ MT3608 boost ─> 5V_AUX (LCD, button LEDs, buzzer)
Heltec 5V pin: NOT connected (it is the charger input; feeding it would loop).
```

- MT3608 with fixed feedback resistors (no trimmer modules: they can ship set to 20V+).
- Charging only happens with the key ON (known, accepted trade-off).
- With key OFF and USB plugged in, the Heltec charger output (no battery) feeds
  VBAT_SW, so the boost and 5V loads run from it. Chargers may cycle without a
  battery: LCD flicker on the bench is expected and harmless.
- Budget: ~150-250 mA from battery; 6000 mAh ≈ 24+ h.
- Parallel cells must be matched and equalised before connecting.

## Part 2: I/O circuits and connectors

- **Output drivers (x3: LED R, LED B, buzzer):** AO3400A low-side, 100 Ω gate
  series, 100k gate pull-down (keeps loads off during boot). R_LOAD footprint in
  series with load: 150 Ω (red), 100 Ω (blue), 0 Ω for buzzer or 5V-LED buttons. *(As built: 0 Ω for both, because the chosen ONPOW LAS1-AGQ 6 V buttons have built-in LED resistors; see hardware/fab/OFFBOARD_PARTS.md.)*
  1N4148W flyback across buzzer.
- **Button inputs (x2):** 10k pull-up to 3V3, 100 nF to GND, 1k series to GPIO.
- **I2C level shift:** 2x BSS138, 4.7k pull-ups on 3V3 side; 5V-side pull-ups
  footprinted, DNP (backpack already has them).
- **Connectors:** JST-XH 2.50 mm vertical, silkscreen-labelled with pin names.

| Ref | Pins | To |
|---|---|---|
| J_BAT | 2 | battery holder |
| J_KEY | 2 | key switch |
| J_HBAT | 2 | Heltec battery socket (SH1.25 to XH pigtail) |
| J_LCD | 4 | GND, 5V, SDA, SCL |
| J_BTN_R, J_BTN_B | 4 | SW, GND, LED+, LED- |
| J_BUZ | 2 | buzzer |
| J_NFC | 4 | GND, 3V3, SDA, SCL (3V3 side of the I2C bus, 100 µF nearby) |

Heltec USB-C, LoRa u.FL and GNSS cable go straight from the Heltec to panel parts.
Heltec sits in 2x 1x18 female headers. Parts: 0805, SOT-23, SOT-23-6, THT connectors.

## Part 3: PCB and enclosure

- 2-layer, 1.6 mm, solid ground pour on bottom. 90 x 60 mm (holes must clear the Heltec), 4x M3 holes 3.5 mm from corners.
- Heltec along one long edge, USB-C at board edge; antenna end overhangs the
  outline (no copper under the antennas). Connectors along the opposite edge,
  same orientation. Power section grouped in one corner, away from u.FL.
- **Header row spacing: 22.86 mm** (measured from Heltec STEP: 2x18 holes, 2.54 pitch); still verify
  with a 1:1 paper print against a real board.
- Enclosure: **Kradex ZP240.190.105SJp** (240 x 191 x 106 mm, clear PC lid, IP67,
  brass inserts) + **ZP240.190-PCB** mounting plate.
  - Lid: 20x4 LCD behind clear lid (no window), 2x IP67 anti-vandal 5V-LED pushbuttons.
  - Walls: IP65 key switch, IP67 capped USB-C panel extension, SMA bulkhead with O-ring (high on a wall).
  - Floor plate: carrier on M3 standoffs, 2x18650 holder, cable ties.
  - L76K GNSS module on a standoff near the lid, away from the LCD frame and battery.

## Part 4: Rust firmware

### Stack

esp-hal 1.2 + Embassy (embassy-executor 0.10, esp-rtos 0.4), no_std.
Toolchain: `espup` (Xtensa Rust), `espflash`, `esp-generate`.

| Concern | Crate | Notes |
|---|---|---|
| HAL | esp-hal | |
| Radio | lora-phy 3.0 (SX1262) | TCXO 1.8V via DIO3, DIO2 as RF switch; FEM pins 7/2/5 driven manually |
| LCD | hd44780-driver 0.4 | verify embedded-hal 1.0 support first; fallback: own PCF8574 driver. Probe 0x27/0x3F |
| GPS | nmea 0.8 | UART1 on 38/39 |
| Config | sequential-storage + esp-storage | defaults when key missing |
| Phone config | esp-radio (WiFi AP) + embassy-net + picoserve | esp-radio is beta: implemented last |
| Auth | ccm + aes | AES-CCM, pre-shared key, per-sender sequence counter (replay protection) |
| NFC | pn532 0.5 | verify embedded-hal 1.0 support first; fallback: own minimal driver (InListPassiveTarget + page read) |

### Layout

```
firmware/
├── core/    no_std, host-testable: game state machine, protocol encode/decode, auth, config types
└── device/  esp32s3 binary: tasks, drivers, pin map; features v4-r2 / v4-r8
```

### Radio protocol (raw LoRa, star)

- Packet: `[net_id, dev_id, seq, type, payload, tag]`, AES-CCM authenticated.
- HQ → device: START, STOP, CONFIG, PING. Device → HQ: STATUS (state, score, battery, GPS), ACK.
- Commands are ACKed and retried.
- Channel 869.525 MHz (g3 sub-band, 10% duty, ≤500 mW ERP). TX power set
  explicitly in code; never rely on driver defaults (hardware can do 28 dBm).

### Milestones

0. Toolchain + blinky on V4
1. LCD + buttons + outputs: port Airsoftcoin mode, no radio
2. Config storage + battery reading
3. RFID: player captures, admin menu, first-admin enrollment
4. LoRa PING/STATUS between two V4s, then authenticated commands and capture events
5. GPS in STATUS
6. WiFi AP config page (incl. admin card list/remove)
7. HQ firmware: USB-serial ↔ LoRa bridge on a bare V4

Out of scope for now: laptop HQ app, OTA updates, additional game modes.

## Part 5: RFID cards

### Hardware

- PN532 module ("NFC V3" red board) in I2C mode (DIP switches), address 0x24,
  on the **3V3 side** of the I2C bus, powered from Heltec 3V3 (500 mA budget).
- No IRQ/RST wires: firmware polls over I2C (GPIO43 is U0TXD and toggles at boot).
- Mounted under the clear lid with a "tap here" mark, ≥2 cm from the LCD metal
  frame. Expected range ~3-5 cm through 3 mm PC.

### Cards

- **Player card:** NTAG213/215 with NDEF text record `ASG1:<team>:<id>`,
  team `R` or `B`, id 1-999. Written with any phone NFC app.
- **Admin card:** identified by UID, allowlist in device config.
- Unknown card: error beep.

### Behaviour

- Ready state: player card tap = capture for the card's team with player id.
  Buttons still capture anonymously (player id 0).
- Admin card tap (any state) opens admin menu on LCD, navigated with the two
  buttons: Reset game / WiFi setup / Status (battery, radio, GPS).
- First admin: when no admin is enrolled, holding both buttons while tapping a
  card enrolls it.
- Each capture `(team, player_id, time)` is queued and sent to HQ as an ACKed
  event. HQ owns per-player stats.
- RF field polled in bursts (~50 ms on / 300 ms), only in states where a card
  does something (~20 mA average).
- Card text parsing (NTAG pages → TLV → NDEF text → `PlayerCard`) lives in `core`.

## Part 6: Audio, GPIO expander, fewer Extended parts (approved 2026-09-29)

### Why
The user asked for a real loudspeaker in addition to the buzzer, and for Basic JLCPCB
parts wherever possible. I2S needs 3 fast GPIOs and none are free on both V4 variants,
so every slow signal moves to an I2C GPIO expander.

### Native GPIO map (supersedes Part 1 for these pins)

| GPIO | Signal |
|---|---|
| 3 / 4 | I2C SCL / SDA (LCD via the level shifter, PN532, expander) |
| 47 | I2S BCLK |
| 48 | I2S LRCLK |
| 21 | I2S DIN |
| 6 | Expander INT (active low, open-drain, pull-up on the carrier) |
| 44, 43 | Spare, not connected on this revision |

### Expander (8 I/O, 3V3 side of the I2C bus)
- Inputs: BTN_R, BTN_B. The 10k pull-up, 100 nF and 1k series RC stay.
- Outputs: LED_R, LED_B and BUZ gate drives (same AO3400A low-side drivers with
  100 Ω + 100k), plus AMP_SD (through a 1k resistor), which drives the amplifier's shutdown pin so it stays
  off during boot and while silent.
- Two spare I/O.
- Its I2C address must not collide with the PN532 (0x24) or the LCD backpack (0x27/0x3F).

### Speaker path
- MAX98357A-class I2S class-D amplifier, **powered from VBAT_SW (3.0–4.2 V)**, not the
  5 V boost. That gives about 1 W into 8 Ω, or 1.5–2 W into 4 Ω if a 4 Ω speaker is
  used, and keeps audio peaks off the 5 V rail
  (no LCD flicker). GAIN_SLOT is tied to GND (12 dB); volume is set digitally in firmware.
- The output is BTL: the new 2-pin XH connector `J_SPK` must never be tied to GND
  (silkscreen note).
- Off-board: Visaton K 50 (2901; the WP variant is out of stock) (8 Ω, 2 W, IP65) in the enclosure wall behind a grille
  with a front gasket (see `hardware/fab/OFFBOARD_PARTS.md`). About 1 W into 8 Ω from
  VBAT. `ORDERING.md` must list this same 8 Ω part.

### Power changes
- Polyfuse raised to 2 A hold (1206L200/16NR, C22374899), for LoRa TX + audio peaks + boost.
- Bulk capacitance moves from THT electrolytics to Basic 1206 ceramics: 2x 47 µF 10 V
  (C96123) on VBAT_SW and 100 µF 6.3 V (C15008) on +3V3.
- The boost (MT3608), inductor and fuse have no Basic/Preferred equivalent at JLCPCB
  (the whole libraries were searched). The MT3608 stays, because 5 V loads remain
  about 200 mA.

### Firmware impact
- An expander driver handles buttons (via INT), LEDs, the buzzer and AMP_SD. P6/P7
  must be set as outputs driven low (the TCA9534 has no internal pull-ups).
- An audio task streams clips over I2S DMA from flash (beeps, siren, spoken lines).
- `core` gets a `Sound` event next to `Beep`.

## Part 7: Build variants (Deluxe / Budget) (approved 2026-09-30)

### Why
The Deluxe unit costs ~700 zł in parts (see `hardware/fab/COSTS.md`). A cheaper tier
should share the board, pin map and firmware `core`, not fork them.

### Model
One PCB, one pin map. A variant is a set of modules; a module is a set of board parts
left unpopulated when absent (`MODULES`/`VARIANTS` in `hardware/design.py`).
`jlc.py` writes a BOM/CPL per variant (`fab/jlc_bom.csv` = deluxe, `fab/jlc_bom_budget.csv`).

| Module | On-board parts | Off-board |
|---|---|---|
| buttons | 2 AO3400A LED drivers, RC input filters, `J_BTN_R/B` | 2 IP67 buttons |
| rfid | `J_NFC1` | PN532, cards |
| speaker | `U3` MAX98357A, caps, `R_SD1`, `J_SPK1` | VISATON K 50 |
| GPS, enclosure, key/toggle | none | L76K, box, switch |

Core (always): Heltec V4, power path, expander `U2`, buzzer path, LCD. The expander stays in
every variant because the LEDs, buzzer and buttons sit behind it.

- **Deluxe:** buttons + rfid + speaker + GPS, Kradex IP67, key switch.
- **Budget:** buttons only, Pawbol S-BOX 416-P IP65 box (190 x 140 x 70 mm inside), generic 16 mm buttons, no GPS, KS22 key (or a toggle). Same board.
- Any mix is valid if it has **buttons or RFID** (`design.check()` enforces it).

### Firmware
- I2C probe at boot: PN532 at 0x24, the expander at 0x20, the LCD at 0x27/0x3F. A missing module
  disables its task instead of failing.
- `cargo` features only for what cannot be probed: speaker fitted, buttons fitted, GPS fitted.
- No buttons: set expander P0/P1 as outputs (no pull-ups fitted, floating inputs would toggle INT).
- No speaker: the I2S nets (GPIO 47/48/21) and `AMP_SD` (expander P5, `U2.10`) have nothing fitted on the board.
  Firmware must leave GPIO 47/48/21 as inputs or unused (never drive them) and must not start the audio task.
- STATUS omits position without GPS. The buzzer is present in every variant.

### Open
Red 6 V ONPOW button availability, key-switch choice (maintained vs momentary), buzzer code,
budget generic-part prices: tracked in `hardware/fab/COSTS.md`.

## Open items to verify during implementation

- Heltec V4 header fit (paper print; 22.86 mm row spacing measured on V3 STEP).
- Heltec charger current (check V4.3 schematic PROG resistor); ok for 6000 mAh?
- hd44780-driver and pn532 embedded-hal 1.0 compatibility.
- PN532 read range through the actual lid.
- ZP240.190.105 internal dimensions and plate hole pattern (Kradex drawing).
- Button choice: IP67 anti-vandal buttons with 5V LED (R_LOAD values depend on it).
- Measure idle current; MT3608 efficiency at light load.
