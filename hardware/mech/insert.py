#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["build123d==0.13.0"]
# ///
"""Geometry for the Pawbol S-BOX 416-P insert: base tray, lid panel, wall bushings, speaker
grille and drill guide.

Every dimension comes from params.py; this file holds shapes only.

    uv run hardware/mech/insert.py --part all --check
"""

import math
import pathlib
import sys

try:
    from build123d import (
        Box,
        Circle,
        Cylinder,
        ExportSVG,
        Plane,
        Polygon,
        Pos,
        Rectangle,
        Rot,
        export_step,
        export_stl,
        extrude,
    )
except ModuleNotFoundError as exc:
    raise SystemExit(
        "build123d is not installed for this interpreter.\n"
        "Run it through uv, which reads the inline metadata at the top of this file:\n"
        "    uv run hardware/mech/insert.py --part all --check"
    ) from exc

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import params as P  # noqa: E402

OUT = HERE / "out"


# --- primitives ------------------------------------------------------------------------------


def box(x0, x1, y0, y1, z0, z1):
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(x1 - x0, y1 - y0, z1 - z0)


def cyl_z(x, y, z0, z1, r):
    return Pos(x, y, (z0 + z1) / 2) * Cylinder(r, z1 - z0)


def cyl_x(y, z, x0, x1, r):
    return Pos((x0 + x1) / 2, y, z) * Rot(Y=90) * Cylinder(r, x1 - x0)


def tri_prism_x(y0, y1, z0, z1, x_centre, width):
    """A wedge in the YZ plane, extruded `width` along X: the bracket gusset.

    Vertices run (y0, z0) -> (y1, z0) -> (y1, z1), so the sloped face is the one that has to
    print unsupported; keep z1 - z0 <= y1 - y0 for a 45-degree-or-shallower overhang.

    Recentred from the built shape's own bounds rather than assuming which way the extrusion
    ran, which is the difference between an arm that joins the post and one that floats.
    """
    profile = Plane.YZ * Polygon((y0, z0), (y1, z0), (y1, z1), align=None)
    prism = extrude(profile, amount=width)
    bb = prism.bounding_box()
    return Pos(x_centre - (bb.min.X + bb.max.X) / 2, 0, 0) * prism


# --- tray ------------------------------------------------------------------------------------


def make_tray():
    x0, x1 = P.FIT, P.BOX_IN[0] - P.FIT
    y0, y1 = P.FIT, P.BOX_IN[1] - P.FIT

    tray = box(x0, x1, y0, y1, 0, P.FLOOR_T)
    # lighten the field, leaving a 12 mm border and 1.2 mm under the cells
    tray -= box(x0 + 12, x1 - 12, y0 + 12, y1 - 12, P.FLOOR_T - 1.2, P.FLOOR_T + 1)

    # corner sleeves: an L per corner, not a closed tube, at a third of the material
    bore_x = P.COLUMN_SIZE[0] + P.FIT
    bore_y = P.COLUMN_SIZE[1] + P.FIT
    sleeve_top = P.panel_z0()
    for cx, cy in P.column_centres():
        tray -= box(cx - bore_x / 2, cx + bore_x / 2, cy - bore_y / 2, cy + bore_y / 2, -1, P.FLOOR_T + 1)
        for wx0, wx1, wy0, wy1 in P.sleeve_walls(cx, cy):
            tray += box(wx0, wx1, wy0, wy1, 0, sleeve_top)

    # cell saddles: two rails, each scalloped for all four cells
    centres = P.trough_centres_y()
    scallop_z = P.CELL_BOTTOM_Z + P.CELL_D / 2 + P.SADDLE_CLEAR
    cell_x = P.PACK_ORIGIN[0] + P.PACK[0] / 2
    for sx in (cell_x - P.SADDLE_INSET, cell_x + P.SADDLE_INSET):
        rail = box(
            sx - P.SADDLE_T / 2, sx + P.SADDLE_T / 2,
            centres[0] - P.CELL_D, centres[-1] + P.CELL_D,
            -0.1, scallop_z,
        )
        for cy in centres:
            rail -= cyl_x(cy, scallop_z, sx - P.SADDLE_T / 2 - 1, sx + P.SADDLE_T / 2 + 1, P.CELL_D / 2 + P.SADDLE_CLEAR)
        tray += rail

    # pack board posts, flush with the board's underside, M3 self-tapping pilots
    pz = P.pack_z()
    for hx, hy in P.PACK_HOLES:
        px, py = P.PACK_ORIGIN[0] + hx, P.PACK_ORIGIN[1] + hy
        post = cyl_z(px, py, -0.1, pz, P.POST_R)
        post -= cyl_z(px, py, pz - 6, pz + 1, P.POST_PILOT / 2)
        tray += post

    # carrier posts: in the margins, reaching in on gusseted arms
    cz = P.carrier_z()
    for (px, py), (hx, hy) in zip(P.carrier_post_xy(), P.carrier_hole_xy(), strict=True):
        post = cyl_z(px, py, -0.1, cz, P.POST_R)
        post -= cyl_z(px, py, cz - 6, cz + 1, P.POST_PILOT / 2)
        tray += post
        tray += tri_prism_x(py, hy, -0.1, cz, px, P.ARM_W)
        tray += cyl_z(hx, hy, cz - 4, cz, P.POST_R)

    # cable clips and wall backing blocks
    tray += _cable_clips()
    tray += _wall_backings()
    return tray


