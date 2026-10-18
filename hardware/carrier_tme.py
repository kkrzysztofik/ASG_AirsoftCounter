"""AirsoftCounter v2 carrier, hand-build TME variant: iron-only, everything from TME.

Derived from carrier.py by import and edit. The NS4168 I2S class-D amp is replaced by a PCM5100A
I2S DAC and a PAM8302A SO-8 class-D amp: the DAC runs on +3V3 with its PLL clocked from BCK (no
MCLK), its L/R outputs are RC-filtered and driven in antiphase through 240k input resistors into
the amp's differential input, and the expander's AMP_SD line enables the amp and unmutes the DAC.
Everything else is the carrier (the TME build is the full deluxe set). gen_sch.py / gen_pcb.py read
it through board.py (`make BOARD=carrier_tme ...`). Run this file to self-check.

Source of truth: docs/plans/2026-10-02-tme-hand-build-design.md.
"""
import board
import carrier
import tme

NAME = "carrier_tme"
TITLE = "AirsoftCounter v2 carrier (hand-build)"

HEADER_POWER = carrier.HEADER_POWER
HEADER_NC = carrier.HEADER_NC
HELTEC_GPIO = carrier.HELTEC_GPIO
FORBIDDEN_GPIO = carrier.FORBIDDEN_GPIO
EXPECTED_GPIO = carrier.EXPECTED_GPIO
heltec_pin_names = carrier.heltec_pin_names

TSSOP20 = "Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm"
SOIC8 = "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm"
C0805, R0805 = carrier.C0805, carrier.R0805

# Everything but the NS4168, plus the DAC, its caps, the output RC + input network and the amp.
PARTS = {r: v for r, v in carrier.PARTS.items() if r != "U3"}
PARTS |= {
    "U_DAC": ("PCM5100APWR", "Audio:PCM5100A", TSSOP20),
    "C_DCP": ("2.2uF", *C0805),         # CAPP-CAPM charge-pump flying cap
    "C_DNEG": ("2.2uF", *C0805),        # VNEG
    "C_DLDO": ("100nF", *C0805),        # LDOO
    "C_DVDD": ("100nF", *C0805), "C_DAVDD": ("100nF", *C0805), "C_DCPV": ("100nF", *C0805),
    "C_DBULK": ("10uF", *C0805),
    "R_OL": ("470R", *R0805), "C_OL": ("2.2nF", *C0805),    # DAC output RC, left
    "R_OR": ("470R", *R0805), "C_OR": ("2.2nF", *C0805),    # right (driven in antiphase)
    "C_INP": ("1uF", *C0805), "R_INP": ("240k", *R0805),    # amp input coupling + gain
    "C_INN": ("1uF", *C0805), "R_INN": ("240k", *R0805),
    "U_AMP": ("PAM8302AADCR", "Amplifier_Audio:PAM8302AAD", SOIC8),
}

# The Heltec headers get named-pin symbols (Heltec V4 pinout); same value and footprint, so nothing
# changes on the board or in the TME list.
PARTS["J2"] = (carrier.PARTS["J2"][0], "local:Heltec_V4_J2", carrier.PARTS["J2"][2])
PARTS["J3"] = (carrier.PARTS["J3"][0], "local:Heltec_V4_J3", carrier.PARTS["J3"][2])
# Root-sheet cable connectors use 5.08 mm-pitch symbols (same pins and footprints): the half row between
# cables holds each rail's power port, which does not fit at 2.54 mm.
for _r in ("J_PWR1", "J_HBAT1", "J_LCD1", "J_NFC1", "J_BTN_R1", "J_BTN_B1", "J_BUZ1", "J_SPK1"):
    _v, _sym, _fp = PARTS[_r]
    PARTS[_r] = (_v, f"local:Conn_W_{_sym[-2:]}", _fp)

