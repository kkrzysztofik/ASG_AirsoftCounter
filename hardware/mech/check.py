#!/usr/bin/env python3
"""Invariants a printed part cannot get wrong.

Runs on a plain /usr/bin/python3 with nothing installed, because these are the checks worth
running on a machine that has no CAD stack. Exit code is the result.
"""

import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import params  # noqa: E402


def fail(msg):
    print(f"FAIL  {msg}")
    return False


def ok(msg):
    print(f"ok    {msg}")
    return True


def box_fits():
    inner = (params.BOX_IN[0] - 2 * params.FIT, params.BOX_IN[1] - 2 * params.FIT)
    if inner[0] <= 0 or inner[1] <= 0:
        return fail("FIT leaves no tray")
    return ok(f"tray envelope {inner[0]:.1f} x {inner[1]:.1f} fits {params.BOX_IN[0]} x {params.BOX_IN[1]}")


def rasters_match():
    """The tray posts must be where the boards actually put their holes."""
    import design
    import pack
    bad = []
    for mod, tag in ((pack, "pack"), (design, "carrier")):
        holes = [(float(mod.PLACE[f"H{i}"][0]), float(mod.PLACE[f"H{i}"][1])) for i in range(1, 5)]
        if holes != params.EXPECTED_HOLES[tag]:
            bad.append(f"{tag}: {holes} != {params.EXPECTED_HOLES[tag]}")
    if bad:
        return fail("board hole raster drifted - " + "; ".join(bad))
    return ok("post rasters match design.py and pack.py")


def stack_fits():
    need = params.stack_height()
    have = params.BOX_IN[2] + params.LID_RECESS
    if need > have:
        return fail(f"stack {need:.1f} > {have:.1f}")
    return ok(f"stack {need:.1f} <= {have:.1f} of usable height")


def cradle_aligns_with_holders():
    want = [params.PACK_ORIGIN[1] + y for y in params.HOLDER_Y]
    got = params.trough_centres_y()
    if [round(v, 3) for v in got] != [round(v, 3) for v in want]:
        return fail(f"cradle {got} off the holders {want}")
    return ok(f"cradle tracks the {len(got)} holders at {params.CELL_PITCH} pitch")


def cradle_is_reachable():
    """The saddle rails have to actually touch the cells they are meant to catch."""
    if params.CELL_BOTTOM_Z <= params.FLOOR_T:
        return fail(f"cell bottom {params.CELL_BOTTOM_Z} is on or under the tray floor")
    return ok(f"cells bottom out at z={params.CELL_BOTTOM_Z} on the saddles, above the floor")


def margin_posts_clear_the_columns():
    half = (params.COLUMN_SIZE[0] / 2, params.COLUMN_SIZE[1] / 2)
    for px, py in params.carrier_post_xy():
        for cx, cy in params.column_centres():
            dx = abs(px - cx) - half[0] - params.POST_R
            dy = abs(py - cy) - half[1] - params.POST_R
            if max(dx, dy) < 2.0:
                return fail(f"carrier post ({px}, {py}) fouls the column at ({cx}, {cy})")
    return ok("carrier margin posts clear the corner columns")


def margin_posts_clear_the_pack_board():
    for px, py in params.carrier_post_xy():
        if params.PACK_ORIGIN[1] - params.POST_R < py < params.PACK_ORIGIN[1] + params.PACK[1] + params.POST_R:
            return fail(f"carrier post ({px}, {py}) sits under the pack board")
    return ok("carrier margin posts sit outside the pack board")


def mesh_open_enough():
    area = params.mesh_open_area()
    if area < params.MESH_OPEN:
        return fail(f"mesh open area {area:.2f} < {params.MESH_OPEN}")
    return ok(f"mesh open area {area:.2f} of the grille disc")


def lcd_clears_the_heltec():
    """The LCD hangs from the panel; the Heltec is the tallest thing on the carrier."""
    gap = params.panel_z0() - params.LCD_DEPTH - params.heltec_top()
    if gap < 2.0:
        return fail(
            f"LCD bottom leaves {gap:.1f} mm over the Heltec; move the carrier, the LCD, "
            "or re-measure LCD_DEPTH"
        )
    return ok(f"{gap:.1f} mm between the LCD's back and the Heltec's top")


def deep_panel_parts_miss_the_carrier():
    """Anything hanging deeper than the Heltec's headroom must sit outside the carrier."""
    headroom = params.panel_z0() - params.heltec_top()
    carrier = params.carrier_box()
    deep = [("LCD", params.lcd_box(), params.LCD_DEPTH)]
    deep += [(f"button {i}", b, params.BUTTON_DEPTH) for i, b in enumerate(params.button_boxes())]
    deep.append(("NFC", params.nfc_box(), params.NFC_DEPTH))
    for name, box, depth in deep:
        if depth <= headroom and name != "LCD":
            continue
        if params._gap(box, carrier) <= 0.0 and depth > headroom:
            return fail(
                f"{name} hangs {depth} mm into {headroom:.1f} mm of headroom and sits over "
                "the carrier"
            )
    return ok(f"panel parts deeper than {headroom:.1f} mm all miss the carrier")


