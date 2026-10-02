"""Every dimension for the Pawbol S-BOX 416-P insert.

No third-party imports: check.py has to run on a plain /usr/bin/python3 with nothing installed.
Coordinates: origin at the inner floor corner of the box, +X along 190, +Y along 140, +Z up.
Sources are named per line; anything marked MEASURE is a placeholder until the box arrives.

Set MECH_PROCESS to price and validate for a different print process: mjf (default), fdm, sla.
"""

import os

# --- JLC3DP design guideline ------------------------------------------------------------------
# Source: https://jlc3dp.com/help/article/3d-printing-design-guideline, read 2026-10-02. The MJF
# column is the one that applies; the SLA/FDM figures are stricter or looser and we are not using
# them. Everything below is asserted in check.py so a rule cannot be quietly broken by a tweak.
GUIDE_SOURCE = "jlc3dp.com/help/article/3d-printing-design-guideline"


# --- print process ----------------------------------------------------------------------------
# Source: jlc3dp.com/help/article/3d-printing-design-guideline, read 2026-10-02. wall is the
# (largest part dimension, minimum wall) table; clear and hole_tol are millimetres per side.
PROCESS = os.environ.get("MECH_PROCESS", "mjf")
PROCESS_RULES = {
    "mjf": {
        "name": "Nylon (MJF)",
        "wall": ((50.0, 1.0), (100.0, 1.2), (200.0, 1.5), (400.0, 2.0)),
        "clear": 0.2, "hole_tol": 0.3,
        "min_build": (10.0, 2.0, 2.0), "max_build": (380.0, 284.0, 380.0),
        "escape": 2.5,
    },
    "fdm": {
        # FDM's wall row is '/' at 50 mm in the published table and the rest of it was behind a
        # truncated render, so the values below are our own defensible floor (3 perimeters of a
        # 0.4 mm nozzle), not a quoted figure. Everything else is from the table.
        "name": "Plastic (FDM)",
        "wall": ((100.0, 1.2), (200.0, 2.0), (400.0, 2.0)),
        "clear": 0.5, "hole_tol": 0.4,
        "min_build": (30.0, 30.0, 10.0), "max_build": (580.0, 480.0, 480.0),
        "escape": 2.5,
    },
    "sla": {
        "name": "Resin (SLA)",
        "wall": ((50.0, 0.5), (100.0, 0.8), (200.0, 1.0), (400.0, 1.5)),
        "clear": 0.2, "hole_tol": 0.3,
        "min_build": (5.0, 5.0, 5.0), "max_build": (780.0, 780.0, 530.0),
        "escape": 2.5,
    },
}
RULES = PROCESS_RULES[PROCESS]
# Which parts are being made by this process. The tray and lid are the FDM candidates; the
# grille, the guide ring and the wall rings are small flat parts that FDM's minimum build size
# rejects, so they stay on MJF or SLA and their features must not be judged against FDM's rules.
PARTS = os.environ.get("MECH_PARTS", "all")


def making(part):
    """True when this run is making that part, so per-part rules only apply to real parts."""
    return PARTS == "all" or part in PARTS.split(",")


def min_wall(max_dim):
    """Minimum wall a part of this size may have, for the selected process."""
    wall = RULES["wall"][0][1]
    for size, w in RULES["wall"]:
        if max_dim <= size:
            return w
        wall = w
    return wall


# --- enclosure -----------------------------------------------------------------------------
# Pawbol karta katalogowa, S-BOX 416_416B_416-P: the drawing note says A, B and C are INSIDE
# dimensions, so the 70 is the base interior and the lid recess sits on top of it.
BOX_IN = (190.0, 140.0, 70.0)  # MEASURE (firm per drawing, confirm with a rule)
WALL = 3.0                    # (196 - 190) / 2, confirmed by (146 - 140) / 2
LID_T = 2.5                   # printed lid panel thickness (the transparent lid is what faces weather)
LID_RECESS = 8.0              # MEASURE depth available above the base rim
# Drop-in clearance, whole part. The rule is per side and the bigger of the two constraints
# wins: the assembled-parts clearance, and the hole tolerance, because holes come out small.
# The 1.33 is margin for a first-off part.
FIT = round(2 * max(RULES["clear"], RULES["hole_tol"]) * 1.33, 1)
FLOOR_T = 2.4                 # tray floor thickness
# Floor left under the lightening pocket. Sized off the rule rather than picked, because FDM
# wants 2.0 mm where MJF wants 1.5 at this part size and the difference is not a free choice.
FLOOR_FIELD = round(min_wall(max(BOX_IN[0], BOX_IN[1])) + 0.1, 2)

