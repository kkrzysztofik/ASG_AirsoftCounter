"""AirsoftCounter pack board: single source of truth for parts and nets.

Same role as design.py for the carrier. gen_sch.py / gen_pcb.py read it through board.py
(BOARD=pack), so run the generators with `make BOARD=pack ...`. Run this file to self-check
(`/usr/bin/python3 pack.py`).

check() runs the shared structural checks (board.check_structure) plus the pack-specific
per-cell branch order: holder+ -> fuse -> shunt -> back-to-back P-FET -> pack rail. Source of
truth for the design: docs/plans/2026-10-01-pack-board-design.md. Part choices and the LCSC
numbers are the P0 facts recorded there.
"""
NAME = "pack"
TITLE = "AirsoftCounter v2 pack"

# Footprints (and symbol + footprint pairs) shared with design.py
R0805 = ("Device:R", "Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder")
C0805 = ("Device:C", "Capacitor_SMD:C_0805_2012Metric_Pad1.18x1.45mm_HandSolder")
SOT23 = "Package_TO_SOT_SMD:SOT-23"
SMA = "Diode_SMD:D_SMA"
BSS138 = ("Transistor_FET:BSS138", SOT23)
AO3401A = ("Transistor_FET:AO3401A", SOT23)
BAT54C = ("Diode:BAT54C", SOT23)
SS34 = ("Diode:SS34", SMA)
C1206 = "Capacitor_SMD:C_1206_3216Metric_Pad1.33x1.80mm_HandSolder"
R1206 = "Resistor_SMD:R_1206_3216Metric_Pad1.30x1.75mm_HandSolder"
FUSE1206 = "Fuse:Fuse_1206_3216Metric_Pad1.42x1.75mm_HandSolder"
SOT23_3 = "Package_TO_SOT_SMD:SOT-23-3"
SOT23_6 = "Package_TO_SOT_SMD:SOT-23-6"
SOIC8EP = "Package_SO:SOIC-8-1EP_3.9x4.9mm_P1.27mm_EP2.41x3.3mm"
QFN24 = "Package_DFN_QFN:QFN-24-1EP_4x4mm_P0.5mm_EP2.6x2.6mm"
VQFN16 = "Package_DFN_QFN:Texas_RGV0016A_VQFN-16-1EP_4x4mm_P0.65mm_EP2.1x2.1mm"
LQFP32 = "Package_QFP:LQFP-32_7x7mm_P0.8mm"
L1210 = "Inductor_SMD:L_1210_3225Metric_Pad1.42x2.65mm_HandSolder"
LRN6045 = "Inductor_SMD:L_Bourns_SRN6045TA"
LED0805 = "LED_SMD:LED_0805_2012Metric_Pad1.15x1.40mm_HandSolder"
XH4 = "Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical"
XH6 = "Connector_JST:JST_XH_B6B-XH-A_1x06_P2.50mm_Vertical"
USBC = "Connector_USB:USB_C_Receptacle_HCTL_HC-TYPE-C-16P-01A"
HOLDER = "Battery:BatteryHolder_Keystone_1042_1x18650"
MH = "MountingHole:MountingHole_3.2mm_M3"
TP = "TestPoint:TestPoint_Pad_D1.5mm"
TACT = "Button_Switch_SMD:SW_SPST_TS-1088-xR020"

