"""AirsoftCounter v2 carrier board: single source of truth for parts and nets.

gen_sch.py and gen_pcb.py read PARTS and NETS from here. Run this file to
self-check the design (`python3 design.py`). Generators must call design.check()
at startup.

check() validates structure (unique pins, known parts, no single-pin nets, no
unconnected parts), every Heltec header pin, and that every assembled part has
an LCSC number (jlc.py builds the JLCPCB assembly files from LCSC). It does NOT validate pin
numbers of other parts or catch dangling 2-pin parts: gen_sch.py (symbol pin
lookup) and KiCad ERC catch those.
"""

# Footprints (and symbol + footprint pairs) shared by PARTS and LCSC below
R0805 = ("Device:R", "Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder")
C0805 = ("Device:C", "Capacitor_SMD:C_0805_2012Metric_Pad1.18x1.45mm_HandSolder")
BSS138 = ("Transistor_FET:BSS138", "Package_TO_SOT_SMD:SOT-23")  # I2C shifter and low-side drivers
C1206 = "Capacitor_SMD:C_1206_3216Metric_Pad1.33x1.80mm_HandSolder"
TSSOP16 = "Package_SO:TSSOP-16_4.4x5mm_P0.65mm"
ESOP8 = "Package_SO:HSOP-8-1EP_3.9x4.9mm_P1.27mm_EP2.3x2.3mm_ThermalVias"  # NS4168 eSOP-8, EP 2.0 mm
XH4 = "Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical"
SOCKET18 = "Connector_PinSocket_2.54mm:PinSocket_1x18_P2.54mm_Vertical"
SOIC8EP = "Package_SO:SOIC-8-1EP_3.9x4.9mm_P1.27mm_EP2.41x3.3mm"

# ref: (value, symbol "lib:name", footprint "lib:name")
PARTS = {
    # Heltec WiFi LoRa 32 V4 headers (pin 1 at USB end). Rows are 22.86 mm apart.
    "J2": ("Heltec_J2", "Connector_Generic:Conn_01x18", SOCKET18),
    "J3": ("Heltec_J3", "Connector_Generic:Conn_01x18", SOCKET18),
    # Off-board connectors: one part, JST-XH 4-pin 2.50 mm vertical. 2-wire nets use pins 1-2, pins 3-4 are NC
    # (see XH_SPARE)
    "J_BAT1": ("BAT", "Connector_Generic:Conn_01x04", XH4),
    "J_KEY1": ("KEY", "Connector_Generic:Conn_01x04", XH4),
    "J_HBAT1": ("HELTEC_BAT", "Connector_Generic:Conn_01x04", XH4),
    "J_LCD1": ("LCD", "Connector_Generic:Conn_01x04", XH4),
    "J_NFC1": ("NFC", "Connector_Generic:Conn_01x04", XH4),
    "J_BTN_R1": ("BTN_R", "Connector_Generic:Conn_01x04", XH4),
    "J_BTN_B1": ("BTN_B", "Connector_Generic:Conn_01x04", XH4),
    "J_BUZ1": ("BUZ", "Connector_Generic:Conn_01x04", XH4),
    "J_SPK1": ("SPK", "Connector_Generic:Conn_01x04", XH4),
    # Cell protection in the negative lead (the Heltec V4 has no under-voltage cutoff, see
    # fab/PARTS_REVIEW.md): 2.5 V over-discharge, 4.25 V overcharge, 10 A overcurrent, short circuit.
    # Board GND is the protected pack negative (VM); only J_BAT1.2 sees the raw cell negative.
    "U4": ("XB8089D", "local:XB8089D", SOIC8EP),
    # Power
    "F1": ("2A PTC", "Device:Polyfuse", "Fuse:Fuse_1206_3216Metric_Pad1.42x1.75mm_HandSolder"),
    "U1": ("MT3608", "Regulator_Switching:MT3608", "Package_TO_SOT_SMD:SOT-23-6"),
    "L1": ("10uH 2A", "Device:L", "Inductor_SMD:L_Bourns_SRN6045TA"),
    "D1": ("SS34", "Diode:SS34", "Diode_SMD:D_SMA"),
    "R_FB1": ("75k", "Device:R", "Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder"),
    "R_FB2": ("10k", "Device:R", "Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder"),
    "C_IN1": ("22uF 25V", "Device:C", C1206),
    "C_OUT1": ("22uF 25V", "Device:C", C1206),
    "C_OUT2": ("22uF 25V", "Device:C", C1206),
    "C_BULK1": ("47uF 10V", "Device:C", C1206),
    "C_BULK2": ("47uF 10V", "Device:C", C1206),
    "C_NFC1": ("100uF 6.3V", "Device:C", C1206),
    # I2C GPIO expander (address 0x20) for buttons, LED/buzzer drivers and the amp's CTRL
    "U2": ("TCA9534PWR", "Interface_Expansion:TCA9534", TSSOP16),
    # I2S class-D amp on VBAT_SW, BTL output to J_SPK1, fixed gain. Replaced the MAX98357A on 2026-09-30
    # (about $0.95 cheaper per board; same Extended setup fee). CTRL high = right I2S slot, low = off.
    "U3": ("NS4168", "local:NS4168", ESOP8),
    # Datasheet asks for ~100 uF + 1 uF at VDD; the 100 uF 6.3 V part is fine on a <= 4.2 V rail
    "C_AMP1": ("100uF 6.3V", "Device:C", C1206),
    # I2C level shifter (5V-side pull-ups DNP: LCD backpack has its own)
    "Q_SDA1": ("BSS138", *BSS138),
    "Q_SCL1": ("BSS138", *BSS138),
    "R_SDA3": ("4k7", "Device:R", "Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder"),
    "R_SCL3": ("4k7", "Device:R", "Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder"),
    "R_SDA5": ("4k7", "Device:R", "Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder"),
    "R_SCL5": ("4k7", "Device:R", "Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder"),
}
# 2-wire connectors: pins 3-4 are unused (gen_sch.py flags them no-connect).
XH_SPARE = {f"{r}.{n}" for r in ("J_BAT1", "J_KEY1", "J_HBAT1", "J_BUZ1", "J_SPK1") for n in (3, 4)}
# Do not populate: the LCD backpack has its own 5V-side pull-ups.
DNP = {"R_SDA5", "R_SCL5"}


