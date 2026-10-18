"""AirsoftCounter pack board: single source of truth for parts and nets.

Same role as carrier.py. gen_sch.py / gen_pcb.py read it through board.py
(BOARD=pack), so run the generators with `make BOARD=pack ...`. Run this file to self-check
(`/usr/bin/python3 pack.py`).

check() runs the shared structural checks (board.check_structure) plus the pack-specific
per-cell branch order: holder+ -> fuse -> shunt -> back-to-back P-FET -> pack rail, holder- on GND.
No protector IC: the default-off MCU switches, the fuses and the charger cover it. Source of
truth for the design: docs/plans/2026-10-01-pack-board-design.md. Part choices and the LCSC
numbers are the P0 facts recorded there.
"""
NAME = "pack"
TITLE = "AirsoftCounter v2 pack"

# Footprints (and symbol + footprint pairs) shared with carrier.py
R0805 = ("Device:R", "Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder")
C0805 = ("Device:C", "Capacitor_SMD:C_0805_2012Metric_Pad1.18x1.45mm_HandSolder")
SOT23 = "Package_TO_SOT_SMD:SOT-23"
SMA = "Diode_SMD:D_SMA"
BSS138 = ("Transistor_FET:BSS138", SOT23)
AO3401A = ("Transistor_FET:AO3401A", SOT23)
SOD123 = "Diode_SMD:D_SOD-123"
B5819W = ("Device:D_Schottky", SOD123)
SS34 = ("Diode:SS34", SMA)
C1206 = "Capacitor_SMD:C_1206_3216Metric_Pad1.33x1.80mm_HandSolder"
R1206 = "Resistor_SMD:R_1206_3216Metric_Pad1.30x1.75mm_HandSolder"
FUSE1206 = "Fuse:Fuse_1206_3216Metric_Pad1.42x1.75mm_HandSolder"
SOT23_3 = "Package_TO_SOT_SMD:SOT-23-3"
SOT23_6 = "Package_TO_SOT_SMD:SOT-23-6"
QFN24 = "Package_DFN_QFN:QFN-24-1EP_4x4mm_P0.5mm_EP2.6x2.6mm"
UQFN16 = "Package_DFN_QFN:UQFN-16-1EP_4x4mm_P0.65mm_EP2.6x2.6mm"
LQFP32 = "Package_QFP:LQFP-32_7x7mm_P0.8mm"
L1210 = "Inductor_SMD:L_1210_3225Metric_Pad1.42x2.65mm_HandSolder"
LRN6045 = "Inductor_SMD:L_Bourns_SRN6045TA"
LED0805 = "LED_SMD:LED_0805_2012Metric_Pad1.15x1.40mm_HandSolder"
XH2 = "Connector_JST:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical"
XH6 = "Connector_JST:JST_XH_B6B-XH-A_1x06_P2.50mm_Vertical"
HDR3 = "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical"
USBC = "Connector_USB:USB_C_Receptacle_HCTL_HC-TYPE-C-16P-01A"
HOLDER = "local:BatteryHolder_MYOUNG_BH-18650-A6AJ012"   # THT, mounted on the bottom side
NTC_BEAD = "local:NTC_Bead_P2.54mm"                       # bottom side, in the holder floor window
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
    # 1206 0R jumpers (2 A rated, <50 mOhm) split the QFN's BAT/SYS pins from the wide rails, so the
    # rails can take the 0.8 mm Power class without crowding the 0.5 mm-pitch pads. Two in parallel
    # for BAT: the 2.048 A charge default (I2C watchdog) crosses them. SYS carries only the load.
    "R_BAT1": ("0R", "Device:R", R1206),
    "R_BAT2": ("0R", "Device:R", R1206),
    "R_SYS1": ("0R", "Device:R", R1206),
    "C_BTST": ("47nF", *C0805),
    # TS bias network for a 10k B3435 NTC: 0-60 C (datasheet section 9.3.7.4). TI's 5.23k/30.9k
    # rounded to Basic 5.1k/30k; the window moves by under 1 C (design doc, simplification delta).
    "RT1": ("5k1", *R0805),
    "RT2": ("30k", *R0805),
    # Hand-soldered 0805 (CMFB 103F3435, LCSC C2889056): no Basic/Preferred NTC exists, so JLCPCB
    # leaves it off and saves the Extended fee. Left off, TS reads 85 % of REGN = cold: no charging.
    "TH_CHG": ("10k NTC", "Device:Thermistor_NTC", R0805[1]),
    "R_CE": ("10k", *R0805),        # /CE low: charging runs with the MCU unpowered
    "R_INT_CHG": ("10k", *R0805),   # /INT pull-up
    "R_STAT": ("1k", *R0805),
    "LED_STAT": ("red", "Device:LED", LED0805),
    "R_CC1": ("5k1", *R0805),
    "R_CC2": ("5k1", *R0805),
    # --- USB-C input (5.1k CC; D+/D- to the MCU) ---
    "J_USB1": ("HC-TYPE-C-16P-01A", "Connector:USB_C_Receptacle_USB2.0_14P", USBC),
    # --- LDO and MCU diode-OR (cell+ / SYS -> VMCU_IN; D_OR1-4 per cell, D_OR5 for SYS) ---
    "U_LDO": ("XC6206P332MR", "Regulator_Linear:XC6206PxxxMR", SOT23_3),
    "C_LDO1": ("1uF", *C0805),
    "C_LDO2": ("1uF", *C0805),
    "D_OR5": ("B5819W", *B5819W),
    # --- monitoring: one PAC1934 (cell n on channel n; ADDRSEL to GND = 0x10, DS20005850E table 5-1) ---
    "U_MON": ("PAC1934T-I/JQ", "Sensor_Energy:PAC1934x-xJQ", UQFN16),
    "C_MON1": ("100nF", *C0805),    # VDD
    "C_MON2": ("100nF", *C0805),    # VDD I/O
    "R_SCL_INT": ("4k7", *R0805),
    "R_SDA_INT": ("4k7", *R0805),
    # SLOW/ALERT: SLOW input at power-up (high = 8 samples/s), firmware reprograms it as open-drain
    # ALERT. PWRDN is active low: pulled up so the monitor runs without firmware.
    "R_ALERT": ("10k", *R0805),
    "R_PWRDN": ("10k", *R0805),
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
    "J_UART1": ("UART", "Connector_Generic:Conn_01x03", HDR3),   # 1 GND, 2 MCU TX, 3 MCU RX; hand-soldered
    # Bring-up test pads on the 3.3 V I2C pair that J_PWR1 carries (SDA_EXT/SCL_EXT, slave 0x30). The
    # rails need none: J_PWR1 pins 3/4 are VBAT_SW and +5V, J_KEY1.1 is SYS, C_MCU1 is 3V3.
    "TP_SDA": ("SDA", "Connector:TestPoint", TP), "TP_SCL": ("SCL", "Connector:TestPoint", TP),
    # --- power out: key switch, 2 A PTC, boost (same parts as carrier.py), 6-pin XH to the carrier ---
    "J_KEY1": ("KEY", "Connector_Generic:Conn_01x02", XH2),
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