# ref: (value, symbol "lib:name", footprint "lib:name")
PARTS = {
    # --- charger: BQ25601 application circuit (values from P0, datasheet section 10.2) ---
    "U_CHG": ("BQ25601RTWR", "Battery_Management:BQ25601", QFN24),
    "L_CHG": ("1u5", "Device:L", L1210),
    "C_VBUS": ("10uF", *C0805),
    "C_PMID": ("10uF", *C0805),
    "C_SYS": ("10uF", *C0805),
    "C_BAT": ("10uF", *C0805),
    "C_REGN": ("4u7", *C0805),
    "C_BTST": ("47nF", *C0805),
    # TS bias network for a 10k B3435 NTC: 0-60 C (datasheet section 9.3.7.4)
    "RT1": ("5k23", *R0805),
    "RT2": ("30k9", *R0805),
    "TH_CHG": ("10k NTC", "Device:Thermistor_NTC", R0805[1]),
    "R_CE": ("10k", *R0805),        # /CE low: charging runs with the MCU unpowered
    "R_INT_CHG": ("10k", *R0805),   # /INT pull-up
    "R_STAT": ("1k", *R0805),
    "LED_STAT": ("red", "Device:LED", LED0805),
    "R_CC1": ("5k1", *R0805),
    "R_CC2": ("5k1", *R0805),
    # --- USB-C input (5.1k CC; D+/D- to the MCU) ---
    "J_USB1": ("HC-TYPE-C-16P-01A", "Connector:USB_C_Receptacle_USB2.0_14P", USBC),
    # --- LDO and MCU diode-OR (cell+ / SYS -> VMCU_IN) ---
    "U_LDO": ("XC6206P332MR", "Regulator_Linear:XC6206PxxxMR", SOT23_3),
    "C_LDO1": ("1uF", *C0805),
    "C_LDO2": ("1uF", *C0805),
    "D_OR1": ("BAT54C", *BAT54C),
    "D_OR2": ("BAT54C", *BAT54C),
    "D_OR3": ("BAT54C", *BAT54C),
    # --- monitoring: 2x INA3221 (U_INA1 = cells 1-3, U_INA2 = cell 4) ---
    "U_INA1": ("INA3221", "Power_Management:INA3221", VQFN16),
    "U_INA2": ("INA3221", "Power_Management:INA3221", VQFN16),
    "C_INA1": ("100nF", *C0805),
    "C_INA2": ("100nF", *C0805),
    "R_SCL_INT": ("4k7", *R0805),
    "R_SDA_INT": ("4k7", *R0805),
    "R_CRIT": ("10k", *R0805),
    "R_WARN": ("10k", *R0805),
    # --- MCU and support ---
    "U_MCU": ("STM32C071KBTx", "MCU_ST_STM32C0:STM32C071KBTx", LQFP32),
    "C_MCU1": ("100nF", *C0805),
    "C_MCU2": ("4u7", *C0805),
    "C_NRST": ("100nF", *C0805),
    "R_BOOT": ("10k", *R0805),
    "SW_BOOT": ("TS-1088-AR02016", "Switch:SW_Push", TACT),
    "SW_RST": ("TS-1088-AR02016", "Switch:SW_Push", TACT),
    "R_LED_MCU": ("1k", *R0805),
    "LED_MCU": ("green", "Device:LED", LED0805),
    "TP_SWDIO": ("SWDIO", "Connector:TestPoint", TP),
    "TP_SWCLK": ("SWCLK/BOOT0", "Connector:TestPoint", TP),
    "TP_NRST": ("NRST", "Connector:TestPoint", TP),
    "TP_GND": ("GND", "Connector:TestPoint", TP),
    # --- power out: key switch, 2 A PTC, boost (same parts as design.py), 6-pin XH to the carrier ---
    "J_KEY1": ("KEY", "Connector_Generic:Conn_01x04", XH4),
    "F_SYS1": ("2A PTC", "Device:Polyfuse", FUSE1206),
    "U1": ("MT3608", "Regulator_Switching:MT3608", SOT23_6),
    "L1": ("10uH 2A", "Device:L", LRN6045),
    "D1": ("SS34", "Device:SS34", SMA),
    "R_FB1": ("75k", *R0805),
    "R_FB2": ("10k", *R0805),
    "C_IN1": ("22uF 25V", "Device:C", C1206),
    "C_OUT1": ("22uF 25V", "Device:C", C1206),
    "C_OUT2": ("22uF 25V", "Device:C", C1206),
    "J_PWR1": ("PWR", "Connector_Generic:Conn_01x06", XH6),
}