# Low-side drivers (loads are ~15 mA LED rings and an ~8 mA buzzer, well inside a BSS138): name -> load resistor value or None. The ONPOW LAS1-AGQ-11E/x/6V button LEDs
# have a built-in resistor, so R_LLR1/R_LLB1 are 0R jumpers (footprint kept as a brightness knob).
DRIVERS = {"LR": "0R", "LB": "0R", "BZ": None}
for n, r_load in DRIVERS.items():
    PARTS[f"Q_{n}1"] = ("BSS138", *BSS138)
    PARTS[f"R_G{n}1"] = ("1k", *R0805)
    PARTS[f"R_PD{n}1"] = ("10k", *R0805)
    if r_load:
        PARTS[f"R_L{n}1"] = (r_load, *R0805)
PARTS["D_FLY1"] = ("1N4148W", "Diode:1N4148W", "Diode_SMD:D_SOD-123")

# Button inputs: 10k pull-up, 100nF, 1k series
for t in ("R", "B"):
    PARTS[f"R_PU{t}1"] = ("10k", *R0805)
    PARTS[f"R_S{t}1"] = ("1k", *R0805)
    PARTS[f"C_B{t}1"] = ("100nF", *C0805)
PARTS["C_EXP1"] = ("100nF", *C0805)  # U2 decoupling
PARTS["R_INT1"] = ("10k", *R0805)  # U2 INT pull-up
PARTS["C_AMP2"] = ("100nF", *C0805)  # U3 VDD decoupling (next to C_AMP1)
# CTRL series resistor + pull-down: CTRL abs max is VDD (VBAT_SW, can sag below the 3V3 expander high),
# the 1k limits that current. No internal pull-down is documented, so the 10k (expander side; CTRL draws
# no current, so it still pulls CTRL to 0 V) holds the amp off while the expander pins float at reset.
PARTS["R_SD1"] = ("1k", *R0805)
PARTS["R_SDPD1"] = ("10k", *R0805)
# U4 supply filter from the datasheet application circuit: 1k from BAT+, 100nF to the cell negative
PARTS["R_PROT1"] = ("1k", *R0805)
PARTS["C_PROT1"] = ("100nF", *C0805)

for i in range(1, 5):
    PARTS[f"H{i}"] = ("M3", "Mechanical:MountingHole", "MountingHole:MountingHole_3.2mm_M3")

