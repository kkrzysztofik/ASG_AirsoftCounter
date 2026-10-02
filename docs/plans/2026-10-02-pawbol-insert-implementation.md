# Pawbol insert Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Emit the base tray, lid panel, speaker grille and drill templates for the Pawbol S-BOX 416-P as parametric build123d parts, in millimetres, printable on a 220x220 PETG bed without supports.

**Architecture:** `params.py` is pure data with no imports, so the invariant check runs on plain `python3`. `insert.py` holds the build123d geometry and writes STEP + STL per part. `check.py` asserts the things a printed part cannot get wrong (envelope, board rasters, stack height, clearances) and runs without build123d installed. The board rasters are read from `hardware/design.py` and `hardware/pack.py` rather than retyped.

**Tech Stack:** Python 3.13, build123d 0.13.0 resolved through `uv` with PEP-723 inline metadata, `/usr/bin/python3` for the dependency-free check.

**Spec:** `docs/plans/2026-10-02-pawbol-insert-design.md`

## Global Constraints

- Units: millimetres throughout. Tray coordinates: origin at the box's inner floor corner, `+X` along 190, `+Y` along 140, `+Z` up.
- `params.py` imports nothing. `check.py` may import `params`, `design` and `pack` and must run under `/usr/bin/python3` with no third-party package installed.
- `insert.py` is the only file allowed to import build123d. No dimension literals in `insert.py`: every number comes from `params`.
- Declared toolchain: `uv run --with build123d` (build123d 0.13.0, verified importable 2026-10-02). No other new dependency; templates are SVG.
- Every part must fit a 220 x 220 mm bed and print in PETG **without supports**: no overhang past 45 degrees, cantilevers get a gusset.
- Mesh open area >= 40 %.
- Unmeasured dimensions stay named parameters with a documented default. None may be silently inlined.

## Review Focus

- **A part that is geometrically right but unprintable without supports.** The carrier arms and the corner-leg flange are the two overhangs; a 23 mm cantilever with no gusset is the likely miss.
- **Envelope clearances.** The tray must be strictly smaller than 190 x 140, not equal to it, or it will not drop into a real tub.
- **The corner leg.** Only feature with no second chance: if `COLUMN_SIZE` or `FIT` is wrong the whole tray reprints. The plan prints a coupon first.
- **The cradle fouling the holder contacts.** Troughs must sit under the cells, not push into the holder bodies or the bead NTCs.
- **Gussets and ribs colliding with the corner columns.** The margin posts sit close to the columns; a gusset that grows the wrong way hits one.

## File Structure

```
hardware/mech/
  params.py       every dimension, no imports
  check.py        plain-python invariants; exit != 0 on failure
  insert.py       build123d geometry + CLI; writes out/*.step, out/*.stl, out/print_1to1.svg
  out/            generated (gitignored except print_1to1.svg)
```

`hardware/Makefile` gains one target, `mech`, next to `boards`.

---

### Task 1: Parameters and the invariant check

**Files:**
- Create: `hardware/mech/params.py`
- Create: `hardware/mech/check.py`
- Modify: `hardware/.gitignore` (add `mech/out/*.step`, `mech/out/*.stl`)

**Interfaces:**
- Consumes: `hardware/design.py` (`W`, `H`, `PLACE["H1".."H4"]`) and `hardware/pack.py` (same names).
- Produces: `params.BOX_IN` `(190.0, 140.0, 70.0)`, `params.WALL` `3.0`, `params.FIT` `0.4`, `params.SCREW_RASTER` `(148.0, 99.0)`, `params.COLUMN_SIZE` `(20.0, 20.0)`, `params.SCREW_D` `4.0`, `params.LID_T` `3.0`, `params.LID_RECESS` `8.0`, `params.CELL_PITCH` `21.66`, `params.CELL_D` `18.4`, `params.STANDOFF_H` `8.0`, `params.FLOOR_T` `2.4`, `params.PACK_ORIGIN`, `params.CARRIER_ORIGIN`, `params.BUTTON_D` `16.0`, `params.SPEAKER_D` `50.0`, `params.MESH_OPEN` `0.40`, and `params.stack_height() -> float`.

- [ ] **Step 1: Write the failing check**

