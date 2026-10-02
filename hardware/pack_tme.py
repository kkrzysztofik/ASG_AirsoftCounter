"""AirsoftCounter pack board, hand-build TME variant: iron-only, everything from TME.

Derived from pack.py by import and edit. The PAC1934 is replaced by four INA228s (one per cell,
their own 10R Kelvin split and ALERTs wired together), the C071 by an STM32L072KZT6 (the internal
bus moves to I2C3 on PA8/PB4, the carrier link to I2C1 on PB6/PB7), the BQ25601 onto the
hand-solder QFN footprint, the MT3608 boost by an MCP1640 (no catch diode), the SMD USB-C by a
through-hole USB4085 and the SMD tact switches by THT 6x6 ones. gen_sch.py / gen_pcb.py read it
through board.py (`make BOARD=pack_tme ...`). Run this file to self-check.

Source of truth: docs/plans/2026-10-02-tme-hand-build-design.md.
"""
import board
import pack
import tme

NAME = "pack_tme"
TITLE = "AirsoftCounter v2 pack (hand-build)"

LQFP32, SOT23_6, R0805, C0805 = pack.LQFP32, pack.SOT23_6, pack.R0805, pack.C0805
VSSOP10 = "Package_SO:VSSOP-10_3x3mm_P0.5mm"
QFN24_HAND = "local:QFN-24-1EP_4x4mm_P0.5mm_EP2.6x2.6mm_HandSolder"
USB_THT = "Connector_USB:USB_C_Receptacle_GCT_USB4085"
TACT_THT = "Button_Switch_THT:SW_PUSH_6mm"

# Variant A parts the hand build drops or replaces.
_REMOVED = {"U_MON", "R_PWRDN", "D1"}
PARTS = {r: v for r, v in pack.PARTS.items() if r not in _REMOVED}
PARTS["U_CHG"] = ("BQ25601RTWT", "Battery_Management:BQ25601", QFN24_HAND)
PARTS["U_MCU"] = ("STM32L072KZT6", "MCU_ST_STM32L0:STM32L072KZTx", LQFP32)
PARTS["C_MCU3"] = ("100nF", *C0805)          # second VDD pin (17)
PARTS["C_VDDA"] = ("1uF", *C0805)            # VDDA (5)
PARTS["J_USB1"] = ("USB4085-GF-A", pack.PARTS["J_USB1"][1], USB_THT)
PARTS["SW_BOOT"] = ("TACT 6x6", "Switch:SW_Push", TACT_THT)
PARTS["SW_RST"] = ("TACT 6x6", "Switch:SW_Push", TACT_THT)
PARTS["U1"] = ("MCP1640T-I/CHY", "Regulator_Switching:MCP1640x-xCHY", SOT23_6)
PARTS["L1"] = ("4u7 2A", "Device:L", pack.LRN6045)   # MCP1640 wants 4.7 uH (no catch diode)
PARTS["R_FB2"] = ("24k", *R0805)                     # 1.21 V x (1 + 75/24) = 4.99 V
PARTS["TH_CHG"] = ("10k NTC 0603", *PARTS["TH_CHG"][1:])
for i in range(1, 5):
    PARTS[f"U_MON{i}"] = ("INA228AIDGSR", "Sensor_Energy:INA228", VSSOP10)
    PARTS[f"C_MON{i}"] = ("100nF", *C0805)

DNP = set(pack.DNP)   # R_BYP1..4 bring-up bypasses stay DNP
# Holders and bead NTCs come from LCSC (see fab/offboard), and the test pads are copper only. TH_CHG
# is now bought at TME, so unlike variant A it stays in the BOM.
NOT_TME = ({f"BT{i}" for i in range(1, 5)} | {f"TH{i}" for i in range(1, 5)}
           | {"TP_SWDIO", "TP_SWCLK", "TP_NRST", "TP_GND"})
NOT_ASSEMBLED = set(pack.NOT_ASSEMBLED) - {"TH_CHG"}
NC_PARTS = set()
NC_PINS = ({p for p in pack.NC_PINS if not p.startswith(("U_MCU.", "U1."))}
           | {f"U_MCU.{p}" for p in (2, 3, 19, 20)})
LCSC = {}
_KEYS = {(v, fp) for r, (v, sym, fp) in PARTS.items()
         if sym != "Mechanical:MountingHole" and r not in DNP | NOT_TME}
TME = tme.from_lcsc(pack.LCSC, _KEYS)
TME |= {
    ("BQ25601RTWT", QFN24_HAND): "BQ25601RTWT",
    ("STM32L072KZT6", LQFP32): "STM32L072KZT6",
    ("INA228AIDGSR", VSSOP10): "INA228AIDGSR",
    ("USB4085-GF-A", USB_THT): "USB4085-GF-A",
    ("TACT 6x6", TACT_THT): "B3F-1000",
    ("MCP1640T-I/CHY", SOT23_6): "MCP1640T-I/CHY",
    ("4u7 2A", pack.LRN6045): "SRN60454R7Y-BOU-0",
    ("24k", R0805[1]): "0805W8F2402T5E",
    ("10k NTC 0603", R0805[1]): "NTCS0603E3103FLT",
}
MODULES, VARIANTS = {}, {"standard": set()}


