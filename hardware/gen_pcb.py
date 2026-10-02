"""Generate <BOARD>.kicad_pcb (placed, unrouted) from the BOARD module (board.py).

Origin top-left, X right, Y down, mm. Design rules and net classes live in
<BOARD>.kicad_pro (written by gen_sch.py); the board is saved beside it without
touching it, then reloaded to check KiCad resolves the classes.
Run: /usr/bin/python3 gen_pcb.py
"""
from pathlib import Path

import pcbnew  # pyright: ignore[reportMissingImports]

import gen_sch
from board import design  # pyright: ignore[reportMissingImports]

HERE = Path(__file__).parent
PCB = HERE / f"{design.NAME}.kicad_pcb"
FPDIR = Path("/usr/share/kicad/footprints")
# GND pour pad connection; route.py (A6) reuses it for the F.Cu pour. Solid, not thermal
# reliefs: reliefs starved J2.1/J3.1/XH GND pins. Cost: harder hand-soldering of THT GND pins.
GND_PAD_CONNECTION = pcbnew.ZONE_CONNECTION_FULL
def mm(x, y):
    return pcbnew.VECTOR2I_MM(x, y)


def layers(*ids):
    ls = pcbnew.LSET()
    for i in ids:
        ls.AddLayer(i)
    return ls


def unconnected_nets():
    """KiCad puts every unused symbol pin on its own net "unconnected-(REF-PinName-PadN)"; mirror it for parity."""
    used = {p for members in design.NETS.values() for p in members}
    out = {}
    for ref, (_, lib_id, _) in design.PARTS.items():
        for body in gen_sch.unit_bodies(gen_sch.flat_symbol(*lib_id.split(":"))):
            for pin in gen_sch.kids(body, "pin"):
                n, name = (gen_sch.unq(gen_sch.child(pin, k)[1]) for k in ("number", "name"))
                if f"{ref}.{n}" not in used:
                    # KiCad escapes "/" in a pin name as "{slash}" when it names an unconnected net
                    out[f"{ref}.{n}"] = f"unconnected-({ref}-{name.replace('/', '{slash}')}-Pad{n})"
    return out


def footprint(board, ref, nets):
    value, _, fpid = design.PARTS[ref]
    lib, name = fpid.split(":")
    # "local" is the project footprint library (fp-lib-table) for parts KiCad does not ship
    fp = pcbnew.FootprintLoad(str(HERE / "local.pretty" if lib == "local" else FPDIR / f"{lib}.pretty"), name)
    if fp is None:
        raise SystemExit(f"{ref}: footprint {fpid} not found")
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    fp.SetReference(ref)
    fp.SetValue(value)
    fp.Reference().SetTextSize(mm(0.8, 0.8))
    fp.Reference().SetTextThickness(pcbnew.FromMM(0.15))
    x, y, rot = design.PLACE[ref]
    fp.SetPosition(mm(x, y))
    fp.SetOrientationDegrees(rot)
    if lib == "MountingHole":
        fp.Reference().SetVisible(False)  # would sit off-board
    if ref in getattr(design, "HIDE_REF", ()):
        fp.Reference().SetVisible(False)  # named by its value text instead (test pads)
    if rot == 180:  # keep the reference above the part, as at rot 0
        r, o = fp.Reference().GetPosition(), fp.GetPosition()
        fp.Reference().SetPosition(pcbnew.VECTOR2I(2 * o.x - r.x, 2 * o.y - r.y))
    # Any footprint's plated holes under the via drill become vias (JLCPCB's 2-layer minimum is
    # 0.3 mm). Today that is only U3's 0.2 mm thermal vias.
    drill, dia = gen_sch.VIA["via_drill"], gen_sch.VIA["via_diameter"]
    for p in fp.Pads():
        if p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH and p.GetDrillSize().x < pcbnew.FromMM(drill):
            p.SetDrillSize(mm(drill, drill))
            p.SetSize(pcbnew.F_Cu, mm(dia, dia))
    if ref in design.REF_AT:
        rx, ry, rrot = design.REF_AT[ref]
        fp.Reference().SetPosition(mm(rx, ry))
        fp.Reference().SetTextAngleDegrees(rrot)
    # links the footprint to its schematic symbol (gen_sch's deterministic uuid)
    fp.SetPath(pcbnew.KIID_PATH("/" + gen_sch.unq(gen_sch.uid(f"sym/{ref}"))))
    fp.SetSheetname("/")
    fp.SetSheetfile(f"{design.NAME}.kicad_sch")
    if ref in design.DNP:
        fp.SetDNP(True)
    if ref in design.DNP or ref in getattr(design, "NOT_ASSEMBLED", set()):
        fp.SetExcludedFromBOM(True)  # must agree with the symbol's in_bom or DRC flags a mismatch
    board.Add(fp)
    if ref in getattr(design, "BOTTOM", ()):  # mirrored onto B.Cu about its own centre (needs the board)
        fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    pads = {}
    for p in fp.Pads():
        pads.setdefault(p.GetNumber(), []).append(p)
    for member, net in nets.items():
        r, n = member.split(".")
        if r != ref:
            continue
        if n not in pads:
            raise SystemExit(f"{member} ({net}): no pad {n} on {fpid} (has {sorted(pads)})")
        for p in pads[n]:
            p.SetNet(board.FindNet(net))
    return fp