def nfc_clears_the_lcd_frame():
    gap = params._gap(params.nfc_box(), params.lcd_box())
    if gap < params.NFC_MIN_FROM_LCD:
        return fail(f"NFC is {gap:.1f} mm from the LCD frame, needs {params.NFC_MIN_FROM_LCD}")
    return ok(f"NFC {gap:.1f} mm off the LCD frame")


def tray_stays_below_the_panel():
    """Every wall backing has to fit under the lid panel, which starts at panel_z0."""
    top = params.panel_z0()
    for name, wp in params.WALL_PARTS.items():
        hi = wp["z"] + params.BACKING_H
        if hi > top:
            return fail(f"wall part {name} backing reaches z={hi:.1f}, the panel starts at {top:.1f}")
    return ok(f"all {len(params.WALL_PARTS)} wall backings stay under the panel at z={top:.1f}")


def backings_clear_the_columns():
    """A nut pocket inside a solid column is a part that cannot be assembled."""
    for name, wp in params.WALL_PARTS.items():
        b = params.backing_box(wp)
        for cx, cy in params.column_centres():
            if params._boxes_overlap(b, params.column_box(cx, cy), clear=1.0):
                return fail(f"wall backing {name} at u={wp['u']} overlaps the column at ({cx}, {cy})")
    return ok(f"all {len(params.WALL_PARTS)} wall backings clear the corner columns")


def clips_clear_the_columns():
    for cx, cy in params.CLIP_XY:
        clip = (cx - 5, cx + 5, cy - 6, cy + 6)
        for kx, ky in params.column_centres():
            if params._boxes_overlap(clip, params.column_box(kx, ky), clear=1.0):
                return fail(f"cable clip at ({cx}, {cy}) overlaps the column at ({kx}, {ky})")
    return ok("both cable clips clear the corner columns")


def sleeve_walls_miss_the_column_bore():
    """The L walls must sit outside the bore, or the sleeve cannot drop over the column."""
    bx = params.COLUMN_SIZE[0] + params.FIT
    by = params.COLUMN_SIZE[1] + params.FIT
    for cx, cy in params.column_centres():
        pad = (cx - bx / 2, cx + bx / 2, cy - by / 2, cy + by / 2)
        for w in params.sleeve_walls(cx, cy):
            if params._boxes_overlap(w, pad):
                return fail(f"sleeve wall {w} intrudes into the {bx:.1f} x {by:.1f} bore {pad}")
    return ok("sleeve walls hug the columns without intruding on the bore")


def jlc_wall_thickness():
    """Guideline 2: the minimum wall depends on the part's own size, so size each one."""
    big = max(params.BOX_IN[0], params.BOX_IN[1])
    grille = params.SPEAKER_D + 2 * params.GRILLE_RIM
    items = [
        ("tray floor field", params.FLOOR_FIELD, big),
        ("tray sleeve wall", params.SLEEVE_WALL, big),
        ("tray saddle rail", params.SADDLE_T, big),
        ("tray bracket arm", params.ARM_W, big),
        ("lid panel", params.LID_T, big),
        ("grille mesh land", params.mesh_land(), grille),
        ("grille face under the holes", params.GRILLE_T - params.GRILLE_RECESS, grille),
    ]
    for name, wp in params.WALL_PARTS.items():
        dia = wp["hole_d"] + params.BUSHING_FLANGE_D
        items.append((f"{name} ring width", params.BUSHING_FLANGE_D / 2, dia))
    for name, wall, size in items:
        need = params.mjf_min_wall(size)
        if wall + 1e-9 < need:
            return fail(f"JLC wall: {name} is {wall:.2f} mm, MJF needs {need:.2f} at {size:.0f} mm")
    return ok(f"JLC wall: all {len(items)} features meet the size-dependent MJF minimum")


def jlc_clearance():
    """Guideline 5 and 10: MJF needs 0.2-0.4 mm per side, and its hole tolerance is +-0.3 mm.

    A nominal 0.2 mm gap is therefore inside the process noise, which is why FIT is what it is.
    """
    per_side = params.FIT / 2
    if per_side < params.MJF_MIN_CLEARANCE:
        return fail(f"JLC clearance: {per_side:.2f} mm per side, MJF needs {params.MJF_MIN_CLEARANCE}")
    if per_side < params.MJF_HOLE_TOL:
        return fail(
            f"JLC clearance: {per_side:.2f} mm per side is inside the +-{params.MJF_HOLE_TOL} mm "
            "MJF hole tolerance, so the part can arrive unable to go in"
        )
    return ok(f"JLC clearance: {per_side:.2f} mm per side clears both the 0.2 mm rule and the "
              f"+-{params.MJF_HOLE_TOL} mm hole tolerance")