def assembled(variant="standard"):
    """Nothing is machine-placed on a hand-build board."""
    return []


# --- nets: variant A with the MCU/monitor/boost pins replaced ----------------------------------
NETS = {n: [p for p in mem if not p.startswith(("U_MCU.", "U_MON.", "U1.", "D1.", "R_PWRDN."))]
        for n, mem in pack.NETS.items()}
del NETS["MON_PWRDN"]

MCU = {"+3V3": [1, 5, 17], "GND": [16, 32], "NRST": [4], "BOOT0": [31], "SWDIO": [23],
       "SWCLK": [24], "USB_DM": [21], "USB_DP": [22], "SCL_INT": [18], "SDA_INT": [27],
       "SCL_EXT": [29], "SDA_EXT": [30], "NTC_PWR": [10], "CHG_CE": [15], "CHG_INT": [26],
       "MON_ALERT": [28], "LED_MCU_DRV": [25],
       "NTC1": [6], "NTC2": [7], "NTC3": [8], "NTC4": [9],
       "SW1_DRV": [11], "SW2_DRV": [12], "SW3_DRV": [13], "SW4_DRV": [14]}
for net, pins in MCU.items():
    NETS.setdefault(net, []).extend(f"U_MCU.{p}" for p in pins)
NETS["SWCLK"] = NETS.get("SWCLK", []) + ["TP_SWCLK.1"]       # BOOT0 is its own pin now
NETS["BOOT0"] = [p for p in NETS["BOOT0"] if p != "TP_SWCLK.1"]
NETS["+3V3"] += ["C_MCU3.1", "C_VDDA.1", *(f"U_MON{i}.6" for i in range(1, 5)),
                 *(f"C_MON{i}.1" for i in range(3, 5)), "U_MON2.2"]   # C_MON1/2 already wired
NETS["GND"] += ["C_MCU3.2", "C_VDDA.2", "U1.2", *(f"U_MON{i}.7" for i in range(1, 5)),
                *(f"C_MON{i}.2" for i in range(3, 5)), *(f"U_MON{i}.1" for i in range(1, 5)),
                "U_MON1.2"]
NETS["SDA_INT"] += [*(f"U_MON{i}.4" for i in range(1, 5)), "U_MON3.2"]
NETS["SCL_INT"] += [*(f"U_MON{i}.5" for i in range(1, 5)), "U_MON4.2"]
NETS["MON_ALERT"] += [f"U_MON{i}.3" for i in range(1, 5)]
NETS["VBAT_SW"] += ["U1.6", "U1.3"]                 # MCP1640 VIN and EN tied to the switched rail
NETS["SW"] = ["U1.1", "L1.2"]
NETS["FB"] = ["U1.4", "R_FB1.2", "R_FB2.1"]
NETS["+5V"] += ["U1.5"]
for i in range(1, 5):
    NETS[f"SNS_F{i}"] = list(NETS[f"SNS_F{i}"]) + [f"U_MON{i}.10", f"U_MON{i}.8"]
    NETS[f"SNS_S{i}"] = list(NETS[f"SNS_S{i}"]) + [f"U_MON{i}.9"]


# --- layout: reused from variant A by assignment; edited in T5.2 --------------------------------
W, H, CORNER = pack.W, pack.H, pack.CORNER
NETCLASS_POWER = tuple(p for p in pack.NETCLASS_POWER if p != "+5V")   # 82 mA peak; U1's fine VOUT pad
NETCLASS_EXPECT = tuple((n, [0.8, 0.2] if n != "+5V" and w == 0.8 else [0.25, 0.15])
                        for n, (w, _) in pack.NETCLASS_EXPECT)
DEFAULT_CLEARANCE = 0.15   # the USB4085's own THT pads sit 0.15 mm apart
RAILS = pack.RAILS
PORT_LIB = pack.PORT_LIB
DRC_RULES = {**pack.DRC_RULES, "min_clearance": 0.15}   # USB4085 THT pads sit 0.15 mm apart
BOTTOM = pack.BOTTOM
_CELL_X, _CELL_Y = pack._CELL_X, pack._CELL_Y
_HOLDER_NPTH = pack._HOLDER_NPTH
PTH_COMPONENT_MIN = 0.4   # the through-hole USB4085 signal pins drill 0.4 mm (was 0.6 for the SMD part's shell)
NPTH_EXPECT = sorted([(x, y, 3.2) for x, y in pack.NPTH_XY]
                     + [(_CELL_X + dx, cy + dy, size) for cy in _CELL_Y
                        for dx, dy, size in _HOLDER_NPTH])   # the USB4085 adds no NPTH
