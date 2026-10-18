# Hierarchical schematics: handover for the remaining boards

Date: 2026-10-18. Branch `esp32-lora-design`. Read with the design
(`2026-10-18-hierarchical-schematics-design.md`, deviations at its top) and the implementation plan
(`2026-10-18-hierarchical-schematics-implementation.md`).

## Status

| Board | Schematic | Notes |
|---|---|---|
| **carrier_tme** | hierarchical, done | Pilot. Root + expander, drivers, audio. Review: 0 errors |
| carrier | flat | Next: the closest to carrier_tme (same board minus the DAC/amp swap) |
| pack | flat | Biggest (127 parts, 4 cell branches, bottom-side holders) |
| pack_tme | flat | Derives from pack.py by import and edit |
| lipo | flat | `lipo.py` imports `pack` (shared constants): check what it reuses before changing pack |
| lipo_tme | flat | Derives from lipo.py |

The goal the user set: "complete schema, not partial". That means three things:

- every block connected through a root (system) sheet with real wires;
- the off-board parts drawn on the other side of each connector;
- the MCU/module shown as one part with named pins.

The user also wants the Konnect `run_design_review` free of **errors**. Warnings are acceptable if they are
explained.

## How the hierarchical mode works (gen_sch.py)

A board module switches to hierarchical mode by defining `SHEETS`. The flat boards must keep regenerating
**byte-identical**, so every shared gen_sch change is checked against them (see Gates).

- **`SHEETS = {name: (title, [BLOCKS indexes])}`**: the function sheets. Each becomes
  `kicad/<board>-<name>.kicad_sch` (the dash keeps `carrier-*` globs off `carrier_tme-*`).
  `fit_block` shrinks each block to its content, and a sheet with one block takes the sheet title.
- **`ROOT`** holds the system sheet:
  - `parts`: `{ref: (x, y, rot, mirror)}`, absolute sheet coordinates. These refs are removed from their
    BLOCKS.
  - `sheets`: `{name: (x, y, w, h)}`. The box height grows to fit its pins. Pins go on the side facing
    their target and are ordered by the target's y.
  - `outline`: `(title, (x, y, w, h))`, the dash-dot module outline (Heltec).
  - `size`: `(w, h)` of the root content from (12.7, 12.7). Keep it within A3: `w + 12.7 <= 405`,
    `h + 12.7 <= 252`.
  - `flags`: `[(net, x, y)]`, the rail PWR_FLAGs. A flag must sit on a sheet that has that rail's parts,
    or ERC reports `pin_not_connected`.
  - `port_modes`: `{ref: "along"}` for 2.54 mm-pitch headers on the root, so their rail ports point
    along the stub and stay in the pin's own row.
- **`OFFBOARD = {"#X_<name>": (value, lib_id, connector, {own pin: connector pin}, cable note,
  (x, y, rot, mirror))}`**:
  - The refs are **virtual** (`#X_`). KiCad leaves them out of the netlist and BOMs, and Konnect's
    bom_health skips them.
  - `board.check_structure` asserts each entry hangs off a `Conn*` part and only uses connector pins
    that are on a net.
  - `check_netlist.py` ignores them.
  - The pin map is one-to-one. Several connector pins mapped to one module pin is not supported, which
    matters for USB-C (see pack).
- **Cables on the root**:
  - Signal pins of an off-board part join their net's tree.
  - Rail pins become `cable()` wires to the connector pin, and `tee_port()` hangs the rail's power port
    off the cable at the first cell from the connector where it fits.
  - Cables are drawn after the signals and before nothing else. Placing ports before cables walled the
    cables in.
- **Footprint linking**: gen_pcb links each footprint to `/<sheet uuid>/<symbol uuid>`. Root parts keep
  `/<symbol uuid>`.
- **Per-block options**, all opt-in, so flat output is unchanged:
  - `vcomb`: one power port for side-by-side up/down rail pins.
  - `combs`: `[[pin, ...]]`, a forced crossable comb over non-adjacent pins (the DAC's grounded config
    pins around XSMT).
  - `tags`: explicit hierarchical labels for nets leaving the sheet.
- **Automatic fallbacks**:
  - An untagged exiting multi-pin group gets a hierarchical label on one of its pins, and routing starts
    from that pin (`seed`).
  - A short internal net with no straight run long enough gets its name label on a stub off the wire.

## Recipe for one board

1. **Read the board module and its design doc** (`docs/plans/2026-10-0*-<board>-design.md`). Map the
   function blocks to sheets, and decide which parts go on the root.
