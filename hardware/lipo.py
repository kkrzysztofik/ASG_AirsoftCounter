"""AirsoftCounter LiPo board: a 2S/3S airsoft LiPo instead of the 18650 pack. No charging.

Same role as pack.py: gen_sch.py / gen_pcb.py read it through board.py (BOARD=lipo), so run the
generators with `make BOARD=lipo ...`. Run this file to self-check (`/usr/bin/python3 lipo.py`).

check() runs board.check_structure plus check_power_path: pads -> fuse -> reverse P-FET -> TVS ->
both bucks and the LDO, both buck ENs on one node that the key pulls up and the MCU can pull down.
Source of truth: docs/plans/2026-10-02-lipo-board-design.md.
"""
import pack

NAME = "lipo"
TITLE = "AirsoftCounter v2 LiPo"

R0805, C0805, SOT23, SOD123 = pack.R0805, pack.C0805, pack.SOT23, pack.SOD123
C1206, FUSE1206, LRN6045, LQFP32 = pack.C1206, pack.FUSE1206, pack.LRN6045, pack.LQFP32
XH2, XH6, MH, TP = pack.XH2, pack.XH6, pack.MH, pack.TP
XH4 = "Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical"
TSOT23_6 = "Package_TO_SOT_SMD:TSOT-23-6"
SOT89 = "Package_TO_SOT_SMD:SOT-89-3"
SMB = "Diode_SMD:D_SMB"
# 1.5 mm2 / 1.7 mm drill: the ~3 A worst case at 2S empty is marginal on 1 mm2, and the 1.7 mm hole
# takes a common 14 AWG XT60 pigtail (L0.1, design doc "Parts").
PADS = "Connector_Wire:SolderWire-1.5sqmm_1x02_P6mm_D1.7mm_OD3mm"