# --- per-cell chain (x4), generated like carrier.py's DRIVERS ---
# PAC1934 (SENSE+, SENSE-) per cell. SENSE+ is also the VBUS input, on the cell side of the shunt,
# so each channel reads its own cell with the switch open.
SENSE_IN = {1: ("11", "12"), 2: ("13", "14"), 3: ("8", "7"), 4: ("10", "9")}
# MCU pin per cell: switch gate drive (PB0/PB1/PB2/PA8) and NTC ADC (PA0..PA3).
SW_PIN = {1: "15", 2: "16", 3: "17", 4: "18"}
NTC_PIN = {1: "7", 2: "8", 3: "9", 4: "10"}

for i in range(1, 5):
    PARTS[f"BT{i}"] = ("18650", "Device:Battery_Cell", HOLDER)      # hand-soldered, not in the JLC BOM
    PARTS[f"F{i}"] = ("5A fuse", "Device:Fuse", FUSE1206)
    PARTS[f"D_CB{i}"] = ("SS34", *SS34)                             # crowbar across the holder
    PARTS[f"R_SH{i}"] = ("10mOhm", "Device:R", R1206)  # PAC1934 +-100 mV FSR -> +-10 A
    PARTS[f"Q_A{i}"] = ("AO3401A", *AO3401A)
    PARTS[f"Q_B{i}"] = ("AO3401A", *AO3401A)
    PARTS[f"R_GS{i}"] = ("1M", *R0805)
    PARTS[f"Q_N{i}"] = ("BSS138", *BSS138)
    PARTS[f"R_PD{i}"] = ("100k", *R0805)
    PARTS[f"R_SW{i}"] = ("1k", *R0805)
    PARTS[f"R_BYP{i}"] = ("0R", *R0805)                             # bring-up bypass, DNP
    PARTS[f"D_OR{i}"] = ("B5819W", *B5819W)                        # cell+ -> MCU supply diode-OR
    PARTS[f"TH{i}"] = ("10k NTC", "Device:Thermistor_NTC", NTC_BEAD)  # MF52 bead, hand-soldered
    PARTS[f"R_NTC{i}"] = ("10k", *R0805)
    # Kelvin sense split (plan P4.2): the shunt's two pads feed the monitor through their own
    # resistor, so the sense net is thin (Default class) while the branch stays wide. 10 Ohm limits
    # the input-clamp current while a reversed cell's crowbar holds CELL_F below GND (PAC1934
    # absolute minimum -0.3 V, +-100 mA per pin), now that holder- sits directly on GND.
    PARTS[f"R_SNSF{i}"] = ("10R", *R0805)
    PARTS[f"R_SNSS{i}"] = ("10R", *R0805)

for i in range(1, 5):
    PARTS[f"H{i}"] = ("M3", "Mechanical:MountingHole", MH)

# Hand-soldered bring-up aids (never in a BOM): UART header and the rail / I2C test pads.
TP_DEBUG = ("TP_SDA", "TP_SCL")
DEBUG = ("J_UART1",) + TP_DEBUG
# Bring-up 0R bypasses, off by default. Cell holders, cell NTC beads and bare test-point pads are
# populated by hand, so they are not in the JLCPCB BOM/CPL (NOT_ASSEMBLED) and need no LCSC number.
DNP = {f"R_BYP{i}" for i in range(1, 5)}
NOT_ASSEMBLED = ({f"BT{i}" for i in range(1, 5)} | {f"TH{i}" for i in range(1, 5)}
                 | {"TH_CHG", "TP_SWDIO", "TP_SWCLK", "TP_NRST", "TP_GND"} | set(DEBUG))
