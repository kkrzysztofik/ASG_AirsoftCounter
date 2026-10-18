# Hierarchical schematics: design (pilot: carrier_tme)

Date: 2026-10-18. Status: implemented on all six boards (carrier, carrier_tme, pack, pack_tme, lipo,
lipo_tme). carrier_tme was the pilot; the rest followed the handover, and the deviations found on the
way are recorded at the end of that document.

Changes from the approved design, made to clear the review findings (each sheet is audited on its own):
- Power-entry caps, the bring-up headers and pads, D_FLY1 and the I2C level shifter with the bus
  pull-ups are drawn on the root beside their connectors (where they sit on the board), so the root
  rails have their bulk caps and the I2C bus its pull-ups on the same sheet. Function sheets: expander,
  drivers, audio.
- Off-board parts use virtual `#X_*` references (out of the netlist and BOMs, like `#PWR`).
- Root cable connectors and off-board modules are drawn at 5.08 mm pitch (schematic only). Every
  off-board pin is a cable wire to its connector pin; a rail's power port hangs off its cable.
- J2 pin 2 is named "CHG IN" (a "5V" name reads as a supply pin to the decoupling audit).

## Problem

The generated schematics are hard to read and feel partial:

- **Blocks are islands.** Each block connects to the rest only through net labels, so you can't follow a
  signal across the board.
- **Off-board parts are missing.** The sheet shows connectors (J_LCD1, J_NFC1, J_SPK1, J_PWR1 …) but not
  what plugs into them.
- **The Heltec is two bare headers.** J2/J3 are generic `Conn_01x18` symbols with numbered pins.
- **The audio block is tangled.** In `carrier_tme.py` every net in that block, internal ones included, is
  tagged in one label column at x = 15.24. The router then draws a long wire from each label to its pins.
  The parts are also placed in rows, not along the signal path.
- **The sheet is badly used.** carrier_tme is on A2, but the content fills only the top ~55% of it.

## Decision

Generate a **hierarchical** schematic: a root "system" sheet plus one sheet per function. Two
alternatives were rejected:

- A flat sheet laid out by signal flow: the cross-block wiring tends to tangle again.
- A flat sheet with a separate overview drawing: the overview isn't electrically checked, so it drifts.

carrier_tme is the pilot. carrier, pack and lipo stay flat until each is migrated in its own step.

## 1. Sheet structure

- **Root sheet ("<TITLE> — system")** shows what plugs into what:
  - The Heltec sockets J2/J3, centred inside one outline titled "Heltec WiFi LoRa 32 V4 (plugs into J2/J3)".
  - Every board connector: J_PWR1, J_HBAT1, J_LCD1, J_NFC1, J_BTN_R1, J_BTN_B1, J_BUZ1, J_SPK1.
  - The off-board parts beyond each connector, the mounting holes, and one sheet box per function sheet.
- **Root wiring:** sheet pins are wired to the Heltec pins and the connectors, so I2C, I2S, AMP_SD, the
  button lines and the driver outputs are visible wires. Power rails (GND, +3V3, +5V, VBAT_SW) stay as
  power symbols.
- **Function sheets for carrier_tme:**
  1. Power: C_BULK1/2, C_5V1/2, rail flags
  2. I2C level shifter: Q_SDA1/Q_SCL1, pull-ups, C_NFC1
  3. GPIO expander + button inputs: U2, C_EXP1, R_INT1, button RC filters
  4. LED/buzzer drivers: the three BSS138 drivers, D_FLY1
  5. Audio: PCM5100A → RC → PAM8302
  6. Debug: J_UART1, J_I2C1, test pads. These are bring-up headers, so they stay in their sheet.
- **Board module:** groups its existing `BLOCKS` into sheets and lists which parts sit on the root.

## 2. Connectivity, net names, checks

- **Net names don't change.**
  - A net that leaves its sheet gets a hierarchical label inside the sheet, a sheet pin, and a root wire
    carrying a global label with the module's net name. KiCad then names it `SDA_3V3`, not `/I2C/SDA_3V3`.
  - Internal nets keep a name label placed next to one of their own pins. There are no far-off label columns.
  - Power rails stay as power symbols.