# --- corner columns and screws --------------------------------------------------------------
# The drawing dimensions 148 and (probably) 99 span the corner screw axes. Only 148 is certain.
SCREW_RASTER = (148.0, 99.0)  # MEASURE 148 sourced, 99 inferred
COLUMN_SIZE = (20.0, 20.0)    # MEASURE corner column cross-section
SCREW_D = 4.0                 # MEASURE plastic screw; M4 assumed
SCREW_CLEAR = 0.3             # hole clearance over SCREW_D
SLEEVE_WALL = 2.0             # printed sleeve wall around a column
# A flange on the sleeve would have to fit between the column top (the base rim) and the lid
# plate, which share a plane. Until the box proves otherwise, 0 keeps the tray off the screw
# stack entirely and the lid panel's feet hold it down.
LEG_FLANGE_T = 0.0            # MEASURE; >0 only if the lid proves to have room

# --- boards (read from hardware/design.py and hardware/pack.py, asserted in check.py) --------
BOARD_T = 1.6
PACK = (96.0, 90.0)
CARRIER = (90.0, 60.0)
PACK_HOLES = [(4.0, 4.0), (92.0, 4.0), (4.0, 86.0), (92.0, 86.0)]
CARRIER_HOLES = [(3.5, 3.5), (86.5, 3.5), (3.5, 56.5), (86.5, 56.5)]
EXPECTED_HOLES = {"pack": PACK_HOLES, "carrier": CARRIER_HOLES}
POST_R = 4.0                  # printed post radius under an M3 self-tapper
POST_PILOT = 2.7              # M3 self-tapping pilot
POST_FLARE = 3.0              # 45-degree flare at a post's base: H/D guidance makes a bare
                              # column this tall too slender to survive bead blasting
POST_FLARE_H = 6.0
PILOT_DEPTH = 5.0             # hole depth for the M3 pilot; see the hole-aperture rule
ARM_W = 8.0                   # width of the carrier bracket arms
# A wall backing is a nut pocket, not a block. Thin and narrow also keeps it clear of the corner
# columns, which reach 31 mm in from the wall and will silently swallow anything wider.
BACKING = (20.0, 6.0)         # (width along the wall, depth into the box) per wall device
BACKING_H = 15.0              # half-height of a wall backing

PACK_ORIGIN = ((BOX_IN[0] - PACK[0]) / 2, (BOX_IN[1] - PACK[1]) / 2)          # (47, 25)
CARRIER_ORIGIN = ((BOX_IN[0] - CARRIER[0]) / 2, (BOX_IN[1] - CARRIER[1]) / 2)  # (50, 40)
STANDOFF_H = 8.0              # pack board -> carrier
HELTEC_H = 15.0               # Heltec in its 2x18 headers, above the carrier

# --- cells ----------------------------------------------------------------------------------
CELL_D = 18.4                 # 18650
CELL_LEN = 65.0
CELL_PITCH = 21.66            # MYOUNG holder pitch, pack design doc
HOLDER_Y = [12.35, 34.01, 55.67, 77.33]  # pack.PLACE["BT1".."BT4"] y, board space
# The holder's own floor holds the cell about this far above the pack board's underside, which
# puts the cell bottom this far above the tray floor. MEASURE on the coupon.
CELL_BOTTOM_Z = 7.4
PACK_OVERLAP = 3.5            # how far the cell protrudes past the holder's underside
SADDLE_T = 8.0                # saddle rail thickness along X
SADDLE_INSET = 22.0           # saddle rails sit this far either side of the cell centres
SADDLE_CLEAR = 0.4
LCD_DEPTH = 13.0              # MEASURE 20x4 + HW-61 backpack, hangs below the panel
BUTTON_DEPTH = 25.0           # MEASURE behind-panel depth of a 16 mm IP65 button
NFC_DEPTH = 5.0               # PN532 module thickness

