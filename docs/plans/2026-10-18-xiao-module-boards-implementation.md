# XIAO ESP32-S3 Module Boards Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add two hand-build board variants, `pack_xiao` and `lipo_xiao`, that replace the STM32L072 of
`pack_tme` / `lipo_tme` with a Seeed XIAO ESP32-S3 module, through to clean ERC/DRC and fab outputs.

**Architecture:** Board modules are Python data (`PARTS`/`NETS`/`PLACE`/`BLOCKS`/...); generators read
them through `board.py` (`BOARD=<name>`). Each new board imports its `_tme` parent and edits it (the
repo's standard derivation). The XIAO keeps the `U_MCU` reference so sheet/placement entries carry
over. Symbol and footprint are copied from Seeed's library by a small tool, not redrawn.

**Tech Stack:** Python 3 (system `/usr/bin/python3`, it has KiCad's `pcbnew`), KiCad 10.0.7
`kicad-cli`, GNU make, the repo's generators (`gen_sch.py`, `gen_pcb.py`, `route.py`).

**Source of truth:** `docs/plans/2026-10-18-xiao-module-boards-design.md` (read it first, all of it —
"Module facts" and "Power domains" explain every non-obvious choice below). If anything here
contradicts it, stop and ask.

---

## Ground rules (read before Task 0)

- Work in `hardware/` unless a step says otherwise. Branch: `esp32-lora-design` (do not switch).
- **The working tree has unrelated uncommitted changes** (`hardware/mech/*.py`, `.serena/`). Never
  `git add -A` / `git add .`; stage only the files a step names. Never revert or touch those files.
- Prefix git with `rtk` (repo convention): `rtk git add …`, `rtk git commit …`.
- Use **`/usr/bin/python3`** (bare `python3` is redirected to `uv run` and has no `pcbnew`),
  **`/usr/bin/make`**, **`/usr/bin/grep -F`**, **`/usr/bin/diff`** — the `rtk` wrappers of
  make/grep/diff hide errors or mangle patterns.
- Commit message style: `hardware: <what>` (see `git log --oneline`). End every commit message with
  a blank line and `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- KiCad 10 gotchas already handled by the generators: "annotation errors" printed by the netlist
  export are harmless (descriptive references); the Konnect PNG renderer drops thin wires — check
  schematics with `kicad-cli sch export pdf`, not PNGs.
- **Stop and ask the user (do not improvise) if:** the module cannot be placed on a board without
  growing the board or moving a connector; ERC/DRC needs a rule severity changed to pass; any
  fact in the design doc's "Module facts" turns out wrong; a `_tme` board's outputs change.

---

### Task 0: Baseline

**Step 1: Confirm the parents are green**

Run (in `hardware/`):
```bash
/usr/bin/python3 lipo_tme.py && /usr/bin/python3 pack_tme.py
```
Expected:
```
lipo_tme ok: 63 parts, 33 nets
pack_tme ok: 132 parts, 80 nets
```

**Step 2: Get Seeed's library (read-only input)**

```bash
gh repo clone Seeed-Studio/OPL_Kicad_Library "${TMPDIR:-/tmp}/gh-clones-${CLAUDE_SESSION_ID}/OPL_Kicad_Library" -- --depth 1
ls "${TMPDIR:-/tmp}/gh-clones-${CLAUDE_SESSION_ID}/OPL_Kicad_Library/Seeed Studio XIAO Series Library"
```
Expected: the listing contains `Seeed_Studio_XIAO_Series.kicad_sym` and `XIAO-ESP32-S3-SMD.kicad_mod`.
Call that folder `$XIAO_LIB` below (it is licensed CC BY-SA 4.0; attribution goes in Task 10).

**Step 3: Commit the design doc and this plan**

```bash
cd .. && rtk git add docs/plans/2026-10-18-xiao-module-boards-design.md docs/plans/2026-10-18-xiao-module-boards-implementation.md
rtk git commit -m "docs: XIAO ESP32-S3 module boards design and plan"
```
(add the Co-Authored-By trailer per the ground rules). `cd hardware` again.

---

### Task 1: Build flow accepts `*_xiao`

**Files:**
- Modify: `hardware/Makefile:59` and the `boards:` target (~line 72-78), header comment line 3
- Modify: `hardware/tme.py:104`
- Modify: `hardware/board.py:1-3` (docstring)

**Step 1:** `Makefile:59` — replace
```make
ifeq ($(filter %_tme,$(BOARD)),)
```
with
```make
ifeq ($(filter %_tme %_xiao,$(BOARD)),)
```
Header comment line 3: `... BOARD=carrier (default), pack, lipo or a *_tme / *_xiao board`.
Comment above `fab:` (the "a *_tme board is hand-built" sentence): say "a *_tme or *_xiao board".

**Step 2:** `boards:` target — append two lines after `$(MAKE) BOARD=lipo_tme all`:
```make
	$(MAKE) BOARD=pack_xiao all
	$(MAKE) BOARD=lipo_xiao all
```
(Tab-indented, like its neighbours.) Do this now; `make boards` is only run in Task 11.

**Step 3:** `tme.py:104` — replace `if board_name.endswith("_tme"):` with
`if board_name.endswith(("_tme", "_xiao")):`

**Step 4:** `board.py` docstring lines 2-3: add "or the XIAO variants pack_xiao / lipo_xiao" after the
TME variants.

**Step 5: Verify nothing else keys off `_tme`**

```bash
/usr/bin/grep -n -F "_tme" *.py Makefile tools/*.py | /usr/bin/grep -v -F "import" 
```
Expected: only data-module names (`carrier_tme`, `pack_tme`, `lipo_tme` as module/board names in
docstrings, `tme_all.py` DEFAULT list). Any other *suffix test* (`endswith`, `filter %`) must get the
same `_xiao` treatment. Leave `tme_all.py` DEFAULT as is (it takes board names as arguments).

**Step 6: Commit**
```bash
rtk git add Makefile tme.py board.py
rtk git commit -m "hardware: build flow treats *_xiao boards as hand-built (TME list, no JLC files)"
```

---

### Task 2: Import the XIAO symbol and footprint

**Files:**
- Create: `hardware/tools/import_xiao.py`
- Modify (generated by the tool): `hardware/kicad/local.kicad_sym`
- Create (generated by the tool): `hardware/kicad/local.pretty/XIAO_ESP32S3_SMD.kicad_mod`

**Step 1: Write the tool** (verified in a dry run; the built-in `check()` is its test):

```python
"""Import Seeed's XIAO ESP32-S3 (SMD) symbol and footprint into the local libraries:
kicad/local.kicad_sym symbol XIAO_ESP32S3 and kicad/local.pretty/XIAO_ESP32S3_SMD.kicad_mod.

Source: github.com/Seeed-Studio/OPL_Kicad_Library, folder "Seeed Studio XIAO Series Library"
(symbol XIAO-ESP32-S3-SMD, footprint XIAO-ESP32-S3-SMD.kicad_mod). Copied, not redrawn; the
footprint's User.2 artwork (~2500 shapes, ~500 KB) is dropped. Re-running replaces both.

Run: /usr/bin/python3 tools/import_xiao.py <path to "Seeed Studio XIAO Series Library">
"""
import re
import sys
from pathlib import Path

import pcbnew  # pyright: ignore[reportMissingImports]

KICAD = Path(__file__).resolve().parent.parent / "kicad"
SRC_NAME, SYM, FP = "XIAO-ESP32-S3-SMD", "XIAO_ESP32S3", "XIAO_ESP32S3_SMD"
# Pin number -> name, as the design doc's "Module facts" fixes them.
PINS = {**{str(i + 1): f"D{i}" for i in range(11)}, "12": "3V3_OUT", "13": "GND", "14": "VBUS",
        "15": "MTDI", "16": "MTDO", "17": "EN", "18": "GND", "19": "MTMS", "20": "MTCK",
        "21": "USB_DN", "22": "USB_DP", "23": "VBAT", "24": "GND", "25": "PAD"}


def block(text, head):
    """The balanced s-expression starting at `head` in text."""
    i, depth = text.index(head), 0
    for j in range(i, len(text)):
        depth += {"(": 1, ")": -1}.get(text[j], 0)
        if depth == 0:
            return text[i:j + 1]
    raise ValueError(head)


def import_symbol(src):
    sym = block(src.read_text(), f'(symbol "{SRC_NAME}"').replace(f'"{SRC_NAME}', f'"{SYM}')
    sym = re.sub(r'\(property "Footprint" "[^"]*"', f'(property "Footprint" "local:{FP}"', sym)
    got = {num: name for name, num in re.findall(r'\(name "([^"]*)"[\s\S]*?\(number "([^"]*)"', sym)}
    assert got == PINS, f"symbol pins differ: {set(got.items()) ^ set(PINS.items())}"
    lib = KICAD / "local.kicad_sym"
    text = lib.read_text()
    if f'(symbol "{SYM}"' in text:
        text = text.replace(block(text, f'(symbol "{SYM}"'), sym)
    else:
        text = text[:text.rindex(")")] + sym + "\n)\n"
    lib.write_text(text)


def children(text):
    """Top-level child s-expressions of the one block in text."""
    out, depth, start = [], 0, None
    for i, ch in enumerate(text):
        if ch == "(":
            depth += 1
            if depth == 2:
                start = i
        elif ch == ")":
            if depth == 2:
                out.append(text[start:i + 1])
            depth -= 1
    return out


def import_footprint(src):
    """Text copy (pcbnew Remove() on ~2500 shapes crashes KiCad 10's Python): drop User.2 children."""
    kept = [c for c in children(src.read_text()) if '(layer "User.2")' not in c]
    body = "\n\t".join(kept)
    (KICAD / "local.pretty" / f"{FP}.kicad_mod").write_text(f'(footprint "{FP}"\n\t{body}\n)\n')


def check():
    fp = pcbnew.FootprintLoad(str(KICAD / "local.pretty"), FP)
    pads = sorted(p.GetNumber() for p in fp.Pads())
    assert pads == sorted(PINS), f"footprint pads: {pads}"
    text = (KICAD / "local.kicad_sym").read_text()
    assert text.count(f'(symbol "{SYM}"') == 1
    print(f"import_xiao ok: local:{SYM} ({len(PINS)} pins), local:{FP} ({len(pads)} pads)")


if __name__ == "__main__":
    lib_dir = Path(sys.argv[1])
    import_symbol(lib_dir / "Seeed_Studio_XIAO_Series.kicad_sym")
    import_footprint(lib_dir / f"{SRC_NAME}.kicad_mod")
    check()
```

Why text instead of pcbnew for the footprint: deleting ~2500 shapes through pcbnew's `Remove()`
segfaults KiCad 10's Python (seen in the dry run). Do not "improve" it back.

**Step 2: Run it twice (second run proves it is idempotent)**

```bash
/usr/bin/python3 tools/import_xiao.py "$XIAO_LIB"
/usr/bin/python3 tools/import_xiao.py "$XIAO_LIB"
/usr/bin/grep -c -F '(symbol "XIAO_ESP32S3"' kicad/local.kicad_sym
ls -la kicad/local.pretty/XIAO_ESP32S3_SMD.kicad_mod
```
Expected: each run ends with `import_xiao ok: local:XIAO_ESP32S3 (25 pins), local:XIAO_ESP32S3_SMD (25 pads)`
(KiCad may print a harmless `property.h ... No enum choices defined` assert line first); grep
prints `1`; the footprint is ~9 KB.

Facts this footprint carries (for later tasks): courtyard ≈ x 0…17.9, y −21.1…0 mm from the
footprint origin (origin = bottom-left courtyard corner, module extends to −y). **The module's
USB-C end is the y ≈ −21 edge** (beside pads 1 = D0 and 14 = VBUS). Pads 23 (BAT+) / 24 (BAT−) sit
mid-module; 15-22 are a 2×4 grid under the module; 25 is a centre pad.

**Step 3: Confirm git sees only the intended changes**
```bash
rtk git status --short kicad/
rtk git diff --stat kicad/local.kicad_sym
```
Expected: `local.kicad_sym` modified (one symbol appended), one new `.kicad_mod`.

**Step 4: Commit**
```bash
rtk git add tools/import_xiao.py kicad/local.kicad_sym kicad/local.pretty/XIAO_ESP32S3_SMD.kicad_mod
rtk git commit -m "hardware: XIAO ESP32-S3 symbol + footprint, imported from Seeed's OPL library"
```

---

### Task 3: `lipo_xiao.py` — parts, nets, self-check

**Files:**
- Create: `hardware/lipo_xiao.py`

**Step 1: Confirm the test fails first**
```bash
/usr/bin/python3 -c "import lipo_xiao"
```
Expected: `ModuleNotFoundError: No module named 'lipo_xiao'`.

**Step 2: Write the module** (verified in a dry run against the real `lipo_tme`: `check()` passes
and all five sheets lay out with zero clashes; the `PLACE` entries marked TODO are placeholders
for Task 5):

```python
"""AirsoftCounter LiPo board, XIAO ESP32-S3 variant: hand-build, no STM32, no ST-Link.

Derived from lipo_tme.py by import and edit. The L072 and its SWD/boot/UART parts go; a Seeed XIAO
ESP32-S3 (bought, soldered on by its castellated pads) takes the U_MCU reference. Two feeds:
keep-alive AP7381 -> D_KA -> module 3V3 pad (3V3_M), run buck +5V -> D_M1 -> module 5V pad (VMOD_5V);
the module's BAT+ pad stays unconnected. gen_sch.py / gen_pcb.py read it through board.py
(`make BOARD=lipo_xiao ...`). Run this file to self-check.

Source of truth: docs/plans/2026-10-18-xiao-module-boards-design.md.
"""
import copy

import board
import lipo
import lipo_tme
import pack
import tme

NAME = "lipo_xiao"
TITLE = "AirsoftCounter v2 LiPo (XIAO hand-build)"

XIAO = ("XIAO ESP32-S3", "local:XIAO_ESP32S3", "local:XIAO_ESP32S3_SMD")
B5819W = ("B5819W", *pack.B5819W)
# L072 support, SWD/boot pads and the UART header: the module has USB, a boot button and a console.
_GONE = {"C_MCU3", "C_VDDA", "R_BOOT", "C_NRST", "TP_NRST", "TP_SWDIO", "TP_SWCLK", "TP_BOOT0",
         "J_UART1"}

PARTS = {r: v for r, v in lipo_tme.PARTS.items() if r not in _GONE}
PARTS["U_MCU"] = XIAO
PARTS["D_KA"] = B5819W   # keep-alive: sits ~0.3 V under the module's own buck, so it never carries run current
PARTS["D_M1"] = B5819W   # run feed: Seeed's diode-fed 5V pad input

# XIAO pins (symbol = footprint numbers): 1-11 D0..D10, 12 3V3, 13 GND, 14 5V (VBUS),
# 15 MTDI, 16 MTDO, 17 EN, 18 GND, 19 MTMS, 20 MTCK, 21/22 USB, 23 BAT+, 24 GND, 25 PAD.
LDO_VIN = lipo_tme.LDO_VIN
TAP_ADC_PIN = {1: "U_MCU.1", 2: "U_MCU.2", 3: "U_MCU.3"}   # D0..D2 = GPIO1..3, ADC1


def _kept(p):
    return p.split(".")[0] not in _GONE | {"U_MCU"}


NETS = {n: [p for p in mem if _kept(p)] for n, mem in lipo_tme.NETS.items()}
for _n in ("NRST", "BOOT0", "SWDIO", "SWCLK", "UART_TX", "UART_RX"):
    del NETS[_n]
NETS["+3V3"] = [p for p in NETS["+3V3"] if not p.startswith(("C_MCU1.", "C_MCU2."))] + ["D_KA.2"]
NETS["3V3_M"] = ["D_KA.1", "U_MCU.12", "C_MCU1.1", "C_MCU2.1"]
NETS["+5V"] += ["D_M1.2"]
NETS["VMOD_5V"] = ["D_M1.1", "U_MCU.14"]
NETS["GND"] += ["U_MCU.13"]
NETS["SDA_EXT"] += ["U_MCU.5"]                     # D4, I2C0 slave 0x30 (pull-ups on the carrier)
NETS["SCL_EXT"] += ["U_MCU.6"]                     # D5
NETS["KILL_DRV"] += ["U_MCU.9"]                    # D8 = GPIO7: no reset pull, RTC, gpio_hold in sleep
for _i in (1, 2, 3):
    NETS[f"TAP{_i}_ADC"] += [TAP_ADC_PIN[_i]]
NC_PINS = {f"U_MCU.{p}" for p in (4, 7, 8, 10, 11, *range(15, 26))}   # 23 = BAT+ must stay open

DNP, NC_PARTS = set(lipo_tme.DNP), set()
NOT_ASSEMBLED = set(lipo_tme.NOT_ASSEMBLED) - _GONE
NOT_TME = (set(lipo_tme.NOT_TME) - _GONE) | {"U_MCU"}   # the XIAO is bought at Botland (OFFBOARD_PARTS.md)
LCSC = {}
_KEYS = {(v, fp) for r, (v, _, fp) in PARTS.items() if r not in NOT_TME and fp != lipo.MH}
TME = {k: s for k, s in lipo_tme.TME.items() if k in _KEYS}
TME[(B5819W[0], B5819W[2])] = tme.TME[pack.LCSC[(B5819W[0], B5819W[2])]]
MODULES, VARIANTS = {}, {"standard": set()}


def assembled(variant="standard"):
    """Nothing is machine-placed on a hand-build board."""
    return []


# --- layout: lipo_tme's, minus the dropped parts ----------------------------------------------
W, H, CORNER = lipo_tme.W, lipo_tme.H, lipo_tme.CORNER
NETCLASS_POWER, NETCLASS_EXPECT = lipo_tme.NETCLASS_POWER, lipo_tme.NETCLASS_EXPECT
RAILS, PORT_LIB, DRC_RULES = lipo_tme.RAILS, lipo_tme.PORT_LIB, lipo_tme.DRC_RULES
BOTTOM, GND_VIAS, HELTEC_PADS = lipo_tme.BOTTOM, lipo_tme.GND_VIAS, lipo_tme.HELTEC_PADS
LABELS, TEXTS, SIZE_MM, NPTH_XY = lipo_tme.LABELS, list(lipo_tme.TEXTS), lipo_tme.SIZE_MM, lipo_tme.NPTH_XY
HIDE_REF = tuple(r for r in lipo_tme.HIDE_REF if r not in _GONE)
PLACE = {r: v for r, v in lipo_tme.PLACE.items() if r not in _GONE}
REF_AT = {r: v for r, v in lipo_tme.REF_AT.items() if r not in _GONE}
# TODO(Task 5): module, D_KA, D_M1 positions
PLACE |= {"U_MCU": (4.0, 47.0, 0), "D_KA": (26.0, 36.0, 0), "D_M1": (26.0, 40.0, 0)}

BLOCKS = copy.deepcopy(lipo_tme.BLOCKS)
for _b in BLOCKS:
    for _r in _GONE & _b["parts"].keys():
        del _b["parts"][_r]
    for _key in ("fields",):
        if _key in _b:
            _b[_key] = {r: f for r, f in _b[_key].items() if r not in _GONE}
    if "tags" in _b:
        # a tag whose net has no pin left on this sheet would dangle (ERC)
        _b["tags"] = {n: t for n, t in _b["tags"].items()
                      if any(m.split(".")[0] in _b["parts"] for m in NETS.get(n, ()))}
_mcu = BLOCKS[lipo_tme.SHEETS["mcu"][1][0]]
_mcu["title"] = "Always-on 3V3 keep-alive and XIAO ESP32-S3"
# clash-free in the dry run; fine-tune in Task 4 if the PDF looks crowded
_mcu["parts"] |= {"D_KA": (106.68, 50.8, 0, None), "D_M1": (106.68, 66.04, 0, None)}

SHEETS = dict(lipo_tme.SHEETS)
SHEETS["mcu"] = (_mcu["title"], lipo_tme.SHEETS["mcu"][1])
ROOT = copy.deepcopy(lipo_tme.ROOT)
ROOT["parts"] = {r: v for r, v in ROOT["parts"].items() if r not in _GONE}
ROOT["port_modes"] = {r: v for r, v in ROOT.get("port_modes", {}).items() if r not in _GONE}
OFFBOARD = dict(lipo_tme.OFFBOARD)


def check_mcu():
    """The XIAO pin roles and both of its feeds."""
    net_of = {p: n for n, mem in NETS.items() for p in mem}
    want = {"U_MCU.1": "TAP1_ADC", "U_MCU.2": "TAP2_ADC", "U_MCU.3": "TAP3_ADC",
            "U_MCU.5": "SDA_EXT", "U_MCU.6": "SCL_EXT", "U_MCU.9": "KILL_DRV",
            "U_MCU.12": "3V3_M", "U_MCU.13": "GND", "U_MCU.14": "VMOD_5V",
            "D_KA.2": "+3V3", "D_KA.1": "3V3_M", "D_M1.2": "+5V", "D_M1.1": "VMOD_5V",
            "U_LDO.1": "VIN", "U_LDO.2": "+3V3", "R_GK.1": "GND"}
    for p, n in want.items():
        assert net_of.get(p) == n, f"{p} on {net_of.get(p)}, want {n}"
    assert "U_MCU.23" in NC_PINS, "XIAO BAT+ is back-driven to ~3.3 V: it must stay unconnected"
    assert not NC_PINS & net_of.keys(), f"NC pins on nets: {NC_PINS & net_of.keys()}"
    assert PARTS["R_GK"][0] == "100k", "GPIO7 has no reset pull: R_GK stays 100k"
    assert PARTS["U_MCU"] == XIAO


def check():
    import sys

    this = sys.modules[__name__]
    board.check_structure(this)
    lipo.check_power_path(this)
    check_mcu()
    lipo.check_sheets(this)
    print(f"lipo_xiao ok: {len(PARTS)} parts, {len(NETS)} nets")


if __name__ == "__main__":
    check()
```

Notes for the reader (do not paste into the file):
- `3V3_M` is the module's 3V3 pad behind `D_KA`; `+3V3` is now only the AP7381 output, its caps,
  `TP_3V3` and `D_KA`'s anode. `C_MCU1`/`C_MCU2` (100 nF / 4.7 µF) become the module-pad decoupling.
- B5819W pin 1 = cathode, pin 2 = anode (same as the pack's `D_OR*`).
- Removing a part also removes it from `BLOCKS`/`ROOT`/`PLACE`/`REF_AT`/`HIDE_REF`; the tag filter
  drops sheet tags whose net has no pin left on that sheet (they would dangle in ERC).

**Step 3: Run the self-check**
```bash
/usr/bin/python3 lipo_xiao.py
```
Expected: `lipo_xiao ok: 56 parts, 29 nets`

**Step 4: Commit**
```bash
rtk git add lipo_xiao.py
rtk git commit -m "hardware: lipo_xiao board module (XIAO ESP32-S3 for the L072, keep-alive + run feeds)"
```

---

### Task 4: `lipo_xiao` schematic

**Files:** Modify `hardware/lipo_xiao.py` (only the `_mcu["parts"]` coordinates / tags if needed).
Generated: `hardware/kicad/lipo_xiao*.kicad_sch`, `lipo_xiao.kicad_pro`.

**Step 1: Preview every sheet**
```bash
BOARD=lipo_xiao /usr/bin/python3 tools/sch_preview.py
kicad-cli sch export pdf -o build/preview/p.pdf build/preview/lipo_xiao.kicad_sch
```
Expected: no clashes printed. Open `build/preview/p.pdf` (Read tool) and look at the "Always-on 3V3
keep-alive and XIAO ESP32-S3" sheet: U_MCU, D_KA (near the old test-pad column, x≈106.68),
D_M1 below it, C_MCU1/C_MCU2 on 3V3_M. If parts overlap visually or text collides, move them in
`_mcu["parts"]` by multiples of 2.54 mm and repeat. A single sheet: `... tools/sch_preview.py mcu`.

**Step 2: Generate the real schematic and run ERC on its own**
```bash
BOARD=lipo_xiao /usr/bin/make sch
kicad-cli sch erc --severity-all --exit-code-violations -o build/lipo_xiao_erc.rpt kicad/lipo_xiao.kicad_sch; echo "erc exit $?"
```
(`make check` would also route the not-yet-placed board, so call ERC directly here.)
Expected: `make sch` ends with the `check_netlist.py` line and no error; `erc exit 0`. Otherwise read
`build/lipo_xiao_erc.rpt`. Typical fixes: a dangling hierarchical label (drop that tag in
`lipo_xiao.py`), an unconnected pin that belongs in `NC_PINS`.

**Step 3: Commit** (schematic files only; PCB comes in Task 5)
```bash
rtk git add lipo_xiao.py kicad/lipo_xiao.kicad_sch kicad/lipo_xiao-*.kicad_sch kicad/lipo_xiao.kicad_pro
rtk git commit -m "hardware: lipo_xiao schematic, ERC clean"
```

---

### Task 5: `lipo_xiao` placement, routing, fab

**Files:** Modify `hardware/lipo_xiao.py` (`PLACE`, `REF_AT`, possibly `TEXTS`).
Generated: `hardware/kicad/lipo_xiao.kicad_pcb`, `hardware/fab/lipo_xiao/*`.

Board: 70 × 50 mm, all SMD on top (`lipo.py` comment above `W, H`). The L072 sat at (22, 44);
the removed parts free the lower-left area. `PLACE` = `(x, y, rotation)` of the footprint origin,
board coordinates in mm, y down.

**Placement rules (from the design doc):**
1. Module courtyard 17.9 × 21.0 mm, fully on the board and clear of every other courtyard.
2. **USB-C end (footprint y ≈ −21 edge) flush with a board edge (≤ 1 mm)** so a cable can reach it.
   Choose rotation so that edge faces outward. If no edge has room → stop and ask.
3. ≥ 15 mm between the module and the XH connectors (`J_BAL1`, `J_KEY1`, `J_PWR1`) — plug and
   finger room.
4. `D_KA` close to the module's 3V3 pad (pad 12), `D_M1` close to the 5V pad (pad 14),
   `C_MCU1`/`C_MCU2` next to pad 12.
5. Nothing under the module except its own pads and traces (no other parts, no vias on pads).

**Step 1:** Set `PLACE["U_MCU"]`, `PLACE["D_KA"]`, `PLACE["D_M1"]` (and move `C_MCU1/2`,
`REF_AT` text if needed) in `lipo_xiao.py`; delete the `# TODO(Task 5)` comment.

**Step 2: Build everything**
```bash
/usr/bin/python3 lipo_xiao.py && BOARD=lipo_xiao /usr/bin/make all 2>&1 | tail -30
```
Expected: exits 0; `fab/lipo_xiao/` holds `lipo_xiao_gerbers_jlcpcb.zip`, `schematic.pdf`,
`tme_bom.csv`, `bom.csv`, `top.png`, `bottom.png`, `print_1to1.pdf`; no "ERC failed"/"DRC failed".
On a DRC failure read `build/lipo_xiao_drc.rpt`, move parts, repeat. Look at `fab/lipo_xiao/top.png`.

**Step 3: TME list sanity**
```bash
cat fab/lipo_xiao/tme_bom.csv
/usr/bin/grep -c -i -F "STM32" fab/lipo_xiao/tme_bom.csv
```
Expected: contains `1N5819HW-7-F` (qty 2) and `AP7381-33SA-7`; the STM32 count is `0`; no XIAO line
(it is off-board, Botland).

**Step 4: Commit**
```bash
rtk git add lipo_xiao.py kicad/lipo_xiao.kicad_pcb kicad/lipo_xiao.kicad_sch kicad/lipo_xiao-*.kicad_sch kicad/lipo_xiao.kicad_pro fab/lipo_xiao
rtk git commit -m "hardware: lipo_xiao placed and routed, ERC/DRC clean, fab package"
```

---

### Task 6: Let `pack_tme.check_branches` check a derived board

**Files:** Modify `hardware/pack_tme.py` (function `check_branches`, ~line 261).

`pack_xiao` drops `MON_ALERT` (the INA226 ALERT pins become unconnected) but its cell branches must
pass the same topology check. Parameterize instead of copying.

**Step 1:** Replace the function head
```python
def check_branches():
    """Every cell in branch order, with its own INA226 across the 10R Kelvin split: IN+ and VBUS on
    the cell side of the shunt, IN- after it, addresses 0x40-0x43 by A1/A0, ALERTs wired together."""
    net_of = {p: n for n, m in NETS.items() for p in m}
```
with
```python
def check_branches(m=None):
    """Every cell in branch order, with its own INA226 across the 10R Kelvin split: IN+ and VBUS on
    the cell side of the shunt, IN- after it, addresses 0x40-0x43 by A1/A0, ALERTs wired together
    (or all unconnected on a board without MON_ALERT). m: a derived board module (default: this one)."""
    import sys

    m = m or sys.modules[__name__]
    net_of = {p: n for n, mem in m.NETS.items() for p in mem}
```
and the line
```python
        assert net_of[f"U_MON{i}.3"] == "MON_ALERT" and net_of[f"U_MON{i}.6"] == "+3V3"
```
with
```python
        assert net_of.get(f"U_MON{i}.3") == ("MON_ALERT" if "MON_ALERT" in m.NETS else None)
        assert net_of[f"U_MON{i}.6"] == "+3V3"
```

**Step 2: Regression**
```bash
/usr/bin/python3 pack_tme.py
```
Expected: `pack_tme ok: 132 parts, 80 nets`. (`check()` calls `check_branches()` with no argument.)

**Step 3: Commit**
```bash
rtk git add pack_tme.py
rtk git commit -m "hardware: pack_tme.check_branches takes the board module (for pack_xiao)"
```

---

### Task 7: `pack_xiao.py` — parts, nets, self-check

**Files:** Create `hardware/pack_xiao.py`

**Step 1: Confirm the test fails first**
```bash
/usr/bin/python3 -c "import pack_xiao"
```
Expected: `ModuleNotFoundError`.

**Step 2: Write the module** (verified in a dry run with Task 6 applied: `check()` passes, all
seven sheets lay out with zero clashes; `PLACE` TODOs are for Task 9):

```python
"""AirsoftCounter pack board, XIAO ESP32-S3 variant: hand-build, no STM32, no ST-Link.

Derived from pack_tme.py by import and edit. The L072 and its SWD/boot/UART/LED parts go, with
CHG_INT, MON_ALERT and the CHG_CE drive (firmware stops charging over I2C, CHG_CONFIG); a Seeed
XIAO ESP32-S3 (bought, soldered on by its castellated pads) takes the U_MCU reference. Two feeds:
keep-alive = its 3V3 pad on the always-on +3V3 (XC6206 on the cell diode-OR), run = its 5V pad on
D_M1 (+5V boost) / D_M2 (VBUS); BAT+ stays unconnected. Gate pull-downs R_PD1..4 are 4k7 against
the 45k boot pull-up on D7. gen_sch.py / gen_pcb.py read it through board.py
(`make BOARD=pack_xiao ...`). Run this file to self-check.

Source of truth: docs/plans/2026-10-18-xiao-module-boards-design.md.
"""
import copy

import board
import pack
import pack_tme

NAME = "pack_xiao"
TITLE = "AirsoftCounter v2 pack (XIAO hand-build)"

XIAO = ("XIAO ESP32-S3", "local:XIAO_ESP32S3", "local:XIAO_ESP32S3_SMD")
B5819W = ("B5819W", *pack.B5819W)
_GONE = {"C_MCU3", "C_VDDA", "R_BOOT", "C_NRST", "TP_NRST", "TP_SWDIO", "TP_SWCLK", "SW_BOOT",
         "SW_RST", "J_UART1", "R_ALERT", "R_INT_CHG", "R_LED_MCU", "LED_MCU"}

PARTS = {r: v for r, v in pack_tme.PARTS.items() if r not in _GONE}
PARTS["U_MCU"] = XIAO
PARTS["D_M1"] = B5819W   # run feed from the boost (key on)
PARTS["D_M2"] = B5819W   # run feed from USB VBUS (cable in); the charger keeps the raw VBUS
for _i in range(1, 5):
    PARTS[f"R_PD{_i}"] = ("4k7", *pack.R0805)   # 0.3 V against a 45k boot pull-up (D7 = U0RXD)

# XIAO pins (symbol = footprint numbers): 1-11 D0..D10, 12 3V3, 13 GND, 14 5V (VBUS),
# 15 MTDI, 16 MTDO (GPIO40), 17 EN, 18 GND, 19 MTMS, 20 MTCK (GPIO39), 21/22 USB, 23 BAT+, 24 GND, 25 PAD.
MCU = {1: "NTC1", 2: "NTC2", 3: "NTC3", 4: "NTC4",       # D0..D3 = GPIO1..4, ADC1
       5: "SDA_EXT", 6: "SCL_EXT",                        # D4/D5, I2C0 slave 0x30
       7: "SCL_INT",                                      # D6 = U0TXD: boot chatter, no START with SDA high
       8: "SW1_DRV", 9: "SW2_DRV", 10: "SW3_DRV", 11: "SW4_DRV",
       16: "NTC_PWR", 20: "SDA_INT",                      # bottom pads: loud, safe failures only
       12: "+3V3", 13: "GND", 14: "VMOD_5V"}
_DROPPED_NETS = ("NRST", "BOOT0", "SWDIO", "SWCLK", "UART_TX", "UART_RX", "USB_DM", "USB_DP",
                 "CHG_INT", "MON_ALERT", "LED_MCU_DRV", "LED_MCU_A")


def _kept(p):
    return p.split(".")[0] not in _GONE | {"U_MCU"}


NETS = {n: [p for p in mem if _kept(p)] for n, mem in pack_tme.NETS.items() if n not in _DROPPED_NETS}
NETS["VMOD_5V"] = ["D_M1.1", "D_M2.1"]
NETS["+5V"] += ["D_M1.2"]
NETS["VBUS"] += ["D_M2.2"]
for _p, _n in MCU.items():
    NETS[_n].append(f"U_MCU.{_p}")
NC_PINS = ({p for p in pack_tme.NC_PINS if not p.startswith("U_MCU.")}
           | {f"U_MCU.{p}" for p in (15, 17, 18, 19, 21, 22, 23, 24, 25)}   # 23 = BAT+ must stay open
           | {"U_CHG.7"} | {f"U_MON{i}.3" for i in range(1, 5)}            # charger INT, monitor ALERTs
           | {f"J_USB1.{p}" for p in ("A6", "B6", "A7", "B7")})             # board USB-C: power only

DNP, NC_PARTS = set(pack_tme.DNP), set()
NOT_ASSEMBLED = set(pack_tme.NOT_ASSEMBLED) - _GONE
NOT_TME = (set(pack_tme.NOT_TME) - _GONE) | {"U_MCU"}   # the XIAO is bought at Botland (OFFBOARD_PARTS.md)
LCSC = {}
_KEYS = {(v, fp) for r, (v, sym, fp) in PARTS.items()
         if sym != "Mechanical:MountingHole" and r not in DNP | NOT_TME}
TME = {k: s for k, s in pack_tme.TME.items() if k in _KEYS}   # B5819W and 4k7 are already on the list
MODULES, VARIANTS = {}, {"standard": set()}


def assembled(variant="standard"):
    """Nothing is machine-placed on a hand-build board."""
    return []


# --- layout: pack_tme's, minus the dropped parts ----------------------------------------------
W, H, CORNER = pack_tme.W, pack_tme.H, pack_tme.CORNER
NETCLASS_POWER, NETCLASS_EXPECT = pack_tme.NETCLASS_POWER, pack_tme.NETCLASS_EXPECT
DEFAULT_CLEARANCE, DRC_RULES = pack_tme.DEFAULT_CLEARANCE, pack_tme.DRC_RULES
RAILS, PORT_LIB, BOTTOM = pack_tme.RAILS, pack_tme.PORT_LIB, pack_tme.BOTTOM
PTH_COMPONENT_MIN, NPTH_EXPECT = pack_tme.PTH_COMPONENT_MIN, pack_tme.NPTH_EXPECT
LABELS, GND_VIAS = pack_tme.LABELS, list(pack_tme.GND_VIAS)
TEXTS = [t for t in pack_tme.TEXTS if t[0] != "GND TX RX"]   # J_UART1 is gone
PTH_UNDER_OK, RULE_SEVERITIES = pack_tme.PTH_UNDER_OK, pack_tme.RULE_SEVERITIES
HELTEC_PADS, SIZE_MM, NPTH_XY, SENSE_IN = {}, pack_tme.SIZE_MM, pack_tme.NPTH_XY, pack_tme.SENSE_IN
HIDE_REF = tuple(r for r in pack_tme.HIDE_REF if r not in _GONE)
PLACE = {r: v for r, v in pack_tme.PLACE.items() if r not in _GONE}
REF_AT = {r: v for r, v in pack_tme.REF_AT.items() if r not in _GONE}
# TODO(Task 9): module, D_M1, D_M2 positions
PLACE |= {"U_MCU": (60.0, 88.0, 0), "D_M1": (80.0, 70.0, 0), "D_M2": (80.0, 74.0, 0)}

BLOCKS = copy.deepcopy(pack_tme.BLOCKS)
for _b in BLOCKS:
    for _r in _GONE & _b["parts"].keys():
        del _b["parts"][_r]
    if "fields" in _b:
        _b["fields"] = {r: f for r, f in _b["fields"].items() if r not in _GONE}
    if "tags" in _b:
        # a tag whose net has no pin left on this sheet would dangle (ERC)
        _b["tags"] = {n: t for n, t in _b["tags"].items()
                      if any(m.split(".")[0] in _b["parts"] for m in NETS.get(n, ()))}
_mcu = BLOCKS[pack_tme.SHEETS["mcu"][1][0]]
_mcu["title"] = "XIAO ESP32-S3, run-feed diodes, charge LED"
# clash-free in the dry run; fine-tune in Task 8 if the PDF looks crowded
_mcu["parts"] |= {"D_M1": (17.78, 66.04, 0, None), "D_M2": (17.78, 91.44, 0, None)}

SHEETS = dict(pack_tme.SHEETS)
SHEETS["mcu"] = (_mcu["title"], pack_tme.SHEETS["mcu"][1])
ROOT = copy.deepcopy(pack_tme.ROOT)
ROOT["parts"] = {r: v for r, v in ROOT["parts"].items() if r not in _GONE}
ROOT["port_modes"] = {r: v for r, v in ROOT.get("port_modes", {}).items() if r not in _GONE}
OFFBOARD = dict(pack_tme.OFFBOARD)


def check_mcu():
    """The XIAO pin roles, both of its feeds, and the parts the pin choice relies on."""
    net_of = {p: n for n, mem in NETS.items() for p in mem}
    want = {f"U_MCU.{p}": n for p, n in MCU.items()}
    want |= {"D_M1.2": "+5V", "D_M1.1": "VMOD_5V", "D_M2.2": "VBUS", "D_M2.1": "VMOD_5V",
             "U_CHG.1": "VBUS", "U_CHG.24": "VBUS", "U_CHG.9": "CHG_CE", "R_CE.2": "GND",
             "U_LDO.3": "VMCU_IN", "U_LDO.2": "+3V3"}
    for p, n in want.items():
        assert net_of.get(p) == n, f"{p} on {net_of.get(p)}, want {n}"
    assert "U_MCU.23" in NC_PINS, "XIAO BAT+ is back-driven to ~3.3 V: it must stay unconnected"
    assert not NC_PINS & net_of.keys(), f"NC pins on nets: {NC_PINS & net_of.keys()}"
    assert not net_of["U_MCU.7"].startswith("SW"), "no cell gate on D6 (U0TXD prints at boot)"
    for i in range(1, 5):
        assert PARTS[f"R_PD{i}"][0] == "4k7", f"R_PD{i}: 4k7 against the boot pull-up"
        assert net_of[f"R_PD{i}.2"] == "GND"
    assert PARTS["U_MCU"] == XIAO and PARTS["U_CHG"][2] == pack_tme.QFN24_HAND


def check():
    import sys

    this = sys.modules[__name__]
    board.check_structure(this)
    pack_tme.check_branches(this)
    check_mcu()
    pack.check_sheets(this)
    print(f"pack_xiao ok: {len(PARTS)} parts, {len(NETS)} nets")


if __name__ == "__main__":
    check()
```

Notes for the reader:
- The module's 3V3 pad sits directly on the board `+3V3` (XC6206 on the cell diode-OR) — no
  diode on the pack, unlike the LiPo (see design doc, Power domains).
- `CHG_CE` keeps `R_CE` (10k to GND): charging is autonomous; firmware stops it over I2C.
- `R_PD1..4` become 4k7: D7 (= SW1_DRV) has a 45 kΩ pull-up at reset.
- The board USB-C keeps VBUS + CC resistors; its data pins become NC.

**Step 3: Run the self-check**
```bash
/usr/bin/python3 pack_xiao.py && /usr/bin/python3 pack_tme.py
```
Expected: `pack_xiao ok: 120 parts, 69 nets` then `pack_tme ok: 132 parts, 80 nets`.

**Step 4: Commit**
```bash
rtk git add pack_xiao.py
rtk git commit -m "hardware: pack_xiao board module (XIAO ESP32-S3 for the L072, 4k7 gate pull-downs)"
```

---

### Task 8: `pack_xiao` schematic

Same procedure as Task 4 with `BOARD=pack_xiao`; the MCU sheet is titled "XIAO ESP32-S3,
run-feed diodes, charge LED". The block keeps `"wired": {"+3V3", "GND"}` from the L072 layout —
if ERC or the preview shows a problem around the XIAO's pins 12/13 (3V3/GND), remove `"wired"` from
`_mcu` and retry. Charger sheet: the `CHG_INT`/`USB_DM`/`USB_DP` tags are gone (pins are NC now).

```bash
BOARD=pack_xiao /usr/bin/python3 tools/sch_preview.py
kicad-cli sch export pdf -o build/preview/p.pdf build/preview/pack_xiao.kicad_sch
BOARD=pack_xiao /usr/bin/make sch
kicad-cli sch erc --severity-all --exit-code-violations -o build/pack_xiao_erc.rpt kicad/pack_xiao.kicad_sch; echo "erc exit $?"
```
Expected: `erc exit 0` (fixes as in Task 4 Step 2), then commit:
```bash
rtk git add pack_xiao.py kicad/pack_xiao.kicad_sch kicad/pack_xiao-*.kicad_sch kicad/pack_xiao.kicad_pro
rtk git commit -m "hardware: pack_xiao schematic, ERC clean"
```

---

### Task 9: `pack_xiao` placement, routing, fab

Board 96 × 90 mm. Cell holders (`BT1..4`) and bead NTCs (`TH1..4`) are on the **bottom**, their
through-hole pins come up through the top; the L072 sat at (66, 77.33) (set `PLACE` in `pack_xiao.py` and delete its `# TODO(Task 9)` comment); `C_MCU1`/`C_MCU2` at
(63.5, 70)/(68, 70). The removed parts (`SW_BOOT`/`SW_RST` at x≈1.6, `J_UART1` at the right
strip, test pads, `LED_MCU`) free space.

Placement rules: rules 1-3 and 5 of Task 5 (XH connectors here: `J_PWR1`, `J_KEY1`; the board
USB-C `J_USB1` is at (87, 23, 90) — put the module's USB end on the same edge if it fits, the
design doc wants the two ports side by side), plus: `D_M1` near pad 14 with short tracks to
`+5V` and `VBUS`/`D_M2`; `C_MCU1/2` next to pad 12. DRC `pth_inside_courtyard` will flag holder
pins under the module — move the module, do not change the rule.

```bash
/usr/bin/python3 pack_xiao.py && BOARD=pack_xiao /usr/bin/make all 2>&1 | tail -30
cat fab/pack_xiao/tme_bom.csv
/usr/bin/grep -c -i -F "STM32" fab/pack_xiao/tme_bom.csv
```
Expected: `make` exits 0 with the full fab set; STM32 count `0`; `SMD0805-4K7-1%` quantity now
includes the 4 gate pull-downs (2 I2C + 4 = 6); `1N5819HW-7-F` quantity 7 (5 diode-OR + 2 run feed).
Commit:
```bash
rtk git add pack_xiao.py kicad/pack_xiao.kicad_pcb kicad/pack_xiao.kicad_sch kicad/pack_xiao-*.kicad_sch kicad/pack_xiao.kicad_pro fab/pack_xiao
rtk git commit -m "hardware: pack_xiao placed and routed, ERC/DRC clean, fab package"
```

---

### Task 10: Power model and docs

**Files:**
- Modify: `hardware/power_budget.py`
- Modify: `hardware/docs/OFFBOARD_PARTS.md`, `hardware/docs/COSTS.md`

**Step 1: `power_budget.py --xiao`** — five exact replacements (verified in a dry run):

1. Docstring usage line: `/usr/bin/python3 power_budget.py [--tme]` → `[--tme | --xiao]`.
2. Replace
   ```python
   TME = "--tme" in sys.argv[1:]   # hand-build boards: L072 + 4x INA226 + PCM5100A/PAM8302A
   ```
   with
   ```python
   XIAO = "--xiao" in sys.argv[1:]  # hand-build with the pack MCU on a XIAO ESP32-S3 (pack_xiao)
   TME = XIAO or "--tme" in sys.argv[1:]   # hand-build boards: L072 + 4x INA226 + PCM5100A/PAM8302A
   ```
3. Replace `MCU_STOP_MA = 0.00043 if TME else 0.085` with
   ```python
   # XIAO: Seeed's 14 uA deep sleep is at 3.8 V into BAT; EST for the 3V3-pad keep-alive, measure it.
   MCU_STOP_MA = 0.014 if XIAO else 0.00043 if TME else 0.085
   # XIAO run feed is the boost: ESP32-S3 ~40 mA at 3.3 V (radio off) through its ~90 % buck = ~29 mA
   # at 5 V while polling (EST); light sleep between polls when parked (EST). Measure both.
   XIAO_RUN_5V, XIAO_IDLE_5V = 30.0, 2.0
   ```
4. In `scenario()`, right after the block
   ```python
           if TME:
               ma["DAC standby"] = DAC_STANDBY
   ```
   add (at function-body indentation, i.e. outside the `if deluxe:`):
   ```python
       if XIAO:
           ma["Pack MCU (XIAO via boost)"] = from_5v(XIAO_RUN_5V)
   ```
5. After
   ```python
   if TME:
       PARKED["DAC standby"] = DAC_STANDBY
   ```
   add
   ```python
   if XIAO:
       PARKED["Pack MCU (XIAO light sleep)"] = from_5v(XIAO_IDLE_5V)
   ```
6. The `model:` print in `main()`: show `TME hand-build (XIAO pack MCU + INA226 + PCM5100A/PAM8302A)`
   when `XIAO`, the existing strings otherwise.

Run:
```bash
/usr/bin/python3 power_budget.py --xiao | tail -5
/usr/bin/python3 power_budget.py --tme | tail -4
```
Expected (`--xiao`): weekend limit 351 mA; "today's firmware, backlight on 283 mA PASS (+24 %
margin)". `--tme` unchanged: 236 mA PASS (+49 %). If `--xiao` FAILS, stop and report.

**Step 2: `docs/OFFBOARD_PARTS.md`** — add a "XIAO hand-build boards (pack_xiao, lipo_xiao)"
section in the style of the existing ones: 1× Seeed Studio XIAO ESP32-S3 (base, **not** Sense,
not Plus) per board, Botland, buy 2 + 1 spare, price/SKU "fill in at ordering"; solder note: edge
castellations with an iron, the bottom pads used on `pack_xiao` (MTDO = pad 16, MTCK = pad 20) need
pre-tinning + hot air; **BAT+ (pad 23) must not be soldered to anything**; BOOT/RESET buttons must stay
reachable. Attribution line: "symbol/footprint from Seeed-Studio/OPL_Kicad_Library (CC BY-SA 4.0)".

**Step 3: `docs/COSTS.md`** — add the XIAO boards next to the `_tme` ones: −STM32L072KZT6 (~€4.60),
−L072 support parts, +2× 1N5819HW-7-F, + XIAO (~€4.4, Botland, confirm at ordering). Follow the
file's existing table format; read it first.

**Step 4: Commit**
```bash
rtk git add power_budget.py docs/OFFBOARD_PARTS.md docs/COSTS.md
rtk git commit -m "hardware: power model --xiao, XIAO off-board part and cost notes"
```

---

### Task 11: Final verification

**Step 1: Regressions — the `_tme` boards must be unchanged**
```bash
/usr/bin/python3 pack_tme.py && /usr/bin/python3 lipo_tme.py
BOARD=pack_tme /usr/bin/make all >/dev/null && BOARD=lipo_tme /usr/bin/make all >/dev/null
rtk git status --short kicad/ fab/
```
Expected: both checks ok; `git status` shows **no** modified `pack_tme*`/`lipo_tme*` files (pack_tme
may rewrite PCB track *order* with identical geometry — if `kicad/pack_tme.kicad_pcb` shows as
modified, compare with `/usr/bin/python3 tools/pcb_diff.py HEAD:kicad/pack_tme.kicad_pcb kicad/pack_tme.kicad_pcb`
(exit 0 = same placement/nets) and `rtk git checkout kicad/pack_tme.kicad_pcb` if so; report it either way).

**Step 2: Both new boards from clean**
```bash
BOARD=lipo_xiao /usr/bin/make all && BOARD=pack_xiao /usr/bin/make all
rtk git status --short
```
Expected: exits 0; no new changes to committed files (determinism).

**Step 3: Report to the user** — a short summary: commits made, part counts, TME lists, where the
modules were placed (and which board edge the USB-C faces), any DRC/ERC compromise, the power model
numbers, and the open items below.

**Open items to hand back (not for this plan):**
- Breadboard spike, design doc "Verification / acceptance" item 3 (3V3 back-drive leakage, deep-sleep
  current, boot-time gate levels, kill sequence) — needs the user and a real XIAO.
- `mech/` insert: second USB-C slot for the module port, window for the module LED.
- Firmware notes: light-sleep between polls (the always-running XIAO is the largest single load in
  the optimized power case: ~47 mA battery-side); `gpio_hold` on lipo `KILL_DRV`; UART0 console off;
  INA226 power-down when idle; per-board ADC two-point calibration (lipo).
