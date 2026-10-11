# Mech parts in FreeCAD: implementation plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** View the insert assembled with the boards in FreeCAD, and edit `params.py` numbers from a FreeCAD
sheet, with `check.py` and a new 3D interference check gating every change.

**Architecture:** `insert.py --part assembly` places every printed part, the KiCad boards (via `kicad-cli`) and
placeholder envelopes in one labelled STEP, and fails on any pairwise overlap. `freecad_sync.FCMacro`
`ast`-parses the plain numbers out of `params.py` into a FreeCAD spreadsheet and writes edits back as
byte-exact span replacements. It restores `params.py` and rebuilds `out/` if any check fails.

**Tech stack:** build123d 0.13 (PEP 723 script through uv), kicad-cli 9, FreeCAD 1.0+ (macro), plain Python 3.11+.

**Design:** `docs/plans/2026-10-11-freecad-port-design.md`. Every code block below was prototyped and run on
2026-10-11. The expected outputs are the real ones from that run.

**Decisions taken while planning (user-approved 2026-10-11):**
- **Wall layout**, seen in portrait from above the lid with x0 at the bottom: key and usbc on x0, sma on x1,
  buzzer and speaker on y1 (the LCD side). New u values clear the corner columns.
- **The carrier arm gusset is flipped** so it hangs from the arm above the pack board. Today the arms cut
  323 mm³ out of the pack board.
- **`PACK_OVERLAP = 0.0`, flagged MEASURE.** The cell's spare 3.5 mm sticks out of the holder's open side, not
  through the board. The stack grows to 52.0 mm of 78.
- **The grille gets the O-ring groove it was meant to have.** The current cut is 0.01 mm deep.

**Ground rules:**
- Run all commands from `hardware/` unless a step says otherwise.
- The main checkout has the hardware-cleanup work in flight (staged `pack_b` deletions, modified
  `Makefile`). Work in the worktree from Task 0, and never `git add -A`. Whichever branch merges second
  rebases. The only shared file is `Makefile`, and the edits are in different lines. After the cleanup, boards
  live in `hardware/kicad/`, which `board_step` already looks in first.
- Nothing here touches `hardware/mech/fab/`. The quote zips there go stale after Task 8. Regenerating them
  (`make mech-fab`) is the user's call, so ask first.

---

### Task 0: Worktree and baseline

**Step 1: Create the worktree** (from the repo root)

```bash
git worktree add ../ASG_AirsoftCounter-freecad -b mech-freecad esp32-lora-design
cd ../ASG_AirsoftCounter-freecad/hardware
```

**Step 2: Baseline**

Run: `make mech`
Expected: `all 21 checks passed`, then `ok` lines for tray (77.9 cm3), lid, grille (8.0 cm3), guide and four
bushings, and two template lines (`template_lid.svg`, `template_walls.svg`).

---

### Task 1: Wall layout data, and a check that guards it

**Files:**
- Modify: `hardware/mech/check.py` (new check, register it in `CHECKS`)
- Modify: `hardware/mech/params.py` (`WALL_PARTS` block, `SPEAKER_WALL`, two helpers at the end)

**Step 1: Write the failing check.** In `check.py`, add this function above `CHECKS = [`:

```python
def wall_holes_clear():
    """Each wall hole clears the corner columns, the tray floor and the lid panel, its outside
    part stays on the wall face, and no two outside parts on one wall overlap."""
    holes = params.wall_holes()
    for name, wall, u, z, d, outer in holes:
        if wall not in params.WALLS:
            return fail(f"wall hole {name}: wall {wall!r} is not one of {', '.join(params.WALLS)}")
        reach, length, r = params.column_reach(wall), params.WALLS[wall], d / 2
        if not reach + r <= u <= length - reach - r:
            return fail(f"wall hole {name}: u {u} puts the {d} mm hole inside a corner column's "
                        f"{reach:.1f} mm reach along {wall} (u must be {reach + r:.1f}..{length - reach - r:.1f})")
        if not params.FLOOR_T + r <= z <= params.panel_z0() - r:
            return fail(f"wall hole {name}: z {z} puts the {d} mm hole into the tray floor or the lid panel")
        if z - outer / 2 < -params.WALL - 1e-6 or u - outer / 2 < -params.WALL - 1e-6 \
                or u + outer / 2 > length + params.WALL + 1e-6:
            return fail(f"wall hole {name}: its {outer} mm outside part hangs off the {wall} wall face")
    for i, a in enumerate(holes):
        for b in holes[i + 1:]:
            gap = ((a[2] - b[2]) ** 2 + (a[3] - b[3]) ** 2) ** 0.5 - (a[5] + b[5]) / 2
            if a[1] == b[1] and gap < 0:
                return fail(f"wall holes {a[0]} and {b[0]}: their outside parts overlap by {-gap:.1f} mm on {a[1]}")
    return ok(f"{len(holes)} wall holes clear the columns, floor, lid and each other")
```

