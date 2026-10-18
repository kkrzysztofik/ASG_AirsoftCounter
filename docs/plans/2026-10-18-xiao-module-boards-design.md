# XIAO ESP32-S3 module boards: pack and LiPo (design)

Date: 2026-10-18. Status: final (v4; module facts verified, implementation plan
`2026-10-18-xiao-module-boards-implementation.md`).
Successors of: the TME hand-build variants (`2026-10-02-tme-hand-build-design.md`), which stay.

v3: the v2 single feeds (diode-OR'd 5V pad on pack, buck `+5V` on lipo) deadlocked the pack on
battery and broke the lipo's latched cutoff. Pack pin budget recounted (13 signals), CHG_CE/
MON_ALERT dropped, gate pull-downs stiffened, hardware I2C, J_UART1 dropped.
v4 (checked against Seeed's XIAO KiCad source and the ESP32-S3 datasheet v2.2): the module's
regulator is a buck that tolerates a held-up 3V3 pad, but the board LDOs cannot run the module
(pack XC6206 drops out at low cells, lipo AP7381 would dissipate ~0.7 W at 3S) — so **two feeds**:
a keep-alive into the 3V3 pad and a run feed into the 5V pad. Reset pulls verified; bottom pads fixed.

## Goal

Replace the STM32L072KZT6 of the two hand-build boards (`pack_tme`, `lipo_tme`) with a
**Seeed Studio XIAO ESP32-S3** module, so a beginner with an iron and hot air can build both
boards with no fine-pitch hand soldering of the MCU and no ST-Link. New derived board modules;
nothing about the JLC boards or the carrier changes.

## Why

- The L072 is the most expensive line of both hand-build BOMs, TME sells it high in its price
  schema (no exact price shown), and street quotes for the low-production `Z` (192 KB) part run
  ~$5.8 single-quantity.
- LQFP-32 gull-wing is the hardest solder joint of both boards; a castellated 2.54 mm module is
  the easiest SMD-class joint there is, and the module survives a dead board.
- No firmware written yet, so zero code cost to change family; the carrier's Heltec V4 is an
  ESP32-S3 — all three brains become one silicon family, one toolchain, one flash story: plug in
  USB, `esptool`.
- Chosen module: **XIAO ESP32-S3** (base, not Sense: no use for its mic/IMU/camera, and Sense
  deep-sleeps at 3 mA vs 14 µA; not the C3 sibling: the carrier is S3; not RP2040: no family fit,
  one I2C). Botland SKU/price into `OFFBOARD_PARTS.md` before ordering; buy 2 + 1 spare.

## Structure

- New `pack_xiao.py` / `lipo_xiao.py` importing their `_tme` parent and editing PARTS/NETS/
  placement, the repo's standard derivation. `board.py`/Makefile learn `BOARD=pack_xiao|lipo_xiao`.
  **The hand-build flow keys off the `_tme` name suffix — `Makefile:59` (`filter %_tme`) and
  `tme.py:104` (`endswith("_tme")`) must accept `*_xiao` too** (`tme_all.py` takes names as args).
- The XIAO is a bought off-board module (like the cell holders and the Heltec): not in the TME
  BOM, listed in `OFFBOARD_PARTS.md`. The boards carry only its footprint.
- New `local:XIAO_S3` footprint from Seeed's published PCB; symbol with the 14 edge pads plus the
  bottom pads as optional pins.

## Module facts (verified 2026-10-18)

Sources: Seeed wiki `xiao_esp32s3_getting_started`; Seeed schematic + KiCad project
`202003751_XIAO ESP32S3_v1.4_SCH*_260226` (both are titled "XIAO ESP32-S3-Sense": Seeed draws
one core board for both; the Sense only adds the camera B2B connector J3 — same SGM6029,
LMBR4010, LP0404 P-FET, SGM40567, 499 Ω on D6, TP1-8); Espressif ESP32-S3 datasheet v2.2 tables
2-1 (pin settings) and 2-2 (power-up glitches); Seeed `OPL_Kicad_Library`, folder "Seeed Studio
XIAO Series Library": symbol `XIAO-ESP32-S3-SMD` (all pins passive) + footprint
`XIAO-ESP32-S3-SMD.kicad_mod` (the pair the boards use).

Symbol/footprint pin numbers: 1-11 = D0..D10, 12 = 3V3_OUT, 13 = GND, 14 = VBUS (5V pad);
bottom grid 15 = MTDI (GPIO41), 16 = MTDO (GPIO40), 17 = EN, 18 = GND, 19 = MTMS (GPIO42),
20 = MTCK (GPIO39), 21/22 = USB D-/D+; 23 = VBAT (BAT+), 24 = GND (BAT-), 25 = centre PAD.

- Edge pads D0..D10 = GPIO1,2,3,4,5,6,43,44,7,8,9; D6 has a 499 Ω series resistor on the module.
  GPIO1-9 are ADC1 (no Wi-Fi conflict).
- Bottom pads: GPIO39 (MTCK), GPIO40 (MTDO), GPIO41 (MTDI), GPIO42 (MTMS), EN (CHIP_PU, 10k/RC
  on the module), BAT+/GND. **No BOOT pad** — GPIO0 is only on the module's button.
- GPIO21 = user LED, GPIO19/20 = native USB.
- Power tree: USB VBUS = 5V pad → Schottky (LMBR4010) → `VIN` → **SGM6029 synchronous buck**
  (EN tied to VIN) → `VCC_3V3` = 3V3 pad. BAT+ → P-FET (gate on VBUS) → `VIN`; SGM40567 charger
  VBUS → BAT. Seeed: the 5V pad accepts external 5 V through a series diode.
- **3V3 pad back-drive (the load-bearing fact):** holding the 3V3 pad at 3.3 V with nothing on the
  5V pad back-feeds `VIN` through the buck's high-side body diode; the buck then enables and
  passes through (VIN < VOUT). The module's Schottky blocks this from the 5V pad; the P-FET puts
  ~3.3 V on BAT+ — **so BAT+ must stay unconnected**. Cost: µA leakage (Schottky reverse, charger
  BAT pin), measured at the spike. With 5 V present, the SGM6029 regulates 3.3 V itself; it and
  the board's LDO are both source-only, so whichever sits higher supplies — no fight.
- Reset pulls (datasheet table 2-1): GPIO1-9 — none (input only); GPIO40-42 — none; GPIO39 —
  weak pull-up after reset unless `EFUSE_DIS_PAD_JTAG`; **GPIO43/44 (D6/D7) — WPU at and after
  reset**, RPU 45 kΩ typ. GPIO1-9 show a 60 µs *low* glitch at power-up (harmless: low = off for
  every driver here).
- Deep sleep 14 µA (Seeed, at 3.8 V into BAT, including the buck and Schottky leakage).

## Module fit (consequences)

- Two hardware I2C controllers via the GPIO matrix, any pads: I2C0 = slave 0x30 to the carrier,
  I2C1 = master on the internal bus (4× INA226 + BQ25601, polled, ≤100 kHz). No bit-banging.
- **D6 = U0TXD:** the boot ROM drives it high and prints on it at every reset. No gate or load
  driver there. It may carry `SCL_INT`: with `SDA_INT` idling high, clock-only chatter forms no
  START. Firmware console on USB CDC (UART0 console off in sdkconfig).
- **D7 = U0RXD has a 45k pull-up:** against the inherited 100k gate pull-down that is ~2.3 V on a
  BSS138 gate — the cell switch would close at every boot. **pack_xiao `R_PD1..4` = 4.7k** (0.3 V
  against the pull-up, 2.7 V when driven through the 1k `R_SW`, 0.7 mA per driven gate); all four
  the same value for one BOM line. lipo `R_GK` stays 100k (its pad, GPIO7, has no pull).
- Deep sleep: `KILL_DRV` (lipo) is held with `gpio_hold`; pack gates are default-off by pull-down.

## Power domains (the load-bearing section)

Facts from the repo (`pack_tme.py` / `lipo_tme.py` NETS, part data):
- pack: the cells reach `SYS` only through the default-off cell switches (`Q_B` → `VPACK` →
  charger → `SYS` → key → `VBAT_SW` → MCP1640 `+5V`). The only rail live from the raw cells is
  `+3V3` = XC6206P332MR (200 mA, ~250 mV dropout at 100 mA) on `VMCU_IN` (Schottky diode-OR of the
  four cells and `SYS`). A module fed only from `+5V` could never boot on battery to close the
  switches that feed it.
- lipo: `+3V3` = AP7381-33SA-7 (150 mA, θJA 167 °C/W in SOT-23) on `VIN` (raw pack), always on.
  The latched cutoff works because the MCU outlives its own kill (`Q_KILL` pulls `BUCK_EN` low).
  A module fed only from buck `+5V` would kill its supply, reboot, kill again.
- The L072 drew a few mA, so a small LDO was enough. The ESP32-S3 draws ~40-80 mA running (radio
  off) and needs VDD ≥ 3.0 V: the pack XC6206 falls below that at cells under ~3.5 V (Schottky +
  dropout), and the lipo AP7381 would dissipate (12.6 − 3.3) V × 80 mA ≈ 0.74 W → ~124 °C rise →
  thermal shutdown.

Therefore two feeds on both boards:
- **Keep-alive → 3V3 pad**, from the always-on LDO: carries deep sleep, boot, and short bridges.
  - pack: 3V3 pad on board `+3V3` directly (XC6206 at ≥ 3.6 V cells dissipates < 50 mW running).
  - lipo: 3V3 pad ← AP7381 through a Schottky `D_KA` (B5819W), so the keep-alive sits ~0.2-0.3 V
    *below* the module's buck and never carries running current while `+5V` is up; the board
    `+3V3` net shrinks to the AP7381 output and its caps.
- **Run → 5V pad** (Seeed's diode-fed input), the module's SGM6029 makes 3.3 V from it:
  - pack: `D_M1` from `+5V` (boost, key on) and `D_M2` from `VBUS` (cable in), both B5819W.
    `VBUS` stays direct to `U_CHG.1/24` — only the module's feed is dioded.
  - lipo: `D_M1` from buck B `+5V`.
- Both regulators are source-only, so the higher one supplies, automatically: key on / cable in →
  module buck; low cells or bucks killed → keep-alive. lipo kill sequence: module asserts
  `KILL_DRV` → `+5V` falls → keep-alive carries the module (~3.0 V via `D_KA`, at the VDD floor) for
  the few hundred ms until firmware enters deep sleep with `KILL_DRV` held — firmware must sleep
  promptly after a kill (≤ 1 s, AP7381 thermal mass).
- **One logic domain:** the module is never dead while `+3V3` is live, so pull-ups and dividers on
  `+3V3` cannot back-feed it. The carrier's EXT pull-ups are on the carrier 3V3, live only with the key.
- **Storage drain** = module deep sleep through the keep-alive (+ LDO quiescent, + µA back-drive
  leakage) replacing the L072's stop mode; INA226s (~0.33 mA each) go to power-down mode by
  firmware when idle, as on `_tme`. `power_budget.py` carries both numbers.
- **CHG_CE dropped from the MCU:** `R_CE` 10k to GND stays (CE active-low → charging autonomous
  with no firmware); firmware stops charging with the BQ25601 `CHG_CONFIG` bit over I2C. A
  watchdog expiry restores the register default (charging on) — the same fail-safe as the pin.

## Pin budget — pack_xiao

Dropped outright: `U_MCU` + caps, NRST/BOOT parts, SWD/BOOT test pads, `J_UART1` + `UART_TX/RX`
(USB CDC console replaces it), `MON_PWRDN` (already dead on `_tme`), `CHG_CE` (see above),
`CHG_INT` + `R_INT_CHG` (charge is autonomous; hardwired `LED_STAT` shows state; status over
I2C), `MON_ALERT` + `R_ALERT` (the bus is polled), `LED_MCU`+R (module's onboard GPIO21 LED
replaces it — enclosure window must show the module LED; insertion redesign note for `mech/`),
USB data pins of the board USB-C (its VBUS + CC pull-downs stay).

13 signals: 11 edge pads + 2 bottom pads; the bottom pads carry only signals whose failure is
loud and safe at first boot (bus dead / all NTCs read 0), never a gate.

| Signal | Pad | Note |
|---|---|---|
| `NTC1` `NTC2` `NTC3` `NTC4` (ADC) | D0, D1, D2, D3 | |
| `SDA_EXT` / `SCL_EXT` (carrier link, I2C0 slave 0x30) | D4 / D5 | |
| `SCL_INT` (I2C1 master) | D6 | boot chatter harmless, see Module fit |
| `SW1..SW4_DRV` (cell gates, default-off) | D7, D8, D9, D10 | `R_PD1..4` = 4.7k (D7's 45k pull-up) |
| `SDA_INT` | GPIO39 (bottom, MTCK) | its after-reset pull-up is harmless on a pulled-up bus |
| `NTC_PWR` (digital out, ~0.7 mA) | GPIO40 (bottom, MTDO) | no reset pull; stays switched (NTCs on always-on `+3V3` would draw ~0.7 mA in storage) |

GPIO41/42 spare. Module 5V pad on `D_M1`/`D_M2` cathodes, 3V3 pad on `+3V3`, BAT+ unconnected.

## Pin budget — lipo_xiao

6 pads of 11: `SDA_EXT`/`SCL_EXT` = D4/D5, `TAP1..3_ADC` = D0..D2, `KILL_DRV` = D8 (GPIO7, no
reset pull, RTC-capable, held through deep sleep). Dropped: `U_MCU` + 3 caps, NRST parts, MCU test
pads, `J_UART1` + `UART_TX/RX`. **Kept:** the AP7381 and its caps (keep-alive). Added: `D_KA`,
`D_M1`. Tap dividers unchanged (tops on the balance leads, always live — legal, the module is too).
D6/D7 may stay as bare-copper U0 bring-up pads (builder's call). BAT+ unconnected.

ADC accuracy: cell 3 = TAP3 (×0.19) − TAP2, so 1 % ADC error ≈ 120 mV per cell at 3S. The
ESP32-S3 ADC needs a per-board two-point calibration (bench supply on the balance plug), stored in
NVS — a firmware step, recorded here because the LVC threshold depends on it.

## Mechanics

- Module USB-C needs a cable route to the outside (its own ~13 × 9 mm slot) next to the board
  USB-C slot; exact positions with the pack insert redesign (`mech/`, out of scope). Two exposed
  ports are accepted (charge vs program/console). The v2 one-port option (board `VBUS` fed from
  the module's 5V pad) is **dropped**: it would push the charger's ~2 A through the module.
- The module's BOOT (GPIO0) and RESET buttons have no bottom pads: keep them reachable by a
  paperclip before gluing inserts (bricking via bad flash is the only case they are needed; first
  flash is buttonless).
- Module + pad row ≥15 mm from XH connectors (layout's job).

## Cost delta (record real numbers at ordering)

Per board: −L072 (~€4.60 TME schema top) − ~€0.50 MCU support parts (pack also −`R_ALERT`,
−`R_INT_CHG`, −`J_UART1`), +2 B5819W (already a TME line), + XIAO (~€4.4 Botland). Roughly
money-neutral; strongly positive on solder difficulty, tooling (no ST-Link), and module
reusability. This is an assemble-ability project, not a cost project.

## Non-goals

- No changes to carrier, JLC boards, firmware architecture, or the charge-control topology
  (cell string, gates, fuses, per-cell INA226 stay).
- No socketed module (solder down; hot air removes it in 30 s).
- No WiFi/ESP-NOW features; the radio is spare capability.

## Left to the builder

Footprint drawing from Seeed's PCB (edge + bottom pads); pad cosmetics within the fixed tables;
placement/routing; `check()` green for both modules (including: 3V3 pad on the keep-alive, 5V pad
on the run diodes only, BAT+ unconnected, `R_PD1..4` = 4.7k, no gate on D6); `make boards` +
ERC/DRC clean; `power_budget.py` numbers (module run current on the 5V path, deep sleep on the
keep-alive); OFFBOARD_PARTS/COSTS updates; whether lipo keeps bare U0 copper pads.

## Verification / acceptance

1. Symbol/footprint imported from Seeed's OPL library (not redrawn); pin numbers as in "Module
   facts"; any difference corrects this doc first.
2. `python3 pack_xiao.py && python3 lipo_xiao.py` pass; `make BOARD=… fab` → Gerbers zero DRC,
   ERC-clean PDFs, TME lists with no STM32/MCU support parts.
3. Breadboard spike (module on DuPonts):
   - 3V3 pad alone at 3.3 V: boots; current into the pad in deep sleep (→ `power_budget.py`);
     BAT+ and 5V pad voltages and leakage as predicted (BAT+ ≈ 3.3 V, 5V pad ≈ 0);
   - 3V3 pad held by an XC6206 / AP7381+Schottky and 5 V through a B5819W into the 5V pad: the
     run current moves to the 5 V path; remove the 5 V — module keeps running on the keep-alive;
   - module USB plugged at the same time: console works, no reverse current into the board LDO;
   - boot-time level on D7..D10 with 4.7k to GND stays < 0.5 V;
   - USB CDC console; one INA226 read on I2C1 at 100 kHz with `SCL_INT` on GPIO43, and a scope
     on the bus through a reset (no START during the ROM log);
   - one NTC ADC read with 12 dB attenuation; two-point tap calibration repeatable;
   - BQ25601: `CHG_CONFIG` = 0 stops charging, watchdog expiry resumes it;
   - lipo: kill sequence at 3S (bucks off, module survives on `D_KA`, sleeps with `KILL_DRV` held,
     bucks stay off); reset with the key on does not glitch `BUCK_EN`.
