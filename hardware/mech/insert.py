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
import subprocess
import sys

try:
    from build123d import (
        Box,
        Circle,
        Compound,
        Cone,
        Cylinder,
        ExportSVG,
        Plane,
        Polygon,
        Pos,
        Rectangle,
        Rot,
        Text,
        Vector,
        export_step,
        export_stl,
        extrude,
        import_step,
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
CLASH_MM3 = 1.0  # overlap below this is boolean noise on touching faces, not a collision


# --- primitives ------------------------------------------------------------------------------


def box(x0, x1, y0, y1, z0, z1):
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(x1 - x0, y1 - y0, z1 - z0)


def cyl_z(x, y, z0, z1, r):
    return Pos(x, y, (z0 + z1) / 2) * Cylinder(r, z1 - z0)


def cyl_x(y, z, x0, x1, r):
    return Pos((x0 + x1) / 2, y, z) * Rot(Y=90) * Cylinder(r, x1 - x0)


def tri_prism_x(y0, y1, z0, z1, x_centre, width):
    """A wedge in the YZ plane, extruded `width` along X: the bracket gusset.

    Vertices run (y0, z0) -> (y1, z0) -> (y1, z1): a right angle at (y1, z0), the slope from
    (y0, z0) to (y1, z1). Pass the ends in either order to put the right angle where you want it.

    Recentred from the built shape's own bounds rather than assuming which way the extrusion
    ran, which is the difference between an arm that joins the post and one that floats.
    """
    profile = Plane.YZ * Polygon((y0, z0), (y1, z0), (y1, z1), align=None)
    prism = extrude(profile, amount=width)
    bb = prism.bounding_box()
    return Pos(x_centre - (bb.min.X + bb.max.X) / 2, 0, 0) * prism


def post(x, y, z_top, pilot=True):
    """A printed post: a straight column plus a 45-degree base flare.

    The guideline's column table (D=3 mm -> H=3-6 mm) makes a bare 32 mm column of any sensible
    diameter too slender to survive bead blasting. The flare is the cheap fix.
    """
    part = cyl_z(x, y, 0, z_top, P.POST_R)
    part += Pos(x, y, P.POST_FLARE_H / 2) * Cone(P.POST_R + P.POST_FLARE, P.POST_R, P.POST_FLARE_H)
    if pilot:
        part -= cyl_z(x, y, z_top - P.PILOT_DEPTH, z_top + 1, P.POST_PILOT / 2)
    return part


# --- tray ------------------------------------------------------------------------------------


def make_tray():
    x0, x1 = P.FIT, P.BOX_IN[0] - P.FIT
    y0, y1 = P.FIT, P.BOX_IN[1] - P.FIT

    tray = box(x0, x1, y0, y1, 0, P.FLOOR_T)
    # lighten the field, then cut the empty middle away: v2 leaves a rim and the two bands that
    # actually carry the posts, clips and sleeves, instead of a plate over the whole box
    tray -= box(x0 + 12, x1 - 12, y0 + 12, y1 - 12, P.FLOOR_FIELD, P.FLOOR_T + 1)
    for wx0, wx1, wy0, wy1 in P.FLOOR_WINDOWS:
        tray -= box(wx0, wx1, wy0, wy1, -1, P.FLOOR_T + 1)

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
    cell_x = P.cell_centre_x()
    for sx in (cell_x - P.SADDLE_INSET, cell_x + P.SADDLE_INSET):
        rail = box(
            sx - P.SADDLE_T / 2, sx + P.SADDLE_T / 2,
            centres[0] - P.CELL_D, centres[-1] + P.CELL_D,
            0, scallop_z,
        )
        for cy in centres:
            rail -= cyl_x(cy, scallop_z, sx - P.SADDLE_T / 2 - 1, sx + P.SADDLE_T / 2 + 1, P.CELL_D / 2 + P.SADDLE_CLEAR)
        tray += rail

    # pack board posts, flush with the board's underside, M3 self-tapping pilots
    pz = P.pack_z()
    for hx, hy in P.PACK_HOLES:
        tray += post(*P.board_xy(P.PACK_ORIGIN, P.PACK, hx, hy), pz)

    # carrier posts: in the margins, reaching in on gusseted arms. The gusset hangs from the arm,
    # full depth at the post and nothing at the hole, so it stays above the pack board it crosses.
    cz = P.carrier_z()
    arm_low = P.pack_z() + P.BOARD_T + P.ARM_CLEAR
    for (px, py), (hx, hy) in zip(P.carrier_post_xy(), P.carrier_hole_xy(), strict=True):
        tray += post(px, py, cz, pilot=False)  # no screw here: the carrier's hole is over the boss
        tray += tri_prism_x(hy, py, cz, arm_low, px, P.ARM_W)
        tray += cyl_z(hx, hy, cz - 4, cz, P.POST_R)
        tray -= cyl_z(hx, hy, cz - P.PILOT_DEPTH, cz + 1, P.POST_PILOT / 2)

    # cable clips
    tray += _cable_clips()
    return tray


def _cable_clips():
    clips = None
    for cx, cy in P.CLIP_XY:
        clip = box(cx - 5, cx + 5, cy - 6, cy + 6, 0, P.FLOOR_T + 8)
        clip -= cyl_x(cy, P.FLOOR_T + 5, cx - 6, cx + 6, P.CLIP_GROOVE_D / 2)
        clips = clip if clips is None else clips + clip
    return clips


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
        panel += cyl_z(cx, cy, z0 - P.button_boss_h(), z0, P.BUTTON_BOSS_R)
        panel -= cyl_z(cx, cy, z0 - P.button_boss_h() - 1, z0 + 1, P.BUTTON_D / 2 + 0.15)

    # LCD mounting bosses on the 93 x 55 grid
    for sx in (-1, 1):
        for sy in (-1, 1):
            px = P.LCD_CENTRE[0] + sx * P.LCD_HOLES[0] / 2
            py = P.LCD_CENTRE[1] + sy * P.LCD_HOLES[1] / 2
            panel += cyl_z(px, py, z0 - P.LCD_BOSS_H, z0, 3.5)
            panel -= cyl_z(px, py, z0 - P.LCD_BOSS_H - 1, z0 + 1, 1.6)
    return panel


# --- wall bushings ------------------------------------------------------------------------------


def make_bushing(device):
    """A reinforcement and O-ring ring around a drilled wall hole. Axis is +Z, sitting on the
    wall's outside face.

    Not a barrel. The hole is drilled at the device's own size, so there is no annulus left for
    a barrel wall: at 6.5 mm hole / 6.4 mm device the wall would be negative. What a bushing was
    ever for here is stopping a 3 mm PS/ABS wall cracking around a 22 or 30 mm hole, and giving
    the O-ring a flat seat, and a ring does both.
    """
    wp = P.WALL_PARTS[device]
    outer = wp["hole_d"] / 2 + P.BUSHING_FLANGE_D / 2
    bore = wp["device_d"] / 2
    gw, gd = P.ORING_GROOVE
    part = cyl_z(0, 0, -P.BUSHING_FLANGE, 0, outer)
    part -= cyl_z(0, 0, -P.BUSHING_FLANGE - 1, 1, bore)
    if outer - bore > gw + 1.0:
        part -= cyl_z(0, 0, -gd, 0.01, bore + gw)
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
    # the face-seal groove is a ring 2 mm outside the hole edge, in the wall-facing side, z = 0,
    # the side with the counterbore
    gw, gd = P.ORING_GROOVE
    r0 = P.SPEAKER_D / 2 + 2
    part -= cyl_z(0, 0, -0.01, gd, r0 + gw) - cyl_z(0, 0, -0.02, gd + 0.01, r0)
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


def template_sheets():
    """(name, shapes, label, bar_y) per drill sheet, in millimetres and already centred.

    Each sheet carries a 100 mm calibration bar, because the one thing that ruins a paper
    template is a printer quietly scaling it to 97 %. One sheet per drilled wall, seen from
    outside, floor edge towards the bar: two walls are 140 mm long and one sheet holding both
    would put a hole on the wrong one.
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

    sheets = [("lid", lid, "LID, seen from inside", -cy - 15)]
    side = {"x0": "bottom", "x1": "top", "y0": "right", "y1": "left"}  # in portrait, x0 at the bottom
    for wall, length in P.WALLS.items():
        holes = [(n, u, z, d) for n, w, u, z, d, _o in P.wall_holes() if w == wall]
        if not holes:
            continue
        # The outer face: the sheet goes on the outside, top edge on the rim (z = BOX_IN[2]),
        # bottom edge at z = -WALL (MEASURE: assumes the base slab is as thick as the side wall).
        # Holes are drawn at z - BOX_IN[2] / 2, so the rim sits at +BOX_IN[2] / 2.
        h = P.BOX_IN[2] + P.WALL
        shapes = [Pos(0, P.BOX_IN[2] / 2 - h / 2, 0) * Rectangle(length + 2 * P.WALL, h)]
        for _n, u, z, d in holes:
            # facing x0 or y1 from outside, u runs right to left
            x = length - u if wall in ("x0", "y1") else u
            shapes.append(Pos(x - length / 2, z - P.BOX_IN[2] / 2, 0) * Circle(d / 2))
        names = ", ".join(n for n, *_ in holes)
        label = f"WALL {wall} ({side[wall]}: {names}) - seen from outside - top edge = box rim"
        sheets.append((f"wall_{wall}", shapes, label, -P.BOX_IN[2] / 2 - 15))
    return sheets


def write_templates():
    import re

    written = []
    for name, shapes, label, bar_y in template_sheets():
        path = OUT / f"template_{name}.svg"
        svg = ExportSVG(margin=8)
        svg.add_layer("cuts", line_weight=0.4)
        svg.add_layer("label", line_weight=0.1)
        for s in shapes:
            svg.add_shape(s, layer="cuts")
        svg.add_shape(Pos(0, bar_y, 0) * Rectangle(100, 2), layer="cuts")
        faces = (Pos(0, bar_y - 8, 0) * Text(label, font_size=5)).faces()
        svg.add_shape(sorted(faces, key=lambda f: (round(f.center().X, 3), round(f.center().Y, 3))), layer="label")
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


# --- assembly ----------------------------------------------------------------------------------

# Where a wall's outside face meets (u, z), and the rotation that turns +Z into the inward normal.
WALL_FRAMES = {
    "x0": (lambda u, z: (-P.WALL, u, z), Rot(Y=90)),
    "x1": (lambda u, z: (P.BOX_IN[0] + P.WALL, u, z), Rot(Y=-90)),
    "y0": (lambda u, z: (u, -P.WALL, z), Rot(X=-90)),
    "y1": (lambda u, z: (u, P.BOX_IN[1] + P.WALL, z), Rot(X=90)),
}


def wall_frame(wall, u, z):
    at, rot = WALL_FRAMES[wall]
    return Pos(*at(u, z)) * rot


def box_shell():
    """The S-BOX base as a stand-in to look against: walls, floor, corner columns, drilled holes."""
    w = P.WALL
    shell = box(-w, P.BOX_IN[0] + w, -w, P.BOX_IN[1] + w, -w, P.BOX_IN[2])
    shell -= box(0, P.BOX_IN[0], 0, P.BOX_IN[1], 0, P.BOX_IN[2] + 1)
    for cx, cy in P.column_centres():
        shell += box(*P.column_box(cx, cy), 0, P.BOX_IN[2])
    for _n, wall, u, z, d, _o in P.wall_holes():
        shell -= wall_frame(wall, u, z) * cyl_z(0, 0, -1, w + 1, d / 2)
    return shell


def board_step(name):
    """A board as KiCad exports it, cached in out/boards/ until its .kicad_pcb changes.

    The default origin is the board's top-left corner with Y flipped up, so the outline spans
    x 0..W, y -H..0 (gen_pcb draws Edge.Cuts from 0,0).
    """
    pcb = HERE.parent / "kicad" / f"{name}.kicad_pcb"
    if not pcb.exists():
        raise SystemExit(f"no {name}.kicad_pcb in hardware/kicad/")
    step = OUT / "boards" / f"{name}.step"
    missing = 0
    if not step.exists() or step.stat().st_mtime < pcb.stat().st_mtime:
        step.parent.mkdir(exist_ok=True)
        tmp = step.with_suffix(".tmp")  # renamed into place only once complete, so a killed run can't be cached
        try:
            r = subprocess.run(["kicad-cli", "pcb", "export", "step", "-f", "-o", str(tmp), str(pcb)],
                               capture_output=True, text=True)
        except FileNotFoundError:
            raise SystemExit("kicad-cli (KiCad 9) is not on PATH; the assembly needs it to export the boards") from None
        if r.returncode:
            raise SystemExit(f"kicad-cli failed on {pcb.name}:\n{r.stdout}{r.stderr}")
        tmp.replace(step)
        missing = (r.stdout + r.stderr).count("Could not add 3D model")
    board = import_step(str(step))
    # every run, not just the export one: a cached bare plate hides the parts from the gate
    if len(board.solids()) == 1:
        print(f"note  {name}: bare board, no component models; the gate cannot see parts on it "
              "(install KiCad's 3D library, then delete out/boards/)")
    elif missing:
        print(f"note  {name}: {missing} footprints have no 3D model (install KiCad's 3D library)")
    return board


def placeholders():
    """Envelopes for what has no model: the cells, the Heltec stack, the panel devices."""
    cell_x = P.cell_centre_x()
    cell_z = P.CELL_BOTTOM_Z + P.CELL_D / 2
    z0 = P.panel_z0()
    out = {}
    for i, cy in enumerate(P.trough_centres_y()):
        out[f"cell_{i + 1}"] = cyl_x(cy, cell_z,
                                     cell_x - P.CELL_LEN / 2, cell_x + P.CELL_LEN / 2, P.CELL_D / 2)
    out["heltec_envelope"] = box(*P.carrier_box(), P.carrier_z() + P.BOARD_T, P.heltec_top())
    out["lcd"] = box(*P.lcd_box(), z0 - P.LCD_DEPTH, z0 - P.LCD_BOSS_H)
    out["nfc"] = box(*P.nfc_box(), z0 - P.NFC_DEPTH, z0)
    for i, (bx, by) in enumerate(P.BUTTON_XY):
        out[f"button_{i + 1}"] = cyl_z(bx, by, z0 - P.BUTTON_DEPTH, z0 + P.LID_T, P.BUTTON_D / 2)
    return out


def make_assembly(boards):
    """Everything in place, as {name: shape}. The drill guide is a tool, not part of the insert."""
    pack, carrier = boards
    parts = {"box": box_shell(), "tray": make_tray(), "lid": make_lid()}
    parts["pack_board"] = Pos(P.PACK_ORIGIN[0], P.PACK_ORIGIN[1] + P.PACK[1], P.pack_z()) * board_step(pack)
    parts["carrier_board"] = Pos(P.CARRIER_ORIGIN[0], P.CARRIER_ORIGIN[1] + P.CARRIER[1], P.carrier_z()) \
        * board_step(carrier)
    for name, wp in P.WALL_PARTS.items():
        # a bushing's z = 0 face is the wall side and the ring stands out along -Z
        parts[f"bushing_{name}"] = wall_frame(wp["wall"], wp["u"], wp["z"]) * make_bushing(name)
    s = P.SPEAKER_WALL
    # the grille's z = 0 face is the wall side too, but the plate stands out along +Z
    parts["grille"] = wall_frame(s["wall"], s["u"], s["z"]) * Rot(X=180) * make_grille()
    parts.update(placeholders())
    return parts


def _boxes_touch(a, b):
    """Bounding boxes share interior; unlike BoundBox.overlaps, containment counts."""
    return (a.min.X < b.max.X and b.min.X < a.max.X and a.min.Y < b.max.Y and b.min.Y < a.max.Y
            and a.min.Z < b.max.Z and b.min.Z < a.max.Z)


def check_assembly(parts):
    names = list(parts)
    boxes = {n: parts[n].bounding_box() for n in names}
    clashes = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if not _boxes_touch(boxes[a], boxes[b]):
                continue
            v = (parts[a] & parts[b]).volume
            if v > CLASH_MM3:
                clashes.append(f"FAIL  assembly: {a} and {b} share {v:.1f} mm3")
    if clashes:
        raise SystemExit("\n".join(clashes))
    print(f"ok    assembly: {len(names)} parts, no interference")


def write_assembly(boards, check):
    parts = make_assembly(boards)
    if check:
        check_assembly(parts)
    children = []
    for name, shape in parts.items():
        shape.label = name
        children.append(shape)
    asm = Compound(children=children)
    asm.label = "insert_assembly"
    export_step(asm, str(OUT / "assembly.step"))
    print("wrote out/assembly.step")


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
    shells = len(part.shells())
    if shells != 1:
        raise SystemExit(
            f"FAIL {name}: {shells} shells, so it encloses a cavity; MJF needs a "
            f"{P.RULES['escape']} mm escape hole into it"
        )
    limit_x = P.BOX_IN[0] - 2 * P.FIT + 1e-6
    limit_y = P.BOX_IN[1] - 2 * P.FIT + 1e-6
    if name in ("tray", "lid"):
        if sx > limit_x or sy > limit_y:
            raise SystemExit(f"FAIL {name}: {sx:.1f} x {sy:.1f} does not fit")
        if sx > 220 or sy > 220:
            raise SystemExit(f"FAIL {name}: does not fit a 220 x 220 bed")
        clash = max((part & col).volume for col in column_solids())
        if clash > CLASH_MM3:
            raise SystemExit(
                f"FAIL {name}: {clash:.1f} mm3 of it sits inside a solid corner column; "
                "the part cannot physically go into the box"
            )

    # guideline 1: the process has its own minimum, expressed largest-side first
    dims = sorted((sx, sy, sz), reverse=True)
    lo = sorted(P.RULES["min_build"], reverse=True)
    hi = sorted(P.RULES["max_build"], reverse=True)
    if any(d < m - 1e-6 for d, m in zip(dims, lo, strict=True)):
        raise SystemExit(
            f"FAIL {name}: {dims[0]:.1f} x {dims[1]:.1f} x {dims[2]:.1f} is under "
            f"{P.RULES['name']}'s {lo[0]:.0f} x {lo[1]:.0f} x {lo[2]:.0f} minimum build size"
        )
    if any(d > m + 1e-6 for d, m in zip(dims, hi, strict=True)):
        raise SystemExit(
            f"FAIL {name}: {dims[0]:.1f} x {dims[1]:.1f} x {dims[2]:.1f} exceeds "
            f"{P.RULES['name']}'s build envelope"
        )
    if name == "grille":
        r0 = P.SPEAKER_D / 2 + 2
        gw, gd = P.ORING_GROOVE
        if part.is_inside(Vector(r0 + gw / 2, 0, gd / 2)):
            raise SystemExit("FAIL grille: no O-ring groove in the wall-facing face")
        if not part.is_inside(Vector(r0 - 0.5, 0, gd / 2)):
            raise SystemExit("FAIL grille: the O-ring groove has no inner wall")
    print(f"ok    {name}: {sx:.1f} x {sy:.1f} x {sz:.1f}, {part.volume / 1000:.1f} cm3, {solids} solid")

def main(argv):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", default="all")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--boards", default="pack,carrier", help="pack and carrier board names")
    args = ap.parse_args(argv)

    OUT.mkdir(exist_ok=True)
    if args.part == "assembly":
        write_assembly(args.boards.split(","), args.check)
        return 0

    names = list(PARTS) + ["bus:" + d for d in P.WALL_PARTS]
    if args.part != "all":
        names = [n for n in args.part.split(",") if n]
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