NETS = {n: [p for p in mem if not p.startswith("U3.")] for n, mem in carrier.NETS.items()}
NETS["I2S_BCLK"] += ["U_DAC.13"]
NETS["I2S_LRCLK"] += ["U_DAC.15"]
NETS["I2S_DIN"] += ["U_DAC.14"]
NETS["AMP_SD"] += ["U_DAC.17"]          # the amp and the DAC's XSMT share the expander line
NETS["AMP_SD_R"] += ["U_AMP.1"]
NETS["SPK_P"] += ["U_AMP.5"]
NETS["SPK_N"] += ["U_AMP.8"]
NETS["VBAT_SW"] += ["U_AMP.6"]
NETS["+3V3"] += ["U_DAC.1", "U_DAC.8", "U_DAC.20",
                 "C_DVDD.1", "C_DAVDD.1", "C_DCPV.1", "C_DBULK.1"]
NETS["GND"] += ["U_DAC.3", "U_DAC.9", "U_DAC.19", "U_DAC.10", "U_DAC.11", "U_DAC.12", "U_DAC.16",
                "C_DNEG.2", "C_DLDO.2", "C_DVDD.2", "C_DAVDD.2", "C_DCPV.2", "C_DBULK.2",
                "C_OL.2", "C_OR.2", "U_AMP.7"]
NETS |= {
    "DAC_CAPP": ["U_DAC.2", "C_DCP.1"], "DAC_CAPM": ["U_DAC.4", "C_DCP.2"],
    "DAC_VNEG": ["U_DAC.5", "C_DNEG.1"], "DAC_LDOO": ["U_DAC.18", "C_DLDO.1"],
    "DAC_OL": ["U_DAC.6", "R_OL.1"], "DAC_OR": ["U_DAC.7", "R_OR.1"],
    "AUD_L": ["R_OL.2", "C_OL.1", "C_INP.1"], "AUD_R": ["R_OR.2", "C_OR.1", "C_INN.1"],
    "AMP_INP_C": ["C_INP.2", "R_INP.1"], "AMP_INN_C": ["C_INN.2", "R_INN.1"],
    "AMP_INP": ["R_INP.2", "U_AMP.3"], "AMP_INN": ["R_INN.2", "U_AMP.4"],
}
NC_PINS = set(carrier.NC_PINS) | {"U_AMP.2"}   # amp pin 2 is NC
# U_DAC: TME has no PCM5100A in stock below a 70 pcs tube (2026-10-02); buy it at LCSC or Mouser.
NOT_TME = {"U_DAC"} | carrier.NOT_ASSEMBLED                            # the rest is bought at TME (J2/J3: ZL262-18SG)
NC_PARTS = set(carrier.NC_PARTS)
DNP = set(carrier.DNP)
NOT_ASSEMBLED = set(carrier.NOT_ASSEMBLED)
HIDE_REF = carrier.HIDE_REF
LCSC = {}
_KEYS = {(v, fp) for r, (v, sym, fp) in PARTS.items()
         if sym != "Mechanical:MountingHole" and r not in DNP | NOT_TME}
TME = tme.from_lcsc(carrier.LCSC, _KEYS)
TME |= {
    ("PAM8302AADCR", SOIC8): "PAM8302AADCR",
    ("470R", R0805[1]): "SMD0805-470R-1%",
    ("240k", R0805[1]): "SMD0805-240K-1%",
    ("2.2nF", C0805[1]): "CC0805KRX7R9BB222",
    ("2.2uF", C0805[1]): "CL21A225KAFNNNE",
    ("1uF", C0805[1]): "CL21B105KAFNNNE",
    ("10uF", C0805[1]): "CL21A106KAYNNNE",
}
MODULES, VARIANTS = {}, {"standard": set()}


def assembled(variant="standard"):
    """Nothing is machine-placed on a hand-build board."""
    return []