# Pins with no connection: charger NC pins and unused control outputs, unused MCU pins, boost NC.
NC_PINS = {"U_CHG.3", "U_CHG.8", "U_CHG.10", "U_CHG.12",
           "U_MCU.1", "U_MCU.2", "U_MCU.3", "U_MCU.20", "U_MCU.32",
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
    ("10mOhm", R1206): "C105362",    # E FOJAN FMF06FTHR010-LH 1% 1 W (2026-10-02)
    ("1M", R0805[1]): "C17514",      # B
    ("100k", R0805[1]): "C149504",   # B
    ("1k", R0805[1]): "C17513",      # B
    ("10k", R0805[1]): "C17414",     # B
    ("4k7", R0805[1]): "C17673",     # B
    ("5k1", R0805[1]): "C27834",     # B
    ("75k", R0805[1]): "C17819",     # P
    ("30k", R0805[1]): "C17621",     # B UNI-ROYAL 0805W8F3002T5E (TS bias, 2026-10-02)
    ("10R", R0805[1]): "C17415",     # B UNI-ROYAL 0805W8F100JT5E (sense taps, 2026-10-02)
    ("0R", R1206): "C17888",         # B UNI-ROYAL 1206W4F0000T5E, jumper 2 A rated (BAT/SYS split)
    ("5A fuse", FUSE1206): "C48332",    # E Bourns SF-1206F500-2, I2t 0.966 A2s
    ("2A PTC", FUSE1206): "C22374899",  # E LUTE 1206L200/16NR
    ("SS34", SMA): "C8678",             # B
    ("B5819W", SOD123): "C8598",        # B SL B5819W, 40 V 1 A Schottky (2026-10-02)
    ("AO3401A", SOT23): "C15127",       # B
    ("BSS138", SOT23): "C7420339",      # P
    ("BQ25601RTWR", QFN24): "C468236",  # E
    ("PAC1934T-I/JQ", UQFN16): "C623960",  # E Microchip, 583 in stock (2026-10-02)
    ("XC6206P332MR", SOT23_3): "C5446",  # B
    ("MT3608", SOT23_6): "C84817",      # E
    ("10uH 2A", LRN6045): "C2046332",   # E
    ("1u5", L1210): "C703084",          # E Murata DFE322512F-1R5M, Isat 3.9 A
    ("STM32C071KBTx", LQFP32): "C42116633",  # E
    ("HC-TYPE-C-16P-01A", USBC): "C2894897",  # E
    ("TS-1088-AR02016", TACT): "C720477",     # B
    ("red", LED0805): "C84256",         # B NCD0805R1
    ("green", LED0805): "C2297",        # B KT-0805G
    ("KEY", XH2): "C158012",            # E JST B2B-XH-A(LF)(SN)
    ("PWR", XH6): "C144397",            # E JST B6B-XH-A(LF)(SN)
}

# net: [ "REF.pin", ... ]. Per-cell nets are built in the loop below.
NETS = {
    # pack rail and charger
    "VPACK": [*(f"Q_B{i}.3" for i in range(1, 5)), *(f"R_BYP{i}.2" for i in range(1, 5)),
              "R_BAT1.2", "R_BAT2.2"],
    "BAT_CHG": ["U_CHG.13", "U_CHG.14", "C_BAT.1", "R_BAT1.1", "R_BAT2.1"],
    "SYS_CHG": ["U_CHG.15", "U_CHG.16", "L_CHG.2", "C_SYS.1", "R_SYS1.1"],
    "SYS": ["R_SYS1.2", "D_OR5.2", "J_KEY1.1"],
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
    "VMCU_IN": [*(f"D_OR{i}.1" for i in range(1, 6)), "U_LDO.3", "C_LDO1.1"],
    "+3V3": ["U_LDO.2", "C_LDO2.1",
             "U_MON.2", "U_MON.15", "C_MON1.1", "C_MON2.1",
             "R_SCL_INT.1", "R_SDA_INT.1", "R_ALERT.1", "R_PWRDN.1",
             "R_INT_CHG.2", "R_STAT.1", "U_MCU.4", "C_MCU1.1", "C_MCU2.1", "SW_BOOT.2"],
    # internal I2C (MCU master): PAC1934 + BQ25601, pull-ups to +3V3
    "SCL_INT": ["U_MCU.30", "U_MON.4", "U_CHG.5", "R_SCL_INT.2"],
    "SDA_INT": ["U_MCU.31", "U_MON.5", "U_CHG.6", "R_SDA_INT.2"],
    "MON_ALERT": ["U_MON.1", "R_ALERT.2", "U_MCU.28"],
    "MON_PWRDN": ["U_MON.16", "R_PWRDN.2", "U_MCU.29"],
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
    "UART_TX": ["U_MCU.19", "J_UART1.2"],     # PA9, USART1_TX
    "UART_RX": ["U_MCU.21", "J_UART1.3"],     # PA10, USART1_RX
    "LED_MCU_DRV": ["U_MCU.26", "R_LED_MCU.1"],
    "LED_MCU_A": ["R_LED_MCU.2", "LED_MCU.2"],
    # external I2C (slave 0x30) to the carrier: no pull-ups here
    "SDA_EXT": ["U_MCU.13", "J_PWR1.5", "TP_SDA.1"],
    "SCL_EXT": ["U_MCU.14", "J_PWR1.6", "TP_SCL.1"],
    # NTC divider supply (PA4), switched off between samples
    "NTC_PWR": ["U_MCU.11", *(f"TH{i}.1" for i in range(1, 5))],
    # ground: holder- (no protector IC), crowbar anodes, gate drive, charger, MCU, earth
    "GND": [*(f"BT{i}.2" for i in range(1, 5)), *(f"D_CB{i}.2" for i in range(1, 5)),
            *(f"Q_N{i}.2" for i in range(1, 5)),
            *(f"R_PD{i}.2" for i in range(1, 5)),
            *(f"R_NTC{i}.2" for i in range(1, 5)),
            "U_CHG.2", "U_CHG.17", "U_CHG.18", "U_CHG.25",
            "C_VBUS.2", "C_PMID.2", "C_SYS.2", "C_BAT.2", "C_REGN.2",
            "RT2.2", "TH_CHG.2",
            "U_LDO.1", "C_LDO1.2", "C_LDO2.2",
            "U_MON.3", "U_MON.6", "U_MON.17", "C_MON1.2", "C_MON2.2",   # ADDRSEL = GND -> 0x10
            "R_CC1.2", "R_CC2.2",
            "J_USB1.A1", "J_USB1.A12", "J_USB1.B1", "J_USB1.B12", "J_USB1.SH",
            "U_MCU.5", "C_MCU1.2", "C_MCU2.2", "C_NRST.2", "SW_RST.2", "R_BOOT.2",
            "LED_MCU.1", "R_CE.2",
            "U1.2", "C_IN1.2", "C_OUT1.2", "C_OUT2.2", "R_FB2.2",
            "J_PWR1.1", "J_PWR1.2", "TP_GND.1", "J_UART1.1"],
}

