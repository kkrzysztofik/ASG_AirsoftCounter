"""AirsoftCounter LiPo board, hand-build TME variant: iron-only, everything from TME.

Derived from lipo.py by import and edit: STM32L072KZT6 for the C071 (the L072 keeps the
same LQFP-32 and adds crystal-less USB), AP7381-33SA-7 for the HT7533-1 (SOT-23), and a TME
table instead of LCSC (nothing is machine-placed). gen_sch.py / gen_pcb.py read it through
board.py (`make BOARD=lipo_tme ...`). Run this file to self-check (`/usr/bin/python3
lipo_tme.py`).

Source of truth: docs/plans/2026-10-02-tme-hand-build-design.md.
"""
import board
import lipo
import tme

NAME = "lipo_tme"
TITLE = "AirsoftCounter v2 LiPo (hand-build)"

# Footprint tuples shared with the JLC original.
LQFP32, SOT23 = lipo.LQFP32, lipo.SOT23

PARTS = dict(lipo.PARTS)
PARTS["U_MCU"] = ("STM32L072KZT6", "MCU_ST_STM32L0:STM32L072KZTx", LQFP32)
PARTS["U_LDO"] = ("AP7381-33SA-7", "Regulator_Linear:AP7381-33SA-7", SOT23)
PARTS["C_MCU3"] = ("100nF", *lipo.C0805)      # second VDD pin (17)
PARTS["C_VDDA"] = ("1uF", *lipo.C0805)        # VDDA (5); value per the design doc's Parts section
PARTS["TP_BOOT0"] = ("BOOT0", "Connector:TestPoint", lipo.TP)
PARTS["TP_SWCLK"] = ("SWCLK", *lipo.PARTS["TP_SWCLK"][1:])
# TPS563200 for the TPS54302 (TME had none, 2026-10-02): same SOT-23-6 pins, but VFB 0.765 V, 2.2-4.7 uH
# and VIN 17 V max (19 V abs): 3S tops out at 12.6 V. 0.765 x (1 + 22/5.1) = 4.07 V, x (1 + 56/10) = 5.05 V.
for _u, _l in (("U_BA", "L_A"), ("U_BB", "L_B")):
    PARTS[_u] = ("TPS563200DDCR", "Regulator_Switching:TPS563200", lipo.TSOT23_6)
    PARTS[_l] = ("3u3", "Device:L", lipo.LRN6045)
PARTS["R_FBA1"] = ("22k", *lipo.R0805)
PARTS["R_FBB1"] = ("56k", *lipo.R0805)

# AP7381-33SA-7 SOT-23: 1 VI, 2 VO, 3 GND (the HT7533-1 was 1 GND, 2 VIN, 3 VOUT).
LDO_VIN = "U_LDO.1"
TAP_ADC_PIN = {1: "U_MCU.7", 2: "U_MCU.8", 3: "U_MCU.9"}   # PA1-PA3

NETS = {n: [p for p in mem if not p.startswith(("U_MCU.", "U_LDO."))]
        for n, mem in lipo.NETS.items()}
NETS["VIN"] += ["U_LDO.1"]
NETS["+3V3"] += ["U_LDO.2", "U_MCU.1", "U_MCU.17", "U_MCU.5", "C_MCU3.1", "C_VDDA.1"]
NETS["GND"] += ["U_LDO.3", "U_MCU.16", "U_MCU.32", "C_MCU3.2", "C_VDDA.2"]
NETS["NRST"] += ["U_MCU.4"]
NETS["BOOT0"] = ["U_MCU.31", "R_BOOT.1", "TP_BOOT0.1"]       # dedicated BOOT0 pin
NETS["SWCLK"] = ["U_MCU.24", "TP_SWCLK.1"]
NETS["SWDIO"] = ["U_MCU.23", "TP_SWDIO.1"]
NETS["SCL_EXT"] = ["U_MCU.29", "J_PWR1.6"]                   # I2C1, the bootloader port
NETS["SDA_EXT"] = ["U_MCU.30", "J_PWR1.5"]
NETS["KILL_DRV"] = ["R_KILL.1", "U_MCU.14"]                  # PB0
for i in (1, 2, 3):
    NETS[f"TAP{i}_ADC"] += [TAP_ADC_PIN[i]]
# Unused L072 pins: PC14/15, PA0/PA4-7, PB1, PA8-12, PA15, PB3-5.
NC_PINS = {f"U_MCU.{p}" for p in (2, 3, 6, 10, 11, 12, 13, 15, 18, 19, 20, 21, 22, 25, 26, 27, 28)}