# ref: (value, symbol "lib:name", footprint "lib:name")
PARTS = {
    # --- input: XT60 pigtail on solder pads, fuse, reverse P-FET, TVS ---
    "J_IN1": ("LIPO", "Connector_Generic:Conn_01x02", PADS),     # hand-soldered pigtail
    "F_IN1": ("5A fuse", "Device:Fuse", FUSE1206),
    "Q_REV1": ("AO3401A", "Transistor_FET:AO3401A", SOT23),      # VGS +-12 V: D_GZ1 is 10 V
    "R_REV1": ("100k", *R0805),
    "D_GZ1": ("MMSZ5240B", "Device:D_Zener", SOD123),            # 10 V VGS clamp
    "D_TVS1": ("SMBJ15A", "Device:D_Zener", SMB),                # unidirectional TVS
    "C_VIN1": ("10uF", *C0805),
    "C_VIN2": ("10uF", *C0805),
    "C_VIN3": ("10uF", *C0805),
    "C_VIN4": ("10uF", *C0805),
    # --- buck A: VIN -> 4.10 V VBAT_SW (Heltec battery socket, amp) ---
    "U_BA": ("TPS54302DDCR", "Regulator_Switching:TPS54302", TSOT23_6),
    "C_BTA": ("100nF", *C0805),
    "L_A": ("10uH 2A", "Device:L", LRN6045),
    "R_FBA1": ("30k", *R0805),
    "R_FBA2": ("5k1", *R0805),
    "C_OA1": ("22uF 25V", "Device:C", C1206),
    "C_OA2": ("22uF 25V", "Device:C", C1206),
    # --- buck B: VIN -> 5.07 V +5V (LCD, LEDs, buzzer) ---
    "U_BB": ("TPS54302DDCR", "Regulator_Switching:TPS54302", TSOT23_6),
    "C_BTB": ("100nF", *C0805),
    "L_B": ("10uH 2A", "Device:L", LRN6045),
    "R_FBB1": ("75k", *R0805),
    "R_FBB2": ("10k", *R0805),
    "C_OB1": ("22uF 25V", "Device:C", C1206),
    "C_OB2": ("22uF 25V", "Device:C", C1206),
    # --- enable: key pulls EN up through R_EN1, R_EN2 pulls it down, the MCU's kill FET overrides ---
    "J_KEY1": ("KEY", "Connector_Generic:Conn_01x02", XH2),
    "R_EN1": ("100k", *R0805),
    "R_EN2": ("47k", *R0805),       # 6 V -> 1.92 V, 13.05 V -> 4.17 V on EN
    "Q_KILL": ("BSS138", "Transistor_FET:BSS138", SOT23),
    "R_GK": ("100k", *R0805),       # gate pull-down: bucks on until the MCU latches them off
    "R_KILL": ("1k", *R0805),
    # --- always-on 3.3 V and the MCU ---
    "U_LDO": ("HT7533-1", "Regulator_Linear:HT75xx-1-SOT89", SOT89),
    "C_LDO1": ("10uF", *C0805),     # L0.1: HT75xx-1 typical application uses 10 uF in/out
    "C_LDO2": ("10uF", *C0805),
    "U_MCU": ("STM32C071KBTx", "MCU_ST_STM32C0:STM32C071KBTx", LQFP32),
    "C_MCU1": ("100nF", *C0805),
    "C_MCU2": ("4u7", *C0805),
    "C_NRST": ("100nF", *C0805),
    "R_BOOT": ("10k", *R0805),
    "TP_SWDIO": ("SWDIO", "Connector:TestPoint", TP),
    "TP_SWCLK": ("SWCLK/BOOT0", "Connector:TestPoint", TP),
    "TP_NRST": ("NRST", "Connector:TestPoint", TP),
    "TP_3V3": ("3V3", "Connector:TestPoint", TP),
    "TP_GND": ("GND", "Connector:TestPoint", TP),
    # --- balance lead: one 4-pin XH takes a 2S (3-pin) plug in pins 1-3; tap 3 then reads 0 V ---
    "J_BAL1": ("BAL", "Connector_Generic:Conn_01x04", XH4),
    "R_TT1": ("470k", *R0805), "R_TB1": ("1M", *R0805),        # x0.680
    "R_TT2": ("1M", *R0805), "R_TB2": ("470k", *R0805),        # x0.320
    "R_TT3": ("1M", *R0805), "R_TT3B": ("1M", *R0805),         # 2M top in two parts
    "R_TB3": ("470k", *R0805),                                  # x0.190
    "C_TAP1": ("100nF", *C0805), "C_TAP2": ("100nF", *C0805), "C_TAP3": ("100nF", *C0805),
    # --- out to the carrier (same pinout as the pack boards) ---
    "J_PWR1": ("PWR", "Connector_Generic:Conn_01x06", XH6),
}
for i in range(1, 5):
    PARTS[f"H{i}"] = ("M3", "Mechanical:MountingHole", MH)

DNP = set()
NOT_ASSEMBLED = {"J_IN1", "TP_SWDIO", "TP_SWCLK", "TP_NRST", "TP_3V3", "TP_GND"}
# Unused MCU pins (all but supply, NRST, 3 ADC, I2C slave, kill, SWD).
NC_PINS = {f"U_MCU.{p}" for p in (1, 2, 3, 10, 11, 12, *range(16, 24), *range(26, 33))}
NC_PARTS = set()