2. **Decide what goes on the root.** This rule came out of the review: Konnect audits **each sheet on
   its own** and keys rails **by net name**. Any sheet showing a rail without that rail's decoupling or
   bulk cap is an *error*, and any sheet with an I2C device but no pull-ups is a *warning*. So draw these
   on the root beside their connector, which is also where they sit on the board:
   - power-entry/bulk caps of every rail that appears on the root;
   - debug headers and test pads;
   - flyback/protection parts at connectors;
   - bus pull-ups.

   Do **not** add parts or rename nets just to quiet the tool. Sheet-pin "rail exits" were tried and
   removed: the audit still saw the rail by name.
3. **Symbols** (create them **through Konnect's library tools**, never by text-editing `local.kicad_sym`):
   - Root cable connectors use 5.08 mm-pitch `local:Conn_W_02/04/06`, overridden in the board module the
     way carrier_tme does for its `J_*`. Footprints are unchanged. Add `Conn_W_03` or others if needed.
   - Off-board modules use 5.08 mm pitch too (`Module_I2C_4`, `Pack_Link_6`, `Button_LED_4`, stock
     `Device:Buzzer`, `Device:Speaker`).
   - For an MCU or module shown as one part, use named-pin symbols. carrier's Heltec symbols are checked
     against `carrier.heltec_pin_names()` by `gen_sch.check_heltec_names()`. Avoid pin names a review
     reads as an undecoupled supply: J2.2 became "CHG IN".
4. **Write `SHEETS` / `ROOT` / `OFFBOARD`** in the board module, plus a `check_sheets()` like
   carrier_tme's: every part drawn exactly once, and every sheet placed.
5. **Iterate the layout** with `BOARD=<b> /usr/bin/python3 tools/sch_preview.py [sheet]`. Render with
   `kicad-cli sch export pdf` and **look at every page**. Typical fixes:
   - move a part, or give a net an explicit `tags` entry;
   - space the right-hand connectors 30.48 mm apart (5.08-pitch 4-pin connectors overlap at 25.4);
   - widen a cable gap, because both connector and module need room for ports.
6. **Gates**, all of them, in this order:
   - **Flat regression** (only needed if gen_sch.py changed). Before the change, hash each still-flat
     board's raw output: `BOARD=<b> /usr/bin/python3 gen_sch.py` then `cp kicad/<b>.kicad_sch
     /tmp/schbase/`. After it, regenerate and `cmp`, which must be identical. Then
     `git checkout -- kicad/<flat boards>`.
   - `make BOARD=<b> sch` must show "netlist matches", with every sheet upgraded to KiCad 10.
   - `make BOARD=<b> all` must give ERC 0, DRC 0 violations, 0 unconnected, 0 schematic parity, and
     "gerbers ok". It reroutes, so run it in the background (several minutes).
   - **Board unchanged apart from paths.** Compare footprint ref, position, rotation, side and pad nets
     against `git show HEAD:hardware/kicad/<b>.kicad_pcb` with a small pcbnew script that loads both
     boards. Only footprint paths may differ, plus unconnected-pin net names wherever a symbol's pin
     names changed.
   - **Konnect**: run `check_schematic_overlaps` on every sheet file (expect 0) and `run_design_review`
     on the root plus the board (expect 0 errors). List the remaining warnings in the report.
7. **Docs, then commit and push.** Update `hardware/docs/ORDERING.md` (the schematic paragraph for that
   board) and the design doc status. Stage with explicit paths, and add the deletions of retired sheet
   files with `git rm`: the `kicad/<b>*.kicad_sch` glob misses deleted files. `.kicad_prl` is gitignored.

## Per-board notes

**carrier** (JLC board, closest to the pilot)
- The same root as carrier_tme. The difference is the audio sheet: NS4168 (U3, C_AMP1/2, R_SD1,
  R_SDPD1, J_SPK1) instead of the DAC and PAM8302.
- Cleanest route: move the hierarchy data (`SHEETS`, `ROOT`, `OFFBOARD`, the `Conn_W` and Heltec symbol
  overrides, `heltec_pin_names`) from carrier_tme.py into carrier.py. carrier_tme then *derives* its data
  by import and edit, as it already does for PARTS/NETS: replace the audio block, drop U3 from ROOT and
  keep its own C_5V placements.
- Re-run carrier_tme's gates after the move.
- The JLC outputs (jlc_bom.csv, jlc_cpl.csv) must not change. jlc.py reads only PARTS.

**pack** (127 parts)
- Blocks: [0] USB-C + BQ25601, [1] PAC1934 monitor + diode-OR + 3V3 LDO, [2] STM32C071 + reset/boot +
  test pads, [3] key switch + PTC + 5 V boost + J_PWR1, [4..7] cell 1..4 branches, [8] holes + flags.
- Suggested sheets: charger, monitor, MCU, boost/key, cell1..cell4. That gives four near-identical cell
  sheets. gen_sch writes one file per sheet, which is fine; KiCad sheet reuse (one file, many instances)
  is not implemented.
- Root:
  - connectors J_USB1, J_KEY1 and J_PWR1, with off-board parts `#X_CARRIER` (to the carrier's J_PWR1,
    6-pin XHP 1:1), `#X_KEY` (EAO 82-6121 key switch, 2-pin) and USB;
  - bring-up pads (TP_*, J_UART1);
  - rail bulk caps for every rail drawn on the root.
