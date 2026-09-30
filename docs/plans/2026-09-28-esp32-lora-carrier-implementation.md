# AirsoftCounter v2 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the Heltec V4 carrier PCB (fully generated and autorouted from a Python netlist) and the Rust firmware up to a playable local game with RFID cards.

**Architecture:** The hardware lives in `hardware/`: `design.py` is the single source of truth for parts and nets. Scripts generate the KiCad schematic and board from it, Freerouting routes the board, and `kicad-cli` ERC/DRC with schematic parity are the tests. The firmware is two crates. `firmware/core` is `no_std` game logic tested on the host with `cargo test`. `firmware/device` is the esp-hal + Embassy binary for the ESP32-S3; it depends on `core` by path and stays thin.

**Tech Stack:** KiCad 9.0.8 (`kicad-cli`, `pcbnew` Python API via `/usr/bin/python3`), Freerouting 2.4.1 (Java 25), Rust stable for `core`, the Espressif Xtensa toolchain via `espup` for `device`, esp-hal 1.2, embassy-executor 0.10, esp-rtos 0.4, heapless 0.9, pn532 0.5.

**Design reference:** `docs/plans/2026-09-28-esp32-lora-carrier-design.md` (read it first).

**Scope:** Hardware A1–A8 and firmware milestones 0–3 are fully specified here. Milestones 4–7 (LoRa, GPS, WiFi page, HQ bridge) get their own detailed plans when reached, because esp-radio is beta and its API will move.

**Conventions:**
- Prefix shell commands with `rtk` (see `~/CLAUDE.md`).
- Run KiCad Python with `/usr/bin/python3`; the system interpreter has `pcbnew`.
- Commit after every task. End commit messages with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

---

## Phase A: Carrier board (hardware/)

Final layout:

```
hardware/
├── design.py        # parts + nets + self-check (source of truth)
├── gen_sch.py       # design.py -> carrier.kicad_sch
├── gen_pcb.py       # design.py -> carrier.kicad_pcb (placed, nets assigned, unrouted)
├── route.py         # DSN export -> Freerouting -> SES import -> zone fill
├── Makefile         # sch / pcb / route / check / fab
├── carrier.kicad_pro, carrier.kicad_sch, carrier.kicad_pcb   (generated, committed)
├── fab/             # gerbers, drill, BOM, renders, 1:1 PDF (generated, committed per release)
└── tools/           # freerouting jar (gitignored)
```

### Task A1: Tooling

**Files:**
- Create: `hardware/tools/.gitignore` (content: `*.jar`)

**Step 1:** Download Freerouting.

```bash
mkdir -p hardware/tools && cd hardware/tools
curl -fLO https://github.com/freerouting/freerouting/releases/download/v2.4.1/freerouting-2.4.1.jar
java -jar freerouting-2.4.1.jar --help | head -40
```

Expected: the help text lists `-de` (input DSN), `-do` (output SES) and `-mp` (max passes), plus a headless/GUI-disable option. **Write the exact headless flags you find into Task A6.** Also disable analytics if there is a flag for it.

**Step 2:** Check the KiCad CLI: run `kicad-cli version` and expect `9.0.8`.

**Step 3:** Commit: `git add hardware/tools/.gitignore && git commit -m "hardware: tooling scaffold"`

### Task A2: design.py, the netlist and its self-check

**Files:**
- Create: `hardware/design.py`

**Step 1:** Create `hardware/design.py` with exactly this content. It was verified before planning: the self-check passes, and it correctly rejects a button moved to GPIO5.

> **Note (post-review, commit ad80848):** the committed `hardware/design.py` is now the authority. It adds checks for all 36 header pins, the `DNP` set, and the renamed `AO3400A` constant; `HELTEC_5V_PIN` is gone. The listing below is the original version.

```python
"""AirsoftCounter v2 carrier board: single source of truth for parts and nets.

gen_sch.py and gen_pcb.py read PARTS and NETS from here. Run this file to
self-check the design (`python3 design.py`).
"""

# ref: (value, symbol "lib:name", footprint "lib:name")
PARTS = {
    # Heltec WiFi LoRa 32 V4 headers (pin 1 at USB end). Rows are 22.86 mm apart.
    "J2": ("Heltec_J2", "Connector_Generic:Conn_01x18", "Connector_PinSocket_2.54mm:PinSocket_1x18_P2.54mm_Vertical"),
    "J3": ("Heltec_J3", "Connector_Generic:Conn_01x18", "Connector_PinSocket_2.54mm:PinSocket_1x18_P2.54mm_Vertical"),
    # Off-board connectors, JST-XH 2.50 mm vertical
    "J_BAT": ("BAT", "Connector_Generic:Conn_01x02", "Connector_JST:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical"),
    "J_KEY": ("KEY", "Connector_Generic:Conn_01x02", "Connector_JST:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical"),
    "J_HBAT": ("HELTEC_BAT", "Connector_Generic:Conn_01x02", "Connector_JST:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical"),
    "J_LCD": ("LCD", "Connector_Generic:Conn_01x04", "Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical"),
    "J_NFC": ("NFC", "Connector_Generic:Conn_01x04", "Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical"),
    "J_BTN_R": ("BTN_R", "Connector_Generic:Conn_01x04", "Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical"),
    "J_BTN_B": ("BTN_B", "Connector_Generic:Conn_01x04", "Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical"),
    "J_BUZ": ("BUZ", "Connector_Generic:Conn_01x02", "Connector_JST:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical"),
    # Power
    "F1": ("1A PTC", "Device:Polyfuse", "Fuse:Fuse_1206_3216Metric_Pad1.42x1.75mm_HandSolder"),
    "U1": ("MT3608", "Regulator_Switching:MT3608", "Package_TO_SOT_SMD:SOT-23-6"),
    "L1": ("10uH 2A", "Device:L", "Inductor_SMD:L_Bourns_SRN6045TA"),
    "D1": ("SS34", "Diode:SS34", "Diode_SMD:D_SMA"),
    "R_FB1": ("75k", "Device:R", "Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder"),
    "R_FB2": ("10k", "Device:R", "Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder"),
    "C_IN": ("22uF 10V", "Device:C", "Capacitor_SMD:C_1206_3216Metric_Pad1.33x1.80mm_HandSolder"),
    "C_OUT1": ("22uF 10V", "Device:C", "Capacitor_SMD:C_1206_3216Metric_Pad1.33x1.80mm_HandSolder"),
    "C_OUT2": ("22uF 10V", "Device:C", "Capacitor_SMD:C_1206_3216Metric_Pad1.33x1.80mm_HandSolder"),
    "C_BULK": ("220uF 10V", "Device:C_Polarized", "Capacitor_THT:CP_Radial_D6.3mm_P2.50mm"),
    "C_NFC": ("100uF 10V", "Device:C_Polarized", "Capacitor_THT:CP_Radial_D6.3mm_P2.50mm"),
    # I2C level shifter (5V-side pull-ups DNP: LCD backpack has its own)
    "Q_SDA": ("BSS138", "Transistor_FET:BSS138", "Package_TO_SOT_SMD:SOT-23"),
    "Q_SCL": ("BSS138", "Transistor_FET:BSS138", "Package_TO_SOT_SMD:SOT-23"),
    "R_SDA3": ("4k7", "Device:R", "Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder"),
    "R_SCL3": ("4k7", "Device:R", "Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder"),
    "R_SDA5": ("4k7 DNP", "Device:R", "Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder"),
    "R_SCL5": ("4k7 DNP", "Device:R", "Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder"),
}

R0805 = ("Device:R", "Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder")
C0805 = ("Device:C", "Capacitor_SMD:C_0805_2012Metric_Pad1.18x1.45mm_HandSolder")
SOT23 = ("Transistor_FET:AO3400A", "Package_TO_SOT_SMD:SOT-23")

# Low-side drivers: name -> (gate GPIO net, load resistor value or None)
DRIVERS = {"LR": ("LED_R_G", "150R"), "LB": ("LED_B_G", "100R"), "BZ": ("BUZ_G", None)}
for n, (_, r_load) in DRIVERS.items():
    PARTS[f"Q_{n}"] = ("AO3400A", *SOT23)
    PARTS[f"R_G{n}"] = ("100R", *R0805)
    PARTS[f"R_PD{n}"] = ("100k", *R0805)
    if r_load:
        PARTS[f"R_L{n}"] = (r_load, *R0805)
PARTS["D_FLY"] = ("1N4148W", "Diode:1N4148W", "Diode_SMD:D_SOD-123")

# Button inputs: 10k pull-up, 100nF, 1k series
for t in ("R", "B"):
    PARTS[f"R_PU{t}"] = ("10k", *R0805)
    PARTS[f"R_S{t}"] = ("1k", *R0805)
    PARTS[f"C_B{t}"] = ("100nF", *C0805)

for i in range(1, 5):
    PARTS[f"H{i}"] = ("M3", "Mechanical:MountingHole", "MountingHole:MountingHole_3.2mm_M3")

# net: [ "REF.pin", ... ]
NETS = {
    "GND": ["J2.1", "J3.1", "J_BAT.2", "J_HBAT.2", "J_LCD.1", "J_NFC.1", "J_BTN_R.2", "J_BTN_B.2",
            "U1.2", "R_FB2.2", "C_IN.2", "C_OUT1.2", "C_OUT2.2", "C_BULK.2", "C_NFC.2",
            "Q_LR.2", "Q_LB.2", "Q_BZ.2", "R_PDLR.2", "R_PDLB.2", "R_PDBZ.2", "C_BR.2", "C_BB.2"],
    "+3V3": ["J3.2", "J3.3", "J_NFC.2", "C_NFC.1", "Q_SDA.1", "Q_SCL.1", "R_SDA3.1", "R_SCL3.1", "R_PUR.1", "R_PUB.1"],
    "VBAT_RAW": ["J_BAT.1", "F1.1"],
    "VBAT_F": ["F1.2", "J_KEY.1"],
    "VBAT_SW": ["J_KEY.2", "J_HBAT.1", "C_BULK.1", "C_IN.1", "U1.5", "U1.4", "L1.1"],
    "SW": ["L1.2", "U1.1", "D1.2"],
    "FB": ["U1.3", "R_FB1.2", "R_FB2.1"],
    "+5V": ["D1.1", "C_OUT1.1", "C_OUT2.1", "R_FB1.1", "J_LCD.2", "J_BTN_R.3", "J_BTN_B.3", "J_BUZ.1",
            "D_FLY.1", "R_SDA5.1", "R_SCL5.1"],
    # I2C
    "SDA_3V3": ["J3.15", "Q_SDA.2", "R_SDA3.2", "J_NFC.3"],
    "SCL_3V3": ["J3.14", "Q_SCL.2", "R_SCL3.2", "J_NFC.4"],
    "SDA_5V": ["Q_SDA.3", "R_SDA5.2", "J_LCD.3"],
    "SCL_5V": ["Q_SCL.3", "R_SCL5.2", "J_LCD.4"],
    # Drivers: GPIO -> gate resistor -> gate (pull-down) ; drain -> load
    "LED_R_G": ["J2.13", "R_GLR.1"], "Q_LR_G": ["R_GLR.2", "Q_LR.1", "R_PDLR.1"],
    "LED_R_K": ["Q_LR.3", "R_LLR.1"], "BTN_R_LEDK": ["R_LLR.2", "J_BTN_R.4"],
    "LED_B_G": ["J2.14", "R_GLB.1"], "Q_LB_G": ["R_GLB.2", "Q_LB.1", "R_PDLB.1"],
    "LED_B_K": ["Q_LB.3", "R_LLB.1"], "BTN_B_LEDK": ["R_LLB.2", "J_BTN_B.4"],
    "BUZ_G": ["J2.16", "R_GBZ.1"], "Q_BZ_G": ["R_GBZ.2", "Q_BZ.1", "R_PDBZ.1"],
    "BUZ_K": ["Q_BZ.3", "J_BUZ.2", "D_FLY.2"],
    # Buttons: switch pulls to GND
    "BTN_R_SW": ["J_BTN_R.1", "R_PUR.2", "C_BR.1", "R_SR.1"], "BTN_R_IN": ["R_SR.2", "J3.17"],
    "BTN_B_SW": ["J_BTN_B.1", "R_PUB.2", "C_BB.1", "R_SB.1"], "BTN_B_IN": ["R_SB.2", "J2.5"],
}

# Heltec header pin -> ESP32 GPIO (V4 pin map). Only pins we use or must avoid.
HELTEC_GPIO = {
    "J3.12": 1, "J3.13": 2, "J3.14": 3, "J3.15": 4, "J3.16": 5, "J3.17": 6, "J3.18": 7,
    "J3.4": 37, "J3.5": 46, "J3.6": 45, "J3.7": 42, "J3.8": 41, "J3.9": 40, "J3.10": 39, "J3.11": 38,
    "J2.5": 44, "J2.6": 43, "J2.7": None, "J2.8": 0, "J2.9": 36, "J2.10": 35, "J2.11": 34, "J2.12": 33,
    "J2.13": 47, "J2.14": 48, "J2.15": 26, "J2.16": 21, "J2.17": 20, "J2.18": 19,
}
# Used internally on V4-R2 or V4-R8 (FEM, GNSS, PSRAM, strapping, USB, LED/Vext, VBAT), or RST.
FORBIDDEN_GPIO = {0, 1, 2, 5, 7, 19, 20, 26, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 45, 46, None}
EXPECTED_GPIO = {"SCL_3V3": 3, "SDA_3V3": 4, "BTN_R_IN": 6, "BTN_B_IN": 44,
                 "LED_R_G": 47, "LED_B_G": 48, "BUZ_G": 21}
HELTEC_5V_PIN = "J2.2"  # charger input: must stay unconnected


def check():
    pins = [p for members in NETS.values() for p in members]
    dupes = {p for p in pins if pins.count(p) > 1}
    assert not dupes, f"pin on several nets: {dupes}"
    for net, members in NETS.items():
        assert len(members) >= 2, f"{net} has a single pin"
        for p in members:
            assert p.split(".")[0] in PARTS, f"{net}: unknown part in {p}"
    used = [p for p in pins if p.split(".")[0] in ("J2", "J3") and p in HELTEC_GPIO]
    for p in used:
        assert HELTEC_GPIO[p] not in FORBIDDEN_GPIO, f"{p} is GPIO{HELTEC_GPIO[p]}, reserved on V4"
    gpio_of_net = {net: HELTEC_GPIO[p] for net, m in NETS.items() for p in m if p in HELTEC_GPIO}
    assert gpio_of_net == EXPECTED_GPIO, gpio_of_net
    assert HELTEC_5V_PIN not in pins, "Heltec 5V pin must not be connected"
    unused = [r for r in PARTS if not r.startswith("H") and not any(p.split(".")[0] == r for p in pins)]
    assert not unused, f"parts with no connections: {unused}"
    print(f"design ok: {len(PARTS)} parts, {len(NETS)} nets")


if __name__ == "__main__":
    check()
```