# --- per-cell chain (x4), generated like design.py's DRIVERS ---
# INA3221 channel inputs: cell 1-3 on U_INA1 channels 1-3, cell 4 on U_INA2 channel 1.
INA_IN = {1: ("12", "11"), 2: ("15", "14"), 3: ("2", "1"), 4: ("12", "11")}
INA_OF = {1: "U_INA1", 2: "U_INA1", 3: "U_INA1", 4: "U_INA2"}
# Diode-OR anode that taps each cell after its fuse: cell -> (ref, pin).
OR_ANODE = {1: ("D_OR1", "1"), 2: ("D_OR1", "2"), 3: ("D_OR2", "1"), 4: ("D_OR2", "2")}
# MCU pin per cell: switch gate drive (PB0/PB1/PB2/PA8) and NTC ADC (PA0..PA3).
SW_PIN = {1: "15", 2: "16", 3: "17", 4: "18"}
NTC_PIN = {1: "7", 2: "8", 3: "9", 4: "10"}

for i in range(1, 5):
    PARTS[f"BT{i}"] = ("18650", "Device:Battery_Cell", HOLDER)      # hand-soldered, not in the JLC BOM
    PARTS[f"F{i}"] = ("5A fuse", "Device:Fuse", FUSE1206)
    PARTS[f"D_CB{i}"] = ("SS34", *SS34)                             # crowbar across the holder
    PARTS[f"R_SH{i}"] = ("20mOhm", "Device:R", R1206)
    PARTS[f"Q_A{i}"] = ("AO3401A", *AO3401A)
    PARTS[f"Q_B{i}"] = ("AO3401A", *AO3401A)
    PARTS[f"R_GS{i}"] = ("1M", *R0805)
    PARTS[f"Q_N{i}"] = ("BSS138", *BSS138)
    PARTS[f"R_PD{i}"] = ("100k", *R0805)
    PARTS[f"R_SW{i}"] = ("1k", *R0805)
    PARTS[f"R_BYP{i}"] = ("0R", *R0805)                             # bring-up bypass, DNP
    PARTS[f"U_P{i}"] = ("XB8089D", "local:XB8089D", SOIC8EP)
    PARTS[f"R_PROT{i}"] = ("1k", *R0805)
    PARTS[f"C_PROT{i}"] = ("100nF", *C0805)
    PARTS[f"TH{i}"] = ("10k NTC", "Device:Thermistor_NTC", R0805[1])
    PARTS[f"R_NTC{i}"] = ("10k", *R0805)

for i in range(1, 5):
    PARTS[f"H{i}"] = ("M3", "Mechanical:MountingHole", MH)

# Bring-up 0R bypasses, off by default. Cell holders and bare test-point pads are populated by
# hand, so they are not in the JLCPCB BOM/CPL (NOT_ASSEMBLED) and need no LCSC number.
DNP = {f"R_BYP{i}" for i in range(1, 5)}
NOT_ASSEMBLED = {f"BT{i}" for i in range(1, 5)} | {"TP_SWDIO", "TP_SWCLK", "TP_NRST", "TP_GND"}
# J_KEY1 is a 4-pin XH; the off-board key switch uses pins 1-2, pins 3-4 stay unconnected.
XH_SPARE = {"J_KEY1.3", "J_KEY1.4"}
# Pins with no connection: charger NC pins and unused control outputs, unused MCU pins, boost NC.
NC_PINS = {"U_CHG.3", "U_CHG.8", "U_CHG.10", "U_CHG.12",
           "U_INA1.10", "U_INA1.13", "U_INA2.10", "U_INA2.13",
           "U_MCU.1", "U_MCU.2", "U_MCU.3", "U_MCU.19", "U_MCU.20", "U_MCU.21", "U_MCU.32",
           "U1.6"}
NC_PARTS = set()