# --- panel devices --------------------------------------------------------------------------
BUTTON_D = 16.0               # budget generic 16 mm (Deluxe is 19)
SPEAKER_D = 50.0              # VISATON K 50
LCD = (98.0, 60.0)            # 20x4 module
LCD_HOLES = (93.0, 55.0)      # M3 grid
LCD_CENTRE = (95.0, 105.0)    # pushed to the top edge, leaving the buttons a clear band below
BUTTON_XY = [(78.0, 20.0), (118.0, 20.0)]   # below the carrier's footprint, so a 25 mm body fits
NFC_CENTRE = (160.0, 25.0)    # bottom right: clear of the LCD frame and of the carrier
NFC_SIZE = 45.0
NFC_MIN_FROM_LCD = 20.0       # or the PN532 range dies
# hole_d = hole drilled in the wall, device_d = the device's own mounting thread/body.
# u is measured along the wall from the corner: every one of these has to clear the corner
# columns, whose footprints reach 31 mm in from each wall (asserted in check.py).
WALL_PARTS = {
    "key":   {"hole_d": 22.3, "device_d": 22.0, "wall": "long",  "u": 45.0, "z": 35.0},
    "usbc":  {"hole_d": 12.2, "device_d": 12.0, "wall": "short", "u": 55.0, "z": 45.0},
    "sma":   {"hole_d": 6.5,  "device_d": 6.4,  "wall": "long",  "u": 145.0, "z": 46.0},
    "buzzer": {"hole_d": 30.0, "device_d": 29.6, "wall": "long", "u": 95.0, "z": 46.0},
}
# Cable tie points, inboard of the corner columns so a clip cannot end up inside one.
CLIP_XY = [(148.0, 30.0), (148.0, 110.0)]
CLIP_GROOVE_D = 4.4           # hole through a clip, for a small cable tie
BACKING_H = 18.0               # half-height of a wall backing block
SPEAKER_WALL = {"wall": "long", "u": 40.0, "z": 30.0}  # Ø50, own grille plate
BUSHING_FLANGE = 4.0          # ring thickness. A ring, not a barrel: the wall is 3 mm of
                              # PS/ABS with a hole in it, and the ring is what stops it cracking
                              # and what seats the O-ring. There is no room for a barrel because
                              # the hole is drilled at the device's own size.
BUSHING_FLANGE_D = 12.0       # extra ring diameter over the drilled hole
ORING_GROOVE = (1.5, 1.0)     # (width, depth) of the face-seal groove

# --- speaker mesh ---------------------------------------------------------------------------
MESH_OPEN = 0.40              # minimum open area over the speaker face
MESH_HOLE_D = 3.5             # hole diameter; 3.5 mm is acoustically transparent well past
                              # 10 kHz at 1.5 mm deep, and gives the land room below
MESH_PITCH = 5.0              # triangular pitch; land 1.5 mm clears the 1.2 the MJF floor needs
                              # at this part size, and 85 holes still opens 42 %
GRILLE_RIM = 8.0              # grille plate radius over the speaker radius
GRILLE_T = 4.0                # total plate thickness
GRILLE_RECESS = 2.5           # inner counterbore, so each hole is only ~1.5 mm deep
GRILLE_BOLT_R = 32.0          # bolt circle for the grille screws


def _span(a, b):
    return (a, b) if a < b else (b, a)


def backing_box(wp):
    """(x0, x1, y0, y1) of a wall backing, so the model and the checks cannot disagree."""
    w, d = BACKING
    if wp["wall"] == "long":
        wall = BOX_IN[1] - FIT
        return (wp["u"] - w / 2, wp["u"] + w / 2, wall - d, wall)
    wall = BOX_IN[0] - FIT
    return (wall - d, wall, wp["u"] - w / 2, wp["u"] + w / 2)


def _boxes_overlap(a, b, clear=0.0):
    return (a[0] - clear < b[1] and b[0] - clear < a[1]
            and a[2] - clear < b[3] and b[2] - clear < a[3])


def column_box(cx, cy):
    return (cx - COLUMN_SIZE[0] / 2, cx + COLUMN_SIZE[0] / 2,
            cy - COLUMN_SIZE[1] / 2, cy + COLUMN_SIZE[1] / 2)


def sleeve_walls(cx, cy):
    """(x0, x1, y0, y1) of the two walls of a corner sleeve.

    An L rather than a closed tube: it still locates the tray in X and Y against the column,
    at a third of the material. The L faces away from the tray centre, so the four corners
    between them block motion in every direction.
    """
    bx = COLUMN_SIZE[0] + FIT
    by = COLUMN_SIZE[1] + FIT
    sx = -1.0 if cx < BOX_IN[0] / 2 else 1.0
    sy = -1.0 if cy < BOX_IN[1] / 2 else 1.0
    ix, ox = cx + sx * bx / 2, cx + sx * (bx / 2 + SLEEVE_WALL)
    iy, oy = cy + sy * by / 2, cy + sy * (by / 2 + SLEEVE_WALL)
    xa = _span(ox, ix)
    ya = _span(oy, cy)
    xb = _span(ox, cx)
    yb = _span(oy, iy)
    return (xa[0], xa[1], ya[0], ya[1]), (xb[0], xb[1], yb[0], yb[1])


