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
AO3400A = ("Transistor_FET:AO3400A", "Package_TO_SOT_SMD:SOT-23")
C1206 = "Capacitor_SMD:C_1206_3216Metric_Pad1.33x1.80mm_HandSolder"
TSSOP16 = "Package_SO:TSSOP-16_4.4x5mm_P0.65mm"
TQFN16 = "Package_DFN_QFN:TQFN-16-1EP_3x3mm_P0.5mm_EP1.23x1.23mm_ThermalVias"
XH2 = "Connector_JST:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical"
XH4 = "Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical"
SOCKET18 = "Connector_PinSocket_2.54mm:PinSocket_1x18_P2.54mm_Vertical"

# ref: (value, symbol "lib:name", footprint "lib:name")
PARTS = {
    # Heltec WiFi LoRa 32 V4 headers (pin 1 at USB end). Rows are 22.86 mm apart.
    "J2": ("Heltec_J2", "Connector_Generic:Conn_01x18", SOCKET18),
    "J3": ("Heltec_J3", "Connector_Generic:Conn_01x18", SOCKET18),
    # Off-board connectors, JST-XH 2.50 mm vertical
    "J_BAT1": ("BAT", "Connector_Generic:Conn_01x02", XH2),
    "J_KEY1": ("KEY", "Connector_Generic:Conn_01x02", XH2),
    "J_HBAT1": ("HELTEC_BAT", "Connector_Generic:Conn_01x02", XH2),
    "J_LCD1": ("LCD", "Connector_Generic:Conn_01x04", XH4),
    "J_NFC1": ("NFC", "Connector_Generic:Conn_01x04", XH4),
    "J_BTN_R1": ("BTN_R", "Connector_Generic:Conn_01x04", XH4),
    "J_BTN_B1": ("BTN_B", "Connector_Generic:Conn_01x04", XH4),
    "J_BUZ1": ("BUZ", "Connector_Generic:Conn_01x02", XH2),
    "J_SPK1": ("SPK", "Connector_Generic:Conn_01x02", XH2),
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
    # I2C GPIO expander (address 0x20) for buttons, LED/buzzer drivers and the amp's SD_MODE
    "U2": ("TCA9534PWR", "Interface_Expansion:TCA9534", TSSOP16),
    # I2S class-D amp on VBAT_SW, BTL output to J_SPK1, 12 dB (GAIN_SLOT to GND)
    "U3": ("MAX98357A", "Audio:MAX98357A", TQFN16),
    "C_AMP1": ("22uF 25V", "Device:C", C1206),
    # I2C level shifter (5V-side pull-ups DNP: LCD backpack has its own)
    "Q_SDA1": ("BSS138", "Transistor_FET:BSS138", "Package_TO_SOT_SMD:SOT-23"),
    "Q_SCL1": ("BSS138", "Transistor_FET:BSS138", "Package_TO_SOT_SMD:SOT-23"),
    "R_SDA3": ("4k7", "Device:R", "Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder"),
    "R_SCL3": ("4k7", "Device:R", "Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder"),
    "R_SDA5": ("4k7", "Device:R", "Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder"),
    "R_SCL5": ("4k7", "Device:R", "Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder"),
}
# Do not populate: the LCD backpack has its own 5V-side pull-ups.
DNP = {"R_SDA5", "R_SCL5"}


# Low-side drivers: name -> load resistor value or None. The ONPOW LAS1-AGQ-11E/x/6V button LEDs
# have a built-in resistor, so R_LLR1/R_LLB1 are 0R jumpers (footprint kept as a brightness knob).
DRIVERS = {"LR": "0R", "LB": "0R", "BZ": None}
for n, r_load in DRIVERS.items():
    PARTS[f"Q_{n}1"] = ("AO3400A", *AO3400A)
    PARTS[f"R_G{n}1"] = ("100R", *R0805)
    PARTS[f"R_PD{n}1"] = ("100k", *R0805)
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
# SD_MODE series resistor: 3V3 logic high into SD_MODE (abs max VDD + 0.3 V) when VBAT_SW sags below
# ~3 V; datasheet asks for ~2k, 1k reuses a BOM line and still reads as logic high (100k pull-down inside).
PARTS["R_SD1"] = ("1k", *R0805)

for i in range(1, 5):
    PARTS[f"H{i}"] = ("M3", "Mechanical:MountingHole", "MountingHole:MountingHole_3.2mm_M3")

# JLCPCB assembly: (value, footprint) -> LCSC part number. Changing a part's value or footprint
# fails check() until a new part is picked (editing the shared R0805/C0805/AO3400A tuples moves
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
    ("MAX98357A", TQFN16): "C910544",  # E Maxim MAX98357AETE+T
    ("10uH 2A", "Inductor_SMD:L_Bourns_SRN6045TA"): "C2046332",  # E Bourns SRN6045TA-100M
    ("MT3608", "Package_TO_SOT_SMD:SOT-23-6"): "C84817",  # E XI'AN Aerosemi MT3608 (1 SW 2 GND 3 FB 4 EN 5 VIN)
    ("AO3400A", AO3400A[1]): "C20917",  # B AOS AO3400A
    ("BSS138", AO3400A[1]): "C7420339",  # P hongjiacheng BSS138 (G=1 S=2 D=3)
    ("75k", R0805[1]): "C17819",  # P UNI-ROYAL 0805W8F7502T5E
    ("10k", R0805[1]): "C17414",  # B 0805W8F1002T5E
    ("100R", R0805[1]): "C17408",  # B 0805W8F1000T5E
    ("0R", R0805[1]): "C17477",  # B UNI-ROYAL 0805W8F0000T5E
    ("100k", R0805[1]): "C149504",  # B 0805W8F1003T5E
    ("1k", R0805[1]): "C17513",  # B 0805W8F1001T5E
    ("4k7", R0805[1]): "C17673",  # B 0805W8F4701T5E
    ("Heltec_J2", SOCKET18): "C2905422",  # E Kinghelm KH-2.54FH-1X18P-H8.5
    ("Heltec_J3", SOCKET18): "C2905422",
}
# Connector values are names, so every name maps to the same part.
LCSC |= {(v, XH2): "C158012" for v in ("BAT", "KEY", "HELTEC_BAT", "BUZ", "SPK")}  # E JST B2B-XH-A(LF)(SN)
LCSC |= {(v, XH4): "C144395" for v in ("LCD", "NFC", "BTN_R", "BTN_B")}  # E JST B4B-XH-A(LF)(SN)