**Step 2:** Run `/usr/bin/python3 hardware/design.py`. Expected: `design ok: 49 parts, 27 nets`.

**Step 3:** Mutation check, done once by hand and not committed. Temporarily change `"R_SR.2", "J3.17"` to `"J3.16"`, run again, and expect `AssertionError: J3.16 is GPIO5, reserved on V4`. Then revert.

**Step 4:** Commit: `git commit -m "hardware: netlist source of truth with GPIO safety check"`

### Task A3: Generate the schematic (gen_sch.py) and pass ERC

**Files:**
- Create: `hardware/gen_sch.py`
- Generated: `hardware/carrier.kicad_sch`, `hardware/carrier.kicad_pro`

**Approach:** a label-per-pin schematic. Each symbol is placed on a grid, and every connected pin gets a short wire stub ending in a **global label** named after its net. KiCad connects same-named labels, so no wires need routing. Power nets (`GND`, `+3V3`, `+5V`) use labels too, plus one `power:PWR_FLAG` symbol each on `GND`, `+3V3`, `+5V` and `VBAT_SW`. The source pins are passive connector pins, so ERC needs the flags.

**Step 1: Write the generator.** Requirements:
1. `import design` for `PARTS` and `NETS`. Invert `NETS` to `pin -> net`.
2. For each unique symbol `lib:name`, read `/usr/share/kicad/symbols/<lib>.kicad_sym` and extract the `(symbol "name" ...)` S-expression. **Flatten `(extends "Base")`:** AO3400A and BSS138 extend `Q_NMOS_GSD`, SS34 extends `SB120`, and 1N4148W extends `1N4001`. Copy the base's graphics and pins and keep the derived symbol's properties. Rename the top-level symbol to `lib:name` inside `(lib_symbols ...)`. Rename sub-symbols to `name_0_1` etc. using the derived name.
3. Write a KiCad 9 schematic: `(kicad_sch (version 20250114) (generator "gen_sch") (uuid …) (paper "A3") (lib_symbols …) …)`. One `(symbol (lib_id "lib:name") (at x y 0) (unit 1) (property "Reference" ref) (property "Value" value) (property "Footprint" fp) (pin "N" (uuid …)) (instances (project "carrier" (path "/<root-uuid>" (reference ref) (unit 1)))))` per part. Place parts on a 25.4 mm grid in rows of 6 (Heltec headers first). *(As built: bounding-box packing, 10 per row on A3. A plain grid overlapped.)* Pin positions come from the symbol's `(pin … (at px py angle) (length L))`. The connection point is `(x+px, y-py)`, because symbol Y points up and schematic Y points down.
4. For every connected pin, add a `(wire (pts (xy …) (xy …)))` of 2.54 mm pointing away from the body along the pin's angle, and a `(global_label "NET" (shape passive) (at end angle) …)` at its end.
5. Put an explicit `(no_connect (at …))` on every unconnected pin of J2/J3, and on MT3608 pin 6 (NC).
7. Call `design.check()` at startup. Mark every ref in `design.DNP` as do-not-populate: in KiCad 9 that's the symbol attributes `(dnp yes)` and `(in_bom no)`. *(`exclude_from_bom` isn't a KiCad 9 token.)*
6. Write `carrier.kicad_pro` as minimal JSON with net classes. `Default` gets 0.25 mm track and 0.2 mm clearance. `Power` gets 0.8 mm track, 0.25 mm clearance and patterns `VBAT*`, `+5V`, `SW`, `GND`, via `net_settings.netclass_patterns`. The board rules are 0.2 mm minimum track and space, and 0.6/0.3 mm vias (JLCPCB standard).

**Step 2: Test with ERC.**

```bash
cd hardware && /usr/bin/python3 gen_sch.py && \
kicad-cli sch erc --severity-error --exit-code-violations -o /tmp/erc.rpt carrier.kicad_sch; echo exit=$?; cat /tmp/erc.rpt
```

Expected: `exit=0`. Iterate on the generator, not the output file, until ERC is clean. Typical first failures are "power input not driven" (a missing PWR_FLAG) and a pin not connected (a missed no-connect).

**Step 3: Parity test against design.py.**

```bash
kicad-cli sch export netlist --format kicadxml -o /tmp/carrier.xml carrier.kicad_sch
```

Add `check_netlist.py`: parse `/tmp/carrier.xml` (`<net name=…><node ref= pin=/>`) and assert that the set of `(net, ref.pin)` pairs equals the one built from `design.NETS`. KiCad prefixes global label nets with `/`, so strip it. Run it and expect `netlist matches design.py`.