# --- layout: reused from the carrier by assignment; edited where the amp block needs it ---------
W, H, CORNER = carrier.W, carrier.H, carrier.CORNER
NETCLASS_POWER = carrier.NETCLASS_POWER
NETCLASS_EXPECT = carrier.NETCLASS_EXPECT
RAILS = carrier.RAILS
PORT_LIB = carrier.PORT_LIB
LABELS = carrier.LABELS
TEXTS = list(carrier.TEXTS)
GND_VIAS = list(carrier.GND_VIAS)
HELTEC_PADS = carrier.HELTEC_PADS
SIZE_MM = carrier.SIZE_MM
NPTH_XY = carrier.NPTH_XY
PLACE = dict(carrier.PLACE)
REF_AT = {r: v for r, v in carrier.REF_AT.items() if r != "U3"}
REF_AT |= {"U_AMP": (10.5, 27.5, 0), "C_DCPV": (20, 42, 0), "C_INP": (25, 42, 0)}
_driver = carrier._driver


def _copy_blocks():
    out = []
    for b in carrier.BLOCKS:
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
# Drivers: J_BUZ1 moved to the root sheet, so BUZ_K leaves the sheet; tag it right of the drain/diode
# node (an auto label on D_FLY1's anode points straight into Q_BZ1's drain).
BLOCKS[5]["tags"]["BUZ_K"] = [(175.26, 27.94, "R")]
# Block 1 was the NS4168 amp; it now holds the DAC, its caps and the PAM8302A amp.
BLOCKS[1] = {
    # Signal flow left to right: I2S in -> DAC (each cap beside its own pin) -> output RC -> coupling C and
    # input R -> amp -> speaker. The L chain runs on y=35.56 (into IN+), R on y=50.8 (into IN-); AMP_SD
    # enters at XSMT and runs under the DAC to R_SD1 / R_SDPD1 below the amp's SD pin. Only nets that
    # leave the sheet are tagged; internal nets are named on their own wires.
    "title": "I2S DAC and speaker amp", "at": (403.86, 12.7), "size": (182.88, 91.44), "vcomb": True,
    # The DAC's grounded config pins (SCK, FLT, DEMP, FMT) share one crossable GND wire: XSMT sits between
    # them and its AMP_SD wire crosses it.
    "combs": [["U_DAC.12", "U_DAC.11", "U_DAC.10", "U_DAC.16"]],
    "parts": {
        "C_DCPV": (35.56, 17.78, 0, None), "C_DVDD": (45.72, 17.78, 0, None),
        "C_DAVDD": (55.88, 17.78, 0, None), "C_DBULK": (66.04, 17.78, 0, None),
        "U_DAC": (50.8, 50.8, 0, None),
        "C_DCP": (78.74, 52.07, 0, None), "C_DNEG": (78.74, 67.31, 0, None), "C_DLDO": (88.9, 64.77, 0, None),
        "R_OL": (81.28, 30.48, 90, None), "C_OL": (90.17, 34.29, 0, None),
        "C_INP": (99.06, 30.48, 90, None), "R_INP": (111.76, 30.48, 90, None),
        "R_OR": (81.28, 45.72, 90, None), "C_OR": (90.17, 49.53, 0, None),
        "C_INN": (99.06, 45.72, 90, None), "R_INN": (111.76, 45.72, 90, None),
        "U_AMP": (132.08, 35.56, 0, None),
        "R_SD1": (124.46, 57.15, 180, None), "R_SDPD1": (116.84, 69.85, 0, None),
        "C_AMP1": (152.4, 58.42, 0, None), "C_AMP2": (165.1, 58.42, 0, None),
        "J_SPK1": (139.7, 88.9, 0, "x"),
    },
    "tags": {
        "I2S_LRCLK": [(15.24, 40.64, "L")], "I2S_DIN": [(15.24, 43.18, "L")], "I2S_BCLK": [(15.24, 45.72, "L")],
        "AMP_SD": [(15.24, 58.42, "L")],
        "SPK_P": [(152.4, 30.48, "R")], "SPK_N": [(152.4, 35.56, "R")],
    },
}