# JLCPCB assembly: (value, footprint) -> LCSC part number. Changing a part's value or footprint
# fails check() until a new part is picked (editing the shared R0805/C0805/BSS138 tuples moves
# their keys along). All verified live against JLCPCB's parts API on 2026-09-29.
# Type: B = Basic, P = Preferred Extended (no setup fee), E = Extended.
LCSC = {
    ("100nF", C0805[1]): "C49678",  # B YAGEO CC0805KRX7R9BB104 50V X7R
    ("22uF 25V", C1206): "C12891",  # B Samsung CL31A226KAHNNNE X5R
    ("47uF 10V", C1206): "C96123",  # B Samsung CL31A476MPHNNNE X5R
    ("100uF 6.3V", C1206): "C15008",  # B Samsung CL31A107MQHNNNE X5R
    ("SS34", "Diode_SMD:D_SMA"): "C8678",  # B MDD SS34
    ("1N4148W", "Diode_SMD:D_SOD-123"): "C81598",  # B ST Semtech 1N4148W
    ("2A PTC", "Fuse:Fuse_1206_3216Metric_Pad1.42x1.75mm_HandSolder"): "C22374899",  # E LUTE 1206L200/16NR 2A hold 16V
    ("TCA9534PWR", TSSOP16): "C783615",  # E TI TCA9534PWR
    ("XB8089D", SOIC8EP): "C79928",  # E XySemi XB8089D (checked on jlcpcb.com/lcsc.com 2026-09-30)
    ("NS4168", ESOP8): "C910588",  # E Nsiway NS4168 (lcsc.com 2026-09-30: $0.38, ~9.9k stock)
    ("10uH 2A", "Inductor_SMD:L_Bourns_SRN6045TA"): "C2046332",  # E Bourns SRN6045TA-100M
    ("MT3608", "Package_TO_SOT_SMD:SOT-23-6"): "C84817",  # E XI'AN Aerosemi MT3608 (1 SW 2 GND 3 FB 4 EN 5 VIN)
    ("BSS138", BSS138[1]): "C7420339",  # P hongjiacheng BSS138 (G=1 S=2 D=3)
    ("75k", R0805[1]): "C17819",  # P UNI-ROYAL 0805W8F7502T5E
    ("10k", R0805[1]): "C17414",  # B 0805W8F1002T5E
    ("0R", R0805[1]): "C17477",  # B UNI-ROYAL 0805W8F0000T5E
    ("1k", R0805[1]): "C17513",  # B 0805W8F1001T5E
    ("4k7", R0805[1]): "C17673",  # B 0805W8F4701T5E
    ("Heltec_J2", SOCKET18): "C2905422",  # E Kinghelm KH-2.54FH-1X18P-H8.5
    ("Heltec_J3", SOCKET18): "C2905422",
}
# Connector values are names, so every name maps to the same part.
LCSC |= {(v, XH4): "C144395" for v in ("BAT", "KEY", "HELTEC_BAT", "BUZ", "SPK", "LCD", "NFC", "BTN_R", "BTN_B")}  # E JST B4B-XH-A(LF)(SN)