# net: [ "REF.pin", ... ]
NETS = {
    "GND": ["J2.1", "J3.1", "J_BAT1.2", "J_HBAT1.2", "J_LCD1.1", "J_NFC1.1", "J_BTN_R1.2", "J_BTN_B1.2",
            "U1.2", "R_FB2.2", "C_IN1.2", "C_OUT1.2", "C_OUT2.2", "C_BULK1.2", "C_BULK2.2", "C_NFC1.2",
            "Q_LR1.2", "Q_LB1.2", "Q_BZ1.2", "R_PDLR1.2", "R_PDLB1.2", "R_PDBZ1.2", "C_BR1.2", "C_BB1.2",
            "U2.1", "U2.2", "U2.3", "U2.8", "C_EXP1.2",  # A0-A2 low: address 0x20
            "U3.2", "U3.3", "U3.11", "U3.15", "U3.17", "C_AMP1.2", "C_AMP2.2"],  # GAIN_SLOT low: 12 dB
    "+3V3": ["J3.2", "J3.3", "J_NFC1.2", "C_NFC1.1", "Q_SDA1.1", "Q_SCL1.1", "R_SDA3.1", "R_SCL3.1", "R_PUR1.1", "R_PUB1.1",
             "U2.16", "C_EXP1.1", "R_INT1.1"],
    "VBAT_RAW": ["J_BAT1.1", "F1.1"],
    "VBAT_F": ["F1.2", "J_KEY1.1"],
    "VBAT_SW": ["J_KEY1.2", "J_HBAT1.1", "C_BULK1.1", "C_BULK2.1", "C_IN1.1", "U1.5", "U1.4", "L1.1",
                "U3.7", "U3.8", "C_AMP1.1", "C_AMP2.1"],
    "SW": ["L1.2", "U1.1", "D1.2"],
    "FB": ["U1.3", "R_FB1.2", "R_FB2.1"],
    "+5V": ["D1.1", "C_OUT1.1", "C_OUT2.1", "R_FB1.1", "J_LCD1.2", "J_BTN_R1.3", "J_BTN_B1.3", "J_BUZ1.1",
            "D_FLY1.1", "R_SDA5.1", "R_SCL5.1"],
    # I2C
    "SDA_3V3": ["J3.15", "Q_SDA1.2", "R_SDA3.2", "J_NFC1.3", "U2.15"],
    "SCL_3V3": ["J3.14", "Q_SCL1.2", "R_SCL3.2", "J_NFC1.4", "U2.14"],
    "EXP_INT": ["J3.17", "U2.13", "R_INT1.2"],  # open drain, active low
    # I2S to the amp; SD_MODE from the expander (high = left channel, low = shutdown)
    "I2S_BCLK": ["J2.13", "U3.16"], "I2S_LRCLK": ["J2.14", "U3.14"], "I2S_DIN": ["J2.16", "U3.1"],
    "AMP_SD": ["U2.10", "R_SD1.1"], "AMP_SD_R": ["R_SD1.2", "U3.4"],
    # J_SPK1 pin 1 is OUT-: with U3 at 180 deg its OUTP pad sits above OUTN, so this avoids a crossing
    "SPK_N": ["U3.10", "J_SPK1.1"], "SPK_P": ["U3.9", "J_SPK1.2"],
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


def assembled():
    """Refs JLCPCB places: everything except DNP parts and mounting holes."""
    return [r for r, (_, sym, _) in PARTS.items() if r not in DNP and sym != "Mechanical:MountingHole"]


def check():
    pins = [p for members in NETS.values() for p in members]
    dupes = {p for p in pins if pins.count(p) > 1}
    assert not dupes, f"pin on several nets: {dupes}"
    for net, members in NETS.items():
        assert len(members) >= 2, f"{net} has a single pin"
        for p in members:
            assert p.split(".")[0] in PARTS, f"{net}: unknown part in {p}"
    assert DNP <= PARTS.keys(), f"unknown DNP parts: {DNP - PARTS.keys()}"
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
    unused = [r for r in PARTS if PARTS[r][1] != "Mechanical:MountingHole"
              and not any(p.split(".")[0] == r for p in pins)]
    assert not unused, f"parts with no connections: {unused}"
    missing = sorted(r for r in assembled() if (PARTS[r][0], PARTS[r][2]) not in LCSC)
    assert not missing, f"assembled parts without an LCSC number: {missing}"
    stale = LCSC.keys() - {(PARTS[r][0], PARTS[r][2]) for r in assembled()}
    assert not stale, f"LCSC entries no assembled part uses: {stale}"
    print(f"design ok: {len(PARTS)} parts, {len(NETS)} nets")


if __name__ == "__main__":
    check()