Then add `    wall_holes_clear,` as the last entry of `CHECKS` (after `wall_parts_sane,`).

**Step 2: Add the helpers it calls.** Append to the end of `params.py`:

```python
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
```

**Step 3: Run it and watch it fail**

Run: `/usr/bin/python3 mech/check.py | tail -3`
Expected: a traceback ending `AttributeError: module 'params' has no attribute 'WALLS'`.

**Step 4: The new layout.** In `params.py`, replace the two comment lines starting
`# u is measured along the wall from the corner` and the whole `WALL_PARTS = {...}` dict with:

```python
# Which wall a device goes through: x0 / x1 are the 140 mm walls at x = 0 / 190, y0 / y1 the
# 190 mm walls at y = 0 / 140. u runs along the wall from the box origin (along Y on an x wall,
# along X on a y wall). Seen in portrait with x0 at the bottom: key and USB-C on the bottom wall,
# SMA on the top, buzzer and speaker on the left long wall (y1, the LCD side). Every hole has to
# clear the corner columns' reach along its wall, and its neighbours (asserted in check.py).
WALLS = {"x0": BOX_IN[1], "x1": BOX_IN[1], "y0": BOX_IN[0], "y1": BOX_IN[0]}  # length along u
WALL_PARTS = {
    "key":    {"hole_d": 22.3, "device_d": 22.0, "wall": "x0", "u": 50.0,  "z": 35.0},
    "usbc":   {"hole_d": 12.2, "device_d": 12.0, "wall": "x0", "u": 90.0,  "z": 45.0},
    "sma":    {"hole_d": 6.5,  "device_d": 6.4,  "wall": "x1", "u": 70.0,  "z": 46.0},
    "buzzer": {"hole_d": 30.0, "device_d": 29.6, "wall": "y1", "u": 125.0, "z": 46.0},
}
```

and replace the `SPEAKER_WALL` line with:

```python
SPEAKER_WALL = {"wall": "y1", "u": 65.0, "z": 30.0}  # Ø50, own grille plate
```

**Step 5: Run it and watch it pass**

Run: `/usr/bin/python3 mech/check.py | tail -3`
Expected: `ok    5 wall holes clear the columns, floor, lid and each other` and `all 22 checks passed`.

**Step 6: Prove it catches the old speaker position**

```bash
/usr/bin/python3 -c "
import sys; sys.path[:0]=['mech','.']; import params; params.SPEAKER_WALL['u']=40.0
import check; sys.exit(0 if check.wall_holes_clear() else 1)"; echo "exit $?"
```
Expected: `FAIL  wall hole speaker: u 40.0 puts the 50.0 mm hole inside a corner column's 31.0 mm reach along y1 (u must be 56.0..134.0)` and `exit 1`.

**Step 7: Commit** (do not regenerate `out/` yet: the drill templates still read the old keys until Task 2)

```bash
git add mech/params.py mech/check.py
git commit -m "mech: wall layout per wall, asserted clear of columns and neighbours

Key and USB-C on x0, SMA on x1, buzzer and speaker on y1. The old speaker
position overlapped a corner column, and nothing checked it.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: One drill template per wall

The old sheet drew one "long" and one "short" wall. Two walls are now 140 mm long, so a shared sheet
would put the SMA hole on the key's wall. `template_shapes()` is dead code (no callers) that reads the
old keys, so delete it.

**Files:**
- Modify: `hardware/mech/insert.py` (delete `template_shapes`, rewrite `template_sheets`)
- Delete: `hardware/mech/out/template_walls.svg`

**Step 1: Delete `template_shapes()`** (the whole function, `def template_shapes():` up to `def template_sheets():`).

**Step 2: Replace `template_sheets()`** with:

```python
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
    for wall, length in P.WALLS.items():
        holes = [(u, z, d) for _n, w, u, z, d, _o in P.wall_holes() if w == wall]
        if not holes:
            continue
        shapes = [Rectangle(length, P.BOX_IN[2])]
        for u, z, d in holes:
            # facing x0 or y1 from outside, u runs right to left
            x = length - u if wall in ("x0", "y1") else u
            shapes.append(Pos(x - length / 2, z - P.BOX_IN[2] / 2, 0) * Circle(d / 2))
        sheets.append((f"wall_{wall}", shapes, f"WALL {wall}, seen from outside", -P.BOX_IN[2] / 2 - 15))
    return sheets