# JLCPCB assembly: (value, footprint) -> LCSC part number. Every number checked live on
# 2026-10-01 (P0); type B = Basic, P = Preferred Extended, E = Extended.
LCSC = {
    ("100nF", C0805[1]): "C49678",   # B YAGEO CC0805KRX7R9BB104
    ("10uF", C0805[1]): "C15850",    # B Samsung CL21A106KAYNNNE 25V X5R
    ("4u7", C0805[1]): "C1779",      # B Samsung CL21A475KAQNNNE 25V X5R
    ("1uF", C0805[1]): "C28323",     # B Samsung CL21B105KBFNNNE 50V X7R
    ("47nF", C0805[1]): "C53134",    # B Samsung CL21B473KBCNNNC 50V X7R
    ("22uF 25V", C1206): "C12891",   # B Samsung CL31A226KAHNNNE
    ("20mOhm", R1206): "C163047",    # E TA-I RLS12FTCR020 1%
    ("1M", R0805[1]): "C17514",      # B
    ("100k", R0805[1]): "C149504",   # B
    ("1k", R0805[1]): "C17513",      # B
    ("10k", R0805[1]): "C17414",     # B
    ("4k7", R0805[1]): "C17673",     # B
    ("5k1", R0805[1]): "C27834",     # B
    ("75k", R0805[1]): "C17819",     # P
    ("5k23", R0805[1]): "C17739",    # E TS bias (BQ25601 datasheet)
    ("30k9", R0805[1]): "C204398",   # E
    ("10k NTC", R0805[1]): "C2889056",  # E CMFB 103F3435, 0805 B3435
    ("5A fuse", FUSE1206): "C48332",    # E Bourns SF-1206F500-2, I2t 0.966 A2s
    ("2A PTC", FUSE1206): "C22374899",  # E LUTE 1206L200/16NR
    ("SS34", SMA): "C8678",             # B
    ("BAT54C", SOT23): "C37704",        # E Nexperia BAT54C,215 (common cathode)
    ("AO3401A", SOT23): "C15127",       # B
    ("BSS138", SOT23): "C7420339",      # P
    ("XB8089D", SOIC8EP): "C79928",     # E
    ("BQ25601RTWR", QFN24): "C468236",  # E
    ("INA3221", VQFN16): "C181255",     # E
    ("XC6206P332MR", SOT23_3): "C5446",  # B
    ("MT3608", SOT23_6): "C84817",      # E
    ("10uH 2A", LRN6045): "C2046332",   # E
    ("1u5", L1210): "C703084",          # E Murata DFE322512F-1R5M, Isat 3.9 A
    ("STM32C071KBTx", LQFP32): "C42116633",  # E
    ("HC-TYPE-C-16P-01A", USBC): "C2894897",  # E
    ("TS-1088-AR02016", TACT): "C720477",     # B
    ("red", LED0805): "C84256",         # B NCD0805R1
    ("green", LED0805): "C2297",        # B KT-0805G
    ("KEY", XH4): "C144395",            # E JST B4B-XH-A(LF)(SN)
    ("PWR", XH6): "C144397",            # E JST B6B-XH-A(LF)(SN)
}