def outline(board):
    r = design.CORNER
    segs = [((r, 0), (design.W - r, 0)), ((design.W, r), (design.W, design.H - r)),
            ((design.W - r, design.H), (r, design.H)), ((0, design.H - r), (0, r))]
    k = r * (1 - 0.5 ** 0.5)  # 45-degree point on each corner arc
    arcs = [((design.W - r, 0), (design.W - k, k), (design.W, r)),
            ((design.W, design.H - r), (design.W - k, design.H - k), (design.W - r, design.H)),
            ((r, design.H), (k, design.H - k), (0, design.H - r)), ((0, r), (k, k), (r, 0))]
    for a, b in segs:
        s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(mm(*a))
        s.SetEnd(mm(*b))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(pcbnew.FromMM(0.05))
        board.Add(s)
    for a, m, b in arcs:
        s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_ARC)
        s.SetArcGeometry(mm(*a), mm(*m), mm(*b))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(pcbnew.FromMM(0.05))
        board.Add(s)


def zone(board, name, x0, y0, x1, y1, lset):
    z = pcbnew.ZONE(board)
    z.SetZoneName(name)
    z.SetLayerSet(lset)
    ol = z.Outline()
    ol.NewOutline()
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        ol.Append(mm(x, y))
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    board.Add(z)
    return z


def rule_area(board, name, box, no_footprints=False, no_copper=False):
    z = zone(board, name, *box, lset=layers(pcbnew.F_Cu, pcbnew.B_Cu))
    z.SetIsRuleArea(True)
    z.SetDoNotAllowFootprints(no_footprints)
    z.SetDoNotAllowPads(False)
    z.SetDoNotAllowTracks(no_copper)
    z.SetDoNotAllowVias(no_copper)
    z.SetDoNotAllowCopperPour(no_copper)


def text(board, s, x, y, rot=0, size=1.0, left=False, top=False):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(s)
    t.SetLayer(pcbnew.F_SilkS)
    t.SetTextSize(mm(size, size))
    t.SetTextThickness(pcbnew.FromMM(max(0.15, 0.15 * size)))
    t.SetPosition(mm(x, y))
    t.SetTextAngleDegrees(rot)
    if left:
        t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
    if top:
        t.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_TOP)
    board.Add(t)


def label(board, fp, name, pins):
    """Centred on the named pins (all pads if none), just outside the XH body on the board side."""
    x, y, rot = design.PLACE[fp.GetReference()]
    half_row = ((len(pins.split()) or len(fp.Pads())) - 1) * 1.25
    if rot == 180:  # bottom edge: J2 sits right above, so the label goes left of the body;
        # pin 1 is the right pad here, so list pins right-to-left to read in pad order
        text(board, f"{name}\n{' '.join(reversed(pins.split()))}", x - 21, y - 1.3, 0, 0.8, left=True, top=True)
        return
    at = (x + half_row, y + 3.9) if rot == 0 else (x + 3.9, y - half_row)
    text(board, f"{name}\n{pins}".strip(), *at, rot, size=0.8, top=True)


