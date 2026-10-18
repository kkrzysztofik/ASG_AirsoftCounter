"""Every dimension for the Pawbol S-BOX 416-P insert.

No third-party imports: check.py has to run on a plain /usr/bin/python3 with nothing installed.
Coordinates: origin at the inner floor corner of the box, +X along 190, +Y along 140, +Z up.
Sources are named per line; anything marked MEASURE is a placeholder until the box arrives.

Set MECH_PROCESS to validate for a different print process: p2s_petg (default), p2s_abs, or the
JLC3DP services mjf, fdm, sla.
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
PROCESS = os.environ.get("MECH_PROCESS", "p2s_petg")
# Home printing on the Bambu P2S, 0.4 mm nozzle (docs/plans/2026-10-11-p2s-prepurchase-design.md).
# Not a published guideline: wall = 3 perimeters of a 0.4 mm line, clearance and hole tolerance
# are first guesses until the coupon (insert.py --part coupon) is printed, build = the P2S volume.
# shrink is what Bambu Studio's filament "Shrinkage (XY)" must be set to; the model is nominal.
_P2S = {
    "wall": ((400.0, 1.2),),
    "clear": 0.2, "hole_tol": 0.2,  # MEASURE with the coupon's fit sweep
    "min_build": (0.0, 0.0, 0.0), "max_build": (256.0, 256.0, 256.0),
    "escape": 0.0,
}
PROCESS_RULES = {
    "p2s_petg": {**_P2S, "name": "PETG (Bambu P2S)", "shrink": 99.7},  # MEASURE, ~0.3 %
    # ABS shrinks ~0.7 %: 1.3 mm over the tray's 190, more than the whole FIT, so the slicer
    # compensation is not optional. Print it in the closed chamber, brim on the tray and lid.
    "p2s_abs": {**_P2S, "name": "ABS (Bambu P2S)", "shrink": 99.3},  # MEASURE, ~0.7 %
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

# Calibration coupon (insert.py --part coupon): a hole per clearance, and a loose peg to try them
COUPON_FITS = (0.15, 0.20, 0.25, 0.30, 0.40)   # per side; set RULES' clear from the one that slides
COUPON_PEG_D = 8.0


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
# v2: the floor is a rim plus two mount bands, with the empty middle cut away. The mounts are
# the posts, clips and sleeves at the two Y bands; everything between them only needs the two
# saddle rails, so the windows stop exactly at the rail edges: a window boundary inside a rail
# would leave a sliver of floor beside it. (x0, x1, y0, y1), asserted clear of every mount in
# check.py.
FLOOR_RIM = 12.0
FLOOR_WINDOWS = [
    (34.0, 68.5, 38.0, 102.0),
    (74.5, 112.5, 38.0, 102.0),
    (118.5, 176.0, 38.0, 102.0),
]
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

# --- boards (read from hardware/carrier.py and hardware/pack.py, asserted in check.py) --------
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
ARM_CLEAR = 2.0               # gap between a carrier arm's gusset and the pack board's top face
CARRIER_BOSS_H = 4.0          # depth of the carrier arm and of the screw boss under the carrier hole

PACK_ORIGIN = ((BOX_IN[0] - PACK[0]) / 2, (BOX_IN[1] - PACK[1]) / 2)          # (47, 25)
# shifted CARRIER_SHIFT toward x0: the pack's right-edge connectors (J_KEY1, J_PWR1, J_UART1, top up to
# z 35.9) stand at tray x >= 134.2, and the carrier's Heltec header pins come 1.8 mm below its underside
CARRIER_SHIFT = 7.0
CARRIER_ORIGIN = ((BOX_IN[0] - CARRIER[0]) / 2 - CARRIER_SHIFT, (BOX_IN[1] - CARRIER[1]) / 2)  # (43, 40)
STANDOFF_H = 8.0              # pack board -> carrier
HELTEC_H = 15.0               # Heltec in its 2x18 headers, above the carrier
HELTEC_PADS = ((44.82, 27.00), (88.00, 49.86))  # carrier-local pin 1 of J3 / pin 18 of J2 (carrier.py)
HELTEC_PCB = (51.7, 25.4)     # MEASURE the Heltec V4 module's board, centred on its header rows
PLUG_REACH = 16.0             # MEASURE a mated XH plug plus its wire bend, above the board's top face
HELTEC_SOCKET_H = 8.5         # MEASURE the 2x18 female headers the Heltec plugs into (KiCad PinSocket body)

# --- cells ----------------------------------------------------------------------------------
CELL_D = 18.4                 # 18650
CELL_LEN = 65.0
CELL_PITCH = 21.66            # MYOUNG holder pitch, pack design doc
HOLDER_X = 46.5                          # pack.PLACE["BT1".."BT4"] x, board space
HOLDER_Y = [12.35, 34.01, 55.67, 77.33]  # pack.PLACE["BT1".."BT4"] y, board space
# Cell bottom above the tray floor, where the saddles catch it; the pack board rests on the cell
# tops (pack_z), so this sets the stack.
CELL_BOTTOM_Z = 7.4           # MEASURE on the coupon
# The holder (14.9 mm) is shorter than the cell (18.4), but the extra 3.5 mm sticks out of the
# holder's open side, towards the floor, not through the board: through the holder's floor window
# the cell's top reaches the board at most. MEASURE on the coupon with a real cell.
PACK_OVERLAP = 0.0            # MEASURE how far the cell's top rises past the pack board's underside
SADDLE_T = 6.0                # saddle rail thickness along X (v2: was 8, 6 is plenty)
SADDLE_INSET = 22.0           # saddle rails sit this far either side of the cell centres
SADDLE_CLEAR = 0.4
LCD_DEPTH = 13.5              # Newhaven NHD-0420D3Z-FL-GBW-V3, 13.5 max depth, hangs below the panel
BUTTON_DEPTH = 25.0           # MEASURE behind-panel depth of a 16 mm IP65 button
NFC_DEPTH = 5.0               # PN532 module thickness

# --- panel devices --------------------------------------------------------------------------
BUTTON_D = 16.0               # budget generic 16 mm (Deluxe is 19)
BUTTON_BOSS_R = BUTTON_D / 2 + 5  # lid boss that clamps the button
SPEAKER_D = 50.0              # VISATON K 50
LCD = (98.0, 60.0)            # 20x4 module
LCD_HOLES = (93.0, 55.0)      # M2.5 grid (Newhaven: 4x Ø2.5 holes)
LCD_PILOT = 2.2               # M2.5 self-tapping pilot in the lid bosses
LCD_BOSS_H = 5.0              # lid bosses the LCD board hangs from
LCD_CENTRE = (95.0, 105.0)    # pushed to the top edge, leaving the buttons a clear band below
BUTTON_XY = [(56.0, 20.0), (96.0, 20.0)]    # below the carrier's footprint, so a 25 mm body fits
NFC_CENTRE = (133.5, 27.0)    # between button 2's lid boss and the (x1, y0) corner column, 20+ mm off
                              # the LCD; the lid webs either side are asserted printable in check.py
NFC_SIZE = 45.0
NFC_MIN_FROM_LCD = 20.0       # or the PN532 range dies
# hole_d = hole drilled in the wall, device_d = the device's own mounting thread/body.
# v2 dropped the tray's wall backing blocks: 23.3 cm3 of the old tray, a fifth of it, to hold a
# nut while you tighten a panel device. A nyloc and a finger do the same job.
# Which wall a device goes through: x0 / x1 are the 140 mm walls at x = 0 / 190, y0 / y1 the
# 190 mm walls at y = 0 / 140. u runs along the wall from the box origin (along Y on an x wall,
# along X on a y wall). Seen in portrait with x0 at the bottom: key and USB-C on the bottom wall,
# SMA on the top, buzzer and speaker on the left long wall (y1, the LCD side). Every hole has to
# clear the corner columns' reach along its wall, and its neighbours (asserted in check.py).
WALLS = {"x0": BOX_IN[1], "x1": BOX_IN[1], "y0": BOX_IN[0], "y1": BOX_IN[0]}  # length along u
WALL_PARTS = {
    "key":    {"hole_d": 22.3, "device_d": 22.0, "wall": "x0", "u": 50.0,  "z": 35.0},
    "usbc":   {"hole_d": 12.2, "device_d": 12.0, "wall": "x0", "u": 90.0,  "z": 45.0},
    "sma":    {"hole_d": 6.5,  "device_d": 6.4,  "wall": "x1", "u": 45.0,  "z": 46.0},
    "buzzer": {"hole_d": 30.0, "device_d": 29.6, "wall": "x1", "u": 85.0,  "z": 40.0},
}
# Cable tie points, inboard of the corner columns so a clip cannot end up inside one.
CLIP_XY = [(148.0, 30.0), (148.0, 110.0)]
CLIP_GROOVE_D = 4.4           # hole through a clip, for a small cable tie
SPEAKER_WALL = {"wall": "y1", "u": 85.0, "z": 30.0}  # Ø50, own grille plate; u 65 hit the left carrier post
# What each device puts inside the box, from the wall's inner face inward, terminals included:
# stages of (diameter, depth), front first, then the cable allowance behind the last stage for the
# plug or wire leaving its back. The assembly gate places these as envelopes.
# Parts from docs/OFFBOARD_PARTS.md.
CABLE_ALLOWANCE = 10.0        # MEASURE plug/wire leaving a wall device's back before it can bend
WALL_BODIES = {
    # BUDGET, not a part: the EAO 82-6121.2000 (series drawing: 60 behind the panel) does not fit.
    # At x0 the left carrier arm stands at x 42.5, so a key may have at most 32 mm behind the
    # wall plus its wire; 30 leaves 2.5 mm. Buy to this (docs/OFFBOARD_PARTS.md #10).
    "key":     (((30.0, 30.0),), CABLE_ALLOWANCE),
    "usbc":    (((16.0, 30.0),), CABLE_ALLOWANCE),  # MEASURE generic IP67 panel extension, no datasheet
    "sma":     (((9.2, 10.0),), CABLE_ALLOWANCE),   # MEASURE GSM-IPX/SMA-150 bulkhead: 8 mm AF nut across corners
    "buzzer":  (((43.0, 32.0),), CABLE_ALLOWANCE),  # MEASURE BZ-38 (PK35N29EPQ), TME Ø43 x 32 overall, all assumed inside
    # VISATON K 50 (2901): Ø50 x 17 overall, 2.7 front frame + 14.3 behind (TME, Farnell,
    # toutlehautparleur). Behind the frame the basket passes the 45 mm front-mount cutout. Its
    # tabs sit on the basket rim, so the wires leave sideways: no axial allowance.
    "speaker": (((50.0, 2.7), (45.0, 14.3)), 0.0),
}
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


def board_xy(origin, size, x, y):
    """A board point in tray coordinates. KiCad's Y runs down, so board y lands at size[1] - y."""
    return origin[0] + x, origin[1] + size[1] - y