```python
# hardware/mech/check.py
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import params, design, pack

def box_fits(part_xy, name):
    assert part_xy[0] <= params.BOX_IN[0] - 2 * params.FIT, f"{name} too wide"

def rasters_match():
    for mod, tag in ((pack, "pack"), (design, "carrier")):
        holes = [(mod.PLACE[f"H{i}"][0], mod.PLACE[f"H{i}"][1]) for i in range(1, 5)]
        assert holes == params.EXPECTED_HOLES[tag], f"{tag} raster drifted: {holes}"

def stack_fits():
    assert params.stack_height() <= params.BOX_IN[2] + params.LID_RECESS

def mesh_open_enough():
    assert params.MESH_OPEN >= 0.40

def cradle_aligns_with_holders():
    assert params.trough_centres_y() == [params.PACK_ORIGIN[1] + y for y in params.HOLDER_Y]

def margin_posts_clear_the_columns():
    for (px, py) in params.carrier_post_xy():
        for (cx, cy) in params.column_centres():
            dx = abs(px - cx) - params.COLUMN_SIZE[0] / 2 - params.POST_R
            dy = abs(py - cy) - params.COLUMN_SIZE[1] / 2 - params.POST_R
            assert max(dx, dy) >= 2.0, f"carrier post {px},{py} is inside a column"
```

plus a `main()` that runs them, prints one line per check and `sys.exit(1)` on the first failure.

- [ ] **Step 2: Run it and watch it fail**

Run: `/usr/bin/python3 hardware/mech/check.py`
Expected: `ModuleNotFoundError: No module named 'params'` (or, once params exists, an `AttributeError` on `EXPECTED_HOLES`).

- [ ] **Step 3: Write `params.py`**

Every entry is `NAME = value  # source`. `EXPECTED_HOLES` holds `{"pack": [(4,4),(92,4),(4,86),(92,86)], "carrier": [(3.5,3.5),(86.5,3.5),(3.5,56.5),(86.5,56.5)]}` copied from `pack.py:482` and `design.py:278`. `stack_height()` returns the sum in the spec's height-budget table: `FLOOR_T + CELL_D + 1.6 + STANDOFF_H + 1.6 + HELTEC_H`, with `HELTEC_H = 15.0`. `SCREW_RASTER` defaults to `(148.0, 99.0)` with the comment that 148 is the drawing's own dimension and 99 is inferred, both to be calipered. Also provide `HOLDER_Y = [12.35, 34.01, 55.67, 77.33]` (from `pack.PLACE["BT1".."BT4"]`), `POST_R = 4.0`, `column_centres()`, `carrier_post_xy()`, `trough_centres_y()`, and `WALL_PARTS` as `{device: {"hole_d", "device_d", "wall_xy"}}`.

- [ ] **Step 4: Run the check and watch it pass**

Run: `/usr/bin/python3 hardware/mech/check.py`
Expected: four `ok` lines and exit 0.

- [ ] **Step 5: Prove the check can fail**

Temporarily set `FIT = 0.0` and `EXPECTED_HOLES["pack"][0] = (5, 5)`; run the check and confirm it exits non-zero with a message naming the part. Then move `HOLDER_Y[0]` by 1 mm and confirm the cradle check fires, and pull one carrier post onto a column centre and confirm the margin check fires. Revert all three.

- [ ] **Step 6: Commit**

```bash
git add hardware/mech/params.py hardware/mech/check.py hardware/.gitignore
git commit -m "mech: insert parameters and dependency-free invariant check"
```

---

### Task 2: Base tray

**Files:**
- Create: `hardware/mech/insert.py`
- Modify: `hardware/mech/check.py` (add a tray-envelope assertion once a bbox is available)

**Interfaces:**
- Consumes: everything in `params`.
- Produces: `insert.make_tray() -> build123d.Part`, `insert.write(part, name)` writing `out/<name>.stl` and `out/<name>.step`, and a CLI `python3 insert.py --part tray|lid|grille|guide|all`, `--check`.

- [ ] **Step 1: Add the failing geometry test**

```python
def test_tray_envelope():
    from insert import make_tray
    p = make_tray()
    bb = p.bounding_box()
    assert len(p.solids()) == 1
    assert p.volume > 0
    assert bb.size.X <= params.BOX_IN[0] - 2 * params.FIT
    assert bb.size.Y <= params.BOX_IN[1] - 2 * params.FIT
    assert bb.size.Z <= params.BOX_IN[2]
```

Run with `uv run --with build123d python hardware/mech/test_geometry.py`; expect `ImportError: cannot import name 'make_tray'`.

- [ ] **Step 2: Build the floor and the four corner legs**

The tray is the floor plate (`FLOOR_T`) inset by `FIT` on all four sides, minus a lightening pocket over the cell area, plus at each `SCREW_RASTER` corner a leg: a sleeve whose outer wall is `COLUMN_SIZE + FIT` and whose top flange sits at `BOX_IN[2]`, carrying a `SCREW_D + 0.3` clearance hole. Gusset every leg to the floor with a 45-degree rib.