def pack_z():
    """Underside of the pack board."""
    return CELL_BOTTOM_Z + CELL_D - PACK_OVERLAP


def carrier_z():
    """Underside of the carrier, standing on standoffs above the pack board."""
    return pack_z() + BOARD_T + STANDOFF_H


def heltec_top():
    """Top of the Heltec seated in the carrier. This is what has to clear the LCD."""
    return carrier_z() + BOARD_T + HELTEC_H


def panel_z0():
    """Underside of the lid panel: the sleeves stop here, the panel sits on their tops."""
    return BOX_IN[2] - LID_T


def stack_height():
    """Floor to the top of the Heltec, the number that has to fit BOX_IN[2] + LID_RECESS."""
    return heltec_top()


def column_centres():
    """The four corner screw axes, as (x, y)."""
    dx = (BOX_IN[0] - SCREW_RASTER[0]) / 2
    dy = (BOX_IN[1] - SCREW_RASTER[1]) / 2
    return [(dx, dy), (BOX_IN[0] - dx, dy), (dx, BOX_IN[1] - dy), (BOX_IN[0] - dx, BOX_IN[1] - dy)]


def trough_centres_y():
    """Cell centre lines, in tray coordinates."""
    return [PACK_ORIGIN[1] + y for y in HOLDER_Y]


def carrier_post_xy():
    """Printed carrier posts.

    All four carrier holes land inside the pack board's footprint, so the posts cannot rise
    from the floor; they stand in the Y margin either side of the pack board and reach in on
    arms at the carrier's height.
    """
    xs = [CARRIER_ORIGIN[0] + h[0] for h in CARRIER_HOLES[:2]]
    y_lo = PACK_ORIGIN[1] - POST_R - 2.0
    y_hi = PACK_ORIGIN[1] + PACK[1] + POST_R + 2.0
    return [(xs[0], y_lo), (xs[1], y_lo), (xs[0], y_hi), (xs[1], y_hi)]


def carrier_hole_xy():
    """Where the carrier's own M3 holes sit, in tray coordinates."""
    return [(CARRIER_ORIGIN[0] + h[0], CARRIER_ORIGIN[1] + h[1]) for h in CARRIER_HOLES]


def _centre_box(centre, size):
    return (centre[0] - size[0] / 2, centre[0] + size[0] / 2,
            centre[1] - size[1] / 2, centre[1] + size[1] / 2)


def lcd_box():
    return _centre_box(LCD_CENTRE, LCD)


def nfc_box():
    return _centre_box(NFC_CENTRE, (NFC_SIZE, NFC_SIZE))


def button_boxes():
    return [_centre_box(c, (BUTTON_D, BUTTON_D)) for c in BUTTON_XY]


def carrier_box():
    return (CARRIER_ORIGIN[0], CARRIER_ORIGIN[0] + CARRIER[0],
            CARRIER_ORIGIN[1], CARRIER_ORIGIN[1] + CARRIER[1])


def _gap(a, b):
    """Separating distance between two axis-aligned boxes; 0 if they overlap."""
    dx = max(a[0] - b[1], b[0] - a[1], 0.0)
    dy = max(a[2] - b[3], b[2] - a[3], 0.0)
    return (dx * dx + dy * dy) ** 0.5


def fit_per_side():
    return FIT / 2


def button_boss_h():
    """How far the lid panel's button bosses hang below it. Sized off the rule: some processes
    refuse a part whose smallest dimension is under their minimum, and this is what sets it, so
    the lid panel grows to 10 mm for FDM without any hand tuning.
    """
    return round(max(6.0, min(RULES["min_build"]) - LID_T), 2)


def mesh_land():
    return MESH_PITCH - MESH_HOLE_D


def mesh_open_area():
    """Open area over the speaker face, counted hole by hole on the triangular grid.

    Pure arithmetic, so it stays out of build123d and can be asserted by check.py.
    """
    import math
    R = SPEAKER_D / 2
    r = MESH_HOLE_D / 2
    row_h = MESH_PITCH * math.sqrt(3) / 2
    holes = 0
    k = -40
    while k <= 40:
        y = k * row_h
        if abs(y) <= R:
            off = MESH_PITCH / 2 if k % 2 else 0.0
            j = -40
            while j <= 40:
                x = off + j * MESH_PITCH
                if math.hypot(x, y) <= R - r:
                    holes += 1
                j += 1
        k += 1
    return holes * math.pi * r ** 2 / (math.pi * R ** 2)
