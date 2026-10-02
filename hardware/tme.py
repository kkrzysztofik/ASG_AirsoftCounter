"""Write TME (tme.eu) Quick Buy lists from the JLCPCB BOMs, for buying a board's parts at TME.

$FAB/jlc_bom[_<variant>].csv -> $FAB/tme_bom[_<variant>].csv    "TME symbol;qty" per line, no header:
                                                                the format TME's Quick Buy > "Upload
                                                                from file" takes (help/1753).
                             -> $FAB/tme_other[_<variant>].csv  parts TME does not sell: LCSC number,
                                                                maker part, qty. Buy those at LCSC.

Symbols were looked up in the TME catalogue on 2026-10-02 (stock was not checked). Where TME lacks
the exact LCSC part, the comment names the substitute and why it fits the same footprint.

/usr/bin/python3 tme.py [boards]   (after jlc.py; boards multiplies every quantity, default 1)
"""
import csv
import os
import sys
from pathlib import Path

import board  # pyright: ignore[reportMissingImports]

HERE = Path(__file__).parent
FAB = HERE / os.environ.get("FAB", "fab")

# LCSC number -> TME symbol. Same maker part unless a comment says otherwise.
# Royalohm resistors use TME's cut-tape SMD0805-*/SMD1206-* symbols (0805S8F/1206S4J, 100 pcs): the
# 0805W8F.../1206W4F... symbols are the same parts sold only as 5000 pcs reels (checked 2026-10-02).
TME = {
    "C105362": "ERJ8BWFR010V",          # sub: Panasonic 10 mOhm 1206 0.5 W 1 % (PSA FMF06FTHR010 not at TME)
    "C12891": "CL31A226KAHNNNE",
    "C144395": "B4B-XH-A (LF)(SN)",
    "C144397": "B6B-XH-A",
    "C149504": "SMD0805-100K-1%",       # Uni-Royal is Royalohm at TME
    "C15008": "CL31A107MQHNNNE",
    "C15127": "AO3401A",
    "C158012": "B2B-XH-A (LF)(SN)",
    "C15850": "CL21A106KAYNNNE",
    "C17414": "SMD0805-10K-1%",
    "C17415": "SMD0805-10R-1%",
    "C17477": "SMD0805-0R",
    "C17513": "SMD0805-1K-1%",
    "C17514": "SMD0805-1M-1%",
    "C17621": "SMD0805-30K-1%",
    "C17673": "SMD0805-4K7-1%",
    "C17709": "SMD0805-470K-1%",
    "C17713": "SMD0805-47K-1%",
    "C1779": "CL21A475KAQNNNE",
    "C17819": "SMD0805-75K-1%",
    "C17888": "SMD1206-0R",             # 1206S4J0000T5E: Royalohm 1206 jumper, 2 A <50 mOhm like W4F
    "C19077425": "MMSZ5240BT1G",        # onsemi, SOD-123
    "C19077569": "SMBJ15A-TSC",         # Taiwan Semi, unidirectional SMB
    "C2046332": "SRN6045100M-BOU-0",    # plain SRN6045-100M (TA not at TME); 1000 pcs minimum
    "C22374899": "1206L200PR",          # sub: Littelfuse 2 A hold 1206 PTC; check its Vmax covers SYS (~4.6 V)
    "C2297": "KP-2012SGC",              # sub: Kingbright green 0805
    "C2894897": "USB4105-GF-A",         # sub: GCT 16P; KiCad's USB4105 land pattern has the HCTL pad centres,
                                        # holes and pin map; its rear stake (~0.8 mm) fits the 0.6 x 1.2 mm slot
    "C14289": "MCP1703AT-3302E/MB",     # sub: same SOT-89 pinout (1 GND, 2 VIN, 3 VOUT), 2 uA Iq, stable with
                                        # the 10 uF caps; but 16 V operating / 18 V abs max vs HT7533's 30 V,
                                        # so less margin above the SMBJ15A clamp
    "C27834": "SMD0805-5K1-1%",
    "C28323": "CL21B105KAFNNNE",        # sub: 25 V (50 V not at TME); every 1uF sits on <= 5 V
    "C2905422": "ZL262-18SG",           # sub: Connfly 1x18 2.54 mm socket, 8.5 mm like the Kinghelm H8.5
    "C311983": "TPS54302DDCR",
    "C37593": "ADS1115IDGSR",
    "C468236": "BQ25601RTWT",           # same die as RTWR, small reel
    "C48332": "C1F-5",                  # sub: Bel 0685F5000-01 5 A fast, I2t 0.83 A2s (Bourns: 5000 reel)
    "C49678": "CC0805KRX7R9BB104",
    "C53134": "CL21B473KBCNNNC",
    "C5446": "XC6206P332MR-G",
    "C623960": "PAC1934T-I/JQ",
    "C703084": "DFE322520FD-1R5M=P2",   # sub: Murata 1.5 uH 1210, 2.0 mm tall (the 1.2 mm one is not at TME)
    "C7420339": "BSS138LT1G",           # onsemi SOT-23
    "C783615": "TCA9534PWR",
    "C81598": "1N4148W-DIO",            # Diotec SOD-123
    "C84256": "KP-2012EC",              # sub: Kingbright red 0805
    "C8598": "1N5819HW-7-F",            # sub: Diodes 1 A 40 V Schottky SOD-123 (B5819W not at TME)
    "C8678": "SSA34-E3/61T",            # sub: Vishay SMA 40 V 3 A (TME's SS34s are SMC or out)
    "C96123": "CL31A476MPHNNNE",
}
# Not at TME (searched 2026-10-02): buy at LCSC. Maker part for the tme_other list.
OTHER = {
    "C42116633": "STM32C071KBT6",       # TME: only the LQFP-48 CBT6; the C031K6T6 shares the LQFP-32 pinout
                                        # but has no I2C2 on PA6/PA7 (the LiPo board's slave port) and no USB
    "C720477": "TS-1088-AR02016",       # no 2-pad 3.9 x 3 mm tact switch at TME
    "C84817": "MT3608",                 # no SOT-23-6 boost with its pinout at TME
    "C910588": "NS4168",                # no pin-compatible I2S amp at TME
}
# Hand-soldered parts (NOT_ASSEMBLED, so not in the JLC BOM) that TME sells, per board (FAB dir name).
HAND = {
    # TH_CHG: 10k B3435 NTC. TME has no 0805 one; the 0603 hand-solders onto the 0805 pads.
    "pack": [("NTCS0603E3103FLT", 1)],
    "pack_b": [("NTCS0603E3103FLT", 1)],
}