- [ ] **Step 3: Add the cell cradle**

Four troughs along X, length `CELL_D + 50`, radius `CELL_D / 2 + 0.4`, centred on the pack board's holder Y positions transformed into tray space, i.e. `PACK_ORIGIN.y + PLACE["BT{n}"].y` for n = 1..4 (`12.35, 34.01, 55.67, 77.33` — read them from `params.HOLDER_Y`). Snap hold-down bar at each trough end, 0.6 mm interference, chamfered lead-in.

- [ ] **Step 4: Add the pack-board posts**

Four posts at `PACK_ORIGIN + hole`, top face at `FLOOR_T + CELL_D + 1.6`, i.e. flush with the pack board's underside, each with a Ø2.7 pilot for an M3 self-tapper.

- [ ] **Step 5: Add the carrier posts as margin brackets**

The carrier's four holes at `CARRIER_ORIGIN + hole` all fall inside the pack board's footprint, so the posts cannot rise from the floor to the carrier. Each carrier post instead stands in the Y margin (`y = FIT + 8` and `y = BOX_IN[1] - FIT - 8`), clear of the pack board and of the corner columns, and reaches its hole with an arm at the carrier's height. Gusset every arm from below at 45 degrees so the part prints unsupported. **This is a deliberate change from the spec's "4 posts for the carrier" and must be flagged in the commit message.**

- [ ] **Step 6: Add the wall backing blocks and cable clips**

Backing blocks sized per `params.WALL_PARTS` at each penetration's wall position; two cable clips for the XH-6 link and the key-switch pair.

- [ ] **Step 7: Write the CLI and outputs**

`--part tray` writes `out/tray.stl` (PETG, 0.2 mm layers, floor down) and `out/tray.step`; print the bounding box and volume; `--check` runs the Step 1 assertions on every part named.

- [ ] **Step 8: Run it**

Run: `uv run --with build123d python hardware/mech/insert.py --part tray --check`
Expected: `tray: 189.2 x 139.2 x 70.0, volume > 0, 1 solid` and exit 0, plus both files in `out/`.

- [ ] **Step 9: Commit**

```bash
git add hardware/mech/insert.py hardware/mech/test_geometry.py
git commit -m "mech: base tray with corner legs, cradle and carrier margin brackets

The carrier's holes all sit inside the pack board footprint, so its posts
stand in the Y margin and reach in on gusseted arms instead of rising from
the floor as the design doc assumed."
```

---

### Task 3: Lid panel

**Files:**
- Modify: `hardware/mech/insert.py`

**Interfaces:**
- Produces: `insert.make_lid() -> build123d.Part`.

- [ ] **Step 1: Add the failing test**

```python
def test_lid_envelope():
    from insert import make_lid
    p = make_lid()
    bb = p.bounding_box()
    assert len(p.solids()) == 1 and p.volume > 0
    assert bb.size.X <= params.BOX_IN[0] - 2 * params.FIT
    assert bb.size.Y <= params.BOX_IN[1] - 2 * params.FIT
    assert bb.size.Z <= params.LID_RECESS
```

- [ ] **Step 2: Build it**

Plate of `LID_T`. LCD frame pocket (98 x 60, 3 mm wall) that presses the module against the clear lid, with the 93 x 55 M3 positions as bosses. Two button bosses of `BUTTON_D` at the panel's lid-hole positions. PN532 pocket kept `>= 20 mm` from the LCD frame, asserted in `check.py`. Four corner ears in the screw stack (lid -> ear -> tray flange -> column), each with a slotted hole so the unmeasured raster has somewhere to go.

- [ ] **Step 3: Run it**

Run: `uv run --with build123d python hardware/mech/insert.py --part lid --check`
Expected: `lid: 189.2 x 139.2 x N`, 1 solid, exit 0.

- [ ] **Step 4: Commit**

```bash
git add hardware/mech/insert.py
git commit -m "mech: lid panel with LCD frame, button bosses and NFC pocket"
```

---

### Task 4: Wall bushings, speaker grille and drill guide ring

**Files:**
- Modify: `hardware/mech/insert.py`

**Interfaces:**
- Produces: `insert.make_bushing(device: str) -> build123d.Part` for each of `params.WALL_PARTS`, `insert.make_grille() -> build123d.Part`, `insert.make_guide() -> build123d.Part`.

- [ ] **Step 1: Add the failing test**

