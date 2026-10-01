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
    "D1": ("SS34", "Diode:SS34", SMA),
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
    # Kelvin sense split (plan P4.2): the shunt's two pads feed the INA3221 through their own 0R, so
    # the sense net is thin (Default class) while the branch stays wide.
    PARTS[f"R_SNSF{i}"] = ("0R", *R0805)
    PARTS[f"R_SNSS{i}"] = ("0R", *R0805)

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
    ("0R", R0805[1]): "C17477",   # B UNI-ROYAL 0805W8F0000T5E (sense split)
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
    "SYS": ["U_CHG.15", "U_CHG.16", "L_CHG.2", "C_SYS.1", "D_OR3.1", "D_OR3.2", "J_KEY1.1"],
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
            "U1.2", "C_IN1.2", "C_OUT1.2", "C_OUT2.2", "R_FB2.2",
            "J_PWR1.1", "J_PWR1.2", "TP_GND.1"],
}

for i in range(1, 5):
    or_ref, or_pin = OR_ANODE[i]
    ina, (inn, inp) = INA_OF[i], INA_IN[i]
    NETS[f"CELL{i}_RAW"] = [f"BT{i}.1", f"F{i}.1"]
    NETS[f"CELL{i}_F"] = [f"F{i}.2", f"D_CB{i}.1", f"R_SH{i}.1", f"R_PROT{i}.1", f"{or_ref}.{or_pin}",
                          f"R_SNSF{i}.1"]
    NETS[f"CELL{i}_S"] = [f"R_SH{i}.2", f"Q_A{i}.3", f"R_BYP{i}.1", f"R_SNSS{i}.1"]
    NETS[f"INA_F{i}"] = [f"R_SNSF{i}.2", f"{ina}.{inn}"]
    NETS[f"INA_S{i}"] = [f"R_SNSS{i}.2", f"{ina}.{inp}"]
    NETS[f"CELL{i}_SRC"] = [f"Q_A{i}.2", f"Q_B{i}.2", f"R_GS{i}.2"]
    NETS[f"CELL{i}_G"] = [f"Q_A{i}.1", f"Q_B{i}.1", f"R_GS{i}.1", f"Q_N{i}.3"]
    NETS[f"CELL{i}_N"] = [f"BT{i}.2", f"D_CB{i}.2", *(f"U_P{i}.{n}" for n in (5, 7, 8, 9)), f"C_PROT{i}.2"]
    NETS[f"PROT{i}_VDD"] = [f"U_P{i}.6", f"R_PROT{i}.2", f"C_PROT{i}.1"]
    NETS[f"SW{i}_G"] = [f"Q_N{i}.1", f"R_PD{i}.1", f"R_SW{i}.2"]
    NETS[f"SW{i}_DRV"] = [f"R_SW{i}.1", f"U_MCU.{SW_PIN[i]}"]
    NETS[f"NTC{i}"] = [f"TH{i}.2", f"R_NTC{i}.1", f"U_MCU.{NTC_PIN[i]}"]

# Cell 4 is channel 1 of U_INA2; its spare channels 2-3 tie to the ch1 IN- reference (P0).
NETS["INA_S4"] += ["U_INA2.15", "U_INA2.14", "U_INA2.2", "U_INA2.1"]

# --- layout (read by gen_sch.py / gen_pcb.py / check_gerbers.py) --------------------------------
# Rails carry power_in pins, so ERC needs a driver on each: +3V3 has the LDO's power_out, the others
# take a PWR_FLAG (their sources are all passive). +5V and SYS have no power_in pin, so they stay
# ordinary labelled nets.
# Nets that get the wider Power class. "SW*" would also catch the MCU's SW*_DRV gate signals (uA),
# which must reach the LQFP32's 0.8 mm-pitch pads, so only the two switching nodes are listed.
# VBUS/SYS/VPACK stay Default (0.25 mm): their 0.5 mm-pitch QFN24 pads are the real current limit
# (~0.9 A each) and the 0.8 mm class cannot leave them without a clearance error, so a wide class
# there buys nothing. Revisit with a 0R split or locked fanout stubs if the pad current is raised.
NETCLASS_POWER = ("VBAT*", "KEY_OUT", "CELL*_RAW", "CELL*_F", "CELL*_S", "CELL*_SRC", "CELL*_N",
                  "+5V", "SW", "SW_CHG")
