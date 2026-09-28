"""AirsoftCounter v2 carrier board: single source of truth for parts and nets.

gen_sch.py and gen_pcb.py read PARTS and NETS from here. Run this file to
self-check the design (`python3 design.py`).
"""

# ref: (value, symbol "lib:name", footprint "lib:name")
PARTS = {
    # Heltec WiFi LoRa 32 V4 headers (pin 1 at USB end). Rows are 22.86 mm apart.
    "J2": ("Heltec_J2", "Connector_Generic:Conn_01x18", "Connector_PinSocket_2.54mm:PinSocket_1x18_P2.54mm_Vertical"),
    "J3": ("Heltec_J3", "Connector_Generic:Conn_01x18", "Connector_PinSocket_2.54mm:PinSocket_1x18_P2.54mm_Vertical"),
    # Off-board connectors, JST-XH 2.50 mm vertical
    "J_BAT": ("BAT", "Connector_Generic:Conn_01x02", "Connector_JST:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical"),
    "J_KEY": ("KEY", "Connector_Generic:Conn_01x02", "Connector_JST:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical"),
    "J_HBAT": ("HELTEC_BAT", "Connector_Generic:Conn_01x02", "Connector_JST:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical"),
    "J_LCD": ("LCD", "Connector_Generic:Conn_01x04", "Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical"),
    "J_NFC": ("NFC", "Connector_Generic:Conn_01x04", "Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical"),
    "J_BTN_R": ("BTN_R", "Connector_Generic:Conn_01x04", "Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical"),
    "J_BTN_B": ("BTN_B", "Connector_Generic:Conn_01x04", "Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical"),
    "J_BUZ": ("BUZ", "Connector_Generic:Conn_01x02", "Connector_JST:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical"),
    # Power
    "F1": ("1A PTC", "Device:Polyfuse", "Fuse:Fuse_1206_3216Metric_Pad1.42x1.75mm_HandSolder"),
    "U1": ("MT3608", "Regulator_Switching:MT3608", "Package_TO_SOT_SMD:SOT-23-6"),
    "L1": ("10uH 2A", "Device:L", "Inductor_SMD:L_Bourns_SRN6045TA"),
    "D1": ("SS34", "Diode:SS34", "Diode_SMD:D_SMA"),
    "R_FB1": ("75k", "Device:R", "Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder"),
    "R_FB2": ("10k", "Device:R", "Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder"),
    "C_IN": ("22uF 10V", "Device:C", "Capacitor_SMD:C_1206_3216Metric_Pad1.33x1.80mm_HandSolder"),
    "C_OUT1": ("22uF 10V", "Device:C", "Capacitor_SMD:C_1206_3216Metric_Pad1.33x1.80mm_HandSolder"),
    "C_OUT2": ("22uF 10V", "Device:C", "Capacitor_SMD:C_1206_3216Metric_Pad1.33x1.80mm_HandSolder"),
    "C_BULK": ("220uF 10V", "Device:C_Polarized", "Capacitor_THT:CP_Radial_D6.3mm_P2.50mm"),
    "C_NFC": ("100uF 10V", "Device:C_Polarized", "Capacitor_THT:CP_Radial_D6.3mm_P2.50mm"),
    # I2C level shifter (5V-side pull-ups DNP: LCD backpack has its own)
    "Q_SDA": ("BSS138", "Transistor_FET:BSS138", "Package_TO_SOT_SMD:SOT-23"),
    "Q_SCL": ("BSS138", "Transistor_FET:BSS138", "Package_TO_SOT_SMD:SOT-23"),
    "R_SDA3": ("4k7", "Device:R", "Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder"),
    "R_SCL3": ("4k7", "Device:R", "Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder"),
    "R_SDA5": ("4k7 DNP", "Device:R", "Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder"),
    "R_SCL5": ("4k7 DNP", "Device:R", "Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder"),
}

R0805 = ("Device:R", "Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder")
C0805 = ("Device:C", "Capacitor_SMD:C_0805_2012Metric_Pad1.18x1.45mm_HandSolder")
SOT23 = ("Transistor_FET:AO3400A", "Package_TO_SOT_SMD:SOT-23")

# Low-side drivers: name -> (gate GPIO net, load resistor value or None)
DRIVERS = {"LR": ("LED_R_G", "150R"), "LB": ("LED_B_G", "100R"), "BZ": ("BUZ_G", None)}
for n, (_, r_load) in DRIVERS.items():
    PARTS[f"Q_{n}"] = ("AO3400A", *SOT23)
    PARTS[f"R_G{n}"] = ("100R", *R0805)
    PARTS[f"R_PD{n}"] = ("100k", *R0805)
    if r_load:
        PARTS[f"R_L{n}"] = (r_load, *R0805)
PARTS["D_FLY"] = ("1N4148W", "Diode:1N4148W", "Diode_SMD:D_SOD-123")

# Button inputs: 10k pull-up, 100nF, 1k series
for t in ("R", "B"):
    PARTS[f"R_PU{t}"] = ("10k", *R0805)
    PARTS[f"R_S{t}"] = ("1k", *R0805)
    PARTS[f"C_B{t}"] = ("100nF", *C0805)

for i in range(1, 5):
    PARTS[f"H{i}"] = ("M3", "Mechanical:MountingHole", "MountingHole:MountingHole_3.2mm_M3")