for i in range(1, 5):
    s_p, s_m = SENSE_IN[i]
    NETS[f"CELL{i}_RAW"] = [f"BT{i}.1", f"F{i}.1"]
    NETS[f"CELL{i}_F"] = [f"F{i}.2", f"D_CB{i}.1", f"R_SH{i}.1", f"D_OR{i}.2", f"R_SNSF{i}.1"]
    NETS[f"CELL{i}_S"] = [f"R_SH{i}.2", f"Q_A{i}.3", f"R_BYP{i}.1", f"R_SNSS{i}.1"]
    NETS[f"SNS_F{i}"] = [f"R_SNSF{i}.2", f"U_MON.{s_p}"]
    NETS[f"SNS_S{i}"] = [f"R_SNSS{i}.2", f"U_MON.{s_m}"]
    NETS[f"CELL{i}_SRC"] = [f"Q_A{i}.2", f"Q_B{i}.2", f"R_GS{i}.2"]
    NETS[f"CELL{i}_G"] = [f"Q_A{i}.1", f"Q_B{i}.1", f"R_GS{i}.1", f"Q_N{i}.3"]
    NETS[f"SW{i}_G"] = [f"Q_N{i}.1", f"R_PD{i}.1", f"R_SW{i}.2"]
    NETS[f"SW{i}_DRV"] = [f"R_SW{i}.1", f"U_MCU.{SW_PIN[i]}"]
    NETS[f"NTC{i}"] = [f"TH{i}.2", f"R_NTC{i}.1", f"U_MCU.{NTC_PIN[i]}"]


# --- layout (read by gen_sch.py / gen_pcb.py / check_gerbers.py) --------------------------------
# Rails carry power_in pins, so ERC needs a driver on each: +3V3 has the LDO's power_out, the others
# take a PWR_FLAG (their sources are all passive). +5V and SYS have no power_in pin, so they stay
# ordinary labelled nets.
# Nets that get the wider Power class. "SW*" would also catch the MCU's SW*_DRV gate signals (uA),
# which must reach the LQFP32's 0.8 mm-pitch pads, so only the two switching nodes are listed.
# VPACK and SYS are wide: VPACK joins the four branches, and at 0.25 mm the cell-to-charger track
# ran 151-294 mOhm, unbalancing the matched ~150 mOhm branches; at 0.8 mm it is 43-85 mOhm. The QFN24 side of each (BAT_CHG,
# SYS_CHG) stays Default behind the R_BAT/R_SYS 0R jumpers: the 0.8 mm class cannot leave those
# 0.5 mm-pitch pads without a clearance error. VBUS stays Default (short, connector beside U_CHG).
NETCLASS_POWER = ("VBAT*", "KEY_OUT", "CELL*_RAW", "CELL*_F", "CELL*_S", "CELL*_SRC",
                  "+5V", "SW", "SW_CHG", "VPACK", "SYS")
RAILS = ("GND", "+3V3", "VPACK", "VBUS", "VMCU_IN", "VBAT_SW", "BAT_CHG")
# A power port names its net by Value, so each rail reuses a stock symbol (carrier convention).
PORT_LIB = {"GND": "power:GND", "+3V3": "power:+3V3", "VPACK": "power:VDC",
            "VBUS": "power:VBUS", "VMCU_IN": "power:+VDC", "VBAT_SW": "power:+BATT",
            "BAT_CHG": "power:VD"}