- **Board link.** Symbol uuids stay `uid("sym/<ref>")`. Each sheet gets `uid("sheet/<name>")`. gen_pcb links
  a footprint to `/<sheet uuid>/<symbol uuid>`, or to `/<symbol uuid>` for root parts, reading the sheet
  of each ref from the module.
- **Off-board parts.**
  - They live in a new `OFFBOARD` table, never in `PARTS`.
  - They're drawn as symbols marked not on board and not in BOM, with `X_` reference prefixes.
  - `check_netlist.py` ignores `OFFBOARD` refs. gen_pcb, jlc.py and tme.py read only `PARTS`.
  - `board.check_structure` asserts that every `OFFBOARD` pin lands on a connector pin's net.
- **Gates (the existing `make` chain):**
  - `make sch`: gen_sch writes the root and sheet files, `kicad-cli sch upgrade` runs on each, and
    `check_netlist.py` confirms the netlist equals `NETS`.
  - `make check`: ERC 0; DRC 0 errors, 0 unconnected, 0 parity.
  - The routed board differs only in footprint paths.

## 3. Heltec module and off-board symbols

- **Heltec.** Two new symbols, `local:Heltec_V4_J2` and `local:Heltec_V4_J3`, keep today's pin numbers.
  - Pin names are generated from `HELTEC_GPIO` / `HEADER_POWER`, e.g. `GPIO44 RX`, `3V3`, `5V (charger, NC)`.
  - On the root they are drawn side by side inside one module outline.
  - Forbidden pins keep their no-connect flags.
- **carrier_tme `OFFBOARD`:**

| Ref | Symbol | Connects to | Cable note |
|---|---|---|---|
| X_PACK | 6-pin "Pack board (P5)": GND GND VBAT 5V SDA SCL | J_PWR1 | XH-6 |
| X_HBAT | 2-pin "Heltec V4 battery input (SH1.25)" | J_HBAT1 | XH-2 → SH1.25 |
| X_LCD | 4-pin I2C module "LCD 1602 + PCF8574" | J_LCD1 | XH-4 |
| X_NFC | 4-pin I2C module "PN532 (I2C)" | J_NFC1 | XH-4 |
| X_BTN_R, X_BTN_B | "ONPOW LAS1-AGQ-11E/x/6V": SW, COM, LED+, LED− | J_BTN_R1, J_BTN_B1 | XH-4 |
| X_BUZ | `Device:Buzzer` | J_BUZ1 | XH-2 |
| X_SPK | `Device:Speaker` | J_SPK1 | XH-2, "BTL: neither side is GND" |

- **Library work.** Three new local symbols (a generic 4-pin I2C module, a 6-pin pack link, a button+LED)
  and the two Heltec symbols. They are created through Konnect's library tools, never by editing
  `local.kicad_sym` as text.
- **Root drawing.** Off-board parts sit just outside their connector, with straight pin-to-pin wires and a
  cable note.

## 4. Layout, rollout, testing

- **Paper.** Each sheet gets its own paper size, chosen from its content.
- **Positions.** Placement stays hand-specified in the module. Hierarchical labels sit on the sheet edge
  that faces their root target.
- **Audio sheet, left to right:**
  - I2S in.
  - U_DAC, with each capacitor beside its own pins: C_DVDD/C_DAVDD/C_DCPV at the supply pins, C_DCP across
    CAPP–CAPM, C_DNEG at VNEG, C_DLDO at LDOO.
  - Output RC: R_OL/C_OL, R_OR/C_OR.
  - C_INP/R_INP, C_INN/R_INN.
  - U_AMP, then SPK± out on the right.
  - AMP_SD comes in at the bottom through R_SD1/R_SDPD1.
- **Root layout.** Sheet boxes sit beside the Heltec pins they use. Sheet pins are ordered by their target's
  position so root wires run parallel. The existing router and clash gate apply to the root too.
- **Rollout.** A module with `SHEETS` builds the hierarchy, and one without stays flat.
- **Testing:**
  - gen_sch's no-clash gate passes per sheet and on the root.
  - The `make` gates above pass.
  - A diff confirms the board changed only in footprint paths.
  - Every sheet is rendered with `kicad-cli sch export pdf` and reviewed for crossings and stray labels.
  - Konnect's `check_schematic_overlaps` reports 0 on every sheet.
  - An assert proves an `OFFBOARD` pin on a non-connector net fails.