# net: [ "REF.pin", ... ]
NETS = {
    "GND": ["J2.1", "J3.1", "U4.1", "U4.2", "U4.3", "U4.4", "J_HBAT1.2", "J_LCD1.1", "J_NFC1.1", "J_BTN_R1.2", "J_BTN_B1.2",
            "U1.2", "R_FB2.2", "C_IN1.2", "C_OUT1.2", "C_OUT2.2", "C_BULK1.2", "C_BULK2.2", "C_NFC1.2",
            "Q_LR1.2", "Q_LB1.2", "Q_BZ1.2", "R_PDLR1.2", "R_PDLB1.2", "R_PDBZ1.2", "C_BR1.2", "C_BB1.2",
            "U2.1", "U2.2", "U2.3", "U2.8", "C_EXP1.2",  # A0-A2 low: address 0x20
            "U3.7", "U3.9", "C_AMP1.2", "C_AMP2.2", "R_SDPD1.2"],
    "+3V3": ["J3.2", "J3.3", "J_NFC1.2", "C_NFC1.1", "Q_SDA1.1", "Q_SCL1.1", "R_SDA3.1", "R_SCL3.1", "R_PUR1.1", "R_PUB1.1",
             "U2.16", "C_EXP1.1", "R_INT1.1"],
    "VBAT_RAW": ["J_BAT1.1", "F1.1", "R_PROT1.1"],
    "BAT_N": ["J_BAT1.2", "U4.5", "U4.7", "U4.8", "U4.9", "C_PROT1.2"],  # raw cell negative
    "PROT_VDD": ["R_PROT1.2", "U4.6", "C_PROT1.1"],
    "VBAT_F": ["F1.2", "J_KEY1.1"],
    "VBAT_SW": ["J_KEY1.2", "J_HBAT1.1", "C_BULK1.1", "C_BULK2.1", "C_IN1.1", "U1.5", "U1.4", "L1.1",
                "U3.6", "C_AMP1.1", "C_AMP2.1"],
    "SW": ["L1.2", "U1.1", "D1.2"],
    "FB": ["U1.3", "R_FB1.2", "R_FB2.1"],
    "+5V": ["D1.1", "C_OUT1.1", "C_OUT2.1", "R_FB1.1", "J_LCD1.2", "J_BTN_R1.3", "J_BTN_B1.3", "J_BUZ1.1",
            "D_FLY1.1", "R_SDA5.1", "R_SCL5.1"],
    # I2C
    "SDA_3V3": ["J3.15", "Q_SDA1.2", "R_SDA3.2", "J_NFC1.3", "U2.15"],
    "SCL_3V3": ["J3.14", "Q_SCL1.2", "R_SCL3.2", "J_NFC1.4", "U2.14"],
    "EXP_INT": ["J3.17", "U2.13", "R_INT1.2"],  # open drain, active low
    # I2S to the amp; CTRL from the expander (high = right slot, low = shutdown)
    "I2S_BCLK": ["J2.13", "U3.3"], "I2S_LRCLK": ["J2.14", "U3.2"], "I2S_DIN": ["J2.16", "U3.4"],
    "AMP_SD": ["U2.10", "R_SD1.1", "R_SDPD1.1"], "AMP_SD_R": ["R_SD1.2", "U3.1"],
    "SPK_N": ["U3.5", "J_SPK1.1"], "SPK_P": ["U3.8", "J_SPK1.2"],
    "SDA_5V": ["Q_SDA1.3", "R_SDA5.2", "J_LCD1.3"],
    "SCL_5V": ["Q_SCL1.3", "R_SCL5.2", "J_LCD1.4"],
    # Drivers: expander P2-P4 -> gate resistor -> gate (pull-down) ; drain -> load
    "LED_R_G": ["U2.6", "R_GLR1.1"], "Q_LR_G": ["R_GLR1.2", "Q_LR1.1", "R_PDLR1.1"],
    "LED_R_K": ["Q_LR1.3", "R_LLR1.1"], "BTN_R_LEDK": ["R_LLR1.2", "J_BTN_R1.4"],
    "LED_B_G": ["U2.7", "R_GLB1.1"], "Q_LB_G": ["R_GLB1.2", "Q_LB1.1", "R_PDLB1.1"],
    "LED_B_K": ["Q_LB1.3", "R_LLB1.1"], "BTN_B_LEDK": ["R_LLB1.2", "J_BTN_B1.4"],
    "BUZ_G": ["U2.9", "R_GBZ1.1"], "Q_BZ_G": ["R_GBZ1.2", "Q_BZ1.1", "R_PDBZ1.1"],
    "BUZ_K": ["Q_BZ1.3", "J_BUZ1.2", "D_FLY1.2"],
    # Buttons: switch pulls to GND; RC output to expander P0/P1
    "BTN_R_SW": ["J_BTN_R1.1", "R_PUR1.2", "C_BR1.1", "R_SR1.1"], "BTN_R_IN": ["R_SR1.2", "U2.4"],
    "BTN_B_SW": ["J_BTN_B1.1", "R_PUB1.2", "C_BB1.1", "R_SB1.1"], "BTN_B_IN": ["R_SB1.2", "U2.5"],
}

# Heltec header pin -> ESP32 GPIO (V4 pin map). Only pins we use or must avoid.
HELTEC_GPIO = {
    "J3.12": 1, "J3.13": 2, "J3.14": 3, "J3.15": 4, "J3.16": 5, "J3.17": 6, "J3.18": 7,
    "J3.4": 37, "J3.5": 46, "J3.6": 45, "J3.7": 42, "J3.8": 41, "J3.9": 40, "J3.10": 39, "J3.11": 38,
    "J2.5": 44, "J2.6": 43, "J2.7": None, "J2.8": 0, "J2.9": 36, "J2.10": 35, "J2.11": 34, "J2.12": 33,
    "J2.13": 47, "J2.14": 48, "J2.15": 26, "J2.16": 21, "J2.17": 20, "J2.18": 19,
}
# Used internally on V4-R2 or V4-R8 (FEM, GNSS, PSRAM, strapping, USB, LED/Vext, VBAT), or RST.
# GPIO3 is a strapping pin (JTAG source select), but only if the STRAP_JTAG_SEL
# efuse is burned. With default efuses it is safe for SCL, so it is not forbidden.
FORBIDDEN_GPIO = {0, 1, 2, 5, 7, 19, 20, 26, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 45, 46, None}
EXPECTED_GPIO = {"SCL_3V3": 3, "SDA_3V3": 4, "EXP_INT": 6,
                 "I2S_BCLK": 47, "I2S_LRCLK": 48, "I2S_DIN": 21}
HEADER_POWER = {"J2.1": "GND", "J3.1": "GND", "J3.2": "+3V3", "J3.3": "+3V3"}
HEADER_NC = {"J2.2", "J2.3", "J2.4"}  # 5V charger input, Vext x2: must stay unconnected