def _tags(nets, x0, y0, per_row=7, pitch=20.32, row=12.7):
    """One global label per net, in a free strip along the bottom of a block."""
    return {n: [(x0 + (k % per_row) * pitch, y0 + (k // per_row) * row, "R")]
            for k, n in enumerate(nets)}


def _cell(i, x0, y0):
    """One cell's branch (design doc order: holder+ -> fuse -> shunt -> back-to-back P-FET) plus
    the crowbar, the NTC and the switch gate drive. Four copies, one per cell block. The diode-OR tap
    (D_ORi) is drawn on the monitor sheet with the rest of the bank: VMCU_IN has a single capacitor."""
    def a(x, y, rot=0):
        return (x0 + x, y0 + y, rot, None)

    return {
        f"BT{i}": a(12.7, 20.32), f"F{i}": a(12.7, 40.64), f"R_SH{i}": a(12.7, 60.96),
        f"Q_A{i}": a(12.7, 82.55), f"Q_B{i}": a(31.75, 82.55),
        f"R_GS{i}": a(24.13, 100.33), f"R_BYP{i}": a(43.18, 100.33),
        f"Q_N{i}": a(12.7, 116.84), f"R_PD{i}": a(7.62, 134.62), f"R_SW{i}": a(25.4, 134.62),
        f"D_CB{i}": a(60.96, 20.32),
        f"R_SNSF{i}": a(45.72, 64.77), f"R_SNSS{i}": a(45.72, 78.74),
        f"TH{i}": a(83.82, 60.96), f"R_NTC{i}": a(83.82, 78.74),
    }


def _blocks():
    """Hand-placed parts, one block per function sheet. Tags are the global labels that carry a
    multi-block net across a block boundary (rails use power ports instead).

    Block 3 (key switch, PTC, 5 V boost) has every part on the root sheet, and block 8's holes are
    root parts too: both its connectors are root parts, and VBAT_SW has exactly one capacitor (C_IN1),
    so the chain, its caps and J_PWR1 must be drawn in one file. Pieces of a block that are root
    parts (J_KEY1/J_PWR1 here) are removed from the sheet by gen_sch.sheet_blocks, so the blocks stay
    the description of each function even where the root draws them."""
    out = []
    # Charger + USB-C receptacle. Caps sit on the side of U_CHG whose pins they decouple. R_INT_CHG,
    # R_STAT and LED_STAT pull the charger's /INT and STAT up to +3V3, which this sheet has no
    # capacitor for, so they are drawn on the MCU sheet with the other status/interface parts.
    out.append({
        "title": "USB-C input, BQ25601 charger", "at": (12.7, 12.7), "size": (203.2, 139.7),
        "parts": {
            "U_CHG": (48.26, 50.8, 0, None),
            "C_VBUS": (15.24, 25.4, 0, None), "C_PMID": (15.24, 50.8, 0, None),
            "R_CE": (15.24, 76.2, 0, None),
            "L_CHG": (81.28, 27.94, 0, None), "C_BTST": (100.33, 27.94, 0, None),
            "C_SYS": (81.28, 55.88, 0, None), "C_BAT": (100.33, 60.96, 0, None),
            "C_REGN": (81.28, 78.74, 0, None), "RT1": (100.33, 78.74, 0, None),
            "RT2": (100.33, 95.25, 0, None), "TH_CHG": (116.84, 95.25, 0, None),
            "J_USB1": (152.4, 71.12, 0, None),
            "R_CC1": (182.88, 60.96, 90, None), "R_CC2": (182.88, 68.58, 90, None),
            "R_SYS1": (124.46, 30.48, 0, None),
            "R_BAT1": (124.46, 55.88, 0, None), "R_BAT2": (137.16, 55.88, 0, None),
        },
        "tags": _tags(["SCL_INT", "SDA_INT", "CHG_INT", "CHG_CE", "USB_DP", "USB_DM", "SYS",
                       "CC2"], 12.7, 118.11),
        # Every rail this sheet draws that no on-board source drives takes its PWR_FLAG here, beside
        # the cap that decouples it in this file.
        "flags": [("VBUS", 15.24, 147.32), ("BAT_CHG", 45.72, 147.32), ("VPACK", 76.2, 147.32)],
    })
    # Monitoring: PAC1934, the whole diode-OR bank and the 3V3 LDO. All five diode-OR legs share
    # VMCU_IN, whose only capacitor (C_LDO1) is here, so the four cell legs are drawn here too.
    # The bank is a column: each cathode (VMCU_IN) needs a power port to its left.
    out.append({
        "title": "Cell monitoring (PAC1934), diode-OR, 3V3 LDO", "at": (228.6, 12.7),
        "size": (139.7, 177.8),
        "parts": {
            "U_MON": (30.48, 60.96, 0, None),
            "C_MON1": (7.62, 20.32, 0, None), "C_MON2": (7.62, 101.6, 0, None),
            "R_SCL_INT": (60.96, 38.1, 90, None), "R_SDA_INT": (60.96, 55.88, 90, None),
            "R_ALERT": (60.96, 73.66, 90, None), "R_PWRDN": (60.96, 91.44, 90, None),
            "D_OR5": (105.41, 20.32, 0, None),
            "D_OR1": (105.41, 45.72, 0, None), "D_OR2": (105.41, 63.5, 0, None),
            "D_OR3": (105.41, 81.28, 0, None), "D_OR4": (105.41, 99.06, 0, None),
            "U_LDO": (144.78, 60.96, 0, None),
            "C_LDO1": (144.78, 38.1, 0, None), "C_LDO2": (144.78, 83.82, 0, None),
        },
        "tags": _tags(["SNS_F1", "SNS_F2", "SNS_F3", "SNS_F4",
                       "SNS_S1", "SNS_S2", "SNS_S3", "SNS_S4",
                       "SCL_INT", "SDA_INT", "MON_ALERT", "MON_PWRDN", "SYS",
                       "CELL1_F", "CELL2_F", "CELL3_F", "CELL4_F"],
                      12.7, 130.81, per_row=6),
        "flags": [("VMCU_IN", 12.7, 170.18)],
    })
    # MCU, decoupling, reset/boot, the status LEDs and the charger's /INT pull-up. The bring-up test
    # pads and J_UART1 are root parts (drawn beside the board-edge connectors). Each LED needs room
    # beside it for its GND port, so the two LED rows are 33 mm apart.
    out.append({
        "title": "STM32C071 MCU, reset/boot, status LEDs", "at": (381.0, 12.7), "size": (139.7, 190.5),
        "parts": {
            "U_MCU": (45.72, 63.5, 0, None),
            "C_MCU1": (17.78, 25.4, 0, None), "C_MCU2": (17.78, 45.72, 0, None),
            "C_NRST": (17.78, 66.04, 0, None), "SW_RST": (20.32, 78.74, 0, None),
            "R_BOOT": (17.78, 91.44, 0, None), "SW_BOOT": (25.4, 104.14, 0, None),
            "R_INT_CHG": (68.58, 25.4, 0, None),
            "R_LED_MCU": (68.58, 81.28, 0, None), "LED_MCU": (88.9, 81.28, 90, None),
            "R_STAT": (68.58, 114.3, 0, None), "LED_STAT": (88.9, 114.3, 90, None),
        },
        "tags": _tags(["SW1_DRV", "SW2_DRV", "SW3_DRV", "SW4_DRV", "USB_DP", "USB_DM",
                       "NTC1", "NTC2", "NTC3", "NTC4", "NTC_PWR", "CHG_CE", "SDA_EXT", "SCL_EXT",
                       "CHG_INT", "MON_ALERT", "MON_PWRDN", "SCL_INT", "SDA_INT",
                       "LED_MCU_A", "LED_MCU_DRV", "SWDIO", "NRST", "BOOT0", "UART_TX", "UART_RX",
                       "STAT"],
                      12.7, 147.32, per_row=6),
    })
    # Power out: key switch, 2 A PTC, 5 V boost and the 6-pin XH to the carrier. Every part is on the
    # root sheet (see the docstring); the block is kept as the description of that function.
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
            "TP_SDA": (12.7, 45.72, 0, None), "TP_SCL": (12.7, 58.42, 0, None),
        },
    })
    # One identical block per cell branch, plus the mounting holes and power flags block (holes are
    # root parts; the flags live on the sheet that carries each rail's capacitor).
    for i, bx in enumerate((12.7, 114.3, 215.9, 317.5)):
        out.append({
            "title": f"Cell {i + 1} branch", "at": (bx, 190.5), "size": (99.06, 180.34),
            "parts": _cell(i + 1, 0, 0),
            "tags": _tags([f"CELL{i + 1}_F", f"CELL{i + 1}_S", f"CELL{i + 1}_RAW", f"CELL{i + 1}_SRC",
                           f"SNS_F{i + 1}", f"SNS_S{i + 1}"], 12.7, 152.4,
                          per_row=4)
                     | {f"NTC{i + 1}": [(83.82, 120.65, "R")]},
        })
    # Mounting holes (root parts) and the pack's flags. Kept as a block so the root parts are
    # documented where the layout is.
    out.append({
        "title": "Mounting holes", "at": (419.1, 190.5), "size": (139.7, 55.88),
        "parts": {"H1": (7.62, 16.51, 0, None), "H2": (22.86, 16.51, 0, None),
                  "H3": (38.1, 16.51, 0, None), "H4": (53.34, 16.51, 0, None)},
    })
    return out


