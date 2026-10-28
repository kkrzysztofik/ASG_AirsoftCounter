"""AirsoftCounter pack board, XIAO ESP32-S3 variant assembled by JLCPCB.

Derived from pack_xiao.py by import and edit: same circuit, outline (96x112, notch, cutout) and
layout, with the iron-only choices pack_tme made put back to pack.py's reflow parts:
BQ25601RTWR on the standard QFN (no EP hole), MT3608 boost + SS34 catch diode + 10 uH (MCP1640
had 94 pcs at JLC), 22 uF 25 V boost caps and 1M gate pull-ups (the 16 V caps and 240k were
TME tape savings). The 4 INA226 stay (cheaper than one PAC1934 at JLC, 2026-10-28). The board
USB-C only charges (the XIAO has its own), so it is a 6-pin power-only receptacle.
Hand-soldered after assembly: the XIAO (no JLC stock), holders, bead NTCs, TH_CHG.
gen_sch.py / gen_pcb.py read it through board.py (`make BOARD=pack_xiao_jlc ...`). Run this file
to self-check.
"""
import board
import pack
import pack_tme
import pack_xiao

# Everything pack_xiao defines, minus its hand-build (TME) tables; the edits follow.
globals().update({k: v for k, v in vars(pack_xiao).items()
                  if k.isupper() and k not in ("NAME", "TITLE", "TME", "NOT_TME")})

NAME = "pack_xiao_jlc"
TITLE = "AirsoftCounter v2 pack (XIAO, JLCPCB assembly)"

USB6P = ("TYPE-C 6P", "Connector:USB_C_Receptacle_PowerOnly_6P", "usbc6p:TYPE-C-6P_C456012")
BOOST = ("U1", "D1")   # pack.py's MT3608 + catch diode: their nets come back from pack.NETS

PARTS = dict(pack_xiao.PARTS)
for _r in ("U_CHG", "U1", "D1", "L1", "R_FB2", "TH_CHG", "C_IN1", "C_OUT1", "C_OUT2",
           *(f"R_GS{i}" for i in range(1, 5))):
    PARTS[_r] = pack.PARTS[_r]
PARTS["J_USB1"] = USB6P

_USB_GONE = {f"J_USB1.{p}" for p in ("A1", "B1", "A4", "B4", "A6", "B6", "A7", "B7")}  # not on a 6P
NETS = {n: [p for p in mem if p.split(".")[0] not in BOOST and p not in _USB_GONE]
        for n, mem in pack_xiao.NETS.items()}
for _n, _mem in pack.NETS.items():
    if _boost_pins := [p for p in _mem if p.split(".")[0] in BOOST]:
        NETS[_n] = NETS[_n] + _boost_pins   # KeyError = pack_xiao renamed a boost net
NC_PINS = (pack_xiao.NC_PINS - _USB_GONE) | {p for p in pack.NC_PINS if p.split(".")[0] in BOOST}

DNP = set(pack_xiao.DNP)
NOT_ASSEMBLED = set(pack_xiao.NOT_ASSEMBLED) | {"U_MCU", "TH_CHG"}
LCSC = {**pack.LCSC,
        ("INA226AIDGSR", pack_tme.VSSOP10): "C49851",   # TI, Extended, 46k stock 2026-10-28
        USB6P[::2]: "C456012"}                           # SHOU HAN TYPE-C 6P, Extended, 705k stock
LCSC = {k: v for k, v in LCSC.items()
        if any((p[0], p[2]) == k for r, p in PARTS.items() if r not in DNP | NOT_ASSEMBLED)}

PTH_COMPONENT_MIN = 0.6   # the 6P's shield slots; the USB4085's 0.4 mm pins are gone

KIID_SEED = 5   # gen_pcb: footprint order the autorouter sees
PLACE = dict(pack_xiao.PLACE)
PLACE["D1"] = pack.PLACE["D1"]
# Mouth where pack.py's HC-16P had it: (90, 23, 90) + its 3.675 body half-length = x 93.675;
# the 6P's mouth is 4.62 in front of its origin.
PLACE["J_USB1"] = (93.675 - 4.62, 23.0, 90)

# The boost block is drawn on the root sheet (as in pack.py), so D1 goes on both.
BLOCKS = [dict(b, parts=dict(b["parts"])) for b in pack_xiao.BLOCKS]
_boost = next(b for b in BLOCKS if "U1" in b["parts"])
_boost["parts"]["D1"] = next(b for b in pack.BLOCKS if "D1" in b["parts"])["parts"]["D1"]
ROOT = dict(pack_xiao.ROOT, parts={**pack_xiao.ROOT["parts"], "D1": pack.ROOT["parts"]["D1"]})


def assembled(variant="standard"):
    """Refs JLCPCB places: everything except DNP parts, hand-soldered parts and holes."""
    return [r for r, (_, sym, _) in PARTS.items()
            if r not in DNP | NOT_ASSEMBLED and sym != "Mechanical:MountingHole"]


def check_jlc():
    """XIAO pin roles as pack_xiao, boost wired as pack, the USB-C power-only."""
    net_of = {p: n for n, mem in NETS.items() for p in mem}
    for p, n in pack_xiao.MCU.items():
        assert net_of.get(f"U_MCU.{p}") == n, f"U_MCU.{p} on {net_of.get(f'U_MCU.{p}')}, want {n}"
    for n, mem in pack.NETS.items():
        for p in mem:
            if p.split(".")[0] in BOOST:
                assert net_of.get(p) == n, f"{p} on {net_of.get(p)}, want {n} (pack.py)"
    assert "U_MCU.23" in NC_PINS, "XIAO BAT+ is back-driven to ~3.3 V: it must stay unconnected"
    assert not NC_PINS & net_of.keys(), f"NC pins on nets: {NC_PINS & net_of.keys()}"
    assert {net_of[f"J_USB1.{p}"] for p in ("A9", "B9")} == {"VBUS"}
    assert (net_of["J_USB1.A5"], net_of["J_USB1.B5"]) == ("CC1", "CC2")
    assert "U_MCU" in NOT_ASSEMBLED, "the XIAO has no JLC stock: hand-soldered"


def check():
    import sys

    this = sys.modules[__name__]
    board.check_structure(this)
    pack_tme.check_branches(this)
    check_jlc()
    pack_xiao.check_posts()
    pack.check_sheets(this)
    print(f"pack_xiao_jlc ok: {len(PARTS)} parts, {len(NETS)} nets, {len(assembled())} placed")


if __name__ == "__main__":
    check()
