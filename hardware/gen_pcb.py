"""Generate carrier.kicad_pcb (placed, unrouted) from design.py.

Origin top-left, X right, Y down, mm. Design rules and net classes live in
carrier.kicad_pro (written by gen_sch.py); the board is saved beside it without
touching it, then reloaded to check KiCad resolves the classes.
Run: /usr/bin/python3 gen_pcb.py
"""
from pathlib import Path

import pcbnew

import design
import gen_sch

HERE = Path(__file__).parent
PCB = HERE / "carrier.kicad_pcb"
FPDIR = Path("/usr/share/kicad/footprints")
W, H, CORNER = 90.0, 60.0, 2.0

# ref: (x, y, rotation deg). Footprint origin = pad 1 for connectors and THT caps.
PLACE = {
    # Heltec V4 headers: pin 1 at the USB end (left), pins run +X (asserted in build)
    "J3": (44.82, 27.00, 90), "J2": (44.82, 49.86, 90),
    "H1": (3.5, 3.5, 0), "H2": (86.5, 3.5, 0), "H3": (3.5, 56.5, 0), "H4": (86.5, 56.5, 0),
    # Top edge: XH open side (-Y at rotation 0) faces the board edge, pin 1 left
    "J_BAT1": (10, 6, 0), "J_KEY1": (19, 6, 0), "J_HBAT1": (28, 6, 0),
    "J_LCD1": (40, 6, 0), "J_NFC1": (54, 6, 0), "J_BTN_R1": (68, 6, 0),
    # Left edge: rotated so the open side faces -X, pin 1 at the bottom
    "J_BTN_B1": (6, 33, 90), "J_BUZ1": (6, 47, 90),
    # Power: MT3608 boost; L1 -> SW -> D1 -> C_OUT and U1 SW/GND kept within ~15 mm
    "F1": (15.5, 14, 0), "C_BULK1": (13.5, 20.5, 0),
    "L1": (22.5, 16, 0), "D1": (30.5, 16, 180), "U1": (28, 21.8, 0), "C_IN1": (32.8, 22.8, 0),
    "C_OUT1": (37, 15.5, 0), "C_OUT2": (37, 19.3, 0),
    "R_FB2": (23.5, 22.5, 180), "R_FB1": (23.5, 26, 0),
    # I2C level shifter + NFC bulk cap, under their connectors
    "Q_SDA1": (44, 16, 0), "R_SDA3": (44, 20, 0), "R_SDA5": (44, 23.3, 0),
    "Q_SCL1": (49.5, 16, 0), "R_SCL3": (49.5, 20, 0), "R_SCL5": (49.5, 23.3, 0),
    "C_NFC1": (55.5, 18, 0),
    # Low-side drivers, one column each (top to bottom R_G, R_PD, Q, R_L): gate pads on one
    # vertical line at x+1, GND pads at x-1, drain straight down into R_L
    "R_GLB1": (16, 29, 0), "R_PDLB1": (16, 32, 180), "Q_LB1": (16, 35.5, 270), "R_LLB1": (16, 39.5, 270),
    "R_GBZ1": (24, 29, 0), "R_PDBZ1": (24, 32, 180), "Q_BZ1": (24, 35.5, 270),
    "R_GLR1": (32, 29, 0), "R_PDLR1": (32, 32, 180), "Q_LR1": (32, 35.5, 270), "R_LLR1": (32, 39.5, 270),
    "D_FLY1": (15, 45, 0),
    # Button RC: BTN_B near its connector, BTN_R near J_BTN_R1 (its GPIO is on J3, top right)
    "R_PUB1": (20, 49, 0), "C_BB1": (20, 52.5, 0), "R_SB1": (25, 50.75, 0),
    "R_PUR1": (66, 15.5, 0), "C_BR1": (66, 19, 0), "R_SR1": (71, 17.25, 0),
}