# Build variants: one board, fewer parts populated. The pin map never changes (everything
# slow already sits behind the U2 expander), so a variant is just a BOM/CPL without a module's refs.
# GPS, enclosure and the other off-board parts are not on the board: they only matter for cost.
# The buzzer path (Q_BZ1, R_GBZ1, R_PDBZ1, D_FLY1, J_BUZ1) and U2 are core and always populated.
MODULES = {
    "speaker": {"U3", "C_AMP1", "C_AMP2", "R_SD1", "R_SDPD1", "J_SPK1"},
    "rfid": {"J_NFC1"},
    "buttons": {"J_BTN_R1", "J_BTN_B1", "Q_LR1", "Q_LB1", "R_GLR1", "R_GLB1", "R_PDLR1", "R_PDLB1",
                "R_LLR1", "R_LLB1", "R_PUR1", "R_PUB1", "R_SR1", "R_SB1", "C_BR1", "C_BB1"},
}
VARIANTS = {
    "deluxe": {"speaker", "rfid", "buttons"},
    "budget": {"buttons"},
}


def assembled(variant="deluxe"):
    """Refs JLCPCB places: everything except DNP parts, mounting holes and modules the variant drops."""
    dropped = set().union(*(MODULES[m] for m in MODULES.keys() - VARIANTS[variant]))
    return [r for r, (_, sym, _) in PARTS.items()
            if r not in DNP | dropped and sym != "Mechanical:MountingHole"]



# --- layout (read by gen_sch.py / gen_pcb.py / check_gerbers.py) ---
NAME = "carrier"
TITLE = "AirsoftCounter v2 carrier"
# Nets that get the wider Power class: gen_sch.py writes them into .kicad_pro, gen_pcb.verify checks.
NETCLASS_POWER = ("VBAT*", "BAT_N", "+5V", "SW")
# (net, [track width, clearance]) the reloaded board must resolve (gen_pcb.verify).
NETCLASS_EXPECT = (("VBAT_SW", [0.8, 0.2]), ("GND", [0.25, 0.2]), ("+5V", [0.8, 0.2]),
                   ("SW", [0.8, 0.2]), ("SPK_P", [0.25, 0.2]), ("SDA_3V3", [0.25, 0.2]))

RAILS = ("GND", "+3V3", "+5V", "VBAT_SW")
# Power ports name their net by Value, so VBAT_SW reuses the stock +BATT arrow: a stock
# symbol keeps ERC's library check (lib_symbol_issues) clean with no ignore.
PORT_LIB = {"GND": "power:GND", "+3V3": "power:+3V3", "+5V": "power:+5V", "VBAT_SW": "power:+BATT"}
NC_PARTS = {"J2", "J3"}  # every unconnected pin gets a no-connect flag
NC_PINS = {"U1.6",  # MT3608 NC
           "U2.11", "U2.12"}  # TCA9534 P6/P7 spare


# --- Layout: blocks of hand-placed parts ---
# Block: title, sheet origin (x, y), size (w, h), parts {ref: (dx, dy, rot, mirror)},
# wired rails (drawn as wires in this block, with one power port each in "tags"),
# tags {net: [(dx, dy, dir)]}: a global label (or the power port of a wired rail) at that point,
# pointing dir; flags [(net, dx, dy)]: a PWR_FLAG wired to a port of that rail;
# fields {ref: {"Reference"/"Value": (dx, dy, justify)}}: horizontal text at that offset from the part.
# Nets without a tag get a label on a wire (one-block nets) or at a pin (a lone pin in a block).
def _driver(x0, n, load):
    """One low-side driver at x offset x0: gate resistor, pull-down, BSS138, load resistor."""
    parts = {f"R_G{n}1": (x0 + 10.16, 38.1, 90, None), f"R_PD{n}1": (x0 + 17.78, 45.72, 0, None),
             f"Q_{n}1": (x0 + 33.02, 38.1, 0, None)}
    if load:
        parts[f"R_L{n}1"] = (x0 + 35.56, 16.51, 180, None)
    return parts


