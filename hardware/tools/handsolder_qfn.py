"""Generate local.pretty/QFN-24-1EP_4x4mm_P0.5mm_EP2.6x2.6mm_HandSolder.kicad_mod from KiCad's
Package_DFN_QFN:QFN-24-1EP_4x4mm_P0.5mm_EP2.6x2.6mm.

The BQ25601 is a 24-pin 0.5 mm QFN with an exposed pad: reflow-only as drawn. For an iron build the
numbered pads are lengthened EXT mm outward (the inner edge stays on the land pattern, so the
pad-to-pad gap and the 0.5 mm pitch are unchanged) and the exposed pad becomes a plated through-hole
so solder can be fed from the back. The courtyard grows by EXT on all sides.

Run: /usr/bin/python3 tools/handsolder_qfn.py   -> builds it, reloads it and self-checks.
"""
from pathlib import Path

import pcbnew  # pyright: ignore[reportMissingImports]

HERE = Path(__file__).resolve().parent
SRC_LIB = Path("/usr/share/kicad/footprints/Package_DFN_QFN.pretty")
SRC = "QFN-24-1EP_4x4mm_P0.5mm_EP2.6x2.6mm"
NAME = "QFN-24-1EP_4x4mm_P0.5mm_EP2.6x2.6mm_HandSolder"
DEST = HERE.parent / "local.pretty"
EXT = 0.6          # outward pad extension, mm
HOLE = 1.5         # through-hole through the exposed pad, mm
EP = 2.6           # exposed pad size, mm (2.6 x 2.6 mm per SLUSD90)
# Courtyard coordinates at or below this are the inner notch corners and must not move.
INNER_LIMIT = 2.0


def _load():
    return pcbnew.FootprintLoad(str(SRC_LIB), SRC)


def _outward(pad):
    """(axis, sign): the pad's long axis and the outward direction along it."""
    sz, pos = pad.GetSize(), pad.GetFPRelativePosition()
    if sz.x >= sz.y:
        return "x", 1 if pos.x > 0 else -1
    return "y", 1 if pos.y > 0 else -1


def _extend(pad):
    axis, sign = _outward(pad)
    sz, pos = pad.GetSize(), pad.GetFPRelativePosition()
    half, ext = pcbnew.FromMM(EXT / 2), pcbnew.FromMM(EXT)
    if axis == "x":
        pad.SetSize(pcbnew.VECTOR2I(sz.x + ext, sz.y))
        pad.SetFPRelativePosition(pcbnew.VECTOR2I(pos.x + sign * half, pos.y))
    else:
        pad.SetSize(pcbnew.VECTOR2I(sz.x, sz.y + ext))
        pad.SetFPRelativePosition(pcbnew.VECTOR2I(pos.x, pos.y + sign * half))


def _through_hole(ep):
    ep.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
    ep.SetShape(pcbnew.PAD_SHAPE_RECT)
    ep.SetSize(pcbnew.VECTOR2I_MM(EP, EP))
    ep.SetDrillSize(pcbnew.VECTOR2I_MM(HOLE, HOLE))
    ls = pcbnew.LSET()
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu, pcbnew.F_Mask, pcbnew.B_Mask):
        ls.AddLayer(layer)
    ep.SetLayerSet(ls)


def _grow_courtyard(fp):
    lim, ext = pcbnew.FromMM(INNER_LIMIT), pcbnew.FromMM(EXT)
    for g in fp.GraphicalItems():
        if g.GetLayer() != pcbnew.F_CrtYd:
            continue
        for getter, setter in ((g.GetStart, g.SetStart), (g.GetEnd, g.SetEnd)):
            v = getter()
            x = v.x + ext * (1 if v.x > 0 else -1) if abs(v.x) > lim else v.x
            y = v.y + ext * (1 if v.y > 0 else -1) if abs(v.y) > lim else v.y
            setter(pcbnew.VECTOR2I(x, y))


def _pin1_to_fab(fp):
    """The source's pin-1 silk triangle lands on the extended pads; put it on F.Fab so the fab
    print still shows orientation without a silk-over-mask DRC warning."""
    for g in fp.GraphicalItems():
        if g.GetLayer() == pcbnew.F_SilkS and g.GetShape() == pcbnew.SHAPE_T_POLY:
            g.SetLayer(pcbnew.F_Fab)