BLOCKS = _blocks()

# Cable connectors drawn on the root get 5.08 mm-pitch symbols (same pins and footprints): the gap
# between a connector and its off-board part holds that rail's power ports, which do not fit at
# 2.54 mm. Nothing on the board changes.
for _r in ("J_PWR1", "J_KEY1"):
    _v, _sym, _fp = PARTS[_r]
    PARTS[_r] = (_v, f"local:Conn_W_{_sym[-2:]}", _fp)


# --- Hierarchical schematic (docs/plans/2026-10-18-hierarchical-schematics-design.md) ---
# Function sheets: name -> (title, BLOCKS indexes). One block per sheet; the parts a block shares with
# ROOT (its connectors and bring-up pads) are drawn on the root instead, by gen_sch.sheet_blocks.
SHEETS = {
    "charger": ("USB-C input, BQ25601 charger", [0]),
    "monitor": ("Cell monitoring (PAC1934), diode-OR, 3V3 LDO", [1]),
    "mcu": ("STM32C071 MCU, reset/boot, status LEDs", [2]),
    "cell1": ("Cell 1 branch (18650 holder)", [4]),
    "cell2": ("Cell 2 branch (18650 holder)", [5]),
    "cell3": ("Cell 3 branch (18650 holder)", [6]),
    "cell4": ("Cell 4 branch (18650 holder)", [7]),
}
# Root (system) sheet: both board-edge connectors with their off-board parts, the key -> PTC -> boost
# -> J_PWR1 chain (block 3, whose rails have a single capacitor each, drawn here with them), the
# bring-up pads, the mounting holes and the pack's rail bulk caps. Function sheets are boxes beside
# the parts they talk to. Coordinates are absolute sheet mm; content starts at (12.7, 12.7).
ROOT = {
    "parts": {
        # key switch (left) and the carrier link (right), each with its off-board part beyond it
        "J_KEY1": (81.28, 33.02, 0, None), "J_PWR1": (337.82, 33.02, 0, "y"),
        # key -> 2 A PTC -> boost -> J_PWR1, flowing left to right, with the caps of VBAT_SW and +5V
        "F_SYS1": (120.65, 33.02, 0, None), "C_IN1": (127.0, 50.8, 0, None),
        "U1": (152.4, 33.02, 0, None), "L1": (177.8, 20.32, 90, None),
        "D1": (195.58, 20.32, 180, None),
        "C_OUT1": (205.74, 35.56, 0, None), "C_OUT2": (215.9, 45.72, 0, None),
        "R_FB1": (205.74, 55.88, 0, None), "R_FB2": (215.9, 63.5, 0, None),
        # bring-up: UART header and the SWD / I2C pads, one row inside their outline
        "J_UART1": (25.4, 233.68, 0, "y"),
        "TP_SWDIO": (55.88, 233.68, 0, None), "TP_SWCLK": (66.04, 233.68, 0, None),
        "TP_NRST": (76.2, 233.68, 0, None), "TP_GND": (86.36, 233.68, 0, None),
        "TP_SDA": (96.52, 233.68, 0, None), "TP_SCL": (106.68, 233.68, 0, None),
        # mounting holes, in the free right margin below the carrier cable
        "H1": (355.6, 222.25, 0, None), "H2": (372.11, 222.25, 0, None),
        "H3": (355.6, 240.03, 0, None), "H4": (372.11, 240.03, 0, None),
    },
    # The rails drawn here whose source is passive: a PWR_FLAG per rail, on the sheet that carries
    # that rail's capacitor (VPACK's flag sits with R_BAT1/R_BAT2 on the charger sheet).
    "flags": [("GND", 25.4, 63.5), ("VBAT_SW", 58.42, 63.5)],
    # The 2.54 mm UART header takes rail ports along its stubs, which stay in the pin's own row.
    "port_modes": {"J_UART1": "along"},
    # Wide channels: every root signal needs a straight run with free rows beside it for its global
    # label, so the gap between boxes is sized from ~70 sheet pins, not from the box content.
    "sheets": {
        "charger": (25.4, 88.9, 60.96, 38.1), "mcu": (118.11, 88.9, 60.96, 48.26),
        "monitor": (210.82, 88.9, 60.96, 38.1),
        "cell1": (25.4, 175.26, 60.96, 38.1), "cell2": (118.11, 175.26, 60.96, 38.1),
        "cell3": (210.82, 175.26, 60.96, 38.1), "cell4": (303.53, 175.26, 60.96, 38.1),
    },
    # The one module-like group on the root: the bring-up pads and the UART header.
    "outline": ("Pack bring-up pads (SWD, UART, I2C)", (17.78, 218.44, 96.52, 30.48)),
    "size": (391.16, 236.22),  # root content from (12.7, 12.7): fits A3
}
# Off-board parts, drawn on the root beyond their connector, never on the board or in a BOM:
# ref -> (value, symbol, connector, {own pin: connector pin}, cable note, (x, y, rot, mirror)).
# J_USB1 is on the charger sheet with its CC pull-downs and C_VBUS, so the USB-C cable has no
# off-board part (USB-C receptacles are panel-side by definition); VBUS's capacitor can only live
# where the charger draws it.
OFFBOARD = {
    "#X_CARRIER": ("Carrier board (J_PWR1)", "local:Pack_Link_6", "J_PWR1",
                   {str(i): str(i) for i in range(1, 7)}, "XH-6 to the carrier's J_PWR1",
                   (386.08, 33.02, 0, None)),
    "#X_KEY": ("EAO 82-6121 key switch", "local:Conn_W_02", "J_KEY1",
               {"1": "1", "2": "2"}, "XH-2", (40.64, 33.02, 0, "y")),
}


