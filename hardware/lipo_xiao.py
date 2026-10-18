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
HIDE_REF = tuple(r for r in lipo_tme.HIDE_REF if r not in _GONE) + \
    ("D_KA", "C_LDO1", "C_MCU1", "C_MCU2", "U_LDO")
PLACE = {r: v for r, v in lipo_tme.PLACE.items() if r not in _GONE}
REF_AT = {r: v for r, v in lipo_tme.REF_AT.items() if r not in _GONE}
# Module in the L072's old area, USB-C edge flush with the board bottom (the only free edge:
# left has J_IN1, top J_BAL1 + the tap row, right J_KEY1/J_PWR1), D0..D2 column facing the
# C_VIN column at x 33. D_KA/D_M1 on the module's power-pad side; its decoupling caps and the
# AP7381 parts + test pads stack in the strip left of the module (courtyard-solved, task 5).
PLACE |= {"U_MCU": (30.9, 28.89, 180),
          "D_KA": (11.35, 42.0, 90), "D_M1": (11.4, 47.3, 270),
          "C_MCU1": (9.0, 43.5, 90), "C_MCU2": (10.6, 32.25, 90),
          "C_LDO2": (5.2, 39.5, 90), "C_LDO1": (8.2, 40.0, 0),
          "TP_3V3": (8.2, 31.5, 0), "TP_GND": (11.0, 28.9, 0),
          "C_VIN3": (33.7, 41.5, 0), "C_VIN4": (33.7, 46.2, 0)}
REF_AT |= {"U_MCU": (24.0, 25.5, 0), "D_M1": (9.45, 47.3, 90), "C_LDO2": (1.6, 42.0, 90)}

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
