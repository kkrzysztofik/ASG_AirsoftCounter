"""AirsoftCounter pack board, variant B: no pack MCU, the Heltec is the I2C master.

Derived from pack.py (variant A) by import and edit: the MCU block, its internal I2C pull-ups and
the default-off switch pull-downs go, and a TCA9534 expander (0x21) plus an ADS1115 cell ADC
(0x48) come in on the carrier I2C bus. gen_sch.py / gen_pcb.py read it through board.py
(BOARD=pack_b), so run the generators with `make BOARD=pack_b ...`. Run this file to self-check
(`/usr/bin/python3 pack_b.py`).

check() runs board.check_structure plus check_branches (the same per-cell branch order as variant
A). Source of truth: docs/plans/2026-10-02-pack-board-variant-b-design.md.
"""
import pack

NAME = "pack_b"
TITLE = "AirsoftCounter v2 pack (no MCU)"

# Footprint tuples shared with variant A.
R0805 = pack.R0805
C0805 = pack.C0805
SMA = pack.SMA
B5819W = pack.B5819W
SS34 = pack.SS34
SOD123 = pack.SOD123
SOT23 = pack.SOT23
SOT23_3 = pack.SOT23_3
SOT23_6 = pack.SOT23_6
QFN24 = pack.QFN24
UQFN16 = pack.UQFN16
L1210 = pack.L1210
LRN6045 = pack.LRN6045
LED0805 = pack.LED0805
XH2 = pack.XH2
XH6 = pack.XH6
USBC = pack.USBC
C1206 = pack.C1206
R1206 = pack.R1206
FUSE1206 = pack.FUSE1206
HOLDER = pack.HOLDER
NTC_BEAD = pack.NTC_BEAD
MH = pack.MH
TSSOP16 = "Package_SO:TSSOP-16_4.4x5mm_P0.65mm"
VSSOP10 = "Package_SO:VSSOP-10_3x3mm_P0.5mm"

# Variant A parts the MCU block carried and variant B drops. The internal I2C pull-ups go because
# the pack chips now sit on the carrier bus; R_PD* become R_PU* (1M pull-up, default-on).
_REMOVED = ({"U_MCU", "C_MCU1", "C_MCU2", "C_NRST", "R_BOOT", "SW_BOOT", "SW_RST",
             "R_LED_MCU", "LED_MCU", "TP_SWDIO", "TP_SWCLK", "TP_NRST", "TP_GND",
             "R_SCL_INT", "R_SDA_INT", "R_PWRDN"}
            | {f"R_PD{i}" for i in range(1, 5)})

PARTS = {r: v for r, v in pack.PARTS.items() if r not in _REMOVED}
PARTS |= {
    "U_EXP": ("TCA9534PWR", "Interface_Expansion:TCA9534", TSSOP16),   # I/O expander 0x21
    "C_EXP1": ("100nF", *C0805),
    "U_ADC": ("ADS1115IDGSR", "Analog_ADC:ADS1115IDGS", VSSOP10),      # 4-ch ADC 0x48
    "C_ADC1": ("100nF", *C0805),
    "R_PWRDN1": ("10k", *R0805),   # VBAT_SW -> PAC1934 PWRDN
    "R_PWRDN2": ("47k", *R0805),   # PAC1934 PWRDN -> GND
}
for i in range(1, 5):
    PARTS[f"R_PU{i}"] = ("1M", *R0805)   # BSS138 gate pull-up: cell ON until the expander writes 0

DNP = set(pack.DNP)                       # R_BYP1..4 bring-up bypasses stay DNP
NOT_ASSEMBLED = {f"BT{i}" for i in range(1, 5)} | {f"TH{i}" for i in range(1, 5)} | {"TH_CHG"}
NC_PINS = ((pack.NC_PINS
            - {"U_MCU.1", "U_MCU.2", "U_MCU.3", "U_MCU.19", "U_MCU.20", "U_MCU.21", "U_MCU.32"})
           | {"U_EXP.13", "U_ADC.2",                       # spare /INT, ADC ALERT/RDY unused
              "J_USB1.A6", "J_USB1.B6", "J_USB1.A7", "J_USB1.B7"})  # D+/D- no longer used
NC_PARTS = set()

LCSC = {k: v for k, v in pack.LCSC.items()
        if k not in {("STM32C071KBTx", pack.LQFP32), ("100k", R0805[1]), ("4k7", R0805[1]),
                     ("green", LED0805), ("TS-1088-AR02016", pack.TACT)}}
LCSC |= {
    ("TCA9534PWR", TSSOP16): "C783615",     # E TI TCA9534PWR, TSSOP-16 (2026-10-02)
    ("ADS1115IDGSR", VSSOP10): "C37593",    # E TI ADS1115IDGSR, VSSOP-10 (2026-10-02)
    ("47k", R0805[1]): "C17713",            # B UNI-ROYAL 0805W8F4702T5E (PWRDN divider)
}

# --- nets: variant A with the MCU pins replaced by expander / ADC pins -----------------------
NETS = {n: list(m) for n, m in pack.NETS.items()}
for _n in ("SCL_INT", "SDA_INT", "USB_DP", "USB_DM", "NRST", "BOOT0", "SWDIO",
           "LED_MCU_DRV", "LED_MCU_A"):
    del NETS[_n]