```python
def test_mesh_is_open_enough():
    from insert import make_grille
    g = make_grille()
    holes = params.mesh_open_area(g)          # computed from the emitted slot area
    assert holes >= params.MESH_OPEN

def test_every_wall_part_has_a_bushing():
    from insert import make_bushing
    for dev in params.WALL_PARTS:
        b = make_bushing(dev)
        assert len(b.solids()) == 1 and b.volume > 0
        assert params.WALL_PARTS[dev]["device_d"] < params.WALL_PARTS[dev]["hole_d"]
```

- [ ] **Step 2: Build the bushings**

One `make_bushing(device)` per entry in `params.WALL_PARTS` (`key`, `usbc`, `sma`, `buzzer`): a flange that seats on the wall's outside face, a barrel through the drilled hole, an O-ring groove on the flange's inner face, and the device's own thread or body bore through the middle. The `key` bushing reduces Ø37 to Ø22.3 and carries the hex/nut pocket; `sma` adds a hex pocket inside; `usbc` keeps the barrel's thread; `buzzer` gets a labyrinth behind its sound slots plus an O-ring.

- [ ] **Step 3: Build the grille and the guide ring**

Grille plate `SPEAKER_D + 2 * 8` across, 4 mm thick, slots (not round holes) giving >= 40 % open area, 3 mm rim, countersunk screw positions, and a gasket groove on the wall face. Guide ring is the same outer profile with a `SPEAKER_D + 0.2` bore and a clamp face — it exists only to hold a 50 mm holesaw.

- [ ] **Step 4: Run it**

Run: `uv run --with build123d python hardware/mech/insert.py --part bushings,grille,guide --check`
Expected: open area printed and >= 0.40, one bushing line per wall device, exit 0.

- [ ] **Step 5: Commit**

```bash
git add hardware/mech/insert.py
git commit -m "mech: per-device wall bushings, speaker mesh grille, drill guide ring"
```

---

### Task 5: 1:1 drill templates

**Files:**
- Modify: `hardware/mech/insert.py`

**Interfaces:**
- Produces: `out/print_1to1.svg`, plus PDF if a converter resolves.

- [ ] **Step 1: Emit the SVG**

build123d `ExportSVG` has no PDF sibling (verified 2026-10-02: `build123d.exporters` holds only `Export2D`, `ExportDXF`, `ExportSVG`), so the template is SVG in exact mm units with a **100 mm calibration bar** drawn on every sheet. Try `uv run --with build123d --with cairosvg python -c "import cairosvg"` once; if it resolves, also write `out/print_1to1.pdf`, otherwise the SVG is the deliverable and the check prints a note.

- [ ] **Step 2: Contents**

Lid sheet: the two `BUTTON_D` centres against the lid outline. Wall sheet: the speaker, key-switch, USB-C and SMA centres against the wall outline, with hole diameters labelled as text. Every sheet carries its calibration bar and the tray's inner outline.

- [ ] **Step 3: Verify the scale**

Run: `uv run --with build123d python hardware/mech/insert.py --part templates`, then open the SVG and confirm the calibration bar measures 100 mm with a steel rule. Expected: 100 mm +/- 0.5.

- [ ] **Step 4: Commit**

```bash
git add hardware/mech/insert.py hardware/mech/out/print_1to1.svg
git commit -m "mech: 1:1 drill templates with a 100 mm calibration bar"
```

---

### Task 6: `make mech` and the README line

**Files:**
- Modify: `hardware/Makefile` (add a `mech` target)
- Modify: `docs/plans/2026-10-02-pawbol-insert-design.md` (Status: model written)

- [ ] **Step 1: Add the target**

```make
MECH = mech
.PHONY: mech
mech:
	/usr/bin/python3 $(MECH)/check.py
	uv run --with build123d $(MECH)/insert.py --part all --check
```

- [ ] **Step 2: Run it**

Run: `make -C hardware mech`
Expected: the check's `ok` lines, then one line per part, exit 0.

- [ ] **Step 3: Commit**

```bash
git add hardware/Makefile docs/plans/2026-10-02-pawbol-insert-design.md
git commit -m "mech: make mech target; design doc status"
```

---

## Before the first real print

`make mech` proves the geometry, not the fit. Two things happen before the tray is printed:

1. **Fit coupon** — print one corner leg and one column sleeve alone, in PETG, and check it slides into a real corner column and the original screw still reaches the thread. This is the only interface that cannot be salvaged by reprinting a small part.
2. **Caliper** the items under "Must be measured" in the design doc and replace the defaults in `params.py`. `SCREW_RASTER` (148 x 99) and `COLUMN_SIZE` (20 x 20) are inference, not measurement.