LABELS = pack.LABELS
TEXTS = list(pack.TEXTS)
GND_VIAS = list(pack.GND_VIAS)
HELTEC_PADS = {}
SIZE_MM = pack.SIZE_MM
NPTH_XY = pack.NPTH_XY
HIDE_REF = pack.HIDE_REF + ("U_CHG", "R_ALERT", "C_VDDA", "C_MCU3", "SW_BOOT", "SW_RST")
SENSE_IN = pack.SENSE_IN
PLACE = dict(pack.PLACE)
for _gone in ("U_MON", "R_PWRDN", "D1"):   # replaced / dropped by the TME build
    del PLACE[_gone]
PLACE.update({
    # The BQ25601 hand-solder footprint is 1.2 mm larger and its exposed pad is soldered from the
    # back, so it leaves the holder floor for the holder-free right strip; the THT tact switches
    # move to the left margin (x < 8) for the same reason.
    "U_CHG": (90.0, 36.0, 0),
    "J_USB1": (87.0, 23.0, 90),   # pulled in so the USB4085's silk clears the board edge
    "SW_BOOT": (1.6, 48.0, 90), "SW_RST": (1.6, 60.0, 90),
    "J_PWR1": (90.0, 70.5, 90), "J_KEY1": (90.0, 79.2, 90),
    "C_MCU3": (59.0, 70.0, 0), "C_VDDA": (74.0, 66.5, 0),
})
for _i, _cy in enumerate(pack._CELL_Y, start=1):
    # One INA228 per cell band, its IN+/IN- facing that cell's 10R Kelvin split.
    PLACE[f"U_MON{_i}"] = (54.0, _cy, 0)
    PLACE[f"C_MON{_i}"] = (54.0, _cy + 6.5, 0)
REF_AT = dict(pack.REF_AT)
REF_AT.pop("U_MON", None)
REF_AT |= {f"U_MON{_i}": (54.0, _cy + 2.6, 0) for _i, _cy in enumerate(pack._CELL_Y, start=1)}
_tags = pack._tags
_cell = pack._cell


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

# --- T5.2 layout -------------------------------------------------------------------------------
# The PAC1934's single monitor block becomes support only; each INA228 moves into the cell block
# it senses, beside that cell's 10R Kelvin split. One fewer long sense route per cell, and the
# four monitors spread over four blocks instead of crowding one.
BLOCKS[1] = {
    "title": "Diode-OR and 3V3 LDO", "at": (228.6, 12.7), "size": (114.3, 139.7),
    "parts": {
        "D_OR5": (25.4, 25.4, 0, None),
        "U_LDO": (50.8, 25.4, 0, None),
        "C_LDO1": (76.2, 25.4, 0, None),
        "C_LDO2": (25.4, 50.8, 0, None),
        "R_SCL_INT": (50.8, 50.8, 0, None),
        "R_SDA_INT": (76.2, 50.8, 0, None),
        "R_ALERT": (25.4, 76.2, 0, None),
    },
    "tags": _tags(["SCL_INT", "SDA_INT", "MON_ALERT", "SYS"], 12.7, 101.6, per_row=4),
}
# The L072 adds VDD (17) and VDDA (5) decoupling.
BLOCKS[2]["size"] = (165.1, 190.5)
BLOCKS[2]["parts"].update({
    "U_MCU": (58.42, 55.88, 0, None),     # the L072 is 25.4 mm wide; move it clear of the left column
    "C_MCU3": (30.48, 25.4, 0, None),
    "C_VDDA": (43.18, 25.4, 0, None),
    "TP_SWDIO": (95.25, 60.96, 0, None),
    "R_LED_MCU": (95.25, 76.2, 0, None),
    "LED_MCU": (105.41, 76.2, 90, None),
    "TP_GND": (95.25, 91.44, 0, None),
})
BLOCKS[2]["tags"].pop("MON_PWRDN", None)
# The L072's three +3V3 pins are adjacent on the top edge (2.54 mm apart), so they cannot each
# take a power port: wire the rails and name them with tags, as the carrier amp block does.
BLOCKS[2]["tags"]["+3V3"] = [(12.7, 186.69, "R")]
BLOCKS[2]["tags"]["GND"] = [(33.02, 186.69, "R")]
BLOCKS[2]["wired"] = {"+3V3", "GND"}
# The synchronous MCP1640 needs no catch diode.
del BLOCKS[3]["parts"]["D1"]