**Step 4: Human-readable export.** Run `kicad-cli sch export pdf -o fab/schematic.pdf carrier.kicad_sch` and open it to check that labels are readable and nothing overlaps badly.

**Step 5:** Commit the generator, `check_netlist.py` and the generated files: `git commit -m "hardware: generated schematic, ERC clean, parity with design.py"`

### Task A4: Generate the board (gen_pcb.py): outline, placement, nets

**Files:**
- Create: `hardware/gen_pcb.py`
- Generated: `hardware/carrier.kicad_pcb`

**Board geometry.** Origin at top-left, X right, Y down, units mm.
- **Outline** 90 x 60 on `Edge.Cuts`, with corner radius 2.
- **Mounting holes** H1–H4 at (3.5, 3.5), (86.5, 3.5), (3.5, 56.5), (86.5, 56.5).
- **Heltec:** the antenna end overhangs the right edge, and USB-C faces left (-X). Pin 1 of both headers is at the USB end. J3 (GPIO1–7 side) is the **top** row, J2 (the 5V/GND side) the bottom row.
  - J3: pin 1 at (44.82, 27.00), running +X at 2.54 mm pitch to pin 18 at (88.00, 27.00).
  - J2: pin 1 at (44.82, 49.86), pin 18 at (88.00, 49.86). The rows are 22.86 mm apart, measured from Heltec's STEP model.
  - Rotate the PinSocket footprints so pin 1 sits at the USB end and the pins run along +X. In KiCad 9, `PinSocket_1x18` pins run +Y from pin 1 at rotation 0, so use -90°. Check pin 18's position after placing. *(As built: **+90°** is correct; -90° puts pin 18 at x = 1.64. `gen_pcb.py` asserts pads 1 and 18.)*
- **Keep-outs:**
  - *(As built: HELTEC_UNDER covers only the gap **between** the socket rows, y ≈ 28.9–48.0, because the full body area would contain the sockets themselves. ANT runs x 89.1–90 and forbids only tracks, vias and pour, because pads are at x = 88.)*
  - Rule area "HELTEC_UNDER" covering the Heltec body (x 42.7–90, y 25.7–51.2) on both copper layers: **no footprints**, tracks allowed. The battery socket on the Heltec's underside needs the space.
  - Rule area "ANT" at x 86–90, y 20–57: no copper at all, pour included. The antenna overhangs just beyond it.
- **Initial placement** (the executor may nudge parts for routability; keep the grouping). **Take reference names from `design.PARTS`:** since commit 99a9704 every ref ends in a digit (J_BAT → J_BAT1, Q_LR → Q_LR1, …), and the names in this table are the old ones.

| Group | Parts | Area (x, y) |
|---|---|---|
| Connectors, top edge, row y = 7, openings facing up | J_BAT 10, J_KEY 19, J_HBAT 28, J_LCD 40, J_NFC 54, J_BTN_R 68 | left to right |
| Connectors, left edge, x = 6, rotated 90° | J_BTN_B y = 30, J_BUZ y = 44 | |
| Power | F1, U1, L1, D1, R_FB1/2, C_IN, C_OUT1/2, C_BULK | x 8–38, y 14–24 |
| Level shifter + NFC cap | Q_SDA/SCL, R_SDA3/5, R_SCL3/5, C_NFC | x 40–60, y 13–22 |
| Drivers | Q_*, R_G*, R_PD*, R_L*, D_FLY | x 12–40, y 28–40 |
| Button RC | R_PU*, R_S*, C_B* | x 12–40, y 42–55 |

*(As built after all connectors became 4-pin XH, 2026-09-30: a 4-pin XH courtyard is 13.5 mm, so only five fit on the top edge between H1 and H2. Top: J_BAT1 10, J_KEY1 24.5, J_HBAT1 39, J_LCD1 53.5, J_NFC1 68. J_BTN_R1 moved to the bottom edge under the J2 row at (76, 55.75), rotated 180°, and its RC stays near U2. Left edge: J_SPK1 y 20.5, J_BTN_B1 35, J_BUZ1 49.5. F1 moved to (19.5, 11.3), between the BAT and KEY labels. `gen_pcb.py` `PLACE` is authoritative.)*

**Step 1: Write the generator.** Requirements:
1. `import design`. Create `pcbnew.BOARD()`, set design rules (0.2 mm clearance and track, 0.6/0.3 mm via) and a 2-layer stack.
2. Create one `NETINFO_ITEM` per net in `design.NETS` and add it to the board.
3. For each part: `pcbnew.FootprintLoad("/usr/share/kicad/footprints/<lib>.pretty", name)`, then set the reference and value, position and rotation, and **set each pad's net** from `design.NETS` (`pad.SetNet(netinfo)`). Pads not in any net stay unconnected.
4. Add Edge.Cuts `PCB_SHAPE` segments and arcs, the two rule areas (`ZONE` with `SetIsRuleArea(True)` and the appropriate `SetDoNotAllow*`), and a `GND` zone on B.Cu covering the whole board (priority 0, 0.3 mm clearance, thermal reliefs). Leave it unfilled; A6 fills it after routing.
5. Silkscreen text next to every connector with the pin names from design.md part 2, pin 1 first, e.g. `BTN_R: SW GND L+ L-`. Add `AirsoftCounter v2 carrier` and the date near the bottom-left.
6. `pcbnew.SaveBoard("carrier.kicad_pcb", board)`.