RAILS = ("GND", "+3V3", "VPACK", "VBUS", "VMCU_IN", "VBAT_SW")
# A power port names its net by Value, so each rail reuses a stock symbol (carrier convention).
PORT_LIB = {"GND": "power:GND", "+3V3": "power:+3V3", "VPACK": "power:VDC",
            "VBUS": "power:VBUS", "VMCU_IN": "power:+VDC", "VBAT_SW": "power:+BATT"}


def _tags(nets, x0, y0, per_row=7, pitch=20.32, row=12.7):
    """One global label per net, in a free strip along the bottom of a block."""
    return {n: [(x0 + (k % per_row) * pitch, y0 + (k // per_row) * row, "R")]
            for k, n in enumerate(nets)}


def _cell(i, x0, y0):
    """One cell's branch (design doc order: holder+ -> fuse -> shunt -> back-to-back P-FET) plus
    the protector, the NTC and the switch gate drive. Four copies, one per cell block."""
    def a(x, y, rot=0):
        return (x0 + x, y0 + y, rot, None)

    return {
        f"BT{i}": a(12.7, 20.32), f"F{i}": a(12.7, 40.64), f"R_SH{i}": a(12.7, 60.96),
        f"Q_A{i}": a(12.7, 82.55), f"Q_B{i}": a(31.75, 82.55),
        f"R_GS{i}": a(24.13, 100.33), f"R_BYP{i}": a(43.18, 100.33),
        f"Q_N{i}": a(12.7, 116.84), f"R_PD{i}": a(7.62, 134.62), f"R_SW{i}": a(25.4, 134.62),
        f"D_CB{i}": a(60.96, 20.32), f"U_P{i}": a(78.74, 35.56),
        f"R_SNSF{i}": a(45.72, 64.77), f"R_SNSS{i}": a(45.72, 78.74),
        f"R_PROT{i}": a(60.96, 50.8), f"C_PROT{i}": a(45.72, 50.8),
        f"TH{i}": a(83.82, 60.96), f"R_NTC{i}": a(83.82, 78.74),
    }


def _blocks():
    """Hand-placed parts, one block per sheet area. Tags are the global labels that carry a
    multi-block net across a block boundary (rails use power ports instead)."""
    out = []
    # Charger + USB-C receptacle. Caps sit on the side of U_CHG whose pins they decouple.
    out.append({
        "title": "USB-C input, BQ25601 charger", "at": (12.7, 12.7), "size": (203.2, 139.7),
        "parts": {
            "U_CHG": (48.26, 50.8, 0, None),
            "C_VBUS": (15.24, 25.4, 0, None), "C_PMID": (15.24, 50.8, 0, None),
            "R_CE": (15.24, 76.2, 0, None), "R_INT_CHG": (15.24, 101.6, 0, None),
            "L_CHG": (81.28, 27.94, 0, None), "C_BTST": (100.33, 27.94, 0, None),
            "C_SYS": (81.28, 55.88, 0, None), "C_BAT": (100.33, 60.96, 0, None),
            "C_REGN": (81.28, 78.74, 0, None), "RT1": (100.33, 78.74, 0, None),
            "RT2": (100.33, 95.25, 0, None), "TH_CHG": (116.84, 95.25, 0, None),
            "R_STAT": (95.25, 48.26, 90, None), "LED_STAT": (76.2, 48.26, 0, None),
            "J_USB1": (152.4, 71.12, 0, None),
            "R_CC1": (182.88, 60.96, 90, None), "R_CC2": (182.88, 68.58, 90, None),
        },
        "tags": _tags(["SCL_INT", "SDA_INT", "CHG_INT", "CHG_CE", "USB_DP", "USB_DM", "SYS",
                       "CC2", "LED_STAT_A"], 12.7, 118.11),
    })
    # Monitoring: 2x INA3221, the diode-OR into the LDO and the MCU supply LDO.
    out.append({
        "title": "Cell monitoring (INA3221 x2), diode-OR, 3V3 LDO", "at": (228.6, 12.7),
        "size": (139.7, 177.8),
        "parts": {
            "U_INA1": (30.48, 40.64, 0, None), "U_INA2": (30.48, 106.68, 0, None),
            "C_INA1": (7.62, 22.86, 0, None), "C_INA2": (7.62, 78.74, 0, None),
            "R_SCL_INT": (60.96, 30.48, 90, None), "R_SDA_INT": (60.96, 43.18, 90, None),
            "R_CRIT": (60.96, 55.88, 90, None), "R_WARN": (60.96, 68.58, 90, None),
            "D_OR1": (78.74, 30.48, 0, None), "D_OR2": (78.74, 60.96, 0, None),
            "D_OR3": (78.74, 91.44, 0, None), "U_LDO": (105.41, 91.44, 0, None),
            "C_LDO1": (105.41, 68.58, 0, None), "C_LDO2": (105.41, 111.76, 0, None),
        },
        "tags": _tags(["CELL1_F", "CELL2_F", "CELL3_F", "CELL4_F",
                       "INA_F1", "INA_F2", "INA_F3", "INA_F4",
                       "INA_S1", "INA_S2", "INA_S3", "INA_S4",
                       "SCL_INT", "SDA_INT", "INA_CRIT", "INA_WARN", "SYS"],
                      12.7, 137.16, per_row=6),
    })
    # MCU, decoupling, reset/boot, test pads and the status LED.
    out.append({
        "title": "STM32C071 MCU, reset/boot, test pads", "at": (381.0, 12.7), "size": (139.7, 190.5),
        "parts": {
            "U_MCU": (45.72, 63.5, 0, None),
            "C_MCU1": (17.78, 25.4, 0, None), "C_MCU2": (17.78, 45.72, 0, None),
            "C_NRST": (17.78, 66.04, 0, None), "SW_RST": (20.32, 78.74, 0, None),
            "R_BOOT": (17.78, 91.44, 0, None), "SW_BOOT": (25.4, 104.14, 0, None),
            "TP_NRST": (12.7, 111.76, 0, None), "TP_SWCLK": (12.7, 119.38, 0, None),
            "TP_SWDIO": (74.93, 76.2, 0, None), "TP_GND": (68.58, 119.38, 0, None),
            "R_LED_MCU": (68.58, 90.17, 0, None), "LED_MCU": (81.28, 90.17, 90, None),
        },
        # Bare test-pad symbols carry their text over the pad; move it aside, or the pad cannot route.
        "fields": {r: {"Reference": (5.08, -2.54, "left"), "Value": (5.08, 2.54, "left")}
                   for r in ("TP_NRST", "TP_SWCLK", "TP_SWDIO", "TP_GND")},
        "tags": _tags(["SW1_DRV", "SW2_DRV", "SW3_DRV", "SW4_DRV", "USB_DP", "USB_DM",
                       "NTC1", "NTC2", "NTC3", "NTC4", "NTC_PWR", "CHG_CE", "SDA_EXT", "SCL_EXT",
                       "CHG_INT", "INA_CRIT", "INA_WARN", "SCL_INT", "SDA_INT",
                       "LED_MCU_A", "LED_MCU_DRV", "SWDIO"],
                      12.7, 135.89, per_row=6),
    })
    # Power out: key switch, 2 A PTC, 5 V boost and the 6-pin XH to the carrier.
    out.append({
        "title": "Key switch, 2 A PTC, 5 V boost, J_PWR1", "at": (533.4, 12.7),
        "size": (165.1, 114.3),
        "parts": {
            "J_KEY1": (12.7, 20.32, 0, None), "F_SYS1": (40.64, 25.4, 0, None),
            "U1": (58.42, 45.72, 0, None), "L1": (83.82, 30.48, 0, None),
            "D1": (99.06, 30.48, 180, None),
            "R_FB1": (99.06, 55.88, 0, None), "R_FB2": (99.06, 71.12, 0, None),
            "C_IN1": (50.8, 71.12, 0, None), "C_OUT1": (83.82, 55.88, 0, None),
            "C_OUT2": (83.82, 74.93, 0, None), "J_PWR1": (124.46, 45.72, 0, None),
        },
        "tags": _tags(["SDA_EXT", "SCL_EXT", "GND", "SYS"], 12.7, 95.25), "wired": {"GND"},
    })
    # One identical block per cell branch.
    for i, bx in enumerate((12.7, 114.3, 215.9, 317.5)):
        out.append({
            "title": f"Cell {i + 1} branch", "at": (bx, 190.5), "size": (99.06, 180.34),
            "parts": _cell(i + 1, 0, 0),
            "tags": _tags([f"CELL{i + 1}_F", f"CELL{i + 1}_S", f"CELL{i + 1}_RAW", f"CELL{i + 1}_SRC",
                           f"PROT{i + 1}_VDD", f"INA_F{i + 1}", f"INA_S{i + 1}"], 12.7, 152.4,
                          per_row=4)
                     | {f"NTC{i + 1}": [(83.82, 120.65, "R")]},
        })
    # Mounting holes and one PWR_FLAG per rail whose source is passive.
    out.append({
        "title": "Mounting holes and power flags", "at": (419.1, 190.5), "size": (127.0, 55.88),
        "parts": {"H1": (7.62, 16.51, 0, None), "H2": (22.86, 16.51, 0, None),
                  "H3": (38.1, 16.51, 0, None), "H4": (53.34, 16.51, 0, None)},
        "flags": [("GND", 10.16, 36.83), ("VPACK", 33.02, 36.83), ("VBUS", 55.88, 36.83),
                  ("VMCU_IN", 78.74, 36.83), ("VBAT_SW", 101.6, 36.83)],
    })
    return out


BLOCKS = _blocks()


# --- PCB (read by gen_pcb.py / route.py / check_gerbers.py) -------------------------------------
# The Keystone 1042 courtyard is 87.88 x 21.66 mm; four holders side by side are 87.88 x 86.64, so
# the cell block alone does not fit the design doc's "about 90 x 85". The board adds a right strip
# (x = 96..140) for the single-side SMD assembly, the 5 V boost and the board-edge connectors, and
# the branch parts sit under their own cell. The size is provisional until the real holder and the
# ZP240.190 plate are measured (design doc, "Unverified").
W, H, CORNER = 140.0, 100.0, 2.0
NETCLASS_EXPECT = (("CELL1_F", [0.8, 0.2]), ("GND", [0.25, 0.2]), ("+5V", [0.8, 0.2]),
                   ("SW", [0.8, 0.2]), ("VPACK", [0.25, 0.2]), ("SDA_EXT", [0.25, 0.2]))
# The branch parts sit under their holder, whose courtyard wraps the whole cell (the cell rides
# ~12 mm above the PCB, so there is no collision): ignore KiCad's 2D courtyard rule for this board.
RULE_SEVERITIES = {"courtyards_overlap": "ignore"}
# The stock USB-C footprint spaces its own shield NPTH 0.185 mm from its GND pads; JLCPCB's 2-layer
# minimum "hole to copper" is 0.2 mm nominal, so keep the 0.15 mm track-width grade rather than fail.
DRC_RULES = {"min_hole_clearance": 0.15}

_CELL_X = 52.0                       # holder centre x (cell block x 8.06..95.94)
_CELL_Y = (17.51, 39.17, 60.83, 82.49)  # holder centres, 21.66 mm pitch


# ref -> (x, y, rot). Holder pads sit at x = centre -/+ 39.69; the under-cell rows keep clear of the
# holder's three NPTH locating holes and of the NTC at the cell middle.
_STRIP = {
    # charger (U_CHG and its application circuit)
    "U_CHG": (107, 8, 0), "L_CHG": (107, 16, 0),
    "C_VBUS": (99, 4, 0), "C_PMID": (99, 10, 0), "C_SYS": (99, 16, 0), "C_BAT": (99, 22, 0),
    "C_REGN": (99, 28, 0), "C_BTST": (99, 34, 0), "R_CE": (99, 40, 0), "R_INT_CHG": (99, 46, 0),
    "R_STAT": (99, 52, 0), "LED_STAT": (99, 58, 0), "R_CC1": (99, 64, 0), "R_CC2": (99, 70, 0),
    "RT1": (107, 24, 0), "RT2": (107, 30, 0), "TH_CHG": (107, 36, 0),
    # LDO and cell diode-OR
    "U_LDO": (107, 44, 0), "C_LDO1": (107, 50, 0), "C_LDO2": (107, 56, 0),
    "D_OR1": (107, 62, 0), "D_OR2": (107, 68, 0), "D_OR3": (107, 74, 0),
    # monitoring support (the INA3221s sit in the cell area, next to the shunts)
    "R_SCL_INT": (118, 40, 0), "R_SDA_INT": (118, 46, 0),
    "R_CRIT": (118, 52, 0), "R_WARN": (118, 58, 0),    # boost (same parts as the carrier)
    "U1": (118, 66, 0), "L1": (118, 74, 0), "D1": (118, 80, 0),
    "F_SYS1": (123, 4, 0), "C_IN1": (123, 12, 0), "C_OUT1": (123, 18, 0), "C_OUT2": (123, 24, 0),
    "R_FB1": (123, 30, 0), "R_FB2": (123, 36, 0),
    # MCU support
    "SW_BOOT": (123, 44, 0), "SW_RST": (123, 52, 0),
    "R_LED_MCU": (123, 58, 0), "LED_MCU": (123, 64, 0),
    "TP_SWDIO": (123, 70, 0), "TP_SWCLK": (123, 74, 0), "TP_NRST": (123, 78, 0),
    "TP_GND": (123, 82, 0), "C_NRST": (123, 88, 0), "R_BOOT": (123, 92, 0),
    "U_MCU": (106, 88, 0), "C_MCU1": (99, 78, 0), "C_MCU2": (99, 90, 0),
    # board-edge connectors (openings face +x)
    "J_USB1": (133, 20, 90), "J_PWR1": (134, 55, 90), "J_KEY1": (134, 82, 90),
    "H1": (4.4, 4.4, 0), "H2": (135.6, 4.4, 0), "H3": (4.4, 95.6, 0), "H4": (135.6, 95.6, 0),
}


def _pcb_place():
    place = dict(_STRIP)
    # The two INA3221s sit in a cell's free middle band, close to the shunts they measure (the 0R
    # sense split keeps their 0.25 mm sense tracks away from the wide Power trunks).
    place.update({"U_INA1": (68, _CELL_Y[1], 0), "C_INA1": (60, _CELL_Y[1], 0),
                  "U_INA2": (68, _CELL_Y[3], 0), "C_INA2": (60, _CELL_Y[3], 0)})
    for i, cy in enumerate(_CELL_Y, start=1):
        # One branch per cell, a copy of the same two rows, in the design-doc branch order.
        row_a = (("D_CB", 20.0), ("F", 28.0), ("R_SH", 36.0), ("Q_A", 44.0), ("Q_B", 52.0),
                 ("R_GS", 60.0), ("R_BYP", 68.0), ("Q_N", 76.0))
        row_b = (("R_PD", 20.0), ("R_SW", 28.0), ("R_PROT", 36.0), ("C_PROT", 44.0),
                 ("U_P", 52.0), ("R_NTC", 60.0))
        for name, x in row_a:
            place[f"{name}{i}"] = (x, cy - 5.0, 0)
        for name, x in row_b:
            place[f"{name}{i}"] = (x, cy + 5.0, 0)
        place[f"TH{i}"] = (_CELL_X, cy, 0)  # NTC under the cell middle
        # 0R sense split right beside the shunt, so the tap leaves the shunt pad, not the wide track
        place[f"R_SNSF{i}"] = (36.0, cy, 0)
        place[f"R_SNSS{i}"] = (44.0, cy, 0)
        place[f"BT{i}"] = (_CELL_X, cy, 0)  # holder, THT, hand-soldered
    return place


PLACE = _pcb_place()
REF_AT = {"D1": (115, 84, 0), "C_MCU2": (99, 86, 90),  # clear of neighbouring silkscreen
          "R_LED_MCU": (127, 58, 90)}
# Test pads are identified by their value text; R_SDA_INT's reference lands on a via (its value
# "4k7" identifies it), and the other three test pads' references would sit on a neighbour's pads.
HIDE_REF = ("TP_SWDIO", "TP_SWCLK", "TP_NRST", "TP_GND", "R_SDA_INT")
LABELS = {}
TEXTS = [
    ("AirsoftCounter v2 pack", 99, 96, 0, 1.0, True), ("2026-10", 99, 98, 0, 1.0, True),
    ("USB", 127, 12, 90, 0.8, False), ("KEY", 127, 70, 90, 0.8, False),
    ("PACK", 127, 42, 90, 0.8, False),
]
GND_VIAS = []
HELTEC_PADS = {}

SIZE_MM = (W, H)
# Mounting-hole centres checked against the NPTH drill file (check_gerbers.py).
NPTH_XY = sorted((PLACE[r][0], PLACE[r][1]) for r in ("H1", "H2", "H3", "H4"))
# The holder footprints add three locating NPTH pins each and the USB-C shell two, so the drill file
# is checked against every expected hit, not just the mounting holes. Coordinates are the footprint
# drills (dx, dy, size) added to the placed part; J_USB1 is at (133, 20) rot 90.
_HOLDER_NPTH = ((-36.13, -8.0, 2.39), (-27.62, 8.0, 3.45), (27.62, -8.0, 3.45))
NPTH_EXPECT = sorted(
    [(x, y, 3.2) for x, y in NPTH_XY]
    + [(_CELL_X + dx, cy + dy, size) for cy in _CELL_Y for dx, dy, size in _HOLDER_NPTH]
    + [(133.0 - 2.605, 20.0 + s * 2.89, 0.65) for s in (-1, 1)])
# The USB-C shell pads are 0.6 mm PTH, below the carrier's 0.8 mm component-drill floor.
PTH_COMPONENT_MIN = 0.6


MODULES = {}
VARIANTS = {"standard": set()}


def assembled(variant="standard"):
    """Refs JLCPCB places: everything except DNP parts, hand-soldered/off-board parts and holes."""
    return [r for r, (_, sym, _) in PARTS.items()
            if r not in DNP | NOT_ASSEMBLED and sym != "Mechanical:MountingHole"]


def check_branches():
    """Every cell: holder+ -> fuse -> shunt -> back-to-back P-FET -> pack rail, in that order, with
    the INA3221 sensing across the shunt through its own 0R split off the shunt pads."""
    net_of = {p: n for n, m in NETS.items() for p in m}
    for i in range(1, 5):
        ina, (inn, inp) = f"U_INA{(i - 1) // 3 + 1}", INA_IN[i]
        assert net_of[f"BT{i}.1"] == net_of[f"F{i}.1"], f"cell {i}: holder+ not on fuse"
        assert net_of[f"F{i}.2"] == net_of[f"R_SH{i}.1"] == net_of[f"R_SNSF{i}.1"], \
            f"cell {i}: fuse -> shunt"
        assert net_of[f"R_SNSF{i}.2"] == net_of[f"{ina}.{inn}"], f"cell {i}: sense not on IN+"
        assert net_of[f"R_SH{i}.2"] == net_of[f"Q_A{i}.3"] == net_of[f"R_SNSS{i}.1"], \
            f"cell {i}: shunt -> FET"
        assert net_of[f"R_SNSS{i}.2"] == net_of[f"{ina}.{inp}"], f"cell {i}: sense not on IN-"
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