# net: [ "REF.pin", ... ]
NETS = {
    "GND": ["J2.1", "J3.1", "J_BAT.2", "J_HBAT.2", "J_LCD.1", "J_NFC.1", "J_BTN_R.2", "J_BTN_B.2",
            "U1.2", "R_FB2.2", "C_IN.2", "C_OUT1.2", "C_OUT2.2", "C_BULK.2", "C_NFC.2",
            "Q_LR.2", "Q_LB.2", "Q_BZ.2", "R_PDLR.2", "R_PDLB.2", "R_PDBZ.2", "C_BR.2", "C_BB.2"],
    "+3V3": ["J3.2", "J3.3", "J_NFC.2", "C_NFC.1", "Q_SDA.1", "Q_SCL.1", "R_SDA3.1", "R_SCL3.1", "R_PUR.1", "R_PUB.1"],
    "VBAT_RAW": ["J_BAT.1", "F1.1"],
    "VBAT_F": ["F1.2", "J_KEY.1"],
    "VBAT_SW": ["J_KEY.2", "J_HBAT.1", "C_BULK.1", "C_IN.1", "U1.5", "U1.4", "L1.1"],
    "SW": ["L1.2", "U1.1", "D1.2"],
    "FB": ["U1.3", "R_FB1.2", "R_FB2.1"],
    "+5V": ["D1.1", "C_OUT1.1", "C_OUT2.1", "R_FB1.1", "J_LCD.2", "J_BTN_R.3", "J_BTN_B.3", "J_BUZ.1",
            "D_FLY.1", "R_SDA5.1", "R_SCL5.1"],
    # I2C
    "SDA_3V3": ["J3.15", "Q_SDA.2", "R_SDA3.2", "J_NFC.3"],
    "SCL_3V3": ["J3.14", "Q_SCL.2", "R_SCL3.2", "J_NFC.4"],
    "SDA_5V": ["Q_SDA.3", "R_SDA5.2", "J_LCD.3"],
    "SCL_5V": ["Q_SCL.3", "R_SCL5.2", "J_LCD.4"],
    # Drivers: GPIO -> gate resistor -> gate (pull-down) ; drain -> load
    "LED_R_G": ["J2.13", "R_GLR.1"], "Q_LR_G": ["R_GLR.2", "Q_LR.1", "R_PDLR.1"],
    "LED_R_K": ["Q_LR.3", "R_LLR.1"], "BTN_R_LEDK": ["R_LLR.2", "J_BTN_R.4"],
    "LED_B_G": ["J2.14", "R_GLB.1"], "Q_LB_G": ["R_GLB.2", "Q_LB.1", "R_PDLB.1"],
    "LED_B_K": ["Q_LB.3", "R_LLB.1"], "BTN_B_LEDK": ["R_LLB.2", "J_BTN_B.4"],
    "BUZ_G": ["J2.16", "R_GBZ.1"], "Q_BZ_G": ["R_GBZ.2", "Q_BZ.1", "R_PDBZ.1"],
    "BUZ_K": ["Q_BZ.3", "J_BUZ.2", "D_FLY.2"],
    # Buttons: switch pulls to GND
    "BTN_R_SW": ["J_BTN_R.1", "R_PUR.2", "C_BR.1", "R_SR.1"], "BTN_R_IN": ["R_SR.2", "J3.17"],
    "BTN_B_SW": ["J_BTN_B.1", "R_PUB.2", "C_BB.1", "R_SB.1"], "BTN_B_IN": ["R_SB.2", "J2.5"],
}

# Heltec header pin -> ESP32 GPIO (V4 pin map). Only pins we use or must avoid.
HELTEC_GPIO = {
    "J3.12": 1, "J3.13": 2, "J3.14": 3, "J3.15": 4, "J3.16": 5, "J3.17": 6, "J3.18": 7,
    "J3.4": 37, "J3.5": 46, "J3.6": 45, "J3.7": 42, "J3.8": 41, "J3.9": 40, "J3.10": 39, "J3.11": 38,
    "J2.5": 44, "J2.6": 43, "J2.7": None, "J2.8": 0, "J2.9": 36, "J2.10": 35, "J2.11": 34, "J2.12": 33,
    "J2.13": 47, "J2.14": 48, "J2.15": 26, "J2.16": 21, "J2.17": 20, "J2.18": 19,
}
# Used internally on V4-R2 or V4-R8 (FEM, GNSS, PSRAM, strapping, USB, LED/Vext, VBAT), or RST.
FORBIDDEN_GPIO = {0, 1, 2, 5, 7, 19, 20, 26, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 45, 46, None}
EXPECTED_GPIO = {"SCL_3V3": 3, "SDA_3V3": 4, "BTN_R_IN": 6, "BTN_B_IN": 44,
                 "LED_R_G": 47, "LED_B_G": 48, "BUZ_G": 21}
HELTEC_5V_PIN = "J2.2"  # charger input: must stay unconnected


def check():
    pins = [p for members in NETS.values() for p in members]
    dupes = {p for p in pins if pins.count(p) > 1}
    assert not dupes, f"pin on several nets: {dupes}"
    for net, members in NETS.items():
        assert len(members) >= 2, f"{net} has a single pin"
        for p in members:
            assert p.split(".")[0] in PARTS, f"{net}: unknown part in {p}"
    used = [p for p in pins if p.split(".")[0] in ("J2", "J3") and p in HELTEC_GPIO]
    for p in used:
        assert HELTEC_GPIO[p] not in FORBIDDEN_GPIO, f"{p} is GPIO{HELTEC_GPIO[p]}, reserved on V4"
    gpio_of_net = {net: HELTEC_GPIO[p] for net, m in NETS.items() for p in m if p in HELTEC_GPIO}
    assert gpio_of_net == EXPECTED_GPIO, gpio_of_net
    assert HELTEC_5V_PIN not in pins, "Heltec 5V pin must not be connected"
    unused = [r for r in PARTS if not r.startswith("H") and not any(p.split(".")[0] == r for p in pins)]
    assert not unused, f"parts with no connections: {unused}"
    print(f"design ok: {len(PARTS)} parts, {len(NETS)} nets")


if __name__ == "__main__":
    check()