def _cable_clips():
    clips = None
    for cx, cy in P.CLIP_XY:
        clip = box(cx - 5, cx + 5, cy - 6, cy + 6, -0.1, P.FLOOR_T + 8)
        clip -= cyl_x(cy, P.FLOOR_T + 5, cx - 6, cx + 6, 2.2)
        clips = clip if clips is None else clips + clip
    return clips


def _wall_backings():
    """A nut pocket inside each wall device, so it can be tightened one-handed.

    Thin and narrow on purpose: solid blocks here were the single biggest slice of the tray's
    material, and at 26 x 12 mm they also ran into the corner columns.
    """
    h = P.BACKING_H
    out = None
    for wp in P.WALL_PARTS.values():
        x0, x1, y0, y1 = P.backing_box(wp)
        b = box(x0, x1, y0, y1, wp["z"] - h, wp["z"] + h)
        # the stem is narrow along the wall and keeps the backing's depth, so it never grows
        # past the wall it hangs from
        if wp["wall"] == "long":
            mid = (x0 + x1) / 2
            stem = box(mid - 5, mid + 5, y0, y1, -0.1, wp["z"] - h + 1)
        else:
            mid = (y0 + y1) / 2
            stem = box(x0, x1, mid - 5, mid + 5, -0.1, wp["z"] - h + 1)
        out = b + stem if out is None else out + b + stem
    return out


# --- lid panel ---------------------------------------------------------------------------------


def make_lid():
    x0, x1 = P.FIT, P.BOX_IN[0] - P.FIT
    y0, y1 = P.FIT, P.BOX_IN[1] - P.FIT
    z0 = P.panel_z0()
    z1 = z0 + P.LID_T
    panel = box(x0, x1, y0, y1, z0, z1)

    # the columns are solid all the way to the rim, so the panel needs relief at each corner
    for cx, cy in P.column_centres():
        rx = P.COLUMN_SIZE[0] / 2 + P.FIT / 2
        ry = P.COLUMN_SIZE[1] / 2 + P.FIT / 2
        panel -= box(cx - rx, cx + rx, cy - ry, cy + ry, z0 - 1, z1 + 1)

    lx0, lx1, ly0, ly1 = P.lcd_box()
    panel -= box(lx0, lx1, ly0, ly1, z0 - 1, z1 + 1)
    for bx0, bx1, by0, by1 in P.button_boxes():
        panel -= cyl_z((bx0 + bx1) / 2, (by0 + by1) / 2, z0 - 1, z1 + 1, (bx1 - bx0) / 2 + 0.15)
    nx0, nx1, ny0, ny1 = P.nfc_box()
    panel -= box(nx0, nx1, ny0, ny1, z0 - 1, z1 + 1)

    # button bosses: the lid's drilled hole lands on something that can clamp the button
    for bx0, bx1, by0, by1 in P.button_boxes():
        cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
        panel += cyl_z(cx, cy, z0 - 6, z0, P.BUTTON_D / 2 + 5)
        panel -= cyl_z(cx, cy, z0 - 7, z0 + 1, P.BUTTON_D / 2 + 0.15)

    # LCD mounting bosses on the 93 x 55 grid
    for sx in (-1, 1):
        for sy in (-1, 1):
            px = P.LCD_CENTRE[0] + sx * P.LCD_HOLES[0] / 2
            py = P.LCD_CENTRE[1] + sy * P.LCD_HOLES[1] / 2
            panel += cyl_z(px, py, z0 - 5, z0, 3.5)
            panel -= cyl_z(px, py, z0 - 6, z0 + 1, 1.6)
    return panel


# --- wall bushings ------------------------------------------------------------------------------


def make_bushing(device):
    """Flange outside, barrel through the wall, device bore down the middle. Axis is +Z."""
    wp = P.WALL_PARTS[device]
    fr = wp["hole_d"] / 2 + P.BUSHING_FLANGE_D / 2
    br = wp["hole_d"] / 2 - 0.1
    dr = wp["device_d"] / 2
    gw, gd = P.ORING_GROOVE
    top = P.WALL + P.BUSHING_LIP

    part = cyl_z(0, 0, -P.BUSHING_FLANGE, 0, fr)
    part += cyl_z(0, 0, 0, top, br)
    part -= cyl_z(0, 0, -P.BUSHING_FLANGE - 1, top + 1, dr)
    if dr < br - gw:
        part -= cyl_z(0, 0, -gd, 0, dr + gw)
    return part