# Connector silk labels (name, pins in pin-1-first order). Pin 1 is the left pad at rot 0 and
# the bottom pad at rot 90; text reads left-to-right / bottom-to-top, so pin 1 comes first.
LABELS = {
    "J_BAT1": ("BAT", "+  -"), "J_KEY1": ("KEY", ""), "J_HBAT1": ("HELTEC BAT", "+  -"),
    "J_LCD1": ("LCD", "GND 5V SDA SCL"), "J_NFC1": ("NFC", "GND 3V3 SDA SCL"),
    "J_BTN_R1": ("BTN_R", "SW GND L+ L-"), "J_BTN_B1": ("BTN_B", "SW GND L+ L-"), "J_BUZ1": ("BUZ", "+  -"),
}
# free text: (text, x, y, rot, size)
TEXTS = [
    ("AirsoftCounter v2 carrier", 9, 56.5, 0, 1.0), ("2026-09", 9, 58.3, 0, 1.0),
    ("USB", 40.5, 38.43, 90, 1.0), ("ANT →", 84, 38.43, 0, 1.0),
]
HELTEC_PADS = {("J3", "1"): (44.82, 27.00), ("J3", "18"): (88.00, 27.00),
               ("J2", "1"): (44.82, 49.86), ("J2", "18"): (88.00, 49.86)}


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
                    out[f"{ref}.{n}"] = f"unconnected-({ref}-{name}-Pad{n})"
    return out


def footprint(board, ref, nets):
    value, _, fpid = design.PARTS[ref]
    lib, name = fpid.split(":")
    fp = pcbnew.FootprintLoad(str(FPDIR / f"{lib}.pretty"), name)
    if fp is None:
        raise SystemExit(f"{ref}: footprint {fpid} not found")
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    fp.SetReference(ref)
    fp.SetValue(value)
    fp.Reference().SetTextSize(mm(0.8, 0.8))
    fp.Reference().SetTextThickness(pcbnew.FromMM(0.12))
    x, y, rot = PLACE[ref]
    fp.SetPosition(mm(x, y))
    fp.SetOrientationDegrees(rot)
    if rot == 180:  # keep the reference above the part, as at rot 0
        r, o = fp.Reference().GetPosition(), fp.GetPosition()
        fp.Reference().SetPosition(pcbnew.VECTOR2I(2 * o.x - r.x, 2 * o.y - r.y))
    # links the footprint to its schematic symbol (gen_sch's deterministic uuid)
    fp.SetPath(pcbnew.KIID_PATH("/" + gen_sch.unq(gen_sch.uid(f"sym/{ref}"))))
    fp.SetSheetname("/")
    fp.SetSheetfile("carrier.kicad_sch")
    if ref in design.DNP:
        fp.SetDNP(True)
        fp.SetExcludedFromBOM(True)
    board.Add(fp)
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
    r = CORNER
    segs = [((r, 0), (W - r, 0)), ((W, r), (W, H - r)), ((W - r, H), (r, H)), ((0, H - r), (0, r))]
    k = r * (1 - 0.5 ** 0.5)  # 45-degree point on each corner arc
    arcs = [((W - r, 0), (W - k, k), (W, r)), ((W, H - r), (W - k, H - k), (W - r, H)),
            ((r, H), (k, H - k), (0, H - r)), ((0, r), (k, k), (r, 0))]
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


def zone(board, name, x0, y0, x1, y1, layers):
    z = pcbnew.ZONE(board)
    z.SetZoneName(name)
    z.SetLayerSet(layers)
    ol = z.Outline()
    ol.NewOutline()
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        ol.Append(mm(x, y))
    board.Add(z)
    return z


def rule_area(board, name, box, no_footprints=False, no_copper=False):
    z = zone(board, name, *box, layers(pcbnew.F_Cu, pcbnew.B_Cu))
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
    t.SetTextThickness(pcbnew.FromMM(0.15 * size))
    t.SetPosition(mm(x, y))
    t.SetTextAngleDegrees(rot)
    if left:
        t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
    if top:
        t.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_TOP)
    board.Add(t)


def label(board, fp, name, pins):
    """Centred on the pad row, just outside the XH body on the board side (below / right of it)."""
    x, y, rot = PLACE[fp.GetReference()]
    half_row = (len(fp.Pads()) - 1) * 1.25
    at = (x + half_row, y + 3.9) if rot == 0 else (x + 3.9, y - half_row)
    text(board, f"{name}\n{pins}".strip(), *at, rot, size=0.8, top=True)