# net: [ "REF.pin", ... ]. Per-cell nets are built in the loop below.
NETS = {
    # pack rail and charger
    "VPACK": [*(f"Q_B{i}.3" for i in range(1, 5)), *(f"R_BYP{i}.2" for i in range(1, 5)),
              "U_CHG.13", "U_CHG.14", "C_BAT.1"],
    "SYS": ["U_CHG.15", "U_CHG.16", "C_SYS.1", "D_OR3.1", "D_OR3.2", "J_KEY1.1"],
    "KEY_OUT": ["J_KEY1.2", "F_SYS1.1"],
    "VBAT_SW": ["F_SYS1.2", "U1.5", "U1.4", "L1.1", "C_IN1.1", "J_PWR1.3"],
    "SW": ["L1.2", "U1.1", "D1.2"],
    "FB": ["U1.3", "R_FB1.2", "R_FB2.1"],
    "+5V": ["D1.1", "C_OUT1.1", "C_OUT2.1", "R_FB1.1", "J_PWR1.4"],
    "VBUS": ["U_CHG.1", "U_CHG.24", "C_VBUS.1", "J_USB1.A4", "J_USB1.A9", "J_USB1.B4", "J_USB1.B9"],
    "PMID": ["U_CHG.23", "C_PMID.1"],
    "SW_CHG": ["U_CHG.19", "U_CHG.20", "L_CHG.1", "C_BTST.2"],  # charger switcher node (BTST cap)
    "BTST": ["U_CHG.21", "C_BTST.1"],
    "REGN": ["U_CHG.22", "C_REGN.1", "RT1.1"],
    "TS": ["U_CHG.11", "RT1.2", "RT2.1", "TH_CHG.1"],
    "VMCU_IN": ["D_OR1.3", "D_OR2.3", "D_OR3.3", "U_LDO.3", "C_LDO1.1"],
    "+3V3": ["U_LDO.2", "C_LDO2.1",
             "U_INA1.4", "U_INA1.16", "C_INA1.1", "U_INA2.4", "U_INA2.16", "C_INA2.1", "U_INA2.5",
             "R_SCL_INT.1", "R_SDA_INT.1", "R_CRIT.1", "R_WARN.1",
             "R_INT_CHG.2", "R_STAT.1", "U_MCU.4", "C_MCU1.1", "C_MCU2.1", "SW_BOOT.2"],
    # internal I2C (MCU master): INA3221 x2 + BQ25601, pull-ups to +3V3
    "SCL_INT": ["U_MCU.30", "U_INA1.6", "U_INA2.6", "U_CHG.5", "R_SCL_INT.2"],
    "SDA_INT": ["U_MCU.31", "U_INA1.7", "U_INA2.7", "U_CHG.6", "R_SDA_INT.2"],
    "INA_CRIT": ["U_INA1.9", "U_INA2.9", "R_CRIT.2", "U_MCU.28"],
    "INA_WARN": ["U_INA1.8", "U_INA2.8", "R_WARN.2", "U_MCU.29"],
    "CHG_INT": ["U_CHG.7", "R_INT_CHG.1", "U_MCU.27"],
    "CHG_CE": ["U_CHG.9", "R_CE.1", "U_MCU.12"],
    "STAT": ["U_CHG.4", "LED_STAT.1"],
    "LED_STAT_A": ["R_STAT.2", "LED_STAT.2"],
    # USB and MCU support
    "USB_DP": ["J_USB1.A6", "J_USB1.B6", "U_MCU.23"],
    "USB_DM": ["J_USB1.A7", "J_USB1.B7", "U_MCU.22"],
    "CC1": ["J_USB1.A5", "R_CC1.1"],
    "CC2": ["J_USB1.B5", "R_CC2.1"],
    "NRST": ["U_MCU.6", "C_NRST.1", "SW_RST.1", "TP_NRST.1"],
    "BOOT0": ["U_MCU.25", "R_BOOT.1", "SW_BOOT.1", "TP_SWCLK.1"],
    "SWDIO": ["U_MCU.24", "TP_SWDIO.1"],
    "LED_MCU_DRV": ["U_MCU.26", "R_LED_MCU.1"],
    "LED_MCU_A": ["R_LED_MCU.2", "LED_MCU.2"],
    # external I2C (slave 0x30) to the carrier: no pull-ups here
    "SDA_EXT": ["U_MCU.13", "J_PWR1.5"],
    "SCL_EXT": ["U_MCU.14", "J_PWR1.6"],
    # NTC divider supply (PA4), switched off between samples
    "NTC_PWR": ["U_MCU.11", *(f"TH{i}.1" for i in range(1, 5))],
    # ground: battery protectors (VM), FET sources, charger, MCU, earth
    "GND": [*(f"U_P{i}.{n}" for i in range(1, 5) for n in (1, 2, 3, 4)),
            *(f"Q_N{i}.2" for i in range(1, 5)),
            *(f"R_PD{i}.2" for i in range(1, 5)),
            *(f"R_NTC{i}.2" for i in range(1, 5)),
            "U_CHG.2", "U_CHG.17", "U_CHG.18", "U_CHG.25",
            "C_VBUS.2", "C_PMID.2", "C_SYS.2", "C_BAT.2", "C_REGN.2",
            "RT2.2", "TH_CHG.2",
            "U_LDO.1", "C_LDO1.2", "C_LDO2.2",
            "U_INA1.3", "U_INA1.5", "U_INA1.17", "C_INA1.2",   # A0 = GND -> 0x40
            "U_INA2.3", "U_INA2.17", "C_INA2.2",
            "R_CC1.2", "R_CC2.2",
            "J_USB1.A1", "J_USB1.A12", "J_USB1.B1", "J_USB1.B12", "J_USB1.S1",
            "U_MCU.5", "C_MCU1.2", "C_MCU2.2", "C_NRST.2", "SW_RST.2", "R_BOOT.2",
            "LED_MCU.1", "R_CE.2",
            "U1.2", "C_IN1.2", "C_OUT1.2", "C_OUT2.2",
            "J_PWR1.1", "J_PWR1.2", "TP_GND.1"],
}