# --- speaker grille and drill guide -------------------------------------------------------------


def make_grille():
    r_out = P.SPEAKER_D / 2 + P.GRILLE_RIM
    hole_r = P.MESH_HOLE_D / 2
    row_h = P.MESH_PITCH * math.sqrt(3) / 2

    part = cyl_z(0, 0, 0, P.GRILLE_T, r_out)
    part -= cyl_z(0, 0, -1, P.GRILLE_RECESS, P.SPEAKER_D / 2 - 2)
    k = -40
    while k <= 40:
        y = k * row_h
        if abs(y) <= P.SPEAKER_D / 2:
            off = P.MESH_PITCH / 2 if k % 2 else 0.0
            j = -40
            while j <= 40:
                x = off + j * P.MESH_PITCH
                if math.hypot(x, y) <= P.SPEAKER_D / 2 - hole_r:
                    part -= cyl_z(x, y, -1, P.GRILLE_T + 1, hole_r)
                j += 1
        k += 1
    for i in range(4):
        a = math.radians(45 + 90 * i)
        part -= cyl_z(P.GRILLE_BOLT_R * math.cos(a), P.GRILLE_BOLT_R * math.sin(a), -1, P.GRILLE_T + 1, 1.6)
    gw, gd = P.ORING_GROOVE
    part -= cyl_z(0, 0, -gd, 0.01, P.SPEAKER_D / 2 + 2 + gw)
    return part


def make_guide():
    """Clamp-on ring for the 50 mm holesaw; nothing clever, just a bore that cannot wander.

    Only ever used to start a hole, so it is a thin ring and not a 12 mm drum.
    """
    r_out = P.SPEAKER_D / 2 + P.GRILLE_RIM
    part = cyl_z(0, 0, 0, 5, r_out)
    part -= cyl_z(0, 0, -1, 6, P.SPEAKER_D / 2 + 0.1)
    return part


# --- templates ----------------------------------------------------------------------------------


def template_shapes():
    """(name, [edges], [labels]) in millimetres for the 1:1 drill sheets."""
    lid_edges = []
    for bx0, bx1, by0, by1 in P.button_boxes():
        lid_edges.append(cyl_z((bx0 + bx1) / 2, (by0 + by1) / 2, 0, 0.1, (bx1 - bx0) / 2))
    wall_edges = []
    for wp in P.WALL_PARTS.values():
        wall_edges.append(cyl_z(wp["u"], 0, 0, 0.1, wp["hole_d"] / 2))
    wall_edges.append(cyl_z(P.SPEAKER_WALL["u"], 0, 0, 0.1, P.SPEAKER_D / 2))
    return [("lid", lid_edges), ("walls", wall_edges)]


def template_sheets():
    """(name, shapes, label, bar_y) per drill sheet, in millimetres and already centred.

    Each sheet carries a 100 mm calibration bar, because the one thing that ruins a paper
    template is a printer quietly scaling it to 97 %.
    """
    cx, cy = P.BOX_IN[0] / 2, P.BOX_IN[1] / 2
    to_centre = Pos(-cx, -cy, 0)

    lid = [Rectangle(P.BOX_IN[0] - 2 * P.FIT, P.BOX_IN[1] - 2 * P.FIT)]
    lx0, lx1, ly0, ly1 = P.lcd_box()
    lid.append(to_centre * (Pos((lx0 + lx1) / 2, (ly0 + ly1) / 2, 0) * Rectangle(lx1 - lx0, ly1 - ly0)))
    nx0, nx1, ny0, ny1 = P.nfc_box()
    lid.append(to_centre * (Pos((nx0 + nx1) / 2, (ny0 + ny1) / 2, 0) * Rectangle(nx1 - nx0, ny1 - ny0)))
    for bx0, bx1, by0, by1 in P.button_boxes():
        lid.append(to_centre * (Pos((bx0 + bx1) / 2, (by0 + by1) / 2, 0) * Circle((bx1 - bx0) / 2)))

    # walls are drawn unfolded, stacked one above the other so the sheet fits a printer
    long_y, short_y = P.BOX_IN[2] / 2 + 15, -P.BOX_IN[2] / 2 - 45
    walls = [Pos(0, long_y, 0) * Rectangle(P.BOX_IN[0], P.BOX_IN[2])]
    walls.append(Pos(0, short_y, 0) * Rectangle(P.BOX_IN[1], P.BOX_IN[2]))
    for wp in P.WALL_PARTS.values():
        if wp["wall"] == "long":
            walls.append(Pos(wp["u"] - cx, long_y + wp["z"] - cy, 0) * Circle(wp["hole_d"] / 2))
        else:
            walls.append(Pos(wp["u"] - cx, short_y + wp["z"] - cy, 0) * Circle(wp["hole_d"] / 2))
    walls.append(Pos(P.SPEAKER_WALL["u"] - cx, long_y + P.SPEAKER_WALL["z"] - cy, 0) * Circle(P.SPEAKER_D / 2))

    return [
        ("lid", lid, "LID, seen from inside", -cy - 15),
        ("walls", walls, "WALLS, unfolded", short_y - 30),
    ]