def cell_centre_x():
    """The cells' axis midpoint along X, in tray coordinates."""
    return board_xy(PACK_ORIGIN, PACK, HOLDER_X, 0)[0]


def trough_centres_y():
    """Cell centre lines, in tray coordinates, ascending (the saddle rails span first to last)."""
    return sorted(board_xy(PACK_ORIGIN, PACK, 0, y)[1] for y in HOLDER_Y)


def carrier_post_xy():
    """Printed carrier posts.

    All four carrier holes land inside the pack board's footprint, so the posts cannot rise
    from the floor; they stand in the Y margin either side of the pack board and reach in on
    arms at the carrier's height.
    """
    y_lo = PACK_ORIGIN[1] - POST_R - 2.0
    y_hi = PACK_ORIGIN[1] + PACK[1] + POST_R + 2.0
    mid = PACK_ORIGIN[1] + PACK[1] / 2
    # one post per hole, in carrier_hole_xy's order, on the nearer margin: make_tray zips the two
    return [(hx, y_lo if hy < mid else y_hi) for hx, hy in carrier_hole_xy()]


def carrier_hole_xy():
    """Where the carrier's own M3 holes sit, in tray coordinates."""
    return [board_xy(CARRIER_ORIGIN, CARRIER, hx, hy) for hx, hy in CARRIER_HOLES]