def build():
    design.check()
    assert PLACE.keys() == design.PARTS.keys(), PLACE.keys() ^ design.PARTS.keys()
    pcbnew.KIID.SeedGenerator(1)  # deterministic uuids across runs
    board = pcbnew.BOARD()
    board.SetCopperLayerCount(2)
    # design rules are not stored in .kicad_pcb: they come from carrier.kicad_pro (checked in verify)

    net_of = {p: net for net, members in design.NETS.items() for p in members} | unconnected_nets()
    for net in dict.fromkeys(net_of.values()):
        board.Add(pcbnew.NETINFO_ITEM(board, net))
    fps = {ref: footprint(board, ref, net_of) for ref in design.PARTS}

    for (ref, n), want in HELTEC_PADS.items():
        got = [pcbnew.ToMM(p.GetPosition()) for p in fps[ref].Pads() if p.GetNumber() == n][0]
        assert all(abs(g - w) < 1e-3 for g, w in zip(got, want)), f"{ref}.{n} at {got}, want {want}"

    outline(board)
    # Nothing between the Heltec socket rows (its battery socket hangs below); tracks/vias fine
    j3 = fps["J3"].GetCourtyard(pcbnew.F_CrtYd).BBox()
    j2 = fps["J2"].GetCourtyard(pcbnew.F_CrtYd).BBox()
    top, bottom = pcbnew.ToMM(j3.GetBottom()) + 0.05, pcbnew.ToMM(j2.GetTop()) - 0.05
    rule_area(board, "HELTEC_UNDER", (42.7, top, W, bottom), no_footprints=True)
    # No pour or traces under the antenna end, right of the pin-18 pads
    pad18 = max(pcbnew.ToMM(p.GetBoundingBox().GetRight()) for r in ("J2", "J3") for p in fps[r].Pads())
    rule_area(board, "ANT", (pad18 + 0.25, 0, W, H), no_copper=True)

    gnd = zone(board, "GND", 0, 0, W, H, layers(pcbnew.B_Cu))
    gnd.SetNet(board.FindNet("GND"))
    gnd.SetAssignedPriority(0)
    gnd.SetLocalClearance(pcbnew.FromMM(0.3))
    gnd.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)

    for ref, (name, pins) in LABELS.items():
        label(board, fps[ref], name, pins)
    for s, x, y, rot, size in TEXTS:
        text(board, s, x, y, rot, size, left=rot == 0 and x < 40)
    return board


def verify():
    """Reload the saved board as KiCad would (with carrier.kicad_pro) and check rules + classes."""
    b = pcbnew.LoadBoard(str(PCB))
    ds = b.GetDesignSettings()
    got = [pcbnew.ToMM(v) for v in (ds.m_MinClearance, ds.m_TrackMinWidth, ds.m_ViasMinSize, ds.m_MinThroughDrill)]
    assert got == [0.2, 0.2, 0.6, 0.3], f"project rules {got}"
    ns = ds.m_NetSettings
    # KiCad 9 names pattern-matched classes "Power,Default" (Default fills unset fields): check values
    for net, want in (("VBAT_SW", [0.8, 0.25]), ("GND", [0.8, 0.25]), ("+5V", [0.8, 0.25]),
                      ("SW", [0.8, 0.25]), ("SDA_3V3", [0.25, 0.2])):
        nc = ns.GetEffectiveNetClass(net)
        got = [pcbnew.ToMM(nc.GetTrackWidth()), pcbnew.ToMM(nc.GetClearance())]
        assert got == want, f"{net} ({nc.GetName()}): track/clearance {got}, want {want}"


def main():
    board = build()
    assert pcbnew.SaveBoard(str(PCB), board, True)  # True: leave carrier.kicad_pro to gen_sch.py
    verify()
    print(f"wrote {PCB.name}: {len(design.PARTS)} footprints, {len(design.NETS)} nets")


if __name__ == "__main__":
    main()