BLOCKS = [
    {"title": "Battery, key switch, 5 V boost", "at": (12.7, 12.7), "size": (190.5, 63.5),
     "parts": {"J_BAT1": (7.62, 25.4, 0, "y"), "F1": (35.56, 22.86, 90, None),
               "J_KEY1": (53.34, 17.78, 90, None), "J_HBAT1": (60.96, 38.1, 0, None),
               "C_BULK1": (73.66, 31.75, 0, None), "C_BULK2": (86.36, 31.75, 0, None),
               "C_IN1": (99.06, 31.75, 0, None), "U1": (121.92, 40.64, 0, None),
               "L1": (121.92, 22.86, 90, None), "D1": (140.97, 22.86, 180, None),
               "R_FB1": (152.4, 35.56, 0, None), "R_FB2": (152.4, 46.99, 0, None),
               "C_OUT1": (165.1, 31.75, 0, None), "C_OUT2": (177.8, 31.75, 0, None),
               "U4": (38.1, 43.18, 0, None), "C_PROT1": (17.78, 45.72, 0, None),
               "R_PROT1": (17.78, 33.02, 0, None)},
     "wired": {"VBAT_SW", "+5V"},
     "tags": {"VBAT_SW": [(66.04, 22.86, "U")], "+5V": [(185.42, 22.86, "U")], "PROT_VDD": [(22.86, 40.64, "U")]},
     "flags": [("GND", 7.62, 55.88), ("VBAT_SW", 30.48, 55.88), ("+5V", 53.34, 55.88)],
     "fields": {"J_KEY1": {"Reference": (-5.08, -1.27, "right"), "Value": (-5.08, 1.27, "right")},
                "U4": {"Reference": (-7.62, -6.35, "left"), "Value": (7.62, -6.35, "right")}}},
    {"title": "I2S speaker amp", "at": (208.28, 12.7), "size": (104.14, 63.5),
     "parts": {"U3": (55.88, 38.1, 0, None), "R_SD1": (25.4, 40.64, 90, None),
               "R_SDPD1": (17.78, 45.72, 0, None),
               "C_AMP1": (68.58, 17.78, 0, None), "C_AMP2": (81.28, 17.78, 0, None),
               "J_SPK1": (96.52, 30.48, 0, "x")},
     "tags": {"AMP_SD": [(13.97, 40.64, "L")]}},
    {"title": "Heltec V4 headers", "at": (317.5, 12.7), "size": (86.36, 76.2),
     "parts": {"J2": (30.48, 38.1, 0, None), "J3": (73.66, 38.1, 0, None)},
     "flags": [("+3V3", 40.64, 68.58)]},
    {"title": "I2C level shifter, LCD (5 V), NFC (3.3 V)", "at": (12.7, 81.28), "size": (111.76, 76.2),
     "parts": {"J_NFC1": (7.62, 38.1, 0, "y"), "C_NFC1": (7.62, 60.96, 0, None),
               "R_SDA3": (33.02, 24.13, 0, None), "Q_SDA1": (45.72, 25.4, 270, None),
               "R_SDA5": (62.23, 24.13, 0, None),
               "R_SCL3": (33.02, 46.99, 0, None), "Q_SCL1": (45.72, 48.26, 270, None),
               "R_SCL5": (62.23, 46.99, 0, None), "J_LCD1": (91.44, 25.4, 0, None)},
     "tags": {"SDA_3V3": [(22.86, 20.32, "U")], "SCL_3V3": [(22.86, 60.96, "D")]},
     "fields": {"Q_SDA1": {"Reference": (3.81, -5.08, "left"), "Value": (3.81, -2.54, "left")},
                "Q_SCL1": {"Reference": (3.81, -5.08, "left"), "Value": (3.81, -2.54, "left")}}},
    {"title": "GPIO expander (0x20), button inputs", "at": (129.54, 81.28), "size": (182.88, 76.2),
     "parts": {"U2": (55.88, 50.8, 0, None), "C_EXP1": (38.1, 30.48, 0, None),
               "R_INT1": (25.4, 40.64, 0, None),
               "R_SR1": (82.55, 22.86, 270, None), "R_PUR1": (114.3, 15.24, 0, None),
               "C_BR1": (121.92, 30.48, 0, None), "J_BTN_R1": (152.4, 25.4, 0, None),
               "R_SB1": (99.06, 43.18, 270, None), "R_PUB1": (111.76, 35.56, 0, None),
               "C_BB1": (119.38, 50.8, 0, None), "J_BTN_B1": (152.4, 45.72, 0, None)},
     "tags": {"EXP_INT": [(15.24, 48.26, "L")]}},
    {"title": "Low-side drivers: button LEDs, buzzer", "at": (12.7, 162.56), "size": (190.5, 60.96),
     "parts": {**_driver(12.7, "LR", True), **_driver(71.12, "LB", True), **_driver(129.54, "BZ", False),
               "D_FLY1": (165.1, 20.32, 270, None), "J_BUZ1": (182.88, 25.4, 0, None)},
     "tags": {"LED_R_G": [(12.7, 38.1, "L")], "LED_B_G": [(71.12, 38.1, "L")], "BUZ_G": [(129.54, 38.1, "L")],
              "BTN_R_LEDK": [(50.8, 10.16, "R")], "BTN_B_LEDK": [(109.22, 10.16, "R")]}},
    {"title": "Mounting holes", "at": (208.28, 162.56), "size": (50.8, 25.4),
     "parts": {"H1": (7.62, 15.24, 0, None), "H2": (17.78, 15.24, 0, None),
               "H3": (27.94, 15.24, 0, None), "H4": (38.1, 15.24, 0, None)}},
]


