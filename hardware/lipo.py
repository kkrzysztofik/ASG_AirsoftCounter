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
    "Q_REV1": ("AO3407A", "Transistor_FET:AO3401A", SOT23),      # same G-S-D pinout (L0.1)
    "R_REV1": ("100k", *R0805),
    "D_GZ1": ("BZT52C12", "Device:D_Zener", SOD123),             # VGS clamp
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
    ("AO3407A", SOT23): "C15155",       # E AOS AO3407A, 128k in stock (2026-10-02)
    ("BZT52C12", SOD123): "C43491",     # E BZT52C12 SOD-123 (2026-10-02; no Basic/Preferred 12 V)
    ("SMBJ15A", SMB): "C113988",        # E SMBJ15A DO-214AA, 135k in stock (2026-10-02)
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