NETS["+3V3"] = ([p for p in NETS["+3V3"]
                 if p not in {"U_MCU.4", "C_MCU1.1", "C_MCU2.1", "SW_BOOT.2",
                              "R_SCL_INT.1", "R_SDA_INT.1", "R_PWRDN.1"}]
                + ["U_EXP.16", "C_EXP1.1", "U_ADC.8", "C_ADC1.1", "U_EXP.1",
                   *(f"R_PU{i}.2" for i in range(1, 5))])   # A0 = 1 -> address 0x21
NETS["GND"] = ([p for p in NETS["GND"]
                if p not in {"U_MCU.5", "C_MCU1.2", "C_MCU2.2", "C_NRST.2", "SW_RST.2",
                             "R_BOOT.2", "LED_MCU.1", "TP_GND.1",
                             *(f"R_PD{i}.2" for i in range(1, 5))}]
               + ["U_EXP.2", "U_EXP.3", "U_EXP.8", "C_EXP1.2", "U_ADC.1", "U_ADC.3",
                  "C_ADC1.2", "R_PWRDN2.2"])                 # A1 = A2 = 0, ADDR = GND -> 0x48
NETS["VBAT_SW"] = NETS["VBAT_SW"] + ["R_PWRDN1.1"]
NETS["CHG_CE"] = ["U_CHG.9", "R_CE.1", "U_EXP.10"]          # /CE  -> P5
NETS["CHG_INT"] = ["U_CHG.7", "R_INT_CHG.1", "U_EXP.11"]    # /INT -> P6
NETS["MON_ALERT"] = ["U_MON.1", "R_ALERT.2", "U_EXP.12"]    # ALERT -> P7
NETS["MON_PWRDN"] = ["U_MON.16", "R_PWRDN1.2", "R_PWRDN2.1"]
NETS["SDA_EXT"] = ["J_PWR1.5", "U_MON.5", "U_CHG.6", "U_EXP.15", "U_ADC.9"]
NETS["SCL_EXT"] = ["J_PWR1.6", "U_MON.4", "U_CHG.5", "U_EXP.14", "U_ADC.10"]
NETS["NTC_PWR"] = ["U_EXP.9", *(f"TH{i}.1" for i in range(1, 5))]   # P4 divider supply

SENSE_IN = pack.SENSE_IN
# Expander P0-P3 drive the four gates, ADC AIN0-3 read the four dividers.
for i in range(1, 5):
    NETS[f"SW{i}_G"] = [f"Q_N{i}.1", f"R_PU{i}.1", f"R_SW{i}.2"]
    NETS[f"SW{i}_DRV"] = [f"R_SW{i}.1", f"U_EXP.{3 + i}"]
    NETS[f"NTC{i}"] = [f"TH{i}.2", f"R_NTC{i}.1", f"U_ADC.{3 + i}"]


# --- layout: unchanged tables reused from variant A, the MCU block rebuilt --------------------
W, H, CORNER = pack.W, pack.H, pack.CORNER
NETCLASS_POWER = pack.NETCLASS_POWER
RAILS = pack.RAILS
PORT_LIB = pack.PORT_LIB
NETCLASS_EXPECT = pack.NETCLASS_EXPECT
DRC_RULES = pack.DRC_RULES
BOTTOM = pack.BOTTOM
GND_VIAS = pack.GND_VIAS
HELTEC_PADS = pack.HELTEC_PADS
LABELS = pack.LABELS
TEXTS = list(pack.TEXTS)
SIZE_MM = pack.SIZE_MM
NPTH_XY = pack.NPTH_XY
NPTH_EXPECT = pack.NPTH_EXPECT
PTH_COMPONENT_MIN = pack.PTH_COMPONENT_MIN
HIDE_REF = ()
MODULES = {}
VARIANTS = {"standard": set()}


def _copy_blocks():
    out = []
    for b in pack.BLOCKS:
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
# Block 0/1: the internal I2C (SCL_INT/SDA_INT) is gone; those chips now tag the carrier bus.
BLOCKS[0]["tags"] = pack._tags(["SDA_EXT", "SCL_EXT", "CHG_INT", "CHG_CE", "SYS", "CC2",
                                "LED_STAT_A"], 12.7, 118.11)
# Block 1: the internal I2C pull-ups and the +3V3 PWRDN pull-up go with the MCU.
for _r in ("R_SCL_INT", "R_SDA_INT", "R_PWRDN"):
    BLOCKS[1]["parts"].pop(_r, None)
BLOCKS[1]["tags"] = pack._tags(["SNS_F1", "SNS_F2", "SNS_F3", "SNS_F4",
                                "SNS_S1", "SNS_S2", "SNS_S3", "SNS_S4",
                                "SDA_EXT", "SCL_EXT", "MON_ALERT", "MON_PWRDN", "SYS"],
                               12.7, 137.16, per_row=6)