W, H, CORNER = 90.0, 60.0, 2.0

# ref: (x, y, rotation deg). Footprint origin = pad 1 for connectors and THT caps.
PLACE = {
    # Heltec V4 headers: pin 1 at the USB end (left), pins run +X (asserted in build)
    "J3": (44.82, 27.00, 90), "J2": (44.82, 49.86, 90),
    "H1": (3.5, 3.5, 0), "H2": (86.5, 3.5, 0), "H3": (3.5, 56.5, 0), "H4": (86.5, 56.5, 0),
    # Top edge: XH open side (-Y at rotation 0) faces the board edge, pin 1 left
    # (4-pin XH courtyards are 13.5 mm: five fit between H1 and H2, a sixth does not)
    "J_BAT1": (10, 6, 0), "J_KEY1": (24.5, 6, 0), "J_HBAT1": (39, 6, 0),
    "J_LCD1": (53.5, 6, 0), "J_NFC1": (68, 6, 0),
    # Bottom edge, under the J2 row: open side faces +Y, pin 1 right
    "J_BTN_R1": (76, 55.75, 180),
    # Left edge: rotated so the open side faces -X, pin 1 at the bottom
    "J_SPK1": (6, 20.5, 90), "J_BTN_B1": (6, 35, 90), "J_BUZ1": (6, 49.5, 90),
    # I2S amp beside J_SPK1 (outputs face up at 90 deg), VDD caps above it; C_AMP2 at 180 puts its
    # VBAT_SW pad over U3.6 (VDD) and its GND pad over U3.7
    "U3": (15.2, 23.2, 90), "C_AMP2": (15.2, 18.4, 180), "C_AMP1": (15.2, 14.9, 0),
    # Power: MT3608 boost; output loop (SW -> D1 -> C_OUT -> GND) on U1's SW/GND side
    "F1": (19.5, 11.3, 0), "C_BULK1": (37, 17, 90), "C_BULK2": (40.5, 17, 90),
    "L1": (28.5, 15.5, 180), "D1": (21.3, 16, 0), "U1": (27, 21.5, 0), "C_IN1": (31.2, 21.8, 270),
    "C_OUT1": (21, 20, 0), "C_OUT2": (21, 22.9, 0),
    "R_FB2": (26.5, 25.5, 0), "R_FB1": (22, 26, 0),
    # Cell protection in the free strip left of J3 (VM pins 1-4 face the boost block's GND)
    "U4": (37.7, 27.4, 0), "R_PROT1": (35.9, 32.5, 0), "C_PROT1": (40.0, 32.5, 0),
    # I2C level shifter, NFC bulk cap and GPIO expander, under their connectors
    "Q_SDA1": (44, 16, 0), "R_SDA3": (44, 20, 0), "R_SDA5": (44, 23.3, 0),
    "Q_SCL1": (49.5, 16, 0), "R_SCL3": (49.5, 20, 0), "R_SCL5": (49.5, 23.3, 0),
    "C_NFC1": (55.5, 15.3, 0), "R_SD1": (54.5, 21.5, 90),
    "U2": (60.2, 21, 0), "R_SDPD1": (75.5, 13.0, 0), "C_EXP1": (60.5, 15.6, 0), "R_INT1": (66, 22.8, 0),
    # Low-side drivers, one column each (top to bottom R_G, R_PD, Q, R_L): gate pads on one
    # vertical line at x+1, GND pads at x-1, drain straight down into R_L
    "R_GLB1": (16, 29, 0), "R_PDLB1": (16, 32, 180), "Q_LB1": (16, 35.5, 270), "R_LLB1": (16, 39.5, 270),
    "R_GBZ1": (24, 29, 0), "R_PDBZ1": (24, 32, 180), "Q_BZ1": (24, 35.5, 270),
    "R_GLR1": (32, 29, 0), "R_PDLR1": (32, 32, 180), "Q_LR1": (32, 35.5, 270), "R_LLR1": (32, 39.5, 270),
    "D_FLY1": (15, 45, 0),
    # Button RC: BTN_B near its connector, BTN_R near J_BTN_R1 and the expander
    "R_PUB1": (20, 49, 0), "C_BB1": (20, 52.5, 0), "R_SB1": (25, 50.75, 0),
    "R_PUR1": (66, 15.5, 0), "C_BR1": (66, 19, 0), "R_SR1": (71, 17.25, 0),
}