def _centre_box(centre, size):
    return (centre[0] - size[0] / 2, centre[0] + size[0] / 2,
            centre[1] - size[1] / 2, centre[1] + size[1] / 2)


def lcd_box():
    return _centre_box(LCD_CENTRE, LCD)


def nfc_box():
    return _centre_box(NFC_CENTRE, (NFC_SIZE, NFC_SIZE))


def button_boxes():
    return [_centre_box(c, (BUTTON_D, BUTTON_D)) for c in BUTTON_XY]


def heltec_box():
    """(x0, x1, y0, y1) of the Heltec module, centred on its header rows."""
    (ax, ay), (bx, by) = (board_xy(CARRIER_ORIGIN, CARRIER, x, y) for x, y in HELTEC_PADS)
    cx, cy = (ax + bx) / 2, (ay + by) / 2
    return (cx - HELTEC_PCB[0] / 2, cx + HELTEC_PCB[0] / 2, cy - HELTEC_PCB[1] / 2, cy + HELTEC_PCB[1] / 2)


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


def column_reach(wall):
    """How far the corner columns' footprints reach along `wall`, from either end."""
    i = 1 if wall[0] == "x" else 0  # u runs along Y on an x wall
    return column_centres()[0][i] + COLUMN_SIZE[i] / 2


def wall_holes():
    """(name, wall, u, z, hole_d, outer_d) for every hole in a wall. outer_d is what sits on the
    outside face: the bushing ring, or the speaker's grille plate."""
    out = [(n, w["wall"], w["u"], w["z"], w["hole_d"], w["hole_d"] + BUSHING_FLANGE_D)
           for n, w in WALL_PARTS.items()]
    s = SPEAKER_WALL
    out.append(("speaker", s["wall"], s["u"], s["z"], SPEAKER_D, SPEAKER_D + 2 * GRILLE_RIM))
    return out