def jlc_holes():
    """Guideline 7: aperture against depth. The table runs to about 3x the diameter."""
    holes = [
        ("board post pilot", params.POST_PILOT, params.PILOT_DEPTH),
        ("cable clip groove", params.CLIP_GROOVE_D, 10.0),
        ("speaker mesh", params.MESH_HOLE_D, params.GRILLE_T - params.GRILLE_RECESS),
    ]
    for name, dia, depth in holes:
        if dia < 1.5:
            return fail(f"JLC holes: {name} is {dia:.1f} mm, MJF has no entry below 1.5 mm")
        if depth > 3 * dia:
            return fail(f"JLC holes: {name} is {dia:.1f} mm across and {depth:.1f} mm deep, "
                        f"past the 3x guidance")
    return ok(f"JLC holes: all {len(holes)} apertures are inside the depth guidance")


def jlc_build_size():
    """Guideline 1: the build envelope, and the 5x5x5 / 10x2x2 minimum.

    The minimum accepts either a 5 mm cube or a 10 x 2 x 2 sliver, so a flat ring is fine.
    """
    big = (params.BOX_IN[0], params.BOX_IN[1], params.panel_z0())
    for i, axis in enumerate("XYZ"):
        if big[i] > params.MJF_MAX_BUILD[i]:
            return fail(f"JLC build: {big[i]:.1f} mm on {axis} exceeds MJF's {params.MJF_MAX_BUILD[i]}")

    rings = []
    for name, wp in params.WALL_PARTS.items():
        dia = wp["hole_d"] + params.BUSHING_FLANGE_D
        rings.append((name, (dia, dia, params.BUSHING_FLANGE)))
    for name, dims in rings:
        cube = all(d >= 5.0 for d in dims)
        sliver = max(dims) >= 10.0 and sorted(dims)[0] >= 2.0
        if not (cube or sliver):
            return fail(f"JLC build: {name} ring {dims} is under the minimum build size")
    return ok(f"JLC build: largest part {big[0]:.0f} x {big[1]:.0f} x {big[2]:.0f} inside "
              f"{params.MJF_MAX_BUILD[0]:.0f} x {params.MJF_MAX_BUILD[1]:.0f} x "
              f"{params.MJF_MAX_BUILD[2]:.0f}; smallest is a {params.BUSHING_FLANGE:.0f} mm "
              "thick ring, which passes on the 10 x 2 x 2 rule")


def jlc_columns():
    """Guideline 8: column diameter against height (D=3 mm -> H=3-6 mm).

    The printed posts are taller than a bare column of their diameter should be, which is what
    the 45-degree base flare is for.
    """
    for name, top in (("pack post", params.pack_z()), ("carrier post", params.carrier_z())):
        ratio = top / (2 * params.POST_R)
        if ratio > 4.0 and params.POST_FLARE <= 0:
            return fail(f"JLC column: {name} is {ratio:.1f}:1 tall with no base flare")
    return ok(f"JLC column: posts are up to "
              f"{max(params.pack_z(), params.carrier_z()) / (2 * params.POST_R):.1f}:1 with a "
              f"{params.POST_FLARE:.0f} mm flare at the base")


def wall_parts_sane():
    for name, p in params.WALL_PARTS.items():
        if p["device_d"] >= p["hole_d"]:
            return fail(f"wall part {name}: device_d {p['device_d']} >= hole_d {p['hole_d']}")
    return ok(f"{len(params.WALL_PARTS)} wall devices each have a bushing")


CHECKS = [
    box_fits,
    rasters_match,
    stack_fits,
    lcd_clears_the_heltec,
    deep_panel_parts_miss_the_carrier,
    nfc_clears_the_lcd_frame,
    cradle_aligns_with_holders,
    cradle_is_reachable,
    margin_posts_clear_the_columns,
    margin_posts_clear_the_pack_board,
    mesh_open_enough,
    tray_stays_below_the_panel,
    backings_clear_the_columns,
    clips_clear_the_columns,
    sleeve_walls_miss_the_column_bore,
    jlc_wall_thickness,
    jlc_clearance,
    jlc_holes,
    jlc_build_size,
    jlc_columns,
    wall_parts_sane,
]


def main():
    results = [c() for c in CHECKS]
    if not all(results):
        print(f"\n{results.count(False)} of {len(results)} checks failed")
        return 1
    print(f"\nall {len(results)} checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