- **USB-C**: J_USB1 has duplicated pins (A4/B4/A9/B9 = VBUS and so on), and OFFBOARD maps one-to-one. Either
  map one representative pin per signal (VBUS, D+, D-, GND) to an off-board "USB-C panel extension" part,
  or leave USB without an off-board part and add a text note. Don't extend the mapper unless needed.
- **Bottom-side parts**: BT1-4 (18650 holders) and TH1-4 (NTC beads in the holder windows) are board
  parts. Keep each holder and its NTC on its cell sheet. If a cell needs an off-board part, use
  `#X_CELLn` "Samsung INR18650-35E" off the holder (a holder is not a `Conn*` part, so the OFFBOARD guard
  would have to allow it). Otherwise skip it.
- The rails here are VPACK, VBUS, VMCU_IN, BAT_CHG, VBAT_SW, +3V3 and GND. The flat review already
  flagged VPACK (decoupled only through a 0 Ω jumper to C_BAT) and the INA/PAC sense pins as false
  positives: see memory `konnect-review-baseline`. Per-sheet audits will multiply these; put the 0 Ω
  jumper and C_BAT on the same sheet.

**pack_tme**
- Derives from pack. After pack is done, adapt: INA226 per cell instead of the PAC1934, STM32L072, the
  BQ25601 hand-solder footprint, its own J_UART1/U_CHG/J_USB1 placements.
- J_UART1 must stay off the holder courtyards. gen_pcb's `PTH_UNDER_OK` check enforces that.

**lipo**
- Blocks: [0] LiPo input (J_IN1 pads, fuse, reverse FET, TVS), [1] buck A 4.10 V / buck B 5.07 V,
  [2] key enable + MCU kill + J_PWR1, [3] 3V3 + STM32C071 + SWD pads, [4] balance-lead dividers,
  [5] holes + flags.
- Off-board: `#X_LIPO` (2S/3S pack on an XT60 pigtail into the J_IN1 pads), `#X_BAL` (balance plug into
  J_BAL1), `#X_KEY` (key switch on J_KEY1) and `#X_CARRIER` (J_PWR1).
- J_IN1 is "Connector_Generic" on solder pads, so the OFFBOARD guard accepts it.
- `lipo.py` imports `pack`. Before editing shared helpers in pack.py, check what lipo takes from it.

**lipo_tme**
- Derives from lipo: STM32L072, TPS563200, TP_BOOT0. Do it after lipo.

## Expected review noise (do not chase)

- Missing MPN on every IC: part numbers live in each module's `LCSC`/`TME` table.
- carrier_tme: U2 "no I2C pull-up" (the pull-ups are on the root) and expander "+3V3 no ≥10 µF bulk"
  (C_NFC1 is on the root). Both are warnings.
- The netlist export prints "annotation errors" because references have no trailing digit (TP_GND, U_MCU).
  It's harmless: ERC and parity pass.
- The Konnect PNG renderer drops thin wires. Check wiring in `kicad-cli sch export pdf`.

## Pitfalls already hit (and fixed)

- **Root rail ports at 2.54 mm pitch**:
  - Ports pointing up or down collide with the next row.
  - Ports pointing along the stub fit, but then a cable can't pass.
  - Hence 5.08 mm root symbols, cable first and tee port.
- **Cable notes**: notes placed in the cable gap blocked tee ports. They now go under the module's
  value text.
- **Hierarchical labels**: a label stub drawn before routing must be the routing seed, or it stays an
  island.
- **Uuids**: everything except `sym/` and `pin/` keys gets a per-sheet prefix (`UID_PREFIX`), and the
  `#PWR`/`#FLG` counters run across sheets. gen_pcb links to `uid("sym/<ref>")`.
- **Unconnected-pin net names**: gen_pcb escapes spaces as KiCad does (`_`).
- **Stale sheet files**: gen_sch deletes `kicad/<board>-*.kicad_sch` that no longer belong to SHEETS.
  Commit that deletion.
- **Headless pcbnew**: a pcbnew under xvfb may still hold `pack_tme.kicad_pcb` open. Never save from it.
