"""Merge the TME Quick Buy lists of the boards being built into one order list.

fab/<board>/tme_bom.csv -> fab/tme_bom_all.csv  "TME symbol;qty" per line, no header: the same format
                                           TME's Quick Buy > "Upload from file" takes, with the
                                           quantities of a symbol used by several boards added up,
                                           plus spares for small passives (lost to the tweezers),
                                           rounded up to TME's order multiple.

carrier/carrier_tme, pack/pack_b/pack_tme and lipo/lipo_tme are alternative builds of the same
board, so name one build per board; the default is the TME hand-build set. Budget variants
(tme_bom_budget.csv) and the off-board lists (fab/offboard/) are left out: upload those separately.

/usr/bin/python3 tme_all.py [board ...]   (after `make boards`; default carrier_tme pack_tme lipo_tme)
"""
import math
import sys
from pathlib import Path

FAB = Path(__file__).parent / "fab"
OUT = FAB / "tme_bom_all.csv"
DEFAULT = ["carrier_tme", "pack_tme", "lipo_tme"]
# Symbol prefix -> TME order multiple (= minimum). SMD0805-10K-1% checked 2026-10-02 (100/100); the
# rest of the Royalohm cut-tape family is assumed the same. Anything not listed is ordered as-is
# (MOQ 1 for the parts checked: BSS138LT1G, CL21A106KAYNNNE, INA228AIDGSR).
MULTIPLE = {"SMD0805-": 100, "SMD1206-": 100}
# Small passives get +10 %, at least +5: easy to lose, cheap to over-buy.
SPARE = ("SMD0805-", "SMD1206-", "CL21", "CL31", "CC0805", "NTCS")


def merge(texts, names=None):
    """Sum "symbol;qty" lines across texts, one "symbol;qty" line per symbol, sorted."""
    qty = {}
    for i, text in enumerate(texts):
        for k, line in enumerate(text.splitlines(), 1):
            if line.strip():
                symbol, _, n = line.rpartition(";")
                if not symbol or not n.strip().isdigit():
                    raise SystemExit(f"tme_all: {names[i] if names else i}:{k}: not 'symbol;qty': {line!r}")
                qty[symbol] = qty.get(symbol, 0) + int(n)
    return "".join(f"{s};{n}\n" for s, n in sorted(qty.items()))


def order(symbol, n):
    """Quantity to order for n fitted parts: spares for small passives, rounded up to TME's multiple."""
    if symbol.startswith(SPARE):
        n += max(5, math.ceil(n / 10))
    m = next((m for p, m in MULTIPLE.items() if symbol.startswith(p)), 1)
    return math.ceil(n / m) * m


def main():
    boards = sys.argv[1:] or DEFAULT
    boms = [FAB / "tme_bom.csv" if b == "carrier" else FAB / b / "tme_bom.csv" for b in boards]
    missing = [str(p) for p in boms if not p.is_file()]
    if missing:
        raise SystemExit(f"tme_all: missing {', '.join(missing)} (run `make boards` first)")
    merged = merge([p.read_text() for p in boms], boms)
    merged = "".join(f"{s};{order(s, int(n))}\n" for s, n in (l.rsplit(";", 1) for l in merged.splitlines()))
    OUT.write_text(merged)
    print(f"tme_all ok: {' + '.join(boards)} -> {OUT} ({len(merged.splitlines())} TME lines)")


if __name__ == "__main__":
    assert merge(["A;1\nB;2\n", "A;3\nB;1\nC;1\n"]) == "A;4\nB;3\nC;1\n"  # same symbol added up
    assert merge(["A;2\n"]) == merge(["A;1\n", "A;1\n"])                   # split across boards
    assert merge(["A;1\n\n B-x (Y);2 \n"]) == " B-x (Y);2\nA;1\n"          # blanks skipped, spaces kept
    assert merge(["A=B;1\n"]) == "A=B;1\n"                                  # symbols may hold '=' etc.
    assert order("SMD0805-10K-1%", 17) == 100                                 # spares, then the 100 multiple
    assert order("SMD0805-10K-1%", 95) == 200                                 # 95 + 10 spares -> 2 packs
    assert order("CL21A106KAYNNNE", 14) == 19 and order("CL21A106KAYNNNE", 80) == 88
    assert order("INA228AIDGSR", 4) == 4                                      # ICs exact
    try:
        merge(["A;x\n"])
        raise AssertionError("bad qty accepted")
    except SystemExit:
        pass
    main()