```

Mirroring: seen from outside, +u runs to the viewer's right on x1 and y0, and to the left on x0 and y1
(the right-hand direction is the view direction × Z). The key is at u=50 on x0, nearer the y=0 corner. From
outside x0 the y=0 corner is on your right, and the sheet draws the key right of centre (x = 140−50 = 90 → +20).

**Step 3: Run**

Run: `uv run mech/insert.py --part templates`
Expected:
```
ok    template_lid.svg: 1:1, 1 unit = 1 mm, 204.8 mm wide, 100 mm bar included
ok    template_wall_x0.svg: 1:1, 1 unit = 1 mm, 156.4 mm wide, 100 mm bar included
ok    template_wall_x1.svg: 1:1, 1 unit = 1 mm, 156.4 mm wide, 100 mm bar included
ok    template_wall_y1.svg: 1:1, 1 unit = 1 mm, 206.4 mm wide, 100 mm bar included
```

**Step 4: Commit**

```bash
git rm -q mech/out/template_walls.svg
git add mech/insert.py mech/out/template_lid.svg mech/out/template_wall_x0.svg mech/out/template_wall_x1.svg mech/out/template_wall_y1.svg
git commit -m "mech: one drill template per wall, seen from outside

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: The grille's O-ring groove

`make_grille()` cuts the groove at z ∈ [-1, 0.01], but the plate spans z ∈ [0, 4], so the groove is 0.01 mm deep.
The wall-facing side is z = 0 (the counterbore side), the same convention `make_bushing` uses.

**Files:** Modify `hardware/mech/insert.py` (`check_part`, `make_grille`, import `Vector`)

**Step 1: Write the failing check.** Add `Vector,` to the build123d import list, after `Rot,`. In `check_part`,
add these lines directly above the final `print(f"ok    {name}: ...`:

```python
    if name == "grille" and part.is_inside(Vector(P.SPEAKER_D / 2 + 1, 0, P.ORING_GROOVE[1] / 2)):
        raise SystemExit("FAIL grille: no O-ring groove in the wall-facing face")
```

**Step 2: Run it and watch it fail**

Run: `uv run mech/insert.py --part grille --check`
Expected: `FAIL grille: no O-ring groove in the wall-facing face`

**Step 3: Fix.** In `make_grille`, replace

```python
    gw, gd = P.ORING_GROOVE
    part -= cyl_z(0, 0, -gd, 0.01, P.SPEAKER_D / 2 + 2 + gw)
```
with
```python
    # the face-seal groove goes in the wall-facing side, z = 0, the side with the counterbore
    gw, gd = P.ORING_GROOVE
    part -= cyl_z(0, 0, -0.01, gd, P.SPEAKER_D / 2 + 2 + gw)
```

**Step 4: Run it and watch it pass**

Run: `uv run mech/insert.py --part grille --check`
Expected: `ok    grille: 66.0 x 66.0 x 4.0, 7.2 cm3, 1 solid` (it was 8.0)

**Step 5: Commit**

```bash
git add mech/insert.py mech/out/grille.stl mech/out/grille.step
git commit -m "mech: grille gets its O-ring groove (was cut 0.01 mm deep)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Name the LCD boss height

The assembly needs it for the LCD placeholder, and it becomes editable in FreeCAD. No geometry change.

**Files:** `hardware/mech/params.py`, `hardware/mech/insert.py`

**Step 1:** In `params.py`, after the `LCD_HOLES` line, add:
```python
LCD_BOSS_H = 5.0              # lid bosses the LCD board hangs from
```
**Step 2:** In `make_lid`, replace
```python
            panel += cyl_z(px, py, z0 - 5, z0, 3.5)
            panel -= cyl_z(px, py, z0 - 6, z0 + 1, 1.6)
```
with
```python
            panel += cyl_z(px, py, z0 - P.LCD_BOSS_H, z0, 3.5)
            panel -= cyl_z(px, py, z0 - P.LCD_BOSS_H - 1, z0 + 1, 1.6)