# Block 2: the expander and the cell ADC replace the STM32 and its support.
BLOCKS[2] = {
    "title": "TCA9534 I/O expander and ADS1115 cell ADC", "at": (381.0, 12.7),
    "size": (139.7, 190.5),
    "parts": {
        "U_EXP": (33.02, 40.64, 0, None), "C_EXP1": (12.7, 25.4, 0, None),
        "U_ADC": (33.02, 101.6, 0, None), "C_ADC1": (12.7, 95.25, 0, None),
        "R_PWRDN1": (66.04, 88.9, 0, None), "R_PWRDN2": (66.04, 101.6, 0, None),
    },
    # the ADS1115 stock Reference sits above VDD and blocks the +3V3 port; move it aside
    "fields": {"U_ADC": {"Reference": (10.16, -7.62, "left"),
                          "Value": (10.16, 7.62, "left")}},
    "tags": pack._tags(["SW1_DRV", "SW2_DRV", "SW3_DRV", "SW4_DRV",
                        "NTC1", "NTC2", "NTC3", "NTC4", "NTC_PWR",
                        "CHG_CE", "CHG_INT", "MON_ALERT", "MON_PWRDN", "SDA_EXT", "SCL_EXT"],
                       12.7, 158.75, per_row=5),
}
# Cell blocks: the 100k gate pull-down becomes a 1M pull-up.
for _b in BLOCKS:
    for _i in range(1, 5):
        if f"R_PD{_i}" in _b.get("parts", {}):
            _b["parts"][f"R_PU{_i}"] = _b["parts"].pop(f"R_PD{_i}")

REF_AT = {r: v for r, v in pack.REF_AT.items() if r != "R_SDA_INT"}
REF_AT["R_PWRDN2"] = (35.0, 89.3, 0)   # default ref row overlaps R_PWRDN1's text


def _pcb_place():
    place = pack._pcb_place()
    for r in list(place):
        if r in _REMOVED:
            del place[r]
    place |= {
        # clear the space above U_MON's top sense pads for the Kelvin escapes
        "C_MON1": (57.5, 29.5, 0),
        # expander and ADC take the MCU's band-4 strip; their caps reuse the old MCU caps' spots
        "U_EXP": (67.0, 77.33, 0), "C_EXP1": (63.5, 70, 0),
        "U_ADC": (74.5, 77.33, 0), "C_ADC1": (68, 70, 0),
        # freed bottom-edge row: gate pull-ups and the PAC1934 PWRDN divider
        "R_PU1": (14, 87.4, 0), "R_PU2": (18, 87.4, 0),
        "R_PU3": (22, 87.4, 0), "R_PU4": (26, 87.4, 0),
        "R_PWRDN1": (31, 87.4, 0), "R_PWRDN2": (35, 87.4, 0),
    }
    return place


PLACE = _pcb_place()


def assembled(variant="standard"):
    """Refs JLCPCB places: everything except DNP parts, hand-soldered/off-board parts and holes."""
    return [r for r, (_, sym, _) in PARTS.items()
            if r not in DNP | NOT_ASSEMBLED and sym != "Mechanical:MountingHole"]


def check_branches():
    """Every cell: holder+ -> fuse -> shunt -> back-to-back P-FET -> pack rail, in that order, with
    the PAC1934 sensing across the shunt through its own 10R split off the shunt pads."""
    net_of = {p: n for n, m in NETS.items() for p in m}
    for i in range(1, 5):
        s_p, s_m = SENSE_IN[i]
        assert net_of[f"BT{i}.1"] == net_of[f"F{i}.1"], f"cell {i}: holder+ not on fuse"
        assert net_of[f"F{i}.2"] == net_of[f"R_SH{i}.1"] == net_of[f"R_SNSF{i}.1"], \
            f"cell {i}: fuse -> shunt"
        assert net_of[f"R_SNSF{i}.2"] == net_of[f"U_MON.{s_p}"], f"cell {i}: sense not on SENSE+"
        assert net_of[f"R_SH{i}.2"] == net_of[f"Q_A{i}.3"] == net_of[f"R_SNSS{i}.1"], \
            f"cell {i}: shunt -> FET"
        assert net_of[f"R_SNSS{i}.2"] == net_of[f"U_MON.{s_m}"], f"cell {i}: sense not on SENSE-"
        assert net_of[f"Q_A{i}.2"] == net_of[f"Q_B{i}.2"], f"cell {i}: FET sources not common"
        assert net_of[f"Q_B{i}.3"] == "VPACK", f"cell {i}: FET not on the pack rail"
        assert net_of[f"BT{i}.2"] == "GND", f"cell {i}: holder- not on GND"
        assert net_of[f"D_OR{i}.2"] == net_of[f"F{i}.2"], f"cell {i}: diode-OR not after the fuse"
        assert net_of[f"R_PU{i}.2"] == "+3V3", f"cell {i}: gate pull-up not to +3V3"


def check():
    import sys

    import board  # pyright: ignore[reportMissingImports]  # local sibling module
    board.check_structure(sys.modules[__name__])
    check_branches()
    print(f"pack_b ok: {len(PARTS)} parts, {len(NETS)} nets")


if __name__ == "__main__":
    check()