PLACE = {r: v for r, v in carrier.PLACE.items() if r != "U3"}
# The DAC/amp corner is dense; reference text there collides with neighbouring silk, so it is
# hidden (the value stays, and the refs are on the fab print and in the schematic).
HIDE_REF = ("U_DAC", "U_AMP", "C_DCP", "C_DNEG", "C_DLDO", "C_DVDD", "C_DAVDD", "C_DCPV",
            "C_DBULK", "R_OL", "C_OL", "R_OR", "C_OR", "C_INP", "R_INP", "C_INN", "R_INN") + carrier.HIDE_REF
PLACE |= {
    # DAC + amp replace the NS4168 in the J_SPK1 corner. U_AMP takes the U3 spot; the DAC and
    # its passives come from a courtyard-free-space search on the JLC board (the corner is dense,
    # so a few of them sit up to 19 mm away), each with >=1 mm to its neighbours for the iron.
    "U_DAC": (25.0, 18.0, 0), "U_AMP": (15.2, 23.2, 90),
    "C_DCP": (21.0, 24.0, 0), "C_DNEG": (26.0, 24.0, 0),
    "C_DLDO": (5.0, 13.0, 0), "C_DVDD": (31.0, 24.0, 0), "C_DAVDD": (32.0, 21.0, 0),
    "C_DCPV": (20.0, 39.5, 0), "C_DBULK": (12.0, 40.0, 0),
    "R_OL": (4.0, 10.0, 0), "C_OL": (32.0, 18.0, 0),
    "R_OR": (7.0, 40.0, 0), "C_OR": (32.0, 15.0, 0),
    "C_INP": (25.0, 39.5, 0), "R_INP": (20.5, 42.5, 0),
    "C_INN": (36.0, 24.0, 0), "R_INN": (25.5, 42.5, 0),
    # +5V reservoir: the carrier's spot is under U_DAC here. Free spot left of J3 pin 1, clear of the DAC
    # corner (beside D_FLY1 it left +3V3 unroutable)
    "C_5V1": (37.0, 27.5, 0), "C_5V2": (37.0, 31.5, 0),
}