def from_lcsc(lcsc_table, keys):
    """TME symbols for the (value, footprint) keys a JLC module already maps to LCSC numbers."""
    return {k: TME[lcsc_table[k]] for k in keys if k in lcsc_table and lcsc_table[k] in TME}


def main():
    boards = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    board_name = os.environ.get("BOARD", "")
    if board_name.endswith("_tme"):
        qty = {}
        for r, (v, sym, fp) in board.design.PARTS.items():
            if sym != "Mechanical:MountingHole" and r not in board.design.DNP | board.design.NOT_TME:
                qty[board.design.TME[(v, fp)]] = qty.get(board.design.TME[(v, fp)], 0) + boards
        (FAB / "tme_bom.csv").write_text("".join(f"{s};{n}\n" for s, n in sorted(qty.items())))
        print(f"tme ok ({board_name}): {len(qty)} TME lines")
        return
    boms = sorted(FAB.glob("jlc_bom*.csv"))
    if not boms:
        sys.exit(f"tme: no jlc_bom*.csv in {FAB} (run jlc.py first)")
    for bom in boms:
        tme, other = [], []
        try:
            with open(bom, newline="") as f:
                rows = list(csv.DictReader(f))
        except OSError as e:
            sys.exit(f"tme: cannot read {bom}: {e}")
        for row in rows:
            lcsc, qty = row["LCSC Part #"], len(row["Designator"].split(",")) * boards
            if lcsc in TME:
                tme.append(f"{TME[lcsc]};{qty}\n")
            elif lcsc in OTHER:
                other.append([lcsc, OTHER[lcsc], qty])
            else:
                sys.exit(f"tme: {bom.name}: {lcsc} ({row['Comment']}) has no TME symbol; add it to tme.py")
        tme += [f"{sym};{qty * boards}\n" for sym, qty in HAND.get(FAB.name, [])]
        suffix = bom.name.removeprefix("jlc_bom")
        (FAB / f"tme_bom{suffix}").write_text("".join(tme))
        try:
            with open(FAB / f"tme_other{suffix}", "w", newline="") as f:
                csv.writer(f, lineterminator="\n").writerows([["LCSC Part #", "Part", "Qty"], *other])
        except OSError as e:
            sys.exit(f"tme: cannot write {FAB}/tme_other{suffix}: {e}")
        print(f"tme ok ({bom.name}): {len(tme)} TME lines, {len(other)} parts to buy elsewhere")


if __name__ == "__main__":
    assert from_lcsc({("1k", "fp"): "C17513"}, {("1k", "fp")}) == {("1k", "fp"): TME["C17513"]}
    assert from_lcsc({("1k", "fp"): "C999999"}, {("1k", "fp")}) == {}          # unknown LCSC
    assert from_lcsc({("1k", "fp"): "C17513"}, {("2k", "fp")}) == {}          # key not in table
    main()