def write_templates():
    import re

    written = []
    for name, shapes, _label, bar_y in template_sheets():
        path = OUT / f"template_{name}.svg"
        svg = ExportSVG(margin=8)
        svg.add_layer("cuts", line_weight=0.4)
        for s in shapes:
            svg.add_shape(s, layer="cuts")
        svg.add_shape(Pos(0, bar_y, 0) * Rectangle(100, 2), layer="cuts")
        svg.write(str(path))
        _check_template_scale(path, re)
        written.append(path)
    return written


def _check_template_scale(path, re):
    """A printed template is worthless if the printer scaled it, so pin the units."""
    head = path.read_text()[:600]
    w = re.search(r'width="(\d+\.?\d*)mm"', head)
    vb = re.search(r'viewBox="[-\d.]+ [-\d.]+ (\d+\.?\d*) ', head)
    if not w or not vb:
        raise SystemExit(f"FAIL {path.name}: no physical units in the SVG")
    if abs(float(w.group(1)) - float(vb.group(1))) > 0.01:
        raise SystemExit(f"FAIL {path.name}: not 1:1, {w.group(1)}mm over {vb.group(1)} units")
    print(f"ok    {path.name}: 1:1, 1 unit = 1 mm, {w.group(1)} mm wide, 100 mm bar included")


# --- driver --------------------------------------------------------------------------------------

PARTS = {
    "tray": make_tray,
    "lid": make_lid,
    "grille": make_grille,
    "guide": make_guide,
}


def column_solids():
    """The box's own corner columns as solids, so parts can be tested against them."""
    out = []
    for cx, cy in P.column_centres():
        out.append(box(cx - P.COLUMN_SIZE[0] / 2, cx + P.COLUMN_SIZE[0] / 2,
                       cy - P.COLUMN_SIZE[1] / 2, cy + P.COLUMN_SIZE[1] / 2,
                       -1, P.BOX_IN[2] + 1))
    return out


def check_part(name, part):
    bb = part.bounding_box()
    sx, sy, sz = bb.size.X, bb.size.Y, bb.size.Z
    solids = len(part.solids())
    if solids != 1:
        raise SystemExit(f"FAIL {name}: {solids} solids, expected 1")
    if part.volume <= 0:
        raise SystemExit(f"FAIL {name}: empty")
    limit_x = P.BOX_IN[0] - 2 * P.FIT + 1e-6
    limit_y = P.BOX_IN[1] - 2 * P.FIT + 1e-6
    if name in ("tray", "lid"):
        if sx > limit_x or sy > limit_y:
            raise SystemExit(f"FAIL {name}: {sx:.1f} x {sy:.1f} does not fit")
        if sx > 220 or sy > 220:
            raise SystemExit(f"FAIL {name}: does not fit a 220 x 220 bed")
        clash = max((part & col).volume for col in column_solids())
        if clash > 1.0:
            raise SystemExit(
                f"FAIL {name}: {clash:.1f} mm3 of it sits inside a solid corner column; "
                "the part cannot physically go into the box"
            )
    print(f"ok    {name}: {sx:.1f} x {sy:.1f} x {sz:.1f}, {part.volume / 1000:.1f} cm3, {solids} solid")


def main(argv):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", default="all")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)

    names = list(PARTS) + ["bus:" + d for d in P.WALL_PARTS]
    if args.part != "all":
        names = [n for n in args.part.split(",") if n]

    OUT.mkdir(exist_ok=True)
    if args.part in ("all", "templates"):
        for path in write_templates():
            print(f"wrote {path.relative_to(HERE.parent)}")
        if args.part == "templates":
            return 0
    for name in names:
        if name.startswith("bus:"):
            dev = name[4:]
            part, fname = make_bushing(dev), f"bushing_{dev}"
        elif name in PARTS:
            part, fname = PARTS[name](), name
        else:
            raise SystemExit(f"unknown part {name}")
        if args.check:
            check_part(fname, part)
        export_stl(part, str(OUT / f"{fname}.stl"))
        export_step(part, str(OUT / f"{fname}.step"))
        print(f"wrote out/{fname}.stl and .step")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