for i in range(1, 5):
    or_ref, or_pin = OR_ANODE[i]
    ina, (inn, inp) = INA_OF[i], INA_IN[i]
    NETS[f"CELL{i}_RAW"] = [f"BT{i}.1", f"F{i}.1"]
    NETS[f"CELL{i}_F"] = [f"F{i}.2", f"D_CB{i}.1", f"R_SH{i}.1", f"R_PROT{i}.1", f"{or_ref}.{or_pin}",
                          f"{ina}.{inn}"]
    NETS[f"CELL{i}_S"] = [f"R_SH{i}.2", f"Q_A{i}.3", f"R_BYP{i}.1", f"{ina}.{inp}"]
    NETS[f"CELL{i}_SRC"] = [f"Q_A{i}.2", f"Q_B{i}.2", f"R_GS{i}.2"]
    NETS[f"CELL{i}_G"] = [f"Q_A{i}.1", f"Q_B{i}.1", f"R_GS{i}.1", f"Q_N{i}.3"]
    NETS[f"CELL{i}_N"] = [f"BT{i}.2", f"D_CB{i}.2", *(f"U_P{i}.{n}" for n in (5, 7, 8, 9)), f"C_PROT{i}.2"]
    NETS[f"PROT{i}_VDD"] = [f"U_P{i}.6", f"R_PROT{i}.2", f"C_PROT{i}.1"]
    NETS[f"SW{i}_G"] = [f"Q_N{i}.1", f"R_PD{i}.1", f"R_SW{i}.2"]
    NETS[f"SW{i}_DRV"] = [f"R_SW{i}.1", f"U_MCU.{SW_PIN[i]}"]
    NETS[f"NTC{i}"] = [f"TH{i}.2", f"R_NTC{i}.1", f"U_MCU.{NTC_PIN[i]}"]

# Cell 4 is channel 1 of U_INA2; its spare channels 2-3 share the ch1 IN- reference (P0).
NETS["CELL4_S"] += ["U_INA2.15", "U_INA2.14", "U_INA2.2", "U_INA2.1"]

MODULES = {}
VARIANTS = {"standard": set()}


def assembled(variant="standard"):
    """Refs JLCPCB places: everything except DNP parts, hand-soldered/off-board parts and holes."""
    return [r for r, (_, sym, _) in PARTS.items()
            if r not in DNP | NOT_ASSEMBLED and sym != "Mechanical:MountingHole"]


def check_branches():
    """Every cell: holder+ -> fuse -> shunt -> back-to-back P-FET -> pack rail, in that order (design doc)."""
    net_of = {p: n for n, m in NETS.items() for p in m}
    for i in range(1, 5):
        assert net_of[f"BT{i}.1"] == net_of[f"F{i}.1"], f"cell {i}: holder+ not on fuse"
        assert net_of[f"F{i}.2"] == net_of[f"R_SH{i}.1"] == net_of[f"U_INA{(i - 1) // 3 + 1}.{INA_IN[i][0]}"], \
            f"cell {i}: fuse -> shunt / IN+"
        assert net_of[f"R_SH{i}.2"] == net_of[f"Q_A{i}.3"] == net_of[f"U_INA{(i - 1) // 3 + 1}.{INA_IN[i][1]}"], \
            f"cell {i}: shunt -> FET / IN-"
        assert net_of[f"Q_A{i}.2"] == net_of[f"Q_B{i}.2"], f"cell {i}: FET sources not common"
        assert net_of[f"Q_B{i}.3"] == "VPACK", f"cell {i}: FET not on the pack rail"
        assert net_of[f"BT{i}.2"] == net_of[f"U_P{i}.5"], f"cell {i}: holder- not on XB8089D BAT-"


def check():
    import sys

    import board  # pyright: ignore[reportMissingImports]  # local sibling module
    board.check_structure(sys.modules[__name__])
    check_branches()
    print(f"pack ok: {len(PARTS)} parts, {len(NETS)} nets")


if __name__ == "__main__":
    check()