LCSC = {
    ("100nF", C0805[1]): "C49678",      # B YAGEO CC0805KRX7R9BB104
    ("10uF", C0805[1]): "C15850",       # B Samsung CL21A106KAYNNNE 25V X5R
    ("4u7", C0805[1]): "C1779",         # B Samsung CL21A475KAQNNNE 25V X5R
    ("22uF 25V", C1206): "C12891",      # B Samsung CL31A226KAHNNNE
    ("1M", R0805[1]): "C17514",         # B
    ("470k", R0805[1]): "C17709",       # B UNI-ROYAL 0805W8F4703T5E (2026-10-02)
    ("100k", R0805[1]): "C149504",      # B
    ("75k", R0805[1]): "C17819",        # P
    ("47k", R0805[1]): "C17713",        # B UNI-ROYAL 0805W8F4702T5E
    ("30k", R0805[1]): "C17621",        # B UNI-ROYAL 0805W8F3002T5E
    ("10k", R0805[1]): "C17414",        # B
    ("5k1", R0805[1]): "C27834",        # B
    ("1k", R0805[1]): "C17513",         # B
    ("5A fuse", FUSE1206): "C48332",    # E Bourns SF-1206F500-2
    ("AO3401A", SOT23): "C15127",       # B AOS AO3401A, VGS +-12 V (2026-10-02)
    ("MMSZ5240B", SOD123): "C19077425",  # P hongjiacheng MMSZ5240B 9.5-10.5 V (2026-10-02)
    ("SMBJ15A", SMB): "C19077569",      # P hongjiacheng SMBJ15A DO-214AA, 20k in stock (2026-10-02)
    ("TPS54302DDCR", TSOT23_6): "C311983",  # E TI TPS54302DDCR, 65k in stock (2026-10-02)
    ("10uH 2A", LRN6045): "C2046332",   # E Bourns SRN6045TA-100M, Isat 4.6 A (2026-10-02)
    ("BSS138", SOT23): "C7420339",      # P
    ("HT7533-1", SOT89): "C14289",      # B Holtek HT7533-1 SOT-89-3, 109k in stock (2026-10-02)
    ("STM32C071KBTx", LQFP32): "C42116633",  # E
    ("KEY", XH2): "C158012",            # E JST B2B-XH-A(LF)(SN)
    ("BAL", XH4): "C144395",            # E JST B4B-XH-A(LF)(SN), carrier part
    ("PWR", XH6): "C144397",            # E JST B6B-XH-A(LF)(SN)
}

# net: [ "REF.pin", ... ]
NETS = {
    "LIPO_RAW": ["J_IN1.1", "F_IN1.1"],
    "LIPO_F": ["F_IN1.2", "Q_REV1.3"],
    "REV_G": ["Q_REV1.1", "D_GZ1.2", "R_REV1.1"],
    "VIN": ["Q_REV1.2", "D_GZ1.1", "D_TVS1.1", "C_VIN1.1", "C_VIN2.1", "C_VIN3.1", "C_VIN4.1",
            "U_BA.3", "U_BB.3", "U_LDO.2", "C_LDO1.1", "R_EN1.1"],
    "KEY_IN": ["R_EN1.2", "J_KEY1.1"],
    "BUCK_EN": ["J_KEY1.2", "U_BA.5", "U_BB.5", "R_EN2.1", "Q_KILL.3"],
    "KILL_G": ["Q_KILL.1", "R_GK.2", "R_KILL.2"],
    "KILL_DRV": ["R_KILL.1", "U_MCU.15"],
    # buck A
    "SW_A": ["U_BA.2", "L_A.1", "C_BTA.2"],
    "BOOT_A": ["U_BA.6", "C_BTA.1"],
    "FB_A": ["U_BA.4", "R_FBA1.2", "R_FBA2.1"],
    "VBAT_SW": ["L_A.2", "R_FBA1.1", "C_OA1.1", "C_OA2.1", "J_PWR1.3"],
    # buck B
    "SW_B": ["U_BB.2", "L_B.1", "C_BTB.2"],
    "BOOT_B": ["U_BB.6", "C_BTB.1"],
    "FB_B": ["U_BB.4", "R_FBB1.2", "R_FBB2.1"],
    "+5V": ["L_B.2", "R_FBB1.1", "C_OB1.1", "C_OB2.1", "J_PWR1.4"],
    # MCU
    "+3V3": ["U_LDO.3", "C_LDO2.1", "U_MCU.4", "C_MCU1.1", "C_MCU2.1", "TP_3V3.1"],
    "NRST": ["U_MCU.6", "C_NRST.1", "TP_NRST.1"],
    "BOOT0": ["U_MCU.25", "R_BOOT.1", "TP_SWCLK.1"],
    "SWDIO": ["U_MCU.24", "TP_SWDIO.1"],
    "SDA_EXT": ["U_MCU.13", "J_PWR1.5"],     # slave 0x30, pull-ups on the carrier
    "SCL_EXT": ["U_MCU.14", "J_PWR1.6"],
    "GND": ["J_IN1.2", "R_REV1.2", "D_TVS1.2", "C_VIN1.2", "C_VIN2.2", "C_VIN3.2", "C_VIN4.2",
            "U_BA.1", "U_BB.1", "R_FBA2.2", "R_FBB2.2", "C_OA1.2", "C_OA2.2", "C_OB1.2", "C_OB2.2",
            "R_EN2.2", "Q_KILL.2", "R_GK.1",
            "U_LDO.1", "C_LDO1.2", "C_LDO2.2",
            "U_MCU.5", "C_MCU1.2", "C_MCU2.2", "C_NRST.2", "R_BOOT.2", "TP_GND.1",
            "J_BAL1.1", "R_TB1.2", "R_TB2.2", "R_TB3.2", "C_TAP1.2", "C_TAP2.2", "C_TAP3.2",
            "J_PWR1.1", "J_PWR1.2"],
}
# Balance taps: plug pin i+1 -> top resistor -> ADC node (bottom resistor + 100 nF) -> PA0..PA2.
NETS["BAL1"] = ["J_BAL1.2", "R_TT1.1"]
NETS["BAL2"] = ["J_BAL1.3", "R_TT2.1"]
NETS["BAL3"] = ["J_BAL1.4", "R_TT3.1"]
NETS["TAP3_MID"] = ["R_TT3.2", "R_TT3B.1"]
for i in (1, 2, 3):
    top = "R_TT3B.2" if i == 3 else f"R_TT{i}.2"
    NETS[f"TAP{i}_ADC"] = [top, f"R_TB{i}.1", f"C_TAP{i}.1", f"U_MCU.{6 + i}"]