DNP, NC_PARTS = set(lipo.DNP), set()
# Test pads and the input pigtail are copper only (not bought, not in the BOM export), same as the
# JLC board: gen_sch marks them in_bom=no and gen_pcb must agree or DRC flags a parity mismatch.
NOT_ASSEMBLED = set(lipo.NOT_ASSEMBLED) | {"TP_BOOT0"}
# Not bought at TME: test pads and the input pigtail's pads are copper only.
NOT_TME = {"J_IN1", "TP_SWDIO", "TP_SWCLK", "TP_NRST", "TP_3V3", "TP_GND", "TP_BOOT0"}
LCSC = {}
_KEYS = {(v, fp) for r, (v, _, fp) in PARTS.items() if r not in NOT_TME and fp != lipo.MH}
TME = tme.from_lcsc(lipo.LCSC, _KEYS)
TME |= {
    ("STM32L072KZT6", LQFP32): "STM32L072KZT6",
    ("AP7381-33SA-7", SOT23): "AP7381-33SA-7",
    ("1uF", lipo.C0805[1]): "CL21B105KAFNNNE",
    ("TPS563200DDCR", lipo.TSOT23_6): "TPS563200DDCR",
    ("3u3", lipo.LRN6045): "SRN6045-3R3Y",            # plain SRN6045, Isat 5 A; fits the TA pads
    ("22k", lipo.R0805[1]): "SMD0805-22K-1%",
    ("56k", lipo.R0805[1]): "SMD0805-56K-1%",
}
MODULES, VARIANTS = {}, {"standard": set()}


def assembled(variant="standard"):
    """Nothing is machine-placed on a hand-build board."""
    return []


# --- layout: reused from lipo by assignment; edited where the parts above need it ------------
W, H, CORNER = lipo.W, lipo.H, lipo.CORNER
NETCLASS_POWER = lipo.NETCLASS_POWER
RAILS = lipo.RAILS
PORT_LIB = lipo.PORT_LIB
NETCLASS_EXPECT = lipo.NETCLASS_EXPECT
DRC_RULES = lipo.DRC_RULES
BOTTOM = lipo.BOTTOM
GND_VIAS = lipo.GND_VIAS
HELTEC_PADS = lipo.HELTEC_PADS
LABELS = lipo.LABELS
TEXTS = list(lipo.TEXTS)
SIZE_MM = lipo.SIZE_MM
NPTH_XY = lipo.NPTH_XY
HIDE_REF = lipo.HIDE_REF + ("TP_BOOT0",)
PLACE = dict(lipo.PLACE)
PLACE |= {
    # L072 VDD/VDDA decoupling in the free strip right of the MCU; TP_BOOT0 joins the test-pad row.
    "C_MCU3": (19.5, 33, 0), "C_VDDA": (24.5, 33, 0),
    "TP_BOOT0": (14.8, 47, 0),
}
REF_AT = dict(lipo.REF_AT)
REF_AT |= {"C_MCU3": (19.5, 31.3, 0), "C_VDDA": (24.5, 34.5, 0)}
_tags = lipo._tags


def _copy_blocks():
    out = []
    for b in lipo.BLOCKS:
        nb = dict(b)
        nb["parts"] = dict(b["parts"])
        if "tags" in b:
            nb["tags"] = {n: list(t) for n, t in b["tags"].items()}
        if "fields" in b:
            nb["fields"] = {r: dict(f) for r, f in b["fields"].items()}
        if "flags" in b:
            nb["flags"] = list(b["flags"])
        if "wired" in b:
            nb["wired"] = set(b["wired"])
        out.append(nb)
    return out


BLOCKS = _copy_blocks()
# MCU block: the L072 adds two supply caps and a dedicated BOOT0 test pad.
_mcu = next(b for b in BLOCKS if b["title"].startswith("Always-on"))
_mcu["title"] = "Always-on 3V3, STM32L072, SWD pads"
_mcu["parts"] |= {
    "C_MCU3": (30.48, 58.42, 0, None),     # pin 17 VDD
    "C_VDDA": (30.48, 76.2, 0, None),      # pin 5 VDDA
    "TP_BOOT0": (106.68, 101.6, 0, None),
}
_mcu["fields"]["TP_BOOT0"] = {"Reference": (5.08, -2.54, "left"),
                               "Value": (5.08, 2.54, "left")}


def check_mcu():
    """The L072 pin roles this board relies on."""
    net_of = {p: n for n, mem in NETS.items() for p in mem}
    want = {"U_MCU.1": "+3V3", "U_MCU.17": "+3V3", "U_MCU.5": "+3V3", "U_MCU.16": "GND",
            "U_MCU.32": "GND", "U_MCU.4": "NRST", "U_MCU.31": "BOOT0", "U_MCU.23": "SWDIO",
            "U_MCU.24": "SWCLK", "U_MCU.29": "SCL_EXT", "U_MCU.30": "SDA_EXT",
            "U_LDO.1": "VIN", "U_LDO.2": "+3V3", "U_LDO.3": "GND"}
    for p, n in want.items():
        assert net_of.get(p) == n, f"{p} on {net_of.get(p)}, want {n}"


def check():
    import sys

    this = sys.modules[__name__]
    board.check_structure(this)
    lipo.check_power_path(this)
    check_mcu()
    print(f"lipo_tme ok: {len(PARTS)} parts, {len(NETS)} nets")


if __name__ == "__main__":
    check()