def check_sheets(m=None):
    """Every board part is drawn exactly once: on the root, or in one block of one sheet; and any
    block that is on no sheet has all its parts on the root (block 3 and the hole block do)."""
    import sys

    m = m or sys.modules[__name__]
    on_sheets = [r for _t, idx in m.SHEETS.values() for i in idx for r in m.BLOCKS[i]["parts"]
                 if r not in m.ROOT["parts"]]
    drawn = on_sheets + list(m.ROOT["parts"])
    twice = sorted({r for r in drawn if drawn.count(r) > 1})
    assert not twice, f"drawn twice: {twice}"
    assert set(drawn) == set(m.PARTS), \
        (f"not drawn: {sorted(set(m.PARTS) - set(drawn))}, "
         f"unknown: {sorted(set(drawn) - set(m.PARTS))}")
    assert m.ROOT["sheets"].keys() == m.SHEETS.keys(), "ROOT['sheets'] must place every sheet"
    used = {i for _t, idx in m.SHEETS.values() for i in idx}
    root = set(m.ROOT["parts"])
    for i, b in enumerate(m.BLOCKS):
        off = sorted(set(b["parts"]) - root) if i not in used else []
        assert not off, f"block {i} is on no sheet and its parts are not root parts: {off}"


# --- PCB (read by gen_pcb.py / route.py / check_gerbers.py) -------------------------------------
# The four 18650 holders (MYOUNG BH-18650-A6AJ012, THT) sit on the bottom side, so the whole top side
# above them takes the single-side SMD assembly: each cell's branch in its own band, and the charger,
# LDO/monitor, boost and MCU groups in the free x 59-80 strip of bands 1-4. The cell NTC beads sit on the
# bottom in each holder's floor window. Board edge connectors on the right, M3 holes at the corners
# clear of the holder ends. The ZP240.190 plate pattern is still unmeasured (design doc, "Unverified").
W, H, CORNER = 96.0, 90.0, 2.0
NETCLASS_EXPECT = (("CELL1_F", [0.8, 0.2]), ("GND", [0.25, 0.2]), ("+5V", [0.8, 0.2]),
                   ("SW", [0.8, 0.2]), ("VPACK", [0.8, 0.2]), ("SYS", [0.8, 0.2]),
                   ("BAT_CHG", [0.25, 0.2]), ("SDA_EXT", [0.25, 0.2]))
# The stock USB-C footprint spaces its own shield NPTH 0.185 mm from its GND pads; JLCPCB's 2-layer
# minimum "hole to copper" is 0.2 mm nominal, so keep the 0.15 mm track-width grade rather than fail.
DRC_RULES = {"min_hole_clearance": 0.15}

BOTTOM = {f"BT{i}" for i in range(1, 5)} | {f"TH{i}" for i in range(1, 5)}
# The NTC beads sit in each holder's floor window on purpose. KiCad 10's pth_inside_courtyard (an error
# now) cannot exempt them, so it is off here and gen_pcb.py checks every other THT pad against the holders.
PTH_UNDER_OK = {f"TH{i}" for i in range(1, 5)}
RULE_SEVERITIES = {"pth_inside_courtyard": "ignore"}
_CELL_X = 46.5                                  # holder centre x (body x 8..85)
_CELL_Y = (12.35, 34.01, 55.67, 77.33)          # holder centres, 21.66 mm pitch (body 20.7)
# Holder drills relative to the holder centre as seen from the top, i.e. after the flip to the bottom
# (footprint x mirrored): + tab on the left, snap pegs d3.3 / d3.3 / d2.4.
_HOLDER_NPTH = ((-27.6, -8.0, 3.3), (27.6, 8.0, 3.3), (-35.8, 8.0, 2.4))

# ref -> (x, y, rot). Groups on top of the free x 59-80 strip, one per cell band.
_STRIP = {
    # band 1: charger (U_CHG, its caps either side, 0R rail splits on the right)
    "U_CHG": (68, 9, 0), "L_CHG": (68, 16, 0),
    "C_VBUS": (61.5, 3.5, 0), "C_PMID": (66.5, 3.6, 0), "C_BTST": (61.5, 10.5, 0),
    "C_REGN": (61.5, 14, 0), "C_SYS": (61.5, 17.5, 0),
    "R_BAT1": (75.5, 4, 0), "R_BAT2": (75.5, 7.5, 0), "R_SYS1": (75.5, 11, 0), "C_BAT": (75.5, 14.5, 0),
    "R_CC1": (80, 20, 90), "R_CC2": (80, 25.5, 90),
    # row between cells 1 and 2: TS network and the charger's control pull-ups / STAT LED
    "RT1": (47, 23.18, 0), "RT2": (51.5, 23.18, 0), "TH_CHG": (56, 23.18, 0),
    "R_CE": (60.5, 23.18, 0), "R_INT_CHG": (65, 23.18, 0), "R_STAT": (69.5, 23.18, 0),
    "LED_STAT": (75.5, 23.18, 0),
    # band 2: U_MON (all four cells), the LDO and the SYS leg of the diode-OR
    "U_MON": (64, 34.01, 0), "C_MON1": (64, 29.5, 0), "C_MON2": (69.5, 38.5, 0), "D_OR5": (64, 41, 0),
    "U_LDO": (75, 28.5, 0), "C_LDO1": (69.8, 30, 90), "C_LDO2": (74.5, 35.5, 0),
    # row between cells 2 and 3: internal I2C pull-ups
    "R_SCL_INT": (61, 44.84, 0), "R_SDA_INT": (65.6, 44.84, 0),
    # band 3: 5 V boost (same parts as the carrier)
    "U1": (64, 51, 0), "L1": (71, 55.67, 0), "D1": (63.5, 59.5, 0),
    "C_IN1": (77.5, 49, 0), "C_OUT1": (77.5, 52.5, 0), "C_OUT2": (77.5, 56, 0),
    "R_FB1": (78, 59.5, 0), "R_FB2": (78, 62.3, 0),
    # row between cells 3 and 4: key-switch PTC
    "F_SYS1": (62, 66.5, 0),
    # band 4: MCU, its decoupling, the monitor's ALERT/PWRDN pull-ups beside MCU pins 28/29
    "R_ALERT": (76.5, 69.3, 0), "R_PWRDN": (76.5, 73.5, 0),
    "U_MCU": (66, 77.33, 0), "C_MCU1": (63.5, 70, 0), "C_MCU2": (68, 70, 0),
    # bottom edge row: buttons, test pads, status LED, NRST/BOOT0 parts
    "SW_BOOT": (16, 87.4, 0), "SW_RST": (23, 87.4, 0),
    "TP_SWDIO": (28.5, 87.4, 0), "TP_SWCLK": (31.5, 87.4, 0), "TP_NRST": (34.5, 87.4, 0),
    "TP_GND": (37.5, 87.4, 0),
    **{r: (66.5 + 2.6 * i, 87.2, 0) for i, r in enumerate(TP_DEBUG)}, "LED_MCU": (42.5, 87.4, 0), "R_LED_MCU": (49, 87.4, 0),
    "R_BOOT": (55, 87.4, 0), "C_NRST": (61, 87.4, 0),
    # board-edge connectors (openings face +x)
    "J_USB1": (90, 23, 90), "J_PWR1": (90, 55, 90), "J_KEY1": (90, 78, 90),
    # UART header upright in the holder-free right strip (THT pins can't go under a holder); rot 180
    # puts pin 1 (GND) at the bottom so the rot-90 label reads in pin order
    "J_UART1": (88.5, 70.04, 180),
    "H1": (4, 4, 0), "H2": (92, 4, 0), "H3": (4, 86, 0), "H4": (92, 86, 0),
}