for _i in range(1, 5):
    _b = BLOCKS[3 + _i]
    _b["title"] = f"Cell {_i} branch + INA228"
    # The NTC bead and its divider resistor move down, clearing the INA228's right-hand pins.
    _b["parts"].update({
        f"U_MON{_i}": (63.5, 71.12, 0, None),
        f"C_MON{_i}": (63.5, 44.45, 0, None),
        f"TH{_i}": (83.82, 105.41, 0, None),
        f"R_NTC{_i}": (83.82, 125.73, 0, None),
    })
    _b["tags"] = (_tags([f"CELL{_i}_F", f"CELL{_i}_S", f"CELL{_i}_RAW", f"CELL{_i}_SRC"],
                         12.7, 152.4, per_row=4)
                   | _tags(["SDA_INT", "SCL_INT", "MON_ALERT"], 12.7, 165.1, per_row=3)
                   | {f"SNS_F{_i}": [(34.29, 68.58, "L")], f"SNS_S{_i}": [(40.64, 57.15, "L")],
                      f"NTC{_i}": [(83.82, 144.78, "R")]})


def check_branches():
    """Every cell in branch order, with its own INA228 across the 10R Kelvin split: IN+ and VBUS on
    the cell side of the shunt, IN- after it, addresses 0x40-0x43 by A1/A0, ALERTs wired together."""
    net_of = {p: n for n, m in NETS.items() for p in m}
    addr = {1: ("GND", "GND"), 2: ("GND", "+3V3"), 3: ("GND", "SDA_INT"), 4: ("GND", "SCL_INT")}
    for i in range(1, 5):
        assert net_of[f"BT{i}.1"] == net_of[f"F{i}.1"], f"cell {i}: holder+ not on fuse"
        assert net_of[f"F{i}.2"] == net_of[f"R_SH{i}.1"] == net_of[f"R_SNSF{i}.1"], \
            f"cell {i}: fuse -> shunt"
        assert net_of[f"R_SNSF{i}.2"] == net_of[f"U_MON{i}.10"] == net_of[f"U_MON{i}.8"], \
            f"cell {i}: IN+/VBUS"
        assert net_of[f"R_SH{i}.2"] == net_of[f"Q_A{i}.3"] == net_of[f"R_SNSS{i}.1"], \
            f"cell {i}: shunt -> FET"
        assert net_of[f"R_SNSS{i}.2"] == net_of[f"U_MON{i}.9"], f"cell {i}: IN-"
        assert net_of[f"Q_B{i}.3"] == "VPACK" and net_of[f"BT{i}.2"] == "GND", f"cell {i}: rail"
        assert (net_of[f"U_MON{i}.1"], net_of[f"U_MON{i}.2"]) == addr[i], f"INA228 {i} address"
        assert net_of[f"U_MON{i}.3"] == "MON_ALERT" and net_of[f"U_MON{i}.6"] == "+3V3"
        assert (net_of[f"U_MON{i}.4"], net_of[f"U_MON{i}.5"]) == ("SDA_INT", "SCL_INT")


def check_mcu():
    """The L072 pin roles and the boost this board relies on."""
    net_of = {p: n for n, m in NETS.items() for p in m}
    want = {"U_MCU.21": "USB_DM", "U_MCU.22": "USB_DP", "U_MCU.18": "SCL_INT",
            "U_MCU.27": "SDA_INT", "U_MCU.29": "SCL_EXT", "U_MCU.30": "SDA_EXT",
            "U_MCU.6": "NTC1", "U_MCU.7": "NTC2", "U_MCU.8": "NTC3", "U_MCU.9": "NTC4",
            "U_MCU.10": "NTC_PWR", "U_MCU.11": "SW1_DRV", "U_MCU.12": "SW2_DRV",
            "U_MCU.13": "SW3_DRV", "U_MCU.14": "SW4_DRV", "U_MCU.15": "CHG_CE",
            "U_MCU.26": "CHG_INT", "U_MCU.28": "MON_ALERT", "U_MCU.25": "LED_MCU_DRV",
            "U_MCU.31": "BOOT0", "U_MCU.4": "NRST", "U_MCU.23": "SWDIO", "U_MCU.24": "SWCLK"}
    for p, n in want.items():
        assert net_of.get(p) == n, f"{p} on {net_of.get(p)}, want {n}"
    assert PARTS["U_CHG"][2] == QFN24_HAND, "U_CHG must use the hand-solder footprint"
    assert "D1" not in PARTS, "the synchronous MCP1640 needs no catch diode"
    for p, n in (("U1.6", "VBAT_SW"), ("U1.3", "VBAT_SW"), ("U1.5", "+5V"), ("U1.4", "FB")):
        assert net_of[p] == n, f"{p} on {net_of[p]}, want {n}"


def check():
    import sys

    this = sys.modules[__name__]
    board.check_structure(this)
    check_branches()
    check_mcu()
    print(f"pack_tme ok: {len(PARTS)} parts, {len(NETS)} nets")


if __name__ == "__main__":
    check()