```
**Step 3:** Run `uv run mech/insert.py --part lid --check`. Expected: `ok    lid: 188.4 x 138.4 x 8.5, 45.6 cm3, 1 solid` (unchanged).

**Step 4: Commit**
```bash
git add mech/params.py mech/insert.py
git commit -m "mech: name the LCD boss height

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Assembly export and interference gate

**Files:**
- Modify: `hardware/mech/insert.py` (imports, `CLASH_MM3`, assembly section, `main`)
- Modify: `.gitignore` (repo root): add `hardware/mech/out/boards/`

Facts the code relies on (measured on 2026-10-11):
- kicad-cli's default STEP origin is the board's **top-left corner, with Y flipped up**, so the outline spans
  x 0..W, y −H..0 and the body runs z 0..1.51. Placing it at `(origin_x, origin_y + H, z)` puts it physically
  right side up.
- No component models export. `${KICAD9_3DMODEL_DIR}` is not installed, so the boards are bare plates.
  Installing KiCad's 3D library adds them with no code change.
- build123d's `Rot(Y=90)` maps +Z to +X, `Rot(Y=-90)` maps +Z to −X, `Rot(X=-90)` maps +Z to +Y, and
  `Rot(X=90)` maps +Z to −Y.
- A `Compound(children=...)` with `.label`s exports as named STEP products, which become FreeCAD tree names.

**Step 1: Imports.** Replace the top import block (from `import math` through the build123d import list) so it
reads:

```python
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
        Vector,
        export_step,
        export_stl,
        extrude,
        import_step,
    )
```

and below `OUT = HERE / "out"` add:

```python
CLASH_MM3 = 1.0  # overlap below this is boolean noise on touching faces, not a collision
```

Also change `if clash > 1.0:` in `check_part` to `if clash > CLASH_MM3:`.

**Step 2: The assembly section.** Insert directly above `# --- driver ---`:

```python
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
    hw = HERE.parent
    pcb = next((p for p in (hw / "kicad" / f"{name}.kicad_pcb", hw / f"{name}.kicad_pcb") if p.exists()), None)
    if pcb is None:
        raise SystemExit(f"no {name}.kicad_pcb in hardware/kicad/ or hardware/")
    step = OUT / "boards" / f"{name}.step"
    if not step.exists() or step.stat().st_mtime < pcb.stat().st_mtime:
        step.parent.mkdir(exist_ok=True)
        r = subprocess.run(["kicad-cli", "pcb", "export", "step", "-f", "-o", str(step), str(pcb)],
                           capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(f"kicad-cli failed on {pcb.name}:\n{r.stdout}{r.stderr}")
        missing = (r.stdout + r.stderr).count("Could not add 3D model")
        if missing:
            print(f"note  {name}: {missing} footprints have no 3D model (install KiCad's 3D library)")
    return import_step(str(step))


def placeholders():
    """Envelopes for what has no model: the cells, the Heltec stack, the panel devices."""
    cell_x = P.PACK_ORIGIN[0] + P.PACK[0] / 2
    cell_z = P.CELL_BOTTOM_Z + P.CELL_D / 2
    z0 = P.panel_z0()
    out = {}
    # where the board puts the cells: KiCad's Y runs down, so board y lands at PACK[1] - y
    for i, y in enumerate(P.HOLDER_Y):
        out[f"cell_{i + 1}"] = cyl_x(P.PACK_ORIGIN[1] + P.PACK[1] - y, cell_z,
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


def check_assembly(parts):
    names = list(parts)
    boxes = {n: parts[n].bounding_box() for n in names}
    clashes = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if not boxes[a].overlaps(boxes[b]):
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
```

The cells are placed where the board puts them (`PACK[1] - y`), not where the tray assumes they are
(`PACK_ORIGIN[1] + y`, see `trough_centres_y`). The two differ by 0.32 mm, inside the 0.4 mm saddle
clearance. Don't "fix" that here. Mention it in the final report.

**Step 3: `main`.** Replace `main()` with:

```python
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
```

**Step 4: Ignore the board cache.** Append `hardware/mech/out/boards/` to the repo-root `.gitignore`.

**Step 5: Run the gate and watch it find the two known defects**

Run: `uv run mech/insert.py --part assembly --check` (about 20 s)
Expected, give or take the last digit:
```
note  pack: 108 footprints have no 3D model (install KiCad's 3D library)
note  carrier: 45 footprints have no 3D model (install KiCad's 3D library)
FAIL  assembly: tray and pack_board share 322.7 mm3
FAIL  assembly: pack_board and cell_1 share 1278.1 mm3
FAIL  assembly: pack_board and cell_2 share 1278.1 mm3
FAIL  assembly: pack_board and cell_3 share 1278.1 mm3
FAIL  assembly: pack_board and cell_4 share 1278.1 mm3
```
Any other FAIL line means a placement bug in Step 2. Stop and debug it. Do not raise `CLASH_MM3`.