def build():
    pcbnew.KIID.SeedGenerator(1)   # deterministic uuids across runs, so the file does not churn
    fp = _load()
    numbered = [p for p in fp.Pads() if p.GetNumber().isdigit()]
    assert len(numbered) == 25, f"expected 24 edge pads + exposed pad, got {len(numbered)}"
    for p in numbered:
        if p.GetNumber() != "25":
            _extend(p)
    _through_hole(next(p for p in numbered if p.GetNumber() == "25"))
    _grow_courtyard(fp)
    _pin1_to_fab(fp)
    fp.SetLibDescription(
        "QFN-24 4x4 mm 0.5 mm pitch, hand-solder variant: pads extended 0.6 mm outward for drag "
        "soldering, exposed pad as a 1.5 mm plated hole to fill from the back. Flux, drag the pad "
        "ends, then solder the exposed pad through the hole. (The source's four paste-only "
        "apertures over the exposed pad are kept; there is no stencil in a hand build.)")
    fp.SetFPID(pcbnew.LIB_ID("local", NAME))
    DEST.mkdir(exist_ok=True)
    out = DEST / f"{NAME}.kicad_mod"
    pcbnew.FootprintSave(str(DEST), fp)   # returns None in this SWIG build; check the file
    assert out.stat().st_size > 0, f"FootprintSave wrote nothing for {NAME}"
    return fp


def _edges(pad):
    """(inward edge, outward edge) along the pad's long axis."""
    axis, sign = _outward(pad)
    sz, pos = pad.GetSize(), pad.GetFPRelativePosition()
    c, h = (pos.x, sz.x / 2) if axis == "x" else (pos.y, sz.y / 2)
    return c - sign * h, c + sign * h


def _cross(pad):
    """(width across the pad's side, centre coordinate along that side)."""
    axis, _ = _outward(pad)
    sz, pos = pad.GetSize(), pad.GetFPRelativePosition()
    return (sz.y, pos.y) if axis == "x" else (sz.x, pos.x)


def check():
    src = {p.GetNumber(): p for p in _load().Pads() if p.GetNumber().isdigit()}
    dst = {p.GetNumber(): p for p in pcbnew.FootprintLoad(str(DEST), NAME).Pads()
           if p.GetNumber().isdigit()}
    assert set(dst) == set(src), f"pad set changed: {set(src) ^ set(dst)}"
    ext = pcbnew.FromMM(EXT)
    for n in (str(i) for i in range(1, 25)):
        s, d = src[n], dst[n]
        assert d.GetAttribute() == pcbnew.PAD_ATTRIB_SMD, f"pad {n} is not SMD"
        ds, ss = d.GetSize(), s.GetSize()
        assert max(ds.x, ds.y) - max(ss.x, ss.y) == ext, f"pad {n} not extended by {EXT} mm"
        assert min(ds.x, ds.y) == min(ss.x, ss.y), f"pad {n} grew on the wrong axis"
        sin, sout = _edges(s)
        din, dout = _edges(d)
        assert din == sin, f"pad {n} inner edge moved"
        assert abs(dout) - abs(sout) == ext, f"pad {n} outer edge not {EXT} mm beyond the source"
    for a, b in ((1, 2), (7, 8)):
        wa, ca = _cross(dst[str(a)])
        wb, cb = _cross(dst[str(b)])
        sa, sca = _cross(src[str(a)])
        sb, scb = _cross(src[str(b)])
        assert (wa, wb) == (sa, sb), f"pad {a}/{b} side width changed"
        assert abs(cb - ca) == abs(scb - sca), f"pad {a}/{b} pitch changed"
    ep = dst["25"]
    assert ep.GetAttribute() == pcbnew.PAD_ATTRIB_PTH, "exposed pad is not through-hole"
    assert ep.GetDrillSize() == pcbnew.VECTOR2I_MM(HOLE, HOLE), "exposed-pad drill is not 1.5 mm"
    assert ep.GetSize() == pcbnew.VECTOR2I_MM(EP, EP), "exposed pad is not 2.6 x 2.6 mm"
    assert not ep.IsOnLayer(pcbnew.F_Paste), "exposed pad still has paste"
    silk_polys = [g for g in pcbnew.FootprintLoad(str(DEST), NAME).GraphicalItems()
                  if g.GetLayer() == pcbnew.F_SilkS and g.GetShape() == pcbnew.SHAPE_T_POLY]
    assert not silk_polys, "pin-1 silk marker still over the extended pads"


if __name__ == "__main__":
    build()
    check()
    print("handsolder_qfn ok")