# --- schematic layout (read by gen_sch.py) -----------------------------------------------------
# Input and the wide rails carry the Power class. The two SW nodes stay Default: the TSOT-23-6
# pads are 0.95 mm pitch, so a 0.8 mm track cannot leave the SW pin (L4.2, Freerouting left it
# unrouted). LIPO_* covers LIPO_RAW and LIPO_F.
NETCLASS_POWER = ("LIPO_*", "VIN", "VBAT_SW", "+5V")
# Rails drawn as power ports: +3V3 has the LDO's power_out, the rest take a PWR_FLAG.
RAILS = ("GND", "+3V3", "VIN", "VBAT_SW", "+5V")
PORT_LIB = {"GND": "power:GND", "+3V3": "power:+3V3", "VIN": "power:VDC",
            "VBAT_SW": "power:+BATT", "+5V": "power:+5V"}
_tags = pack._tags

BLOCKS = [
    {"title": "LiPo input: fuse, reverse FET, TVS", "at": (12.7, 12.7), "size": (127.0, 88.9),
     "parts": {"J_IN1": (12.7, 30.48, 0, None), "F_IN1": (35.56, 25.4, 0, None),
               "Q_REV1": (58.42, 30.48, 0, None), "R_REV1": (58.42, 55.88, 0, None),
               "D_GZ1": (76.2, 45.72, 0, None), "D_TVS1": (93.98, 45.72, 0, None),
               "C_VIN1": (106.68, 45.72, 0, None), "C_VIN2": (114.3, 45.72, 0, None),
               "C_VIN3": (106.68, 66.04, 0, None), "C_VIN4": (114.3, 66.04, 0, None)}},
    {"title": "Buck A 4.10 V (VBAT_SW), buck B 5.07 V (+5V)", "at": (152.4, 12.7),
     "size": (152.4, 139.7),
     "parts": {"U_BA": (30.48, 30.48, 0, None), "C_BTA": (55.88, 20.32, 0, None),
               "L_A": (76.2, 27.94, 0, None), "R_FBA1": (96.52, 38.1, 0, None),
               "R_FBA2": (96.52, 53.34, 0, None), "C_OA1": (114.3, 38.1, 0, None),
               "C_OA2": (127.0, 38.1, 0, None),
               "U_BB": (30.48, 91.44, 0, None), "C_BTB": (55.88, 81.28, 0, None),
               "L_B": (76.2, 88.9, 0, None), "R_FBB1": (96.52, 99.06, 0, None),
               "R_FBB2": (96.52, 114.3, 0, None), "C_OB1": (114.3, 99.06, 0, None),
               "C_OB2": (127.0, 99.06, 0, None)},
     "tags": _tags(["BUCK_EN"], 12.7, 127.0)},
    {"title": "Key enable, MCU kill, J_PWR1", "at": (12.7, 114.3), "size": (127.0, 88.9),
     "parts": {"J_KEY1": (12.7, 20.32, 0, None), "R_EN1": (35.56, 20.32, 0, None),
               "R_EN2": (55.88, 35.56, 0, None), "Q_KILL": (76.2, 40.64, 0, None),
               "R_GK": (66.04, 60.96, 0, None), "R_KILL": (50.8, 50.8, 0, None),
               "J_PWR1": (96.52, 35.56, 180, None)},
     "tags": _tags(["BUCK_EN", "KILL_DRV", "SDA_EXT", "SCL_EXT", "KILL_G", "GND"], 12.7, 76.2),
     "wired": {"GND"}},
    {"title": "Always-on 3V3, STM32C071, SWD pads", "at": (317.5, 12.7), "size": (139.7, 152.4),
     "parts": {"U_LDO": (30.48, 20.32, 0, None), "C_LDO1": (12.7, 30.48, 0, None),
               "C_LDO2": (50.8, 30.48, 0, None),
               "U_MCU": (60.96, 88.9, 0, None),
               "C_MCU1": (17.78, 58.42, 0, None), "C_MCU2": (17.78, 76.2, 0, None),
               "C_NRST": (17.78, 93.98, 0, None), "R_BOOT": (17.78, 111.76, 0, None),
               "TP_NRST": (106.68, 50.8, 0, None), "TP_SWCLK": (106.68, 60.96, 0, None),
               "TP_SWDIO": (106.68, 71.12, 0, None), "TP_3V3": (106.68, 81.28, 0, None),
               "TP_GND": (106.68, 91.44, 0, None)},
     "fields": {r: {"Reference": (5.08, -2.54, "left"), "Value": (5.08, 2.54, "left")}
                for r in ("TP_NRST", "TP_SWCLK", "TP_SWDIO", "TP_3V3", "TP_GND")},
     "tags": _tags(["TAP1_ADC", "TAP2_ADC", "TAP3_ADC", "KILL_DRV", "SDA_EXT", "SCL_EXT",
                    "NRST", "BOOT0", "SWDIO"], 12.7, 127.0, per_row=5)},
    {"title": "Balance lead dividers", "at": (152.4, 165.1), "size": (152.4, 76.2),
     "parts": {"J_BAL1": (22.86, 20.32, 180, None),
               "R_TT1": (40.64, 20.32, 0, None), "R_TB1": (40.64, 40.64, 0, None),
               "C_TAP1": (55.88, 40.64, 0, None),
               "R_TT2": (76.2, 20.32, 0, None), "R_TB2": (76.2, 40.64, 0, None),
               "C_TAP2": (91.44, 40.64, 0, None),
               "R_TT3": (111.76, 12.7, 0, None), "R_TT3B": (111.76, 27.94, 0, None),
               "R_TB3": (111.76, 45.72, 0, None), "C_TAP3": (127.0, 45.72, 0, None)},
     "tags": _tags(["TAP1_ADC", "TAP2_ADC", "TAP3_ADC", "TAP3_MID", "BAL1"], 12.7, 63.5)},
    {"title": "Mounting holes and power flags", "at": (317.5, 177.8), "size": (139.7, 50.8),
     "parts": {"H1": (7.62, 16.51, 0, None), "H2": (22.86, 16.51, 0, None),
               "H3": (38.1, 16.51, 0, None), "H4": (53.34, 16.51, 0, None)},
     "flags": [("GND", 10.16, 36.83), ("VIN", 33.02, 36.83), ("VBAT_SW", 55.88, 36.83),
               ("+5V", 78.74, 36.83)]},
]

