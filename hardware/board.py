"""Pick the board module the generators work on: BOARD=carrier (default, design.py), pack (pack.py),
pack_b (pack_b.py, the no-pack-MCU variant), lipo (lipo.py, the 2S/3S LiPo power board), or the
hand-built TME variants carrier_tme / pack_tme / lipo_tme (nothing machine-placed).

Every generator imports the board as `from board import design`, so the same code
builds either board from its own data module.
"""
import importlib
import os

NAME = os.environ.get("BOARD", "carrier")
design = importlib.import_module({"carrier": "design", "pack": "pack", "pack_b": "pack_b",
                                "lipo": "lipo", "carrier_tme": "carrier_tme",
                                "pack_tme": "pack_tme", "lipo_tme": "lipo_tme"}[NAME])


def check_structure(m):
    """Board-independent checks on a board module (design.py or pack.py): unique pins, known
    parts, no single-pin nets, known DNP, no unconnected non-mechanical part, complete and
    non-stale LCSC for m.assembled(), and MODULES/VARIANTS naming known parts/modules."""
    pins = [p for members in m.NETS.values() for p in members]
    dupes = {p for p in pins if pins.count(p) > 1}
    assert not dupes, f"pin on several nets: {dupes}"
    for net, members in m.NETS.items():
        assert len(members) >= 2, f"{net} has a single pin"
        for p in members:
            assert p.split(".")[0] in m.PARTS, f"{net}: unknown part in {p}"
    assert set(m.DNP).issubset(m.PARTS), f"unknown DNP parts: {m.DNP - m.PARTS.keys()}"
    unused = [r for r in m.PARTS if m.PARTS[r][1] != "Mechanical:MountingHole"
              and not any(p.split(".")[0] == r for p in pins)]
    assert not unused, f"parts with no connections: {unused}"
    missing = sorted(r for r in m.assembled() if (m.PARTS[r][0], m.PARTS[r][2]) not in m.LCSC)
    assert not missing, f"assembled parts without an LCSC number: {missing}"
    stale = m.LCSC.keys() - {(m.PARTS[r][0], m.PARTS[r][2]) for r in m.assembled()}
    assert not stale, f"LCSC entries no assembled part uses: {stale}"
    for mod, refs in m.MODULES.items():
        assert refs <= m.PARTS.keys(), f"module {mod}: unknown parts {refs - m.PARTS.keys()}"
    for v, mods in m.VARIANTS.items():
        assert mods <= m.MODULES.keys(), f"variant {v}: unknown modules {mods - m.MODULES.keys()}"
    if hasattr(m, "TME"):
        # Hand-built board: nothing machine-placed, every bought part has a TME symbol.
        assert not m.LCSC and not m.assembled(), "TME board must have no LCSC parts / placements"
        bought = {(v, fp) for r, (v, sym, fp) in m.PARTS.items()
                  if sym != "Mechanical:MountingHole" and r not in m.DNP | m.NOT_TME}
        missing = sorted(k for k in bought if k not in m.TME)
        assert not missing, f"parts without a TME symbol: {missing}"
        stale = m.TME.keys() - bought
        assert not stale, f"TME entries no part uses: {stale}"


if __name__ == "__main__":
    import types
    bad = types.SimpleNamespace(PARTS={"R1": ("1k", "Device:R", "fp")}, NETS={"A": ["R1.1"]}, DNP=set(),
                                LCSC={}, MODULES={}, VARIANTS={"x": set()}, assembled=lambda v="x": ["R1"])
    try:
        check_structure(bad)
    except AssertionError as e:
        assert "single pin" in str(e), e
    else:
        raise SystemExit("check_structure accepted a single-pin net")

    bom = {"R1": ("1k", "Device:R", "fp"), "R2": ("2k", "Device:R", "fp")}
    nets = {"A": ["R1.1", "R2.1"]}

    def tme_ns(table):
        return types.SimpleNamespace(PARTS=bom, NETS=nets, DNP=set(), NOT_TME=set(), LCSC={},
                                     MODULES={}, VARIANTS={"x": set()}, TME=table,
                                     assembled=lambda v="x": [])

    check_structure(tme_ns({("1k", "fp"): "S1", ("2k", "fp"): "S2"}))   # complete table passes
    try:
        check_structure(tme_ns({("1k", "fp"): "S1"}))
    except AssertionError as e:
        assert "without a TME symbol" in str(e), e
    else:
        raise SystemExit("check_structure accepted a TME table missing a part")
    try:
        check_structure(tme_ns({("1k", "fp"): "S1", ("2k", "fp"): "S2", ("3k", "fp"): "S3"}))
    except AssertionError as e:
        assert "no part uses" in str(e), e
    else:
        raise SystemExit("check_structure accepted a stale TME entry")
    print("board.py self-check ok")