**Step 6: Commit** (the gate isn't in `make mech` until Task 8, so the build stays green)

```bash
git add mech/insert.py ../.gitignore
git commit -m "mech: assembly STEP with boards and placeholders, pairwise interference gate

Finds two existing defects, fixed next: the carrier arm gussets cut
through the pack board, and the cells pass through it.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Hang the carrier arm gusset from the arm

**Files:** `hardware/mech/params.py`, `hardware/mech/insert.py`

**Step 1:** In `params.py`, after `ARM_W`, add:
```python
ARM_CLEAR = 2.0               # gap between a carrier arm's gusset and the pack board's top face
```

**Step 2:** In `insert.py`, replace the `tri_prism_x` docstring's first paragraph and the overhang sentence
(everything above `Recentred from the built shape's own bounds`) with:

```python
    """A wedge in the YZ plane, extruded `width` along X: the bracket gusset.

    Vertices run (y0, z0) -> (y1, z0) -> (y1, z1): a right angle at (y1, z0), the slope from
    (y0, z0) to (y1, z1). Pass the ends in either order to put the right angle where you want it.

    Recentred from the built shape's own bounds rather than assuming which way the extrusion
```

**Step 3:** In `make_tray`, replace the carrier-post block (from `# carrier posts: in the margins` through the
`tray += cyl_z(hx, hy, cz - 4, cz, P.POST_R)` line) with:

```python
    # carrier posts: in the margins, reaching in on gusseted arms. The gusset hangs from the arm,
    # full depth at the post and nothing at the hole, so it stays above the pack board it crosses.
    cz = P.carrier_z()
    arm_low = P.pack_z() + P.BOARD_T + P.ARM_CLEAR
    for (px, py), (hx, hy) in zip(P.carrier_post_xy(), P.carrier_hole_xy(), strict=True):
        tray += post(px, py, cz)
        tray += tri_prism_x(hy, py, cz, arm_low, px, P.ARM_W)
        tray += cyl_z(hx, hy, cz - 4, cz, P.POST_R)
```

Swapping the ends makes `tri_prism_x` put the right angle at (post, carrier top). The gusset is full depth at
the post and comes to nothing at the hole. Its underside slopes at about 17°: fine on MJF (powder-supported),
but it needs support on FDM.

**Step 4: Run**

Run: `uv run mech/insert.py --part tray --check && uv run mech/insert.py --part assembly --check 2>&1 | grep -v ^note`
Expected: tray `ok`, then only the four `pack_board and cell_N` FAIL lines remain.

**Step 5: Commit**
```bash
git add mech/params.py mech/insert.py
git commit -m "mech: carrier arm gusset hangs from the arm, clear of the pack board

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: The cell sits under the board, not through it

**Files:** `hardware/mech/params.py`

**Step 1:** Replace the `PACK_OVERLAP = 3.5 ...` line with:

```python
# The holder (14.9 mm) is shorter than the cell (18.4), but the extra 3.5 mm sticks out of the
# holder's open side, towards the floor, not through the board: through the holder's floor window
# the cell's top reaches the board at most. MEASURE on the coupon with a real cell.
PACK_OVERLAP = 0.0            # how far the cell's top rises past the pack board's underside
```

**Step 2: Run everything**

Run: `/usr/bin/python3 mech/check.py | grep -E 'FAIL|stack|checks' && uv run mech/insert.py --part assembly --check 2>&1 | grep -v ^note`
Expected:
```
ok    stack 52.0 <= 78.0 of usable height
all 22 checks passed
ok    assembly: 19 parts, no interference
wrote out/assembly.step
```

**Step 3: The other process too**

Run: `MECH_PROCESS=fdm uv run mech/insert.py --part assembly --check 2>&1 | grep -v ^note`
Expected: `ok    assembly: 19 parts, no interference`

**Step 4: Commit**
```bash
git add mech/params.py
git commit -m "mech: cells sit under the pack board (PACK_OVERLAP 3.5 -> 0, MEASURE)

The holder is 3.5 mm shorter than the cell, but the excess sticks out of
the open side, not through the board. Board, carrier and Heltec rise 3.5 mm;
the stack is 52.0 of 78 mm.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: The gate goes into `make mech`, outputs regenerate

**Files:** `hardware/Makefile` (the `mech:` target), `hardware/mech/out/*`

**Step 1:** In the `mech:` recipe, add a third line after `uv run mech/insert.py --part $(PARTS) --check`:
```make
	uv run mech/insert.py --part assembly --check
```
and in the comment block above it, add the line:
`# The assembly (out/assembly.step) places every part with the boards and fails on any overlap.`

**Step 2: Run**

Run: `make mech`
Expected: `all 22 checks passed`, four template lines, eight part `ok` lines (tray about 71.9 cm3, grille 7.2),
then `ok    assembly: 19 parts, no interference`.

**Step 3: Commit the regenerated outputs**
```bash
git status --short mech/out   # expect tray, lid, grille and the bushings modified (or unchanged), and assembly.step new
git add Makefile mech/out/*.stl mech/out/*.step mech/out/*.svg
git commit -m "mech: make mech runs the assembly gate; regenerate outputs

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: FreeCAD sync macro, plain-Python half (TDD)

**Files:** Create `hardware/mech/freecad_sync.FCMacro`

**Step 1: Write the test first.** Create the file containing only the module docstring, the imports, the
constants, `selftest()` and the `--selftest` dispatch from the final file in Task 10. Make `leaves` and `rewrite`
stubs that `raise NotImplementedError`.

**Step 2: Run it and watch it fail**

Run: `/usr/bin/python3 mech/freecad_sync.FCMacro --selftest`
Expected: `NotImplementedError`

**Step 3: Implement** `_number`, `leaves`, `rewrite` and `digest` exactly as in the final file below.

**Step 4: Run it and watch it pass**

Run: `/usr/bin/python3 mech/freecad_sync.FCMacro --selftest`
Expected: `ok    selftest: 45 leaves, 3 edits touch exactly 3 lines, comments intact`.

Why byte offsets: `ast` reports `col_offset` in UTF-8 bytes, and `params.py` contains `Ø` and `×`. Slicing the
encoded line keeps the edit exact even when a non-ASCII character sits earlier on the line.

**Step 5: Commit**
```bash
git add mech/freecad_sync.FCMacro
git commit -m "mech: freecad_sync parses and rewrites params.py numbers byte-exactly

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: FreeCAD sync macro, FreeCAD half

**Files:** Modify `hardware/mech/freecad_sync.FCMacro` to its final form:

```python
"""Edit the insert's dimensions in FreeCAD, with params.py staying the source of truth.

Run it once (Macro > Macros..., or a toolbar button): it opens out/assembly.step and adds a
Params sheet with every plain number in params.py. Edit values in the sheet, run it again: the
changed numbers go into params.py, the parts are rebuilt and checked, and the assembly reloads.
A failed check puts params.py back as it was and keeps your edits in the sheet.

Only scalars are editable; tuples, lists and derived values stay in params.py. Needs uv on the
PATH FreeCAD sees. Test the non-GUI half on a plain Python:

    /usr/bin/python3 hardware/mech/freecad_sync.FCMacro --selftest
"""

import ast
import hashlib
import os
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
PARAMS = HERE / "params.py"
ASSEMBLY = HERE / "out" / "assembly.step"
SHEET = "Params"
MEASURE_RGB = (1.0, 0.95, 0.6)


# --- params.py, no FreeCAD ------------------------------------------------------------------------


def _number(node):
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        inner = _number(node.operand)
        return None if inner is None else -inner
    return None


def leaves(text):
    """[(name, value, line, col, end_col, comment)] for every top-level `NAME = <number>`.

    line is 1-based, col and end_col are UTF-8 byte offsets of the value, as ast gives them.
    """
    lines = text.splitlines()
    out = []
    for node in ast.parse(text).body:
        if not (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)):
            continue
        value = _number(node.value)
        if value is None or node.value.lineno != node.value.end_lineno:
            continue
        raw = lines[node.lineno - 1].encode()
        rest = raw[node.value.end_col_offset:].decode()
        comment = rest.split("#", 1)[1].strip() if "#" in rest else ""
        out.append((node.targets[0].id, value, node.value.lineno,
                    node.value.col_offset, node.value.end_col_offset, comment))
    return out


def rewrite(text, changes):
    """text with each changed value's span replaced; every other byte untouched."""
    lines = text.splitlines(keepends=True)
    for name, value, line, col, end, _c in leaves(text):
        if name not in changes:
            continue
        new = changes[name]
        lit = str(int(new)) if isinstance(value, int) and float(new).is_integer() else repr(float(new))
        raw = lines[line - 1].encode()
        lines[line - 1] = (raw[:col] + lit.encode() + raw[end:]).decode()
    return "".join(lines)


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def selftest():
    text = PARAMS.read_text()
    found = {leaf[0]: leaf for leaf in leaves(text)}
    assert {"WALL", "LID_T", "BUTTON_D"} <= set(found), sorted(found)
    assert "BOX_IN" not in found and "FIT" not in found, "tuples and derived values are not leaves"
    changes = {"WALL": 3.25, "LID_T": 2.0, "BUTTON_D": 19.0}
    new = rewrite(text, changes)
    old_lines, new_lines = text.splitlines(), new.splitlines()
    assert len(old_lines) == len(new_lines)
    diff = [(a, b) for a, b in zip(old_lines, new_lines) if a != b]
    assert len(diff) == 3, diff
    for a, b in diff:
        assert a.split("#", 1)[1:] == b.split("#", 1)[1:], (a, b)  # comment survives byte for byte
    after = {leaf[0]: leaf[1] for leaf in leaves(new)}
    assert all(after[k] == v for k, v in changes.items()), after
    assert rewrite(text, {}) == text
    assert rewrite("N = 4  # int\n", {"N": 5.0}) == "N = 5  # int\n"
    assert rewrite("N = -1.5\n", {"N": -2.0}) == "N = -2.0\n"
    print(f"ok    selftest: {len(found)} leaves, 3 edits touch exactly 3 lines, comments intact")
    return 0


# --- FreeCAD ----------------------------------------------------------------------------------------


def _uv():
    for c in (shutil.which("uv"), os.path.expanduser("~/.local/bin/uv"), os.path.expanduser("~/.cargo/bin/uv")):
        if c and os.path.exists(c):
            return c
    raise RuntimeError("uv not found. FreeCAD's PATH is:\n" + os.environ.get("PATH", ""))


def _run_checks():
    """(ok, output) for the full rebuild. check.py goes first: it is instant and writes nothing,
    while insert.py rewrites out/ part by part."""
    uv = _uv()
    steps = [
        [uv, "run", "check.py"],
        [uv, "run", "insert.py", "--part", "all", "--check"],
        [uv, "run", "insert.py", "--part", "assembly", "--check"],
    ]
    log = []
    for cmd in steps:
        r = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True)
        log.append(f"$ {' '.join(cmd[1:])}\n{r.stdout}{r.stderr}")
        if r.returncode:
            return False, "\n".join(log)
    return True, "\n".join(log)


def load():
    import FreeCAD as App
    import Import

    if not ASSEMBLY.exists():
        raise RuntimeError(f"{ASSEMBLY} is missing: run `uv run insert.py --part assembly` first")
    Import.open(str(ASSEMBLY))
    doc = App.ActiveDocument
    text = PARAMS.read_text()
    sheet = doc.addObject("Spreadsheet::Sheet", SHEET)
    sheet.addProperty("App::PropertyString", "ParamsHash")
    sheet.ParamsHash = digest(text)
    sheet.set("A1", "name")
    sheet.set("B1", "value")
    sheet.set("C1", "params.py comment")
    for row, (name, value, _l, _c, _e, comment) in enumerate(leaves(text), start=2):
        sheet.set(f"A{row}", name)
        sheet.set(f"B{row}", repr(value))
        sheet.setAlias(f"B{row}", name)
        sheet.set(f"C{row}", "'" + comment)
        if "MEASURE" in comment:
            sheet.setBackground(f"A{row}:C{row}", MEASURE_RGB)
    doc.recompute()
    return doc


def sync(doc):
    import FreeCAD as App

    sheet = doc.getObject(SHEET)
    text = PARAMS.read_text()
    if digest(text) != sheet.ParamsHash:
        return _say("params.py changed on disk since this sheet was loaded. Close this document "
                    "and run the macro again to reload; nothing was written.")
    changes = {}
    for name, value, *_ in leaves(text):
        v = sheet.get(name)
        try:
            v = float(getattr(v, "Value", v))
        except (TypeError, ValueError):
            return _say(f"{name}: {v!r} is not a number; nothing was written.")
        if v != value:
            changes[name] = v
    if not changes:
        return _say("No parameter changed.")
    PARAMS.write_text(rewrite(text, changes))
    try:
        ok, log = _run_checks()
    except Exception as exc:  # uv missing, or anything else: never leave params.py half-applied
        ok, log = False, str(exc)
    if not ok:
        PARAMS.write_text(text)
        # a failure midway leaves out/ half rebuilt with the rejected values; rebuild it
        try:
            rebuilt, _ = _run_checks()
        except Exception:
            rebuilt = False
        note = "out/ rebuilt from it" if rebuilt else "REBUILD OF out/ FAILED, run `make mech`"
        return _say(f"A check failed; params.py is restored, {note}, your edits stay in the sheet.\n\n"
                    + log[-3000:])
    App.closeDocument(doc.Name)
    load()
    _say("Updated " + ", ".join(f"{k} = {v:g}" for k, v in changes.items()))


def _say(msg):
    import FreeCAD as App

    App.Console.PrintMessage(msg + "\n")
    try:
        from PySide import QtGui
        QtGui.QMessageBox.information(None, "freecad_sync", msg)
    except ImportError:
        pass


def main():
    import FreeCAD as App

    doc = App.ActiveDocument
    if doc is not None and doc.getObject(SHEET) is not None:
        sync(doc)
    else:
        load()


if "--selftest" in sys.argv:
    sys.exit(selftest())
else:
    main()
```

Behaviour to preserve:
- `check.py` runs first because it's instant and writes nothing.
- After a failure, `params.py` is restored and `out/` is rebuilt, because `insert.py` writes part by part.
- Every FreeCAD import is inside a function, so the self-test still runs on plain Python.
- The macro relies on FreeCAD's macro runner setting `__file__`. Task 11 step 1 confirms it. A `NameError` there
  means it doesn't: stop and report it.

**Step 1:** Run `/usr/bin/python3 mech/freecad_sync.FCMacro --selftest`. It still passes.

**Step 2:** Run `uvx ruff check --select E,F,W --line-length 120 mech/freecad_sync.FCMacro`. Expected: `All checks passed!`

**Step 3: Commit**
```bash
git add mech/freecad_sync.FCMacro
git commit -m "mech: freecad_sync loads the assembly with a Params sheet, syncs edits behind the checks

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: FreeCAD smoke test (manual; needs FreeCAD)

The user installs FreeCAD (`sudo apt install freecad`, or the 1.0+ AppImage). Ask them first; don't sudo on your own.

1. FreeCAD → Macro → Macros… → User macros location: `hardware/mech` → `freecad_sync.FCMacro` → Execute.
   Expect a document with 19 named parts and a `Params` sheet. The MEASURE rows are yellow.
2. Set `WALL` to 3.2 in the sheet and run the macro again. Expect "Updated WALL = 3.2", the reloaded assembly,
   and `git diff mech/params.py` showing exactly one changed line with its comment intact.
3. Set `ARM_CLEAR` to 9 and run it. Expect the dialog "A check failed; params.py is restored, out/ rebuilt from
   it", and `git diff mech/params.py` unchanged from step 2.
4. `git checkout mech/params.py mech/out` and `make mech` (back to clean).
5. If uv isn't found (common with the AppImage), the dialog prints FreeCAD's PATH. Start FreeCAD from a shell
   that has uv on its PATH.

---

### Task 12: Docs

**Files:** `docs/plans/2026-10-11-freecad-port-design.md`

Add a `## Deviations found while planning` section:
- The STEP origin is the board's top-left corner, not its centre.
- The clash threshold is 1 mm³ (`CLASH_MM3`, shared with the column check), not 0.
- There are extra placeholders: cells, buttons, nfc.
- `check.py` runs through `uv` and goes first.
- `out/` is rebuilt after a failed sync.
- Wall layout and the three defects fixed (arm gusset, cell height, grille groove).
- The 0.32 mm cell/trough mirror remains open.

Commit:
```bash
git add ../docs/plans/2026-10-11-freecad-port-design.md
git commit -m "docs: FreeCAD design, deviations found while planning

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

**Final report to the user** must mention:
- `fab/` quote zips are stale (grille groove, tray gussets, cell height). Offer `make mech-fab`.
- The 0.32 mm board/tray Y mirror on the cell troughs.
- Installing KiCad's 3D library makes the assembly show components and checks them for collisions too.
- Speaker and buzzer device bodies aren't modelled. The speaker hole's top (z 55) is above the LCD's bottom
  (z 54.5), and the LCD ends 5 mm from that wall, so a speaker body deeper than 5 mm hits the LCD there.