# --- PCB (read by gen_pcb.py / route.py / check_gerbers.py) ------------------------------------
# 50 x 40 mm, single-side SMD on top. Left edge: the LiPo solder pads. Right edge: J_PWR1 and
# J_KEY1. Top edge: J_BAL1. Bucks in the middle with their input caps between them; MCU and
# dividers in the lower-left, away from the switch nodes.
W, H, CORNER = 70.0, 50.0, 2.0
NETCLASS_EXPECT = (("VIN", [0.8, 0.2]), ("VBAT_SW", [0.8, 0.2]), ("+5V", [0.8, 0.2]),
                   ("SW_A", [0.25, 0.2]), ("SW_B", [0.25, 0.2]),
                   ("GND", [0.25, 0.2]), ("SDA_EXT", [0.25, 0.2]))
DRC_RULES = {}
BOTTOM = set()
PLACE = {
    # board edge: LiPo pads left, balance lead top, carrier + key right, M3 holes at the corners
    "J_IN1": (5, 25, 90), "J_BAL1": (35, 4.5, 0),
    "J_KEY1": (66, 14, 90), "J_PWR1": (66, 33, 90),
    # input: fuse, reverse FET + gate clamp, TVS
    "F_IN1": (12, 18, 0), "Q_REV1": (17.5, 18, 0), "R_REV1": (12, 22, 0),
    "D_GZ1": (17.5, 22, 0), "D_TVS1": (24, 18, 0),
    # balance dividers along the top
    "R_TT1": (12, 10, 0), "R_TB1": (12, 14, 0), "C_TAP1": (16, 14, 0),
    "R_TT2": (24, 10, 0), "R_TB2": (24, 14, 0), "C_TAP2": (28, 14, 0),
    "R_TT3": (48, 10, 0), "R_TT3B": (48, 14, 0), "R_TB3": (52, 14, 0), "C_TAP3": (56, 14, 0),
    # buck A: VIN -> 4.10 V VBAT_SW
    "U_BA": (38, 22, 0), "C_BTA": (34, 18, 0),
    "C_VIN1": (33, 22, 0), "C_VIN2": (33, 26, 0),
    "L_A": (45, 27, 0), "R_FBA1": (39, 27, 0), "R_FBA2": (39, 31, 0),
    "C_OA1": (53, 22, 90), "C_OA2": (53, 29, 90),
    # buck B: VIN -> 5.07 V +5V
    "U_BB": (38, 41, 0), "C_BTB": (34, 37, 0),
    "C_VIN3": (33, 41, 0), "C_VIN4": (33, 45, 0),
    "L_B": (45, 46, 0), "R_FBB1": (39, 46, 0), "R_FBB2": (39, 48, 0),
    "C_OB1": (53, 41, 90), "C_OB2": (53, 47, 90),
    # enable: key pull-up, pull-down, MCU kill FET
    "R_EN1": (57, 20, 0), "R_EN2": (57, 25, 0), "Q_KILL": (61, 20, 0),
    "R_GK": (61, 25, 0), "R_KILL": (57, 30, 0),
    # always-on 3V3 and the MCU
    "U_LDO": (9, 36, 0), "C_LDO1": (9, 40, 0), "C_LDO2": (13.5, 40, 0),
    "U_MCU": (22, 44, 0), "C_MCU1": (14.5, 36, 0), "C_MCU2": (20, 36, 0),
    "C_NRST": (25.5, 36, 0), "R_BOOT": (30, 33, 0),
    "TP_SWDIO": (9.4, 44, 0), "TP_SWCLK": (12.1, 44, 0), "TP_NRST": (14.8, 44, 0),
    "TP_3V3": (9.4, 47, 0), "TP_GND": (12.1, 47, 0),
    "H1": (4.5, 4.5, 0), "H2": (65.5, 4.5, 0), "H3": (4.5, 45.5, 0), "H4": (65.5, 45.5, 0),
}
REF_AT = {"D_GZ1": (17.5, 24.5, 0), "D_TVS1": (24, 21.5, 0),
          "J_PWR1": (61, 33, 90), "J_KEY1": (61.5, 8, 90),
          "R_FBB2": (34, 48, 0),
          "C_LDO1": (9, 42.5, 0), "C_LDO2": (13.5, 42.5, 0),
          "C_NRST": (25.5, 38.2, 0), "U_MCU": (22, 44, 0)}