*(As built: KiCad 9 drops **all** net classes from `.kicad_pro` unless each has a `"priority"`. Design rules live only in `carrier.kicad_pro`, which `gen_sch.py` writes, because a `.kicad_pcb` can't hold them. `gen_pcb.py` saves with `aSkipSettings=True` and `verify()` asserts the rules after reloading.)*

**Step 2: Parity test.**

```bash
cd hardware && /usr/bin/python3 gen_pcb.py && \
kicad-cli pcb drc --schematic-parity --severity-error -o /tmp/drc.rpt carrier.kicad_pcb; grep -E "violations|unconnected|parity" /tmp/drc.rpt | head
```

Expected: **0 schematic parity issues** and 0 footprint courtyard overlaps. Unconnected items are expected, since the board isn't routed yet.

**Step 3: Visual check.** Run `kicad-cli pcb render --side top -o fab/placed_top.png carrier.kicad_pcb` and look at the PNG. Check connector orientation and that nothing sits under the Heltec, then adjust the placement table in `gen_pcb.py` if needed.

**Step 4:** Commit: `git commit -m "hardware: generated placed board, parity clean"`

### Task A5: 1:1 footprint check against the real Heltec (HUMAN CHECKPOINT)

**Step 1:** `kicad-cli pcb export pdf --layers F.Cu,F.SilkS,Edge.Cuts --scale 1 -o fab/print_1to1.pdf carrier.kicad_pcb`

**Step 2:** Ask the user to print it at 100% (no "fit to page"), check that a 10 mm reference line measures 10 mm, and push a real Heltec V4's header pins through the paper at J2/J3. Also confirm **orientation**: pin 1 (GND on both headers) must be at the USB-C end, and J3 (GPIO1–7 side) on the top row. A mirrored or reversed Heltec would put GND/3V3 on GPIO pins.

**Step 3:** If the pins don't line up, fix the J2/J3 coordinates in `gen_pcb.py`, regenerate and reprint. **Don't continue to routing until the user confirms the fit.**

### Task A6: Autoroute (route.py) and pass full DRC

**Files:**
- Create: `hardware/route.py`

**Step 1: Write route.py.** Requirements:
1. Load `carrier.kicad_pcb` and call `pcbnew.ExportSpecctraDSN(board, "/tmp/carrier.dsn")`.
2. Run `java -jar tools/freerouting-2.4.1.jar -de /tmp/carrier.dsn -do /tmp/carrier.ses -mp 100 <headless flags from A1>` with `subprocess.run(check=True)`.
3. Reload the board, call `pcbnew.ImportSpecctraSES(board, "/tmp/carrier.ses")`, then add a GND zone on F.Cu too (same outline, lower priority than tracks) and fill all zones with `pcbnew.ZONE_FILLER(board).Fill(board.Zones())`. Save.
4. *(From the A4 review's trial route.)*
   - Load `hardware/carrier.kicad_pcb` **in place**, with `carrier.kicad_pro` beside it. A copy without the `.kicad_pro` silently loses its net classes, which gave 44 DRC violations.
   - Call `gen_pcb.verify()`, or the same net-class asserts, right after `LoadBoard`.
   - Call `pcbnew.KIID.SeedGenerator(...)` before the SES import, so the routed board is byte-stable.
   - Use `gen_pcb.GND_PAD_CONNECTION` (solid) for the F.Cu pour; thermal reliefs gave starved_thermal errors.
   - In the trial, Freerouting was deterministic and routed everything: 0 unrouted, 0 violations. Pre-routing the boost loop was unnecessary once A4 mirrored the boost block.

**Step 2: Full DRC as the test.**

```bash
cd hardware && /usr/bin/python3 route.py && \
kicad-cli pcb drc --schematic-parity --severity-error --exit-code-violations -o /tmp/drc.rpt carrier.kicad_pcb; echo exit=$?; grep -iE "unconnected|violations" /tmp/drc.rpt
```

Expected: `exit=0`, **0 violations and 0 unconnected items**.
- If Freerouting leaves nets unrouted, increase `-mp`, then nudge placement in `gen_pcb.py` and re-run A4 → A6.
- Never hand-edit the routed `.kicad_pcb`: every fix goes through the generators so the board stays reproducible.

**Step 3: Review the power routing.** Render the top and bottom (`kicad-cli pcb render --side top/bottom`) and check:
- The MT3608 loop (C_IN → U1 → L1 → D1 → C_OUT) is short and all on one layer.
- VBAT/+5V tracks use the 0.8 mm Power class.
- No tracks cross the ANT area.

If the autorouter made the switching loop long, pre-route it in `gen_pcb.py` as fixed tracks (they go into the DSN as `wire (type protect)`) and re-route the rest.

**Step 4:** Commit: `git commit -m "hardware: autorouted board, DRC clean"`

### Task A7: Fab outputs + Makefile

**Files:**
- Create: `hardware/Makefile`

**Step 1: Makefile.**

```make
PY=/usr/bin/python3
.PHONY: all sch pcb route check fab
all: check fab
sch:   ; $(PY) design.py && $(PY) gen_sch.py && kicad-cli sch export netlist --format kicadxml -o /tmp/carrier.xml carrier.kicad_sch && $(PY) check_netlist.py
pcb: sch ; $(PY) gen_pcb.py
route: pcb ; $(PY) route.py
check: route
	kicad-cli sch erc --severity-error --exit-code-violations -o /tmp/erc.rpt carrier.kicad_sch
	kicad-cli pcb drc --schematic-parity --severity-error --exit-code-violations -o /tmp/drc.rpt carrier.kicad_pcb
fab: check
	mkdir -p fab/gerbers
	kicad-cli pcb export gerbers -o fab/gerbers/ carrier.kicad_pcb
	kicad-cli pcb export drill -o fab/gerbers/ carrier.kicad_pcb
	cd fab && zip -jq carrier_gerbers.zip gerbers/*
	kicad-cli sch export bom --fields "Reference,Value,Footprint,\$${QUANTITY}" --group-by Value,Footprint -o fab/bom.csv carrier.kicad_sch
	kicad-cli sch export pdf -o fab/schematic.pdf carrier.kicad_sch
	kicad-cli pcb render --side top -o fab/top.png carrier.kicad_pcb
	kicad-cli pcb render --side bottom -o fab/bottom.png carrier.kicad_pcb
```

**Step 2:** Run `cd hardware && rtk make all`. Expected: exits 0, and `fab/` contains `carrier_gerbers_jlcpcb.zip`, `bom.csv`, `schematic.pdf`, `top.png` and `bottom.png`.

**Step 3:** Check that `fab/bom.csv` does **not** list R_SDA5/R_SCL5, because they are excluded from the BOM through `design.DNP`. Also check that the schematic PDF shows them as DNP.

**Step 4:** Commit: `git commit -m "hardware: reproducible build and fab outputs"`

### Task A8: Order (HUMAN CHECKPOINT)

**Step 1:** Show the user `fab/top.png`, `fab/bottom.png`, `fab/schematic.pdf` and the BOM.

**Step 2:** Once they approve, they upload `fab/carrier_gerbers_jlcpcb.zip` to JLCPCB (2 layers, 1.6 mm, HASL, any colour, 5 pcs). Parts come from TME or LCSC following `bom.csv`, plus the off-board parts listed in design part 3 and part 5. **Ordering is the user's action.** Don't place orders.

### Task A9: JLCPCB assembly package (PCBA, SMD + THT)

*(Added 2026-09-29 at the user's request: full assembly, including through-hole parts.)*

**Files:**
- Modify: `hardware/design.py`: add an `LCSC` map from `(value, footprint)` to an LCSC part number. `check()` asserts that every part except DNP parts and mounting holes has one.
- Create: `hardware/jlc.py`, which writes `fab/jlc_bom.csv` (Comment, Designator, Footprint, LCSC Part #) from `design.py`, and `fab/jlc_cpl.csv` (Designator, Mid X, Mid Y, Layer, Rotation) from `kicad-cli pcb export pos --format csv --units mm`. It includes a per-footprint rotation-correction table.
- Modify: `hardware/Makefile` (the fab target runs `jlc.py`) and `fab/ORDERING.md` (an assembly section).

**Steps:**
1. Research the parts. For each BOM line, find an in-stock LCSC part in the JLCPCB library whose package matches our footprint, and **verify the part number from a live source**, never from memory. Prefer Basic parts over Extended. Record the sources in the commit message or a comment.
2. Write a failing `check()` test: a part with no LCSC entry must fail. Add the map and make it pass.
3. Write `jlc.py` and add it to `make fab`. Validate that every non-DNP footprint appears in the CPL exactly once, that the CPL designators equal the BOM designators, and that the coordinates are inside 90 × 60 mm.
4. Rotations: start with a correction of 0 everywhere. Research the known KiCad → JLCPCB offsets for our footprints (SOT-23, SOT-23-6, SMA, SOD-123, CP_Radial, JST-XH, PinSocket). Apply them only if a source confirms them, and list in `ORDERING.md` the parts the user must check in JLCPCB's placement preview.
5. `ORDERING.md` assembly section: which files to upload, which JLCPCB assembly service supports THT, top-side assembly, and which parts to check in the preview. No prices.
6. Commit: "hardware: JLCPCB assembly BOM + CPL".

*As built (2026-09-29):* `jlc.py` has no rotation-correction table. Sources disagree on SOT-23 (180° or −90°), and JLC's engineers correct rotation from the silkscreen polarity marks, so `ORDERING.md` lists the parts to check in the preview instead. The CPL comes from pcbnew alone, not from `kicad-cli pcb export pos`: pcbnew gives the reference, rotation (normalised to 0–360) and side, with the coordinates in the Gerber convention (board Y negated). Checked against the pos file, all 43 parts matched. Mid X/Y is the centre of the F.CrtYd courtyard, not the footprint anchor. The THT footprints are anchored on pin 1, which would put J2/J3 21.6 mm off, and the pad centre would still leave the JST-XH bodies 0.525 mm off. The red step of step 2 is the `check()` assertion in `design.py` (an empty `LCSC` failed for all 43 assembled parts). There is no separate test file. The 10 V capacitor values became the ratings of the parts picked: 22uF 25V, 220uF 16V, 100uF 25V.

### Task A10: Speaker (I2S amp), I2C GPIO expander, Basic bulk caps

*(Added 2026-09-29. Design doc Part 6.)* Parts were verified live against the complete
JLCPCB Basic and Preferred libraries.

**Netlist changes (`hardware/design.py`), with everything regenerated through `make all`:**
- New U2 **TCA9534PWR** (C783615, TSSOP-16) on +3V3, address **0x20** (A0–A2 to GND),
  100 nF (C49678) decoupling. INT goes to **GPIO6** (J3.17) with a 10k (C17414) pull-up
  to +3V3.
  - P0 = BTN_R_IN and P1 = BTN_B_IN, each after the existing 1k series resistor with its
    10k/100nF RC.
  - P2/P3/P4 drive the existing LED_R/LED_B/BUZ gate resistors.
  - P5 = AMP_SD.
  - P6/P7 are unconnected.
- *(Superseded 2026-09-30: U3 is now an NS4168, C910588, eSOP-8. CTRL high = **right** I2S slot, so the
  firmware (C7) must send audio in the right slot or both; hold CTRL low between clips (13 mA when on).
  See `hardware/fab/PART_ALTERNATIVES.md`.)*
- New U3 **MAX98357AETE+T** (C910544, TQFN-16-EP 3x3), VDD on **VBAT_SW**, with 22 µF
  (C12891) + 100 nF (C49678) at VDD.
  - DIN = **GPIO21** (J2.16), BCLK = **GPIO47** (J2.13), LRCLK = **GPIO48** (J2.14).
  - GAIN_SLOT tied to GND (12 dB). SD_MODE = AMP_SD (a 3.3 V high selects the left
    channel, low is shutdown).
  - EP and all GND pins to GND with thermal vias. OUTP/OUTN go to new **J_SPK**
    (B2B-XH, C158012). Silkscreen: `SPK (BTL, not GND)`.
- Remove the old direct GPIO nets (buttons on GPIO6/44, LEDs on 47/48, buzzer on 21).
  GPIO44 and GPIO43 are left unconnected. Update `EXPECTED_GPIO`.
- Bulk caps:
  - C_BULK1 (220 µF THT) becomes 2x **47 µF 10 V 1206 C96123** (C_BULK1, C_BULK2) on
    VBAT_SW.
  - C_NFC1 (100 µF THT) becomes **100 µF 6.3 V 1206 C15008** on +3V3.
- F1 becomes **2 A hold 1206L200/16NR C22374899** (same 1206 footprint).
- MT3608, L1 (Bourns), connectors and sockets are unchanged.

**Steps:**
1. `check()` first: update the expected GPIO map and add the new parts' LCSC entries.
   Check that `check()` fails on the old map, then passes.
2. `gen_pcb.py` PLACE: put the amp near J_SPK and VBAT_SW with short OUTP/OUTN, and the
   expander near J3 and the button RCs. Keep the boost loop untouched.
3. `make all`: ERC/DRC/parity must be clean, the autoroute complete, gerbers ok, jlc ok.
4. Update `ORDERING.md` (Extended list, speaker note) and the renders.
5. Commit: "hardware: I2S speaker amp, TCA9534 expander, ceramic bulk caps".

*As built (2026-09-29):* 58 parts, 35 nets, 23 JLC BOM lines (8 Extended, 2 Preferred, 13 Basic), 52 placements. ERC 0/0 and DRC 0/0/0 at all severities, parity clean, Freerouting 0 unrouted, and two full `make all` runs give the same board. The red step of step 1 was `check()` with the new `EXPECTED_GPIO` against the old netlist. All new LCSC numbers were checked live (type and stock) on 2026-09-29. Deviations:
- Net names: `EXP_INT` (GPIO6), `I2S_BCLK`/`I2S_LRCLK`/`I2S_DIN` (47/48/21), `AMP_SD`, `SPK_P`/`SPK_N`. Decoupling and pull-up refs: C_EXP1, R_INT1, C_AMP1 (22 µF), C_AMP2 (100 nF).
- **R_SD1 (1k, reuses C17513) in series with SD_MODE** (`AMP_SD` → `AMP_SD_R`). SD_MODE's absolute maximum is VDD + 0.3 V, and the datasheet asks for about 2k in series when a 3.3 V logic high meets VDD below about 3 V (VBAT_SW sagging). 1k keeps SD_MODE above the 1.4 V left-channel threshold against the internal 100k pull-down. The TCA9534 has no internal pull-ups (datasheet), so at power-up the 100k gate pull-downs keep the LED/buzzer drivers off and the internal pull-down keeps the amp in shutdown.
- **J_SPK1 pin 1 is OUT-** (silkscreen `SPK (BTL, not GND)` / `OUT- OUT+`). With U3 at 180°, its OUTP pad sits above OUTN, and the connector's pin 2 is the upper one, so this avoids a crossing. The speaker traces are 9.4 mm (OUT+) and 8.5 mm (OUT-), F.Cu, no vias.
- **LED resistors R_LLR1/R_LLB1 are 0R (C17477, Basic)**, because the ONPOW LAS1-AGQ-11E/x/6V buttons have a built-in LED resistor. The footprints stay as a brightness knob and the 150R part (C17471) is gone.
- U3 uses the ThermalVias footprint, but its 0.2 mm via drills are below the 0.3 mm board minimum (and JLCPCB's standard 2-layer via). `gen_pcb.py` widens them to 0.3/0.6 mm, and `carrier.kicad_pro` ignores `lib_footprint_mismatch`: every footprint is loaded fresh from the library, so that deliberate change is the only possible mismatch. The EP (pin 17, typed Unspecified) goes to GND. The project ERC pin map treats Unspecified like Passive (it is the design's only Unspecified pin), otherwise ERC warns.
- **Net classes:** GND left the Power class (it's now Default, 0.25 mm), and Power's clearance went from 0.25 to 0.2 mm. A 0.8 mm GND track couldn't reach U3.11 (between OUTN and a NC pin at 0.5 mm pitch) or U2's A0–A2. The TSSOP/TQFN pad gaps are exactly 0.25 mm, so VBAT_SW could only neck down into U3's VDD pads at 0.2 mm. Both copper layers are solid GND pours, and Freerouting ran every U3 GND pin into the exposed pad. The SPK nets stay Default too (0.25 mm): a 0.5 mm track can't enter a 0.25 mm pad at 0.5 mm pitch. That's fine for about 1 A peaks over 9 mm.
- **Board minimum track width is 0.15 mm (it was 0.2 mm).** Freerouting necks GND to 0.187 mm into the U1/U2/U3 pads, and `--router.neck_width_um` / `automatic_neckdown=false` don't change that. JLCPCB's 2-layer minimum is 0.127 mm.
- Placement: J_SPK1 is on the left edge at y 20.75, and J_BTN_B1 moved down to y 35 to make room for the silkscreen labels. U3 and its caps sit in the old C_BULK1 spot, beside J_SPK1, with F1 moved up to y 11.3. C_BULK1/C_BULK2 are between C_IN1 and the level shifter, on VBAT_SW. U2 is at (60.2, 21) between the level shifter and the BTN_R RC, with C_EXP1, R_INT1 and R_SD1 around it. The boost block is unchanged. The I2S traces run 75–91 mm from J2 to U3, partly on B.Cu, and each line crosses about 5 traces on the other layer (LED_B_G, BUZ_K, +3V3, BTN_B_IN, and the other I2S lines), so its return path through the pours is broken there. The review fix below adds stitching vias along that corridor.
- **Review fix: GND vias and routing.** `gen_pcb.py` places locked GND vias (0.6/0.3 mm), each tied with a locked 0.5 mm F.Cu stub: at C_AMP1.2 (18.0, 14.2) and at C_AMP2.2 (17.5, 18.4). Before, Freerouting had cut the F.Cu pour around U3 into an island, so C_AMP2's return ran more than 20 mm. Now it goes C_AMP2.2 → 1.3 mm stub → via → B.Cu pour → U3's exposed-pad vias, 4.6 mm away. Three untied stitching vias sit along the I2S corridor, at (21.4, 28.3), (29.0, 43.6) and (37.2, 45.5), about 0.6 mm from the I2S lines at the BTN_B_IN crossings and about 2.9 mm at the LED_B_G crossings. `route.py` keeps locked tracks and vias, and refuses only unlocked ones. It also strips KiCad's `(plane GND …)` from the DSN. With the plane in place, Freerouting counted every THT GND pin and via as connected through an ideal B.Cu plane and never routed them, while its own B.Cu traces cut that pour: J3.1 ended up on an island on both layers, and extra vias only moved the problem around. GND is now routed like any other net (290 mm of GND track), so the pours can only add connections. This routing has no neck below 0.25 mm. The 0.15 mm rule stays as margin, because earlier routings of this board did neck down. ERC and DRC in the Makefile now run with `--severity-all`.
- The THT electrolytics are gone, so the smallest plated component hole is now 0.95 mm, and `check_gerbers.py` still passes.

**Firmware follow-up (update C2/C4 when reached):** buttons, LEDs and the buzzer go
through a TCA9534 driver (write 0 to the output register before setting pins as
outputs; set the unused P6/P7 as outputs driven low; button presses via INT on GPIO6). New audio milestone: I2S TX DMA on
47/48/21, AMP_SD via the expander, clips in flash. **Low-battery brownout risk:** the amp runs straight off VBAT_SW, so audio peaks plus LoRa TX on a low cell can pull the Heltec below its brownout level. Cap the volume by battery voltage, and don't play (or duck) audio during LoRa TX when the battery is low.

---

## Phase B: firmware/core (host-tested game logic)

### Task B1: Crate scaffold

**Files:**
- Create: `firmware/core/Cargo.toml`, `firmware/core/src/lib.rs`

**Step 1:**

```toml
[package]
name = "asg-core"
version = "0.1.0"
edition = "2021"

[dependencies]
heapless = "0.9"
```

```rust
#![no_std]
pub mod card;
pub mod game;
```

Create empty `src/game.rs` and `src/card.rs`.

**Step 2:** Run `cd firmware/core && rtk cargo build`. Expected: builds.

**Step 3:** Commit: `git commit -m "firmware: core crate scaffold"`

### Task B2: Game rules, test-first

Port of `src/state/*.cpp`, with two deliberate fixes:
- Mining now lasts exactly `mining_time_s`. The old code ran one extra second after showing 00:00.
- Captures count on a button **press** (edge), not while it's held. The edge detection is in `device`; the core API is already event-based.

**Files:**
- Create: `firmware/core/src/game.rs`

**Step 1: Write the failing tests first.** Paste the `#[cfg(test)] mod tests` block from the listing below into `game.rs`, with only the type and function signatures stubbed as `todo!()`.

**Step 2:** Run `rtk cargo test`. Expected: FAIL (the tests panic at `todo!()`).

**Step 3:** Implement. Final content of `game.rs` (verified: 8 tests pass, clippy clean):

> **Note (post-review, commit f4b781d):** `firmware/core/src/*.rs` are now the authority. The listing below has a bug: counts of 1000 overflow the 20-character line and disappear. The committed code fixes it with `{:<16}{:>4}`, makes the fields private behind getters (`phase()`, `score()`, `left()`), and has 16 tests.

```rust
//! Airsoftcoin game rules, ported from the Arduino state machine.
//! Pure logic: time comes in as milliseconds, effects go out as return values.

use core::fmt::Write;
use heapless::String;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Team {
    Red,
    Blue,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Config {
    pub mining_time_s: u16,
    pub block_size: u16,
}

impl Default for Config {
    fn default() -> Self {
        Self { mining_time_s: 5, block_size: 3 }
    }
}

impl Config {
    /// Limits from the original IR config menu.
    pub fn clamped(self) -> Self {
        Self {
            mining_time_s: self.mining_time_s.clamp(5, 30000),
            block_size: self.block_size.clamp(1, 1000),
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Leds {
    Blink,
    On,
    Off,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Beep {
    pub on_ms: u16,
    pub off_ms: u16,
    pub times: u8,
}

pub const READY_BEEP: Beep = Beep { on_ms: 200, off_ms: 100, times: 3 };
pub const MINED_BEEP: Beep = Beep { on_ms: 200, off_ms: 200, times: 5 };

const INTRO_MS: u64 = 3000;
const READY_BEEP_EVERY_MS: u64 = 15000;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Phase {
    Intro { until: u64 },
    Ready { next_beep: u64 },
    Mining { left_s: u16, next_tick: u64 },
    Depleted { since: u64 },
}

pub struct Game {
    pub phase: Phase,
    pub red: u16,
    pub blue: u16,
    pub left: u16,
    cfg: Config,
}

impl Game {
    pub fn new(cfg: Config, now: u64) -> Self {
        let cfg = cfg.clamped();
        Self { phase: Phase::Intro { until: now + INTRO_MS }, red: 0, blue: 0, left: cfg.block_size, cfg }
    }

    /// Advance time. Returns a beep pattern to play, if any.
    pub fn tick(&mut self, now: u64) -> Option<Beep> {
        match self.phase {
            Phase::Intro { until } if now >= until => {
                self.phase = Phase::Ready { next_beep: now + READY_BEEP_EVERY_MS };
                None
            }
            Phase::Ready { next_beep } if now >= next_beep => {
                self.phase = Phase::Ready { next_beep: next_beep + READY_BEEP_EVERY_MS };
                Some(READY_BEEP)
            }
            Phase::Mining { mut left_s, mut next_tick } if now >= next_tick => {
                while now >= next_tick && left_s > 0 {
                    left_s -= 1;
                    next_tick += 1000;
                }
                if left_s == 0 {
                    self.phase = Phase::Ready { next_beep: now + READY_BEEP_EVERY_MS };
                    return Some(MINED_BEEP);
                }
                self.phase = Phase::Mining { left_s, next_tick };
                None
            }
            _ => None,
        }
    }

    /// A team captured the coin (button or player card). Returns true if it counted.
    pub fn capture(&mut self, team: Team, now: u64) -> bool {
        if !matches!(self.phase, Phase::Ready { .. }) {
            return false;
        }
        match team {
            Team::Red => self.red += 1,
            Team::Blue => self.blue += 1,
        }
        self.left -= 1;
        self.phase = if self.left == 0 {
            Phase::Depleted { since: now }
        } else {
            Phase::Mining { left_s: self.cfg.mining_time_s, next_tick: now + 1000 }
        };
        true
    }

    pub fn leds(&self) -> Leds {
        match self.phase {
            Phase::Intro { .. } => Leds::Blink,
            Phase::Ready { .. } => Leds::On,
            Phase::Mining { .. } | Phase::Depleted { .. } => Leds::Off,
        }
    }

    /// LCD backlight: blinks once per second when the point is depleted.
    pub fn backlight(&self, now: u64) -> bool {
        match self.phase {
            Phase::Depleted { since } => ((now - since) / 1000).is_multiple_of(2),
            _ => true,
        }
    }

    /// The four 20-character LCD lines.
    pub fn lines(&self) -> [String<20>; 4] {
        let mut l: [String<20>; 4] = Default::default();
        // Writes cannot fail: every line is at most 20 chars.
        let _ = write!(l[0], "{:<17}{:>3}", "Czerwoni", self.red);
        let _ = write!(l[1], "{:<17}{:>3}", "Niebiescy", self.blue);
        let _ = match self.phase {
            Phase::Intro { .. } => write!(l[2], "Tryb Airsoftcoin"),
            Phase::Ready { .. } => write!(l[2], "GOTOWY"),
            Phase::Mining { left_s, .. } => write!(l[2], "Kopanie {:02}:{:02}", left_s / 60, left_s % 60),
            Phase::Depleted { .. } => write!(l[2], "PUNKT WYCZERPANY"),
        };
        let _ = write!(l[3], "{:<17}{:>3}", "Pozostalo", self.left);
        l
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn ready_game(cfg: Config) -> Game {
        let mut g = Game::new(cfg, 0);
        assert_eq!(g.tick(3000), None);
        g
    }

    #[test]
    fn intro_lasts_three_seconds_with_blinking_leds() {
        let mut g = Game::new(Config::default(), 0);
        assert_eq!(g.leds(), Leds::Blink);
        g.tick(2999);
        assert!(matches!(g.phase, Phase::Intro { .. }));
        g.tick(3000);
        assert!(matches!(g.phase, Phase::Ready { .. }));
        assert_eq!(g.leds(), Leds::On);
    }

    #[test]
    fn ready_beeps_every_15_seconds() {
        let mut g = ready_game(Config::default());
        assert_eq!(g.tick(17999), None);
        assert_eq!(g.tick(18000), Some(READY_BEEP));
        assert_eq!(g.tick(18001), None);
        assert_eq!(g.tick(33000), Some(READY_BEEP));
    }

    #[test]
    fn capture_only_counts_when_ready() {
        let mut g = Game::new(Config::default(), 0);
        assert!(!g.capture(Team::Red, 100));
        g.tick(3000);
        assert!(g.capture(Team::Red, 3100));
        assert!(!g.capture(Team::Blue, 3200)); // mining now
        assert_eq!((g.red, g.blue, g.left), (1, 0, 2));
    }

    #[test]
    fn mining_counts_down_then_beeps_and_is_ready_again() {
        let mut g = ready_game(Config { mining_time_s: 5, block_size: 3 });
        g.capture(Team::Blue, 10_000);
        assert_eq!(g.leds(), Leds::Off);
        assert_eq!(g.tick(11_000), None);
        assert!(matches!(g.phase, Phase::Mining { left_s: 4, .. }));
        assert_eq!(g.tick(14_999), None);
        assert_eq!(g.tick(15_000), Some(MINED_BEEP));
        assert!(matches!(g.phase, Phase::Ready { .. }));
    }

    #[test]
    fn late_tick_catches_up() {
        let mut g = ready_game(Config { mining_time_s: 5, block_size: 3 });
        g.capture(Team::Blue, 10_000);
        assert_eq!(g.tick(13_500), None);
        assert!(matches!(g.phase, Phase::Mining { left_s: 2, next_tick: 14_000 }));
    }

    #[test]
    fn last_capture_depletes_the_point_and_blinks_backlight() {
        let mut g = ready_game(Config { mining_time_s: 5, block_size: 1 });
        assert!(g.capture(Team::Red, 5000));
        assert!(matches!(g.phase, Phase::Depleted { .. }));
        assert_eq!(g.tick(60_000), None);
        assert!(g.backlight(5500));
        assert!(!g.backlight(6500));
        assert!(g.backlight(7500));
    }

    #[test]
    fn config_is_clamped() {
        let g = Game::new(Config { mining_time_s: 1, block_size: 0 }, 0);
        assert_eq!(g.left, 1);
        assert_eq!(Config { mining_time_s: 60000, block_size: 5000 }.clamped(), Config { mining_time_s: 30000, block_size: 1000 });
    }

    #[test]
    fn lines_fit_the_20x4_lcd() {
        let mut g = ready_game(Config { mining_time_s: 30000, block_size: 1000 });
        g.capture(Team::Red, 4000);
        let l = g.lines();
        assert_eq!(l[0].as_str(), "Czerwoni           1");
        assert_eq!(l[2].as_str(), "Kopanie 500:00");
        assert_eq!(l[3].as_str(), "Pozostalo        999");
        assert!(l.iter().all(|s| s.len() <= 20));
    }
}
```

**Step 4:** Run `rtk cargo test && rtk cargo clippy --all-targets -- -D warnings`. Expected: all pass, no warnings.

**Step 5:** Commit: `git commit -m "core: Airsoftcoin game rules with tests"`

### Task B3: Player card parser, test-first

**Files:**
- Create: `firmware/core/src/card.rs`

**Step 1:** Write the tests first (the `mod tests` block below) with `parse_player_card` stubbed. Run them and expect FAIL.

**Step 2:** Implement. Final content (verified: 3 tests pass):

```rust
//! Player card format: NTAG21x with one NDEF text record `ASG1:<R|B>:<id>`.
//! Input is the tag memory starting at page 4 (the first user page).

use crate::game::Team;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct PlayerCard {
    pub team: Team,
    pub id: u16,
}

pub fn parse_player_card(mem: &[u8]) -> Option<PlayerCard> {
    parse_text(ndef_message(mem)?)
        .and_then(|t| core::str::from_utf8(t).ok())
        .and_then(parse_asg)
}

/// Walk the TLV blocks and return the NDEF message body.
fn ndef_message(mem: &[u8]) -> Option<&[u8]> {
    let mut i = 0;
    while i < mem.len() {
        match mem[i] {
            0x00 => i += 1,       // NULL TLV
            0xFE => return None,  // terminator before any NDEF TLV
            tag => {
                let (len, hdr) = match *mem.get(i + 1)? {
                    0xFF => (u16::from_be_bytes([*mem.get(i + 2)?, *mem.get(i + 3)?]) as usize, 4),
                    l => (l as usize, 2),
                };
                let body = mem.get(i + hdr..i + hdr + len)?;
                if tag == 0x03 {
                    return Some(body);
                }
                i += hdr + len; // lock / memory control / proprietary TLVs
            }
        }
    }
    None
}

/// First record must be a short well-known "T" (text) record.
fn parse_text(msg: &[u8]) -> Option<&[u8]> {
    let [header, type_len, payload_len, rest @ ..] = msg else { return None };
    let short = header & 0x10 != 0;
    let well_known = header & 0x07 == 0x01;
    let has_id = header & 0x08 != 0;
    if !short || !well_known || has_id || *type_len != 1 || rest.first() != Some(&b'T') {
        return None;
    }
    let payload = rest.get(1..1 + *payload_len as usize)?;
    let lang_len = (*payload.first()? & 0x3F) as usize;
    payload.get(1 + lang_len..)
}

fn parse_asg(text: &str) -> Option<PlayerCard> {
    let mut parts = text.trim().split(':');
    if parts.next()? != "ASG1" {
        return None;
    }
    let team = match parts.next()? {
        "R" => Team::Red,
        "B" => Team::Blue,
        _ => return None,
    };
    let id: u16 = parts.next()?.parse().ok()?;
    if parts.next().is_some() || !(1..=999).contains(&id) {
        return None;
    }
    Some(PlayerCard { team, id })
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Tag memory as a phone NFC app writes it: NDEF TLV, text record, terminator.
    fn tag(text: &str) -> heapless::Vec<u8, 64> {
        let mut v = heapless::Vec::new();
        let payload_len = 3 + text.len() as u8; // status byte + "en" + text
        v.extend_from_slice(&[0x03, 4 + payload_len, 0xD1, 0x01, payload_len, b'T', 0x02, b'e', b'n']).unwrap();
        v.extend_from_slice(text.as_bytes()).unwrap();
        v.push(0xFE).unwrap();
        v
    }

    #[test]
    fn parses_red_and_blue_cards() {
        assert_eq!(parse_player_card(&tag("ASG1:R:017")), Some(PlayerCard { team: Team::Red, id: 17 }));
        assert_eq!(parse_player_card(&tag("ASG1:B:999")), Some(PlayerCard { team: Team::Blue, id: 999 }));
    }

    #[test]
    fn skips_lock_control_tlv() {
        let mut mem: heapless::Vec<u8, 64> = heapless::Vec::new();
        mem.extend_from_slice(&[0x01, 0x03, 0xA0, 0x10, 0x44]).unwrap();
        mem.extend_from_slice(&tag("ASG1:B:5")).unwrap();
        assert_eq!(parse_player_card(&mem), Some(PlayerCard { team: Team::Blue, id: 5 }));
    }

    #[test]
    fn rejects_bad_content() {
        for t in ["ASG1:G:1", "ASG1:R:0", "ASG1:R:1000", "ASG2:R:1", "ASG1:R:1:x", "hello"] {
            assert_eq!(parse_player_card(&tag(t)), None, "{t}");
        }
        assert_eq!(parse_player_card(&[0xFE]), None);
        assert_eq!(parse_player_card(&[0x03, 0x20, 0xD1]), None); // truncated
        assert_eq!(parse_player_card(&[]), None);
    }
}
```

**Step 3:** Run `rtk cargo test`. Expected: 11 passed in total.

**Step 4:** Commit: `git commit -m "core: NTAG player card parser"`

### Task B4: Admin menu logic, test-first

**Files:**
- Create: `firmware/core/src/admin.rs` and add `pub mod admin;` to `lib.rs`

**Behaviour:**
- `Menu::new()` starts on item 0 of `[Reset, WifiSetup, Status, Exit]`.
- `Menu::press(Team::Red)` moves to the next item, wrapping around.
- `Menu::press(Team::Blue)` returns `Some(Item)` for the selected item. *(As built: reuses `game::Team` for the buttons; `admin::Item` is both the menu entry and the returned action.)*
- `lines()` renders a 20x4 screen: title `ADMIN`, the previous, current (prefixed `>`) and next item.

**Step 1:** Write tests covering: next wraps from Exit to Reset; select returns the right action; `lines()[2]` starts with `>`; every line is at most 20 chars. Run them and expect FAIL.

**Step 2:** Implement (about 50 lines: an enum, an index and a match). Run the tests and expect PASS.

**Step 3:** Commit: `git commit -m "core: admin menu"`

---

## Phase C: firmware/device (ESP32-S3), milestones 0–3

**Before writing any device code:** look up the current esp-hal 1.2 / esp-rtos 0.4 APIs with context7 (`resolve-library-id esp-hal`) or docs.rs, and start from the `esp-generate` template instead of from memory. The esp-hal API changed a lot before 1.0.

### Task C1 (Milestone 0): Toolchain + blinky

**Step 1:**

```bash
cargo install espup espflash esp-generate --locked
espup install --targets esp32s3
. ~/export-esp.sh
cargo +esp --version
```

Expected: an `esp` toolchain version is printed. *(Done 2026-09-29: Xtensa Rust 1.97.0, espflash 4.6.0, esp-generate 1.4.0; `asg-core` builds for `xtensa-esp32s3-none-elf`.)*

**Step 2:** Generate the project. Run `esp-generate --help` first and use the headless options for: chip esp32s3, embassy, defmt or log, probe-rs off, and no WiFi yet. Then:

```bash
cd firmware && esp-generate --chip esp32s3 --headless <options from --help> device
```

**Step 3:** In `device/Cargo.toml`, add `asg-core = { path = "../core" }` and the features `v4-r2 = []` and `v4-r8 = []`, with `default = ["v4-r2"]`.

**Step 4:** Create `device/src/board.rs` with the pin map from design part 1. It's the only place GPIO numbers appear:

```rust
//! Heltec WiFi LoRa 32 V4 (no display) + AirsoftCounter carrier. See design doc parts 1 and 6.
pub const I2C_SDA: u8 = 4;
pub const I2C_SCL: u8 = 3;
pub const EXP_INT: u8 = 6; // TCA9534 INT, active low, 10k pull-up on the carrier
pub const I2S_BCLK: u8 = 47;
pub const I2S_LRCLK: u8 = 48;
pub const I2S_DIN: u8 = 21;
pub const VBAT_ADC: u8 = 1;
// GPIO44 (U0RXD) and GPIO43 (U0TXD) are spare and unconnected; never enable UART0.

/// TCA9534 expander (I2C 0x20) pin map.
pub mod exp {
    pub const ADDR: u8 = 0x20;
    pub const BTN_RED: u8 = 0; // input, active low
    pub const BTN_BLUE: u8 = 1; // input, active low
    pub const LED_RED: u8 = 2;
    pub const LED_BLUE: u8 = 3;
    pub const BUZZER: u8 = 4;
    pub const AMP_SD: u8 = 5; // high = amp on (left channel), low = shutdown
    // P6, P7 unconnected: configure as outputs driven low.
}
#[cfg(feature = "v4-r2")] pub const ONBOARD_LED: u8 = 35;
#[cfg(feature = "v4-r8")] pub const ONBOARD_LED: u8 = 46;
#[cfg(feature = "v4-r2")] pub const VEXT: u8 = 36; // active low
#[cfg(feature = "v4-r8")] pub const VEXT: u8 = 40;
#[cfg(feature = "v4-r2")] pub const ADC_CTRL: Option<u8> = Some(37);
#[cfg(feature = "v4-r8")] pub const ADC_CTRL: Option<u8> = None;
```

(If esp-hal 1.2 hands out pins as typed peripherals instead of numbers, turn this into a function that takes `Peripherals` and returns a `Board` struct. Keep it the only file that names GPIOs.)

**Step 5:** Make `main.rs` blink `ONBOARD_LED` once per second with an Embassy `Timer` and log `"alive"`.

**Step 6:** Flash to a bare V4 over USB-C: `cd firmware/device && cargo run --release`. The template's runner is `espflash flash --monitor`. Expected: the LED blinks and `alive` prints every second. **This needs the user to connect the board. Ask first.**

**Step 7:** Commit: `git commit -m "device: toolchain and blinky on Heltec V4"`

*As built (2026-09-29), steps 2–5 and 7 done, step 6 (flash) pending hardware:*
- Generated with `cd firmware && esp-generate --headless -s -o esp32s3 -o unstable-hal -o embassy -o log -o esp-backtrace -O . device`. `embassy` requires `unstable-hal` (the generator refuses without it); no probe-rs, defmt, alloc or radio.
- Versions (Cargo.lock): esp-hal 1.2.2 (`unstable`), esp-rtos 0.4.0 (`embassy`), embassy-executor 0.10.0, embassy-time 0.5.1, esp-bootloader-esp-idf 0.6.0, esp-println 0.18.0 + log 0.4, esp-backtrace 0.20.0. Edition 2024, `rust-toolchain.toml` = `esp`.
- esp-hal hands out typed pins, so `board.rs` keeps the numeric constants as documentation and adds `Board::new(Peripherals) -> Board` (by-role fields: `onboard_led: AnyPin`, plus `timg0`/`sw_int0` for the scheduler). Later tasks add their peripherals to `Board`. `lib.rs` has a `compile_error!` unless exactly one of `v4-r2`/`v4-r8` is enabled.
- `main.rs` logs `asg_core::game::Config::default().block_size` (proves the dependency links), then blinks the LED (500 ms on / 500 ms off) and logs `alive` every second.
- `cargo build --release` (R2) and `--no-default-features --features v4-r8` both build; `cargo clippy --release -- -D warnings` is clean for both. The app image (`espflash save-image`) is about 99 KB. Added `-Wl,--no-warn-rwx-segments` to `.cargo/config.toml` to silence a harmless linker warning from the template.

### Task C2: TCA9534 expander driver + outputs (LEDs, buzzer) as tasks

*(Revised for A10: LEDs, buzzer and buttons are on the TCA9534 expander at I2C 0x20, not on native GPIOs.)*

**Files:**
- Create: `device/src/expander.rs` and `device/src/outputs.rs`

**Conventions from the C1 review (apply from C2 on):**
- **`Board` fields use concrete pin types** for pins that are the same on both variants (`GPIO4`, `GPIO3`, `GPIO6`, `GPIO1`, `GPIO47`, `GPIO48`, `GPIO21`). `AnyPin` is only for variant-dependent pins (LED, VEXT, `adc_ctrl: Option<AnyPin>`). esp-hal's ADC needs concrete `GPIOn` types.
- Add fields one task at a time: `i2c: I2C0, sda: GPIO4, scl: GPIO3` (C2), `exp_int: GPIO6` (C4), `adc1, vbat: GPIO1, adc_ctrl, flash: FLASH` (C5), `i2s: I2S0, dma: DMA_CH0, bclk: GPIO47, lrclk: GPIO48, din: GPIO21` (C7).
- Keep it one flat struct, and delete each `u8` constant once its typed field exists.
- **Shared I2C, decided:** one place builds `I2c::new(..).with_sda().with_scl().into_async()` at **100 kHz** (for the PCF8574 and the level shifter). It goes in a `StaticCell<Mutex<NoopRawMutex, _>>`. Each driver (expander, LCD, PN532) gets an `embassy_embedded_hal::shared_bus::asynch::i2c::I2cDevice`. Dependencies: embassy-sync, embassy-embedded-hal.

**Step 1: `expander.rs`**, a small TCA9534 driver over the shared async I2C bus (`embassy-embedded-hal` shared bus or a `Mutex`).
- Registers: 0 input, 1 output, 2 polarity, 3 config (1 = input).
- `init()` **writes output = 0x00 first, then config = 0b0000_0011** (P0/P1 inputs; P2–P7 outputs driven low, including the unused P6/P7).
- `set(pin, bool)` keeps a shadow copy of the output register. `read_inputs()` returns the input register.
- The expander pin map lives in `board::exp`.

**Step 2: `outputs.rs`.**
- A `led_task` receives `asg_core::game::Leds` over a `Signal` and drives P2/P3 through the expander: `On`, `Off`, or `Blink` at 300/300 ms.
- A `buzzer_task` receives `Beep` over a `Channel<_, Beep, 4>` and toggles P4.
- I2C writes at these rates are trivial.

**Step 3:** Hardware test on the carrier. At boot, send `Leds::Blink` and one `READY_BEEP`. Expected: both LEDs blink and 3 beeps sound. **Nothing lights or beeps during reset or boot**: the TCA9534 powers up as all-inputs and the gate pull-downs hold the MOSFETs off.

**Step 4:** Commit: `git commit -m "device: TCA9534 driver, LED and buzzer tasks"`

### Task C3: LCD driver + address probe

**Files:**
- Create: `device/src/lcd.rs`

**Step 1:** Check whether `hd44780-driver` 0.4 works with embedded-hal 1.0 `I2c`: add it and compile a minimal init. **If it doesn't:** write a small PCF8574 HD44780 driver in `lcd.rs` covering 4-bit init, `clear`, `set_cursor(col, row)`, `write_str` and `backlight(bool)`, with backpack pin mapping RS=P0, RW=P1, E=P2, BL=P3, D4–D7=P4–P7. The row offsets for a 20x4 are `[0x00, 0x40, 0x14, 0x54]`.

**Step 2:** Address probe. Try a zero-length write to 0x27, then 0x3F, and use whichever ACKs. Log the result. If neither answers, show nothing and log an error; the device keeps running.

**Step 3:** An `lcd_task` receives `[String<20>; 4]` plus the backlight state and redraws **only lines that changed**. Rewriting all 80 characters every 50 ms flickers.

**Step 4:** Hardware test: the 20x4 LCD shows 4 test lines. Expected: readable text, and the log shows the detected address.

**Step 5:** Commit: `git commit -m "device: 20x4 LCD with address probe"`

### Task C4 (Milestone 1): Buttons + game loop, a playable local game

**Files:**
- Create: `device/src/buttons.rs`
- Modify: `device/src/main.rs`

**Step 1:** `buttons.rs`, *(revised for A10: buttons are expander inputs P0/P1)*. One task:
- Wait on GPIO6 (`EXP_INT`, active low, carrier pull-up; `Input` with no internal pull) with `wait_for_falling_edge().await`.
- Then `read_inputs()`, which also clears INT, and compare with the previous state.
- A high→low transition on P0 sends `Team::Red` and on P1 sends `Team::Blue`, into a `Channel<_, Team, 4>`.
- After each event, `Timer::after_millis(50)` as a software guard on top of the RC filter.
- Also poll `read_inputs()` every 200 ms as a fallback in case an INT edge is missed.

**Step 2:** Game loop in `main`: every 50 ms, or when a button event arrives (`select`):
- Call `game.tick(now_ms)` and send any returned beep to the buzzer.
- For a button event, call `game.capture(team, now_ms)`.
- Push `game.leds()` to the LED task, and `game.lines()` plus `game.backlight(now)` to the LCD.

Use `Config::default()` for now.

**Step 3:** Play through on hardware and check each step:
- The intro shows for 3 s with the LEDs blinking.
- GOTOWY appears with the LEDs on.
- A press adds a point and the countdown runs.
- 5 beeps, then GOTOWY again.
- After the block is used up, PUNKT WYCZERPANY appears with the backlight blinking.

**Step 4:** Commit: `git commit -m "device: playable Airsoftcoin game (milestone 1)"`

### Task C5 (Milestone 2): Config storage + battery

*(From C1: espflash assumes 4 MB of flash by default, but the Heltec V4 has **16 MB**. First confirm it with `espflash board-info` on real hardware, then set the flash size (`espflash --flash-size 16mb` or `[flash]` in espflash.toml) and add a partition table with an `nvs`-type data partition for config and room for audio clips in C7.)*

**Files:**
- Create: `device/src/storage.rs`, `device/src/battery.rs`

**Step 1:** Add a `serialize`/`deserialize` pair for `Config` to `asg-core`: 4 bytes, little-endian `mining_time_s` then `block_size`, a version byte, and `clamped()` on load. Test it first: round-trip, a wrong version returns `None`, and too short returns `None`.

**Step 2:** `storage.rs`: `sequential-storage` map on an `esp-storage` flash range. Check the partition table produced by esp-generate and add a small `nvs`-type data partition if needed. `load() -> Config` returns `Config::default()` when nothing is stored or the data can't be decoded. **No first-boot flashing ritual.**

**Step 3:** `battery.rs`: on R2, set ADC_CTRL HIGH before reading. Read GPIO1 in millivolts and multiply by 4.9 (the 100k/390k divider). Keep the ×4.9 factor as a named constant with a comment saying it needs calibrating against a multimeter per batch.

**Step 4:** Hardware test:
- Change the config through a temporary debug path (e.g. hold both buttons at boot to set mining time to 10 s), reboot, and expect the value to persist.
- The battery reading should be within ±0.1 V of a multimeter.

**Step 5:** Commit: `git commit -m "device: persistent config and battery reading (milestone 2)"`

### Task C6 (Milestone 3): RFID player cards + admin

**Files:**
- Create: `device/src/nfc.rs`
- Modify: `device/src/storage.rs`, `device/src/main.rs`, `core/src/game.rs`

**Step 1:** Check whether the `pn532` 0.5 crate works over esp-hal I2C (embedded-hal 1.0). **If not:** write a minimal driver in `nfc.rs` covering I2C frame wrap and ACK, `SAMConfiguration` (normal mode), `InListPassiveTarget` (106 kbps type A, returns the UID), and `InDataExchange` with NTAG `READ` (0x30), which returns 4 pages (16 bytes) per call. The PN532 I2C address is 0x24. After each command, wait for the status byte (0x01) before reading the response.

**Step 2:** `nfc_task`, polling only while the game wants cards (`Phase::Ready`) or an admin tap is possible (any time):
- Poll `InListPassiveTarget` with a short timeout every 300 ms, then turn the RF field off (`RFConfiguration`).
- On a tag: if the UID is on the admin list, send `CardEvent::Admin`.
- Otherwise read pages 4..=15 (48 bytes) and call `asg_core::card::parse_player_card`. `Some` sends `CardEvent::Player(card)`; `None` sends `CardEvent::Unknown` (error beep).
- The same UID within 2 s is ignored, so a card resting on the lid doesn't retrigger.

**Step 3:** Admin list in storage: `heapless::Vec<heapless::Vec<u8, 10>, 8>`. For first enrollment, if the list is empty and both buttons are held when a card is read, store its UID and play a confirmation beep.

**Step 4:** Game integration:
- `CardEvent::Player(c)` → `game.capture(c.team, now)`. Log the player id; LoRa sends it in milestone 4.
- `CardEvent::Admin` → switch the display and buttons to a new `asg_core::admin::Menu` (feed button edges to `press(Team)`, act on the returned `Item`).
- `Reset` → `Game::new(config, now)`; `Status` → show battery voltage; `Exit` → back to the game. `WifiSetup` logs "not yet" until milestone 6.

**Step 5:** Hardware test (PN532 in I2C mode, cards written with a phone app):
- An `ASG1:R:017` card in Ready adds a red point.
- An unknown card gives the error beep.
- An empty admin list plus both buttons plus a card enrolls it.
- The admin card opens the menu, and Reset works.
- Measure the read range through the actual lid, and note it in the design doc's open items.

**Step 6:** Commit: `git commit -m "device: RFID player captures and admin menu (milestone 3)"`

---

### Task C7 (new): Speaker audio over I2S

*(Added for A10.)*

**Files:**
- Create: `device/src/audio.rs` and `device/assets/*.raw`
- Modify: `asg-core` (add a `Sound` event)

**Step 1: core, test-first.**
- `Game::tick`/`capture` return an optional `Sound`: `Captured`, `MiningDone`, `Depleted` or `Ready`, alongside the existing `Beep`.
- Host tests pin which events produce which sound.

**Step 2: `audio.rs`.**
- I2S TX with DMA on BCLK=GPIO47, LRCLK=GPIO48, DIN=GPIO21.
- 16 kHz, 16-bit stereo frames, with the mono sample duplicated into both slots (the amp plays the left channel).
- Before playback, `AMP_SD` (expander P5) goes high and the task waits about 10 ms; about 100 ms after the last sample, `AMP_SD` goes low again.
- Clips are raw 16 kHz mono PCM embedded with `include_bytes!` (a few seconds each; the 16 MB flash is ample). A software volume scale is applied.

**Step 3: brownout guard.**
- Scale the volume down when the battery voltage (C5) is low.
- Don't start a clip while a LoRa TX is in progress (milestone 4).

**Step 4:** Hardware test with the Visaton 8 Ω speaker: each game event plays its clip, and nothing is heard at boot.

**Step 5:** Commit: `git commit -m "device: I2S speaker audio"`

## Milestones 4–7 (separate plans later)

Write a new plan (superpowers:writing-plans) at the start of each one, using the design doc parts 4 and 5 as the spec:

4. **LoRa:** `asg-core::protocol` (encode/decode + AES-CCM auth + replay counter, all host-tested), lora-phy SX1262 with TCXO 1.8V, DIO2 as RF switch, and the FEM pins 7/2/5 driven manually. 869.525 MHz, TX power set explicitly. PING/STATUS, then START/STOP/CONFIG and capture events with ACK and retry.
5. **GPS:** UART1 on 38/39, `nmea` crate, position in STATUS.
6. **WiFi setup page:** esp-radio AP, embassy-net and picoserve. Config form plus the admin card list.
7. **HQ bridge:** a bare V4, USB serial ↔ LoRa, line protocol for a laptop.