def _pcb_place():
    place = dict(_STRIP)
    for i, cy in enumerate(_CELL_Y, start=1):
        # One branch per cell, a copy of the same three rows, in the design-doc branch order.
        row_a = (("D_CB", 17.0), ("F", 24.5), ("R_SH", 30.5), ("Q_A", 36.0), ("Q_B", 41.0),
                 ("R_GS", 46.5), ("Q_N", 52.0))
        row_b = (("R_PD", 17.0), ("R_SW", 21.5), ("D_OR", 28.0), ("R_NTC", 46.0))
        for name, x in row_a:
            place[f"{name}{i}"] = (x, cy - 4.0, 0)
        for name, x in row_b:
            place[f"{name}{i}"] = (x, cy + 4.5, 0)
        # 0R sense split right beside the shunt, so the tap leaves the shunt pad, not the wide track
        place[f"R_SNSF{i}"] = (30.5, cy, 0)
        place[f"R_SNSS{i}"] = (36.0, cy, 0)
        place[f"R_BYP{i}"] = (41.0, cy, 0)  # DNP bypass right under Q_A/Q_B, off the busy row a
        place[f"BT{i}"] = (_CELL_X, cy, 0)  # holder, bottom side, THT, hand-soldered
        place[f"TH{i}"] = (_CELL_X, cy, 0)  # bead NTC, bottom side, in the holder floor window
    return place


PLACE = _pcb_place()


def _ref_at():
    """Reference text positions where the default (above the part) lands on a neighbour: rows at a
    4.5 mm pitch alternate above/below, and a few refs move off a peg hole's mask opening."""
    def below(ref, dy):
        x, y, _ = PLACE[ref]
        return (x, y + dy, 0)
    out = {}
    for i, cy in enumerate(_CELL_Y, start=1):
        out[f"D_CB{i}"] = (17.0, cy - 1.3, 0)  # above it sits the d3.3 peg
        out |= {f"{r}{i}": below(f"{r}{i}", 1.9) for r in ("R_SW", "D_OR")}
    out |= {r: below(r, 1.65) for r in ("RT2", "R_CE", "R_STAT", "LED_STAT", "R_SDA_INT",
                                        "R_FB2")}
    out["U_MON"] = below("U_MON", 3.6)
    # rotated, to the right of the part (free strip before the - tab / USB-C)
    out |= {"C_IN1": (80.6, 49, 90), "R_CC1": (81.6, 20, 90),
            "R_CC2": (81.6, 25.5, 90)}
    return out


REF_AT = _ref_at()
# Test pads are identified by their value text.
HIDE_REF = ("TP_SWDIO", "TP_SWCLK", "TP_NRST", "TP_GND", "J_UART1", *TP_DEBUG)
LABELS = {}
TEXTS = [
    ("AirsoftCounter v2 pack", 24, 1.8, 0, 1.0, True), ("2026-10", 24, 3.6, 0, 1.0, True),
    ("USB", 85.5, 32, 90, 0.8, False), ("PACK", 85.5, 62, 90, 0.8, False),
    ("KEY", 85.5, 81.8, 90, 0.8, False),
    ("GND TX RX", 91.5, 67.5, 90, 0.8, False),
    *((n, 66.5 + 2.6 * i, 85.0, 0, 0.8, False) for i, n in enumerate(("SDA", "SCL"))),
]
GND_VIAS = []
HELTEC_PADS = {}

SIZE_MM = (W, H)
# Mounting-hole centres checked against the NPTH drill file (check_gerbers.py).
NPTH_XY = sorted((PLACE[r][0], PLACE[r][1]) for r in ("H1", "H2", "H3", "H4"))
# The holders add three snap-peg NPTH each and the USB-C shell two, so the drill file is checked
# against every expected hit, not just the mounting holes. J_USB1 is at (90, 23) rot 90.
NPTH_EXPECT = sorted(
    [(x, y, 3.2) for x, y in NPTH_XY]
    + [(_CELL_X + dx, cy + dy, size) for cy in _CELL_Y for dx, dy, size in _HOLDER_NPTH]
    + [(90.0 - 2.605, 23.0 + s * 2.89, 0.65) for s in (-1, 1)])
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


def check():
    import sys

    import board  # pyright: ignore[reportMissingImports]  # local sibling module
    board.check_structure(sys.modules[__name__])
    check_branches()
    check_sheets()
    print(f"pack ok: {len(PARTS)} parts, {len(NETS)} nets")


if __name__ == "__main__":
    check()