# Reference text moved off neighbouring silk in the packed boost block: ref -> (x, y, rot)
REF_AT = {
    "L1": (33.3, 15.5, 90), "U1": (29.55, 21.5, 90), "C_OUT1": (21, 18.4, 0),
    "C_OUT2": (21, 24.6, 0), "R_FB1": (19.3, 27.0, 90), "C_IN1": (33.05, 21.8, 90),
    "F1": (23.5, 11.3, 0),  # F1 sits right under the top connector labels
    "U3": (13.45, 23.2, 90),  # inside U3's outline, left of the exposed pad (the SPK label is outside)
    "R_PROT1": (40.0, 34.4, 0), "C_PROT1": (40.0, 36.0, 0), "R_SDPD1": (75.5, 14.7, 0),  # staggered below the parts, clear of U4/Q_LR1 silk
    "J_BTN_R1": (60, 53.1, 0),  # between J2 and its label (default lands inside the body at 180 deg)
}

# Connector silk labels (name, pins in pin-1-first order). Pin 1 is the left pad at rot 0 and
# the bottom pad at rot 90; text reads left-to-right / bottom-to-top, so pin 1 comes first
# (at rot 180 pin 1 is the right pad; label() reverses the list).
LABELS = {
    "J_BAT1": ("BAT", "+  -"), "J_KEY1": ("KEY", ""), "J_HBAT1": ("HELTEC BAT", "+  -"),
    "J_LCD1": ("LCD", "GND 5V SDA SCL"), "J_NFC1": ("NFC", "GND 3V3 SDA SCL"),
    "J_BTN_R1": ("BTN_R", "SW GND L+ L-"), "J_BTN_B1": ("BTN_B", "SW GND L+ L-"), "J_BUZ1": ("BUZ", "+  -"),
    "J_SPK1": ("SPK (BTL, not GND)", "OUT- OUT+"),
}
# free text: (text, x, y, rot, size, left-justified)
TEXTS = [
    ("AirsoftCounter v2 carrier", 9, 56.5, 0, 1.0, True), ("2026-09", 9, 58.3, 0, 1.0, True),
    ("USB", 40.5, 38.43, 90, 1.0, False), ("ANT →", 84, 38.43, 0, 1.0, False),
]


# Locked GND vias gen_pcb places before routing (route.py keeps them): (x, y, pad it is tied to).
# C_AMP1/C_AMP2 get a via beside their GND pad, so the amp decoupling returns straight to the B.Cu
# pour instead of through a long F.Cu detour (the F.Cu pour around U3 is cut up by traces).
# The untied three stitch the pours along the I2S corridor, next to where the I2S lines change layer
# and cross B.Cu traces (+5V/LED_B_G, +3V3, BTN_B_IN), so their return current can follow them.
GND_VIAS = [(18.0, 14.2, ("C_AMP1", "2")), (12.9, 18.4, ("C_AMP2", "2")),
            (21.4, 28.3, None), (29.0, 43.6, None), (37.2, 45.5, None)]
HELTEC_PADS = {("J3", "1"): (44.82, 27.00), ("J3", "18"): (88.00, 27.00),
               ("J2", "1"): (44.82, 49.86), ("J2", "18"): (88.00, 49.86)}


SIZE_MM = (W, H)
# Mounting-hole centres checked against the NPTH drill file (check_gerbers.py).
NPTH_XY = sorted((PLACE[r][0], PLACE[r][1]) for r in ("H1", "H2", "H3", "H4"))

def check():
    # Board-independent structure lives in board.check_structure, so pack.py runs the same checks.
    import sys

    import board  # pyright: ignore[reportMissingImports]
    board.check_structure(sys.modules[__name__])
    # Carrier specifics: every Heltec header pin known/mapped, no reserved GPIO, a variant loads an input.
    pins = [p for members in NETS.values() for p in members]
    net_of = {p: net for net, m in NETS.items() for p in m}
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
    got = sorted((n, HELTEC_GPIO[p]) for n, m in NETS.items() for p in m if p in HELTEC_GPIO)
    assert got == sorted(EXPECTED_GPIO.items()), got
    for v, mods in VARIANTS.items():
        assert mods & {"buttons", "rfid"}, f"variant {v} has no input (needs buttons or rfid)"
    print(f"design ok: {len(PARTS)} parts, {len(NETS)} nets, variants {sorted(VARIANTS)}")


if __name__ == "__main__":
    check()
