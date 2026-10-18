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
# Block 1 was the NS4168 amp; it now holds the DAC, its caps and the PAM8302A amp.
BLOCKS[1] = {
    "title": "I2S DAC and speaker amp", "at": (403.86, 12.7), "size": (152.4, 152.4),
    "parts": {
        # Rows 25.4 mm apart and 12.7 mm between 2-pin parts: enough margin for wire routing.
        # The two ICs sit 23 mm apart so their pin zones stay clear.
        "C_DVDD": (25.4, 25.4, 0, None), "C_DAVDD": (38.1, 25.4, 0, None),
        "C_DCPV": (50.8, 25.4, 0, None), "C_DBULK": (63.5, 25.4, 0, None),
        "C_DCP": (76.2, 25.4, 0, None), "C_DNEG": (88.9, 25.4, 0, None),
        "C_DLDO": (101.6, 25.4, 0, None), "C_OL": (114.3, 25.4, 0, None),
        "C_OR": (127.0, 25.4, 0, None),
        "U_DAC": (55.88, 50.8, 0, None),
        "U_AMP": (101.6, 50.8, 0, None),
        "R_OL": (25.4, 76.2, 0, None), "R_OR": (38.1, 76.2, 0, None),
        "C_INP": (50.8, 76.2, 0, None), "C_INN": (63.5, 76.2, 0, None),
        "R_INP": (76.2, 76.2, 0, None), "R_INN": (88.9, 76.2, 0, None),
        "C_AMP1": (101.6, 76.2, 0, None), "C_AMP2": (114.3, 76.2, 0, None),
        "R_SD1": (127.0, 76.2, 0, None), "R_SDPD1": (139.7, 63.5, 0, None),
        "J_SPK1": (139.7, 88.9, 0, "x"),
    },
    # Every net that leaves its pin pair is tagged explicitly in the free column at x=15.24:
    # the DAC-to-amp nets are too short for gen_sch's labeler to find a straight run, so
    # auto-naming them is not reliable. +3V3/GND are wired here because the DAC's three supply
    # pins are 2.54 mm apart and cannot each take their own power port.
    "tags": {
        "I2S_BCLK": [(15.24, 10.16, "L")], "I2S_LRCLK": [(15.24, 15.24, "L")],
        "I2S_DIN": [(15.24, 20.32, "L")],
        "+3V3": [(15.24, 25.4, "L")], "GND": [(15.24, 30.48, "L")],
        "DAC_CAPP": [(15.24, 35.56, "L")], "DAC_CAPM": [(15.24, 40.64, "L")],
        "DAC_VNEG": [(15.24, 45.72, "L")], "DAC_LDOO": [(15.24, 50.8, "L")],
        "DAC_OL": [(15.24, 55.88, "L")], "DAC_OR": [(15.24, 60.96, "L")],
        "AUD_L": [(15.24, 66.04, "L")], "AUD_R": [(15.24, 71.12, "L")],
        "AMP_INP_C": [(15.24, 76.2, "L")], "AMP_INN_C": [(15.24, 81.28, "L")],
        "AMP_INP": [(15.24, 86.36, "L")], "AMP_INN": [(15.24, 91.44, "L")],
        "AMP_SD_R": [(15.24, 96.52, "L")], "SPK_P": [(15.24, 101.6, "L")],
        "SPK_N": [(15.24, 106.68, "L")],
        "AMP_SD": [(149.86, 76.2, "L")],
    },
    "wired": {"+3V3", "GND"},
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
SHEETS = {
    "power": ("Power: pack rail bulk, +5V reservoir", [0]),
    "i2c": ("I2C level shifter, NFC bulk", [3]),
    "expander": ("GPIO expander (0x20), button inputs", [4]),
    "drivers": ("Low-side drivers: button LEDs, buzzer", [5]),
    "audio": ("I2S DAC and speaker amp", [1]),
    "debug": ("Debug: UART, I2C, test pads", [6]),
}
# Root (system) sheet: {ref: (x, y, rot, mirror)} in root coordinates, sheet boxes {name: (x, y, w, h)},
# and the outline drawn round J2/J3 so they read as one module.
ROOT = {
    "parts": {
        "J2": (190.5, 76.2, 0, None), "J3": (241.3, 76.2, 0, None),
        "J_PWR1": (63.5, 50.8, 0, "y"), "J_HBAT1": (63.5, 88.9, 0, "y"),
        "J_LCD1": (342.9, 50.8, 0, None), "J_NFC1": (342.9, 76.2, 0, None),
        "J_BTN_R1": (342.9, 101.6, 0, None), "J_BTN_B1": (342.9, 127.0, 0, None),
        "J_BUZ1": (342.9, 152.4, 0, None), "J_SPK1": (342.9, 177.8, 0, None),
        "H1": (25.4, 254.0, 0, None), "H2": (35.56, 254.0, 0, None),
        "H3": (45.72, 254.0, 0, None), "H4": (55.88, 254.0, 0, None),
    },
    "sheets": {
        "power": (88.9, 38.1, 38.1, 25.4), "i2c": (279.4, 38.1, 38.1, 38.1),
        "expander": (279.4, 91.44, 38.1, 50.8), "drivers": (279.4, 152.4, 38.1, 38.1),
        "audio": (279.4, 203.2, 38.1, 38.1), "debug": (88.9, 177.8, 38.1, 38.1),
    },
    "outline": ("Heltec WiFi LoRa 32 V4 (plugs into J2/J3)", (165.1, 30.48, 101.6, 104.14)),
    "size": (391.16, 236.22),  # root content from (12.7, 12.7): fits A3
}
# Off-board parts, drawn on the root beyond their connector, never on the board or in a BOM:
# ref -> (value, symbol, connector, {own pin: connector pin}, cable note, (x, y, rot, mirror)).
_PINS4 = {"1": "1", "2": "2", "3": "3", "4": "4"}
OFFBOARD = {
    "X_PACK": ("Pack board (P5)", "local:Pack_Link_6", "J_PWR1",
               {str(i): str(i) for i in range(1, 7)}, "XH-6", (25.4, 50.8, 0, None)),
    "X_HBAT": ("Heltec V4 battery input (SH1.25)", "Connector_Generic:Conn_01x02", "J_HBAT1",
               {"1": "1", "2": "2"}, "XH-2 to SH1.25", (25.4, 88.9, 0, None)),
    "X_LCD": ("LCD 1602 + PCF8574", "local:Module_I2C_4", "J_LCD1", _PINS4, "XH-4", (381.0, 50.8, 0, "y")),
    "X_NFC": ("PN532 (I2C)", "local:Module_I2C_4", "J_NFC1", _PINS4, "XH-4", (381.0, 76.2, 0, "y")),
    "X_BTN_R": ("ONPOW LAS1-AGQ-11E/R/6V", "local:Button_LED_4", "J_BTN_R1", _PINS4, "XH-4",
                (381.0, 101.6, 0, "y")),
    "X_BTN_B": ("ONPOW LAS1-AGQ-11E/B/6V", "local:Button_LED_4", "J_BTN_B1", _PINS4, "XH-4",
                (381.0, 127.0, 0, "y")),
    "X_BUZ": ("BZ-38 buzzer", "Device:Buzzer", "J_BUZ1", {"1": "1", "2": "2"}, "XH-2", (381.0, 152.4, 0, None)),
    "X_SPK": ("VISATON K 50, 8 ohm", "Device:Speaker", "J_SPK1", {"1": "1", "2": "2"},
              "XH-2, BTL: neither side is GND", (381.0, 177.8, 0, None)),
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
