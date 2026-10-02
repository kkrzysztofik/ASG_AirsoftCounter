"""Every dimension for the Pawbol S-BOX 416-P insert.

No imports: check.py has to run on a plain /usr/bin/python3 with nothing installed.
Coordinates: origin at the inner floor corner of the box, +X along 190, +Y along 140, +Z up.
Sources are named per line; anything marked MEASURE is a placeholder until the box arrives.
"""

# --- enclosure -----------------------------------------------------------------------------
# Pawbol karta katalogowa, S-BOX 416_416B_416-P: the drawing note says A, B and C are INSIDE
# dimensions, so the 70 is the base interior and the lid recess sits on top of it.
BOX_IN = (190.0, 140.0, 70.0)  # MEASURE (firm per drawing, confirm with a rule)
WALL = 3.0                    # (196 - 190) / 2, confirmed by (146 - 140) / 2
LID_T = 3.0                   # MEASURE transparent lid plate
LID_RECESS = 8.0              # MEASURE depth available above the base rim
FIT = 0.4                     # drop-in clearance, whole part; tune on the coupon
FLOOR_T = 2.4                 # tray floor thickness

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
ARM_W = 8.0                   # width of the carrier bracket arms
BACKING = (26.0, 12.0)        # (width along the wall, depth into the box) per wall device

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
# hole_d = hole drilled in the wall, device_d = the device's own mounting thread/body
WALL_PARTS = {
    "key":   {"hole_d": 22.3, "device_d": 22.0, "wall": "long",  "u": 40.0, "z": 35.0},
    "usbc":  {"hole_d": 12.2, "device_d": 12.0, "wall": "short", "u": 30.0, "z": 45.0},
    "sma":   {"hole_d": 6.5,  "device_d": 6.4,  "wall": "long",  "u": 150.0, "z": 46.0},
    "buzzer": {"hole_d": 30.0, "device_d": 29.6, "wall": "long", "u": 95.0, "z": 46.0},
}
BACKING_H = 18.0               # half-height of a wall backing block
SPEAKER_WALL = {"wall": "long", "u": 40.0, "z": 30.0}  # Ø50, own grille plate
BUSHING_FLANGE = 4.0          # bushing flange thickness
BUSHING_LIP = 2.0             # bushing lip past the wall's inner face
BUSHING_FLANGE_D = 12.0       # extra flange diameter over the drilled hole
ORING_GROOVE = (1.5, 1.0)     # (width, depth) of the face-seal groove

# --- speaker mesh ---------------------------------------------------------------------------
MESH_OPEN = 0.40              # minimum open area over the speaker face
MESH_HOLE_D = 2.6             # round holes print stronger at this land width than slots
MESH_PITCH = 3.6              # triangular pitch; land = pitch - hole = 1.0 mm
GRILLE_RIM = 8.0              # grille plate radius over the speaker radius
GRILLE_T = 4.0                # total plate thickness
GRILLE_RECESS = 2.5           # inner counterbore, so each hole is only ~1.5 mm deep
GRILLE_BOLT_R = 32.0          # bolt circle for the grille screws


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