# --- Hierarchical schematic (docs/plans/2026-10-18-hierarchical-schematics-design.md) ---
# Function sheets: name -> (title, BLOCKS indexes). A block's parts land on that sheet, except the ROOT parts
# (connectors, Heltec headers, holes), which gen_sch draws on the root sheet instead.
# Drawn on the root beside their connectors, where they sit on the board: the power-entry caps, the
# bring-up headers and pads, D_FLY1 (across the buzzer), and the I2C level shifter with the bus pull-ups
# (the bus itself is drawn on the root). Each rail on the root then has its own bulk cap there.
SHEETS = {
    "expander": ("GPIO expander (0x20), button inputs", [4]),
    "drivers": ("Low-side drivers: button LEDs, buzzer", [5]),
    "audio": ("I2S DAC and speaker amp", [1]),
}
# Root (system) sheet: {ref: (x, y, rot, mirror)} in root coordinates, sheet boxes {name: (x, y, w, h)},
# and the outline drawn round J2/J3 so they read as one module.
ROOT = {
    "parts": {
        "J2": (190.5, 76.2, 0, None), "J3": (241.3, 76.2, 0, None),
        # Connector pins face their off-board part: left-side connectors as drawn (pins left), right-side
        # ones mirrored (pins right); the cable gap between holds the rail ports.
        "J_PWR1": (81.28, 50.8, 0, None), "J_HBAT1": (81.28, 88.9, 0, None),
        "J_LCD1": (337.82, 45.72, 0, "y"), "J_NFC1": (337.82, 76.2, 0, "y"),
        "J_BTN_R1": (337.82, 106.68, 0, "y"), "J_BTN_B1": (337.82, 137.16, 0, "y"),
        "J_BUZ1": (337.82, 165.1, 0, "y"), "J_SPK1": (337.82, 190.5, 0, "y"),
        "H1": (25.4, 238.76, 0, None), "H2": (35.56, 238.76, 0, None),
        "H3": (45.72, 238.76, 0, None), "H4": (55.88, 238.76, 0, None),
        # power entry: pack-rail bulk and the +5V reservoir beside J_PWR1, the NFC bulk beside J_NFC1
        "C_BULK1": (106.68, 50.8, 0, None), "C_BULK2": (116.84, 50.8, 0, None),
        "C_5V1": (127.0, 50.8, 0, None), "C_5V2": (137.16, 50.8, 0, None),
        "C_NFC1": (314.96, 88.9, 0, None),
        # bring-up: UART / I2C headers and rail test pads, pins towards the Heltec
        "J_UART1": (101.6, 182.88, 0, "y"), "J_I2C1": (101.6, 203.2, 0, "y"),
        "TP_3V3": (129.54, 182.88, 0, None), "TP_5V": (139.7, 182.88, 0, None),
        "TP_VSW": (129.54, 200.66, 0, None), "TP_GND": (139.7, 200.66, 0, None),
        # I2C level shifter and bus pull-ups (the flat block-3 layout, moved beside J_LCD1)
        "R_SDA3": (283.21, 44.45, 0, None), "Q_SDA1": (295.91, 45.72, 270, None), "R_SDA5": (312.42, 44.45, 0, None),
        "R_SCL3": (283.21, 67.31, 0, None), "Q_SCL1": (295.91, 68.58, 270, None), "R_SCL5": (312.42, 67.31, 0, None),
        "D_FLY1": (325.12, 160.02, 270, None),
    },
    "flags": [("GND", 106.68, 68.58), ("VBAT_SW", 121.92, 68.58), ("+5V", 137.16, 68.58),
              ("+3V3", 152.4, 68.58)],
    # The 2.54 mm headers (Heltec, debug) take rail ports along their stubs, which stay in the pin's own
    # row; the cable connectors' rail ports hang off their cables instead (gen_sch.tee_port).
    "port_modes": {r: "along" for r in ("J2", "J3", "J_UART1", "J_I2C1")},
    "sheets": {
        "expander": (271.78, 101.6, 38.1, 50.8), "drivers": (271.78, 160.02, 38.1, 38.1),
        "audio": (203.2, 165.1, 50.8, 25.4),
    },
    "outline": ("Heltec WiFi LoRa 32 V4 (plugs into J2/J3)", (165.1, 30.48, 101.6, 104.14)),
    "size": (391.16, 236.22),  # root content from (12.7, 12.7): fits A3
}
# Off-board parts, drawn on the root beyond their connector, never on the board or in a BOM:
# ref -> (value, symbol, connector, {own pin: connector pin}, cable note, (x, y, rot, mirror)).
_PINS4 = {"1": "1", "2": "2", "3": "3", "4": "4"}
OFFBOARD = {
    "#X_PACK": ("Pack board (P5)", "local:Pack_Link_6", "J_PWR1",
               {str(i): str(i) for i in range(1, 7)}, "XH-6", (27.94, 50.8, 0, "y")),
    "#X_HBAT": ("Heltec V4 battery", "local:Conn_W_02", "J_HBAT1",
               {"1": "1", "2": "2"}, "XH-2 to the module's SH1.25", (40.64, 88.9, 0, "y")),
    "#X_LCD": ("LCD 1602 + PCF8574", "local:Module_I2C_4", "J_LCD1", _PINS4, "XH-4", (386.08, 45.72, 0, None)),
    "#X_NFC": ("PN532 (I2C)", "local:Module_I2C_4", "J_NFC1", _PINS4, "XH-4", (386.08, 76.2, 0, None)),
    "#X_BTN_R": ("ONPOW LAS1-AGQ-11E/R/6V", "local:Button_LED_4", "J_BTN_R1", _PINS4, "XH-4",
                (386.08, 106.68, 0, None)),
    "#X_BTN_B": ("ONPOW LAS1-AGQ-11E/B/6V", "local:Button_LED_4", "J_BTN_B1", _PINS4, "XH-4",
                (386.08, 137.16, 0, None)),
    "#X_BUZ": ("BZ-38 buzzer", "Device:Buzzer", "J_BUZ1", {"1": "1", "2": "2"}, "XH-2", (386.08, 165.1, 0, None)),
    "#X_SPK": ("VISATON K 50, 8 ohm", "Device:Speaker", "J_SPK1", {"1": "1", "2": "2"},
              "XH-2, BTL: neither side is GND", (386.08, 190.5, 0, None)),
}