HIDE_REF = ("TP_SWDIO", "TP_SWCLK", "TP_NRST", "TP_3V3", "TP_GND")
LABELS = {}
TEXTS = [("AirsoftCounter v2 LiPo", 10, 2.5, 0, 1.0, True), ("2026-10", 10, 4.5, 0, 1.0, True),
         ("LIPO 2S/3S", 30, 25, 90, 0.8, False)]
GND_VIAS = []
HELTEC_PADS = {}
SIZE_MM = (W, H)
NPTH_XY = sorted((PLACE[r][0], PLACE[r][1]) for r in ("H1", "H2", "H3", "H4"))

MODULES = {}
VARIANTS = {"standard": set()}


def assembled(variant="standard"):
    """Refs JLCPCB places: everything except DNP parts, hand-soldered/off-board parts and holes."""
    return [r for r, (_, sym, _) in PARTS.items()
            if r not in DNP | NOT_ASSEMBLED and sym != "Mechanical:MountingHole"]


def check_power_path():
    """Input order and the EN wiring the latched cutoff depends on."""
    net_of = {p: n for n, m in NETS.items() for p in m}
    assert net_of["J_IN1.1"] == net_of["F_IN1.1"], "input + not on the fuse"
    assert net_of["J_IN1.2"] == "GND", "input - not on GND"
    assert net_of["F_IN1.2"] == net_of["Q_REV1.3"], "fuse not on the reverse FET drain"
    assert net_of["Q_REV1.1"] == net_of["D_GZ1.2"] == net_of["R_REV1.1"], "FET gate clamp"
    vin = net_of["Q_REV1.2"]
    assert vin == "VIN", "reverse FET source is not VIN"
    for p in ("D_TVS1.1", "D_GZ1.1", "U_BA.3", "U_BB.3", "U_LDO.2", "R_EN1.1"):
        assert net_of[p] == vin, f"{p} not on VIN"
    assert net_of["U_BA.5"] == net_of["U_BB.5"] == net_of["R_EN2.1"] == net_of["Q_KILL.3"], \
        "buck ENs not on one node with the pull-down and the kill FET"
    assert net_of["R_EN1.2"] == net_of["J_KEY1.1"] and net_of["J_KEY1.2"] == net_of["U_BA.5"], \
        "key does not switch the EN pull-up"
    assert net_of["L_A.2"] == "VBAT_SW" and net_of["L_B.2"] == "+5V", "buck outputs swapped"
    assert net_of["R_GK.1"] == "GND", "kill gate pull-down missing (bucks must default on)"
    for i in (1, 2, 3):
        assert net_of[f"J_BAL1.{i + 1}"] == net_of[f"R_TT{i}.1"], f"tap {i} divider not on the plug"
        assert net_of[f"U_MCU.{6 + i}"] == f"TAP{i}_ADC", f"tap {i} not on its ADC pin"


def check():
    import sys

    import board  # pyright: ignore[reportMissingImports]  # local sibling module
    board.check_structure(sys.modules[__name__])
    check_power_path()
    print(f"lipo ok: {len(PARTS)} parts, {len(NETS)} nets")


if __name__ == "__main__":
    check()