def build():
    design.check()
    assert design.PLACE.keys() == design.PARTS.keys(), design.PLACE.keys() ^ design.PARTS.keys()
    pcbnew.KIID.SeedGenerator(1)  # deterministic uuids across runs
    board = pcbnew.BOARD()
    board.SetCopperLayerCount(2)
    # design rules are not stored in .kicad_pcb: they come from {design.NAME}.kicad_pro (checked in verify)
    # (the comment is informational; the file is written by gen_sch.py)

    net_of = {p: net for net, members in design.NETS.items() for p in members} | unconnected_nets()
    for net in dict.fromkeys(net_of.values()):
        board.Add(pcbnew.NETINFO_ITEM(board, net))
    fps = {ref: footprint(board, ref, net_of) for ref in design.PARTS}

    if design.HELTEC_PADS:  # carrier only: pin-1 positions of the Heltec socket rows
        for (ref, n), want in design.HELTEC_PADS.items():
            got = [pcbnew.ToMM(p.GetPosition()) for p in fps[ref].Pads() if p.GetNumber() == n][0]
            assert all(abs(g - w) < 1e-3 for g, w in zip(got, want, strict=True)), f"{ref}.{n} at {got}, want {want}"

    gnd_net = board.FindNet("GND")
    drill, dia = gen_sch.VIA["via_drill"], gen_sch.VIA["via_diameter"]
    for x, y, tie in design.GND_VIAS:
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(mm(x, y))
        v.SetWidth(pcbnew.FromMM(dia))
        v.SetDrill(pcbnew.FromMM(drill))
        v.SetNet(gnd_net)
        v.SetLocked(True)
        board.Add(v)
        if tie:
            ref, n = tie
            pad = next(p for p in fps[ref].Pads() if p.GetNumber() == n)
            assert pad.GetNetname() == "GND", f"{ref}.{n} is not GND"
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(pad.GetPosition())
            t.SetEnd(mm(x, y))
            t.SetWidth(pcbnew.FromMM(0.5))
            t.SetLayer(pcbnew.F_Cu)
            t.SetNet(gnd_net)
            t.SetLocked(True)
            board.Add(t)

    outline(board)
    if design.HELTEC_PADS:  # carrier only: keep the Heltec socket/antenna area clear
        # Nothing between the Heltec socket rows (its battery socket hangs below); tracks/vias fine
        j3 = fps["J3"].GetCourtyard(pcbnew.F_CrtYd).BBox()
        j2 = fps["J2"].GetCourtyard(pcbnew.F_CrtYd).BBox()
        left = pcbnew.ToMM(j3.GetLeft()) - 0.275  # 42.7
        top, bottom = pcbnew.ToMM(j3.GetBottom()) + 0.05, pcbnew.ToMM(j2.GetTop()) - 0.05
        rule_area(board, "HELTEC_UNDER", (left, top, design.W, bottom), no_footprints=True)
        # No pour or traces under the antenna end, right of the pin-18 pads
        pad18 = max(pcbnew.ToMM(p.GetBoundingBox().GetRight()) for r in ("J2", "J3") for p in fps[r].Pads())
        rule_area(board, "ANT", (pad18 + 0.25, 0, design.W, design.H), no_copper=True)

    gnd = zone(board, "GND", 0, 0, design.W, design.H, lset=layers(pcbnew.B_Cu))
    gnd.SetNet(board.FindNet("GND"))
    gnd.SetAssignedPriority(0)
    gnd.SetLocalClearance(pcbnew.FromMM(0.3))
    gnd.SetPadConnection(GND_PAD_CONNECTION)

    for ref, (name, pins) in design.LABELS.items():
        label(board, fps[ref], name, pins)
    for s, x, y, rot, size, left in design.TEXTS:
        text(board, s, x, y, rot, size, left)
    return board, len(set(net_of.values())) - len(design.NETS)


def verify():
    """Reload the saved board as KiCad would (with <BOARD>.kicad_pro) and check rules + classes."""
    b = pcbnew.LoadBoard(str(PCB))
    ds = b.GetDesignSettings()
    got = [pcbnew.ToMM(v) for v in (ds.m_MinClearance, ds.m_TrackMinWidth, ds.m_ViasMinSize, ds.m_MinThroughDrill)]
    want = [getattr(design, "DRC_RULES", {}).get("min_clearance", 0.2), 0.15, 0.6, 0.3]
    assert got == want, f"project rules {got}"
    ns = ds.m_NetSettings
    # KiCad 9 names pattern-matched classes "Power,Default" (Default fills unset fields): check values
    for net, want in design.NETCLASS_EXPECT:
        nc = ns.GetEffectiveNetClass(net)
        got = [pcbnew.ToMM(nc.GetTrackWidth()), pcbnew.ToMM(nc.GetClearance())]
        assert got == want, f"{net} ({nc.GetName()}): track/clearance {got}, want {want}"


def main():
    board, n_unconnected = build()
    if not pcbnew.SaveBoard(str(PCB), board, True):  # True: leave <BOARD>.kicad_pro to gen_sch.py
        raise SystemExit("save failed")
    verify()
    print(f"wrote {PCB.name}: {len(design.PARTS)} footprints, "
          f"{len(design.NETS)} design nets + {n_unconnected} unconnected-pin nets")


if __name__ == "__main__":
    main()