def check_sheets():
    """Every board part is drawn exactly once: on the root, or in one block of one sheet."""
    in_sheets = [r for _t, idx in SHEETS.values() for i in idx for r in BLOCKS[i]["parts"] if r not in ROOT["parts"]]
    drawn = in_sheets + list(ROOT["parts"])
    twice = sorted({r for r in drawn if drawn.count(r) > 1})
    assert not twice, f"drawn twice: {twice}"
    assert set(drawn) == set(PARTS), f"not drawn: {sorted(set(PARTS) - set(drawn))}, " \
                                     f"unknown: {sorted(set(drawn) - set(PARTS))}"
    assert ROOT["sheets"].keys() == SHEETS.keys(), "ROOT['sheets'] must place every sheet"


def check_header(m):
    """The carrier's Heltec header checks (from carrier.check), reading module m."""
    pins = [p for members in m.NETS.values() for p in members]
    net_of = {p: net for net, mem in m.NETS.items() for p in mem}
    for p, net in HEADER_POWER.items():
        assert net_of.get(p) == net, f"{p} must be on {net}, is on {net_of.get(p)}"
    for p in pins:
        if p.split(".")[0] not in ("J2", "J3"):
            continue
        assert p not in HEADER_NC, f"{p} must stay unconnected"
        assert p in HELTEC_GPIO or p in HEADER_POWER, f"{p} is not a known header pin"
        if p in HELTEC_GPIO:
            g = HELTEC_GPIO[p]
            name = f"GPIO{g}" if g is not None else "RST"
            assert g not in FORBIDDEN_GPIO, f"{p} is {name}, reserved on V4"
    got = sorted((n, HELTEC_GPIO[p]) for n, mem in m.NETS.items() for p in mem if p in HELTEC_GPIO)
    assert got == sorted(EXPECTED_GPIO.items()), got


def check_audio():
    """DAC pin roles, amp wiring and the DAC/amp interface."""
    net_of = {p: n for n, m in NETS.items() for p in m}
    want = {"U_DAC.13": "I2S_BCLK", "U_DAC.15": "I2S_LRCLK", "U_DAC.14": "I2S_DIN",
            "U_DAC.17": "AMP_SD", "U_DAC.12": "GND", "U_DAC.16": "GND", "U_DAC.11": "GND",
            "U_DAC.10": "GND", "U_DAC.1": "+3V3", "U_DAC.8": "+3V3", "U_DAC.20": "+3V3",
            "U_AMP.1": "AMP_SD_R", "U_AMP.6": "VBAT_SW", "U_AMP.7": "GND",
            "U_AMP.5": "SPK_P", "U_AMP.8": "SPK_N"}
    for p, n in want.items():
        assert net_of.get(p) == n, f"{p} on {net_of.get(p)}, want {n}"
    assert "U3" not in PARTS


def check():
    import sys

    this = sys.modules[__name__]
    board.check_structure(this)
    check_header(this)
    check_audio()
    check_sheets()
    print(f"carrier_tme ok: {len(PARTS)} parts, {len(NETS)} nets")


if __name__ == "__main__":
    check()
