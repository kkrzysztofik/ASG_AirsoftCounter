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

# _THB: bottom pads 16/20 (the only ones used) are plated holes, soldered with an iron from the back
XIAO = ("XIAO ESP32-S3", "local:XIAO_ESP32S3", "local:XIAO_ESP32S3_SMD_THB")
B5819W = ("B5819W", *pack.B5819W)
_GONE = {"C_MCU3", "C_VDDA", "R_BOOT", "C_NRST", "TP_NRST", "TP_SWDIO", "TP_SWCLK", "SW_BOOT",
         "SW_RST", "J_UART1", "R_ALERT", "R_INT_CHG", "R_LED_MCU", "LED_MCU"}

PARTS = {r: v for r, v in pack_tme.PARTS.items() if r not in _GONE}
PARTS["U_MCU"] = XIAO
PARTS["D_M1"] = B5819W   # run feed from the boost (key on)
PARTS["D_M2"] = B5819W   # run feed from USB VBUS (cable in); the charger keeps the raw VBUS
for _i in range(1, 5):
    PARTS[f"R_PD{_i}"] = ("4k7", *pack.R0805)
    PARTS[f"R_GS{_i}"] = ("240k", *pack.R0805)   # P-FET gate pull-up: 17 uA while closed; shares carrier_tme's 240k tape   # 0.3 V against a 45k boot pull-up (D7 = U0RXD)

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
TME[("240k", pack.R0805[1])] = "SMD0805-240K-1%"   # R_GS1..4, carrier_tme's tape
MODULES, VARIANTS = {}, {"standard": set()}


def assembled(variant="standard"):
    """Nothing is machine-placed on a hand-build board."""
    return []


# --- layout: pack_tme's, minus the dropped parts ----------------------------------------------
# Board grows 96×90 -> 96×112 (builder-approved 2026-10-18): the four holder bands tile the old
# field (courtyards x 7.7..85.3, end legs to x 75.75, GND pins x 81..83.4 at 21.5 mm pitch), so
# 96×90 holds no 17.9 mm flat span anywhere. The new 22 mm top strip carries the module, its two
# run diodes (east, cathodes west straight into pad 14 under the module) and the 3V3 caps (west,
# hugging pad 12); USB-C end flush on the new top edge, 28 mm clear floor left in the Pawbol box.
# The M3 pattern and every connector stay exactly at pack_tme's spots.
W, H, CORNER = pack_tme.W, 112.0, pack_tme.CORNER
# The enclosure tray's two y0-side carrier posts (mech/params.carrier_post_xy, Ø8) stand in the old
# board's margin, at board y 96: the strip clears them by a notch (left post, x -0.5) and a round
# cutout (inner post, x 82.5). check_posts() holds them to mech/params with POST_CLEAR to spare.
POST_CLEAR = 1.0
NOTCH_BL = (5.0, 90.0)
CUTOUTS = [(82.5, 96.0, 10.0)]
NETCLASS_POWER, NETCLASS_EXPECT = pack_tme.NETCLASS_POWER, pack_tme.NETCLASS_EXPECT
DEFAULT_CLEARANCE, DRC_RULES = pack_tme.DEFAULT_CLEARANCE, pack_tme.DRC_RULES
RAILS, PORT_LIB, BOTTOM = pack_tme.RAILS, pack_tme.PORT_LIB, pack_tme.BOTTOM
PTH_COMPONENT_MIN, NPTH_EXPECT = pack_tme.PTH_COMPONENT_MIN, pack_tme.NPTH_EXPECT
LABELS, GND_VIAS = pack_tme.LABELS, list(pack_tme.GND_VIAS)
TEXTS = [t for t in pack_tme.TEXTS if t[0] != "GND TX RX"]   # J_UART1 is gone
PTH_UNDER_OK, RULE_SEVERITIES = pack_tme.PTH_UNDER_OK, pack_tme.RULE_SEVERITIES
HELTEC_PADS, NPTH_XY, SENSE_IN = {}, pack_tme.NPTH_XY, pack_tme.SENSE_IN
SIZE_MM = (W, H)
HIDE_REF = tuple(r for r in pack_tme.HIDE_REF if r not in _GONE)
PLACE = {r: v for r, v in pack_tme.PLACE.items() if r not in _GONE}
REF_AT = {r: v for r, v in pack_tme.REF_AT.items() if r not in _GONE}
# Module rot 180, USB end flush at the new top edge y 112 (the lipo trick); power column
# (pads 8-14) lands at x 62.7..65.5, NTC/I2C column at 28.7..31.3. D_M1/D_M2 east in the free
# corridor, C_MCU1/2 west at pad 12, TPs just south of the module under its bottom pads.
# Module 2 mm west of the inner post's cutout (edge pads 1 mm clear of it).
PLACE |= {"U_MCU": (76.0, 90.85, 180), "D_M1": (81.5, 109.0, 0), "D_M2": (81.5, 105.2, 0),
          "C_MCU1": (55.5, 103.9, 90), "C_MCU2": (55.5, 99.5, 90),
          "TP_SDA": (66.5, 88.6, 0), "TP_SCL": (69.1, 88.6, 0)}
REF_AT |= {"U_MCU": (88.5, 106.0, 90), "C_MCU2": (52.0, 99.5, 0)}

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


def check_posts():
    """Every tray carrier post that reaches the board passes it through NOTCH_BL or a CUTOUT."""
    import math
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent / "mech"))
    import params as P  # noqa: PLC0415  (mech's plain-number parameters, no CAD imports)

    r = P.POST_R + POST_CLEAR
    for px, py in P.carrier_post_xy():
        # tray -> board: pack_xiao shares the pack's frame (same M3 holes), it only runs further in y
        x, y = px - P.PACK_ORIGIN[0], P.PACK_ORIGIN[1] + P.PACK[1] - py
        if math.hypot(x - min(max(x, 0), W), y - min(max(y, 0), H)) >= r:
            continue  # clear of the board
        in_notch = x + r <= NOTCH_BL[0] and y - r >= NOTCH_BL[1]
        in_cut = any(math.hypot(x - cx, y - cy) + r <= d / 2 for cx, cy, d in CUTOUTS)
        assert in_notch or in_cut, f"carrier post at board ({x:.1f}, {y:.1f}) hits the board"


def check():
    import sys

    this = sys.modules[__name__]
    board.check_structure(this)
    pack_tme.check_branches(this)
    check_mcu()
    check_posts()
    pack.check_sheets(this)
    print(f"pack_xiao ok: {len(PARTS)} parts, {len(NETS)} nets")


if __name__ == "__main__":
    check()
