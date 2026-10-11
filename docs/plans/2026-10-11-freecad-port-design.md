# Mech parts in FreeCAD: design

The insert parts (`hardware/mech/insert.py`, build123d) already export STEP, so any CAD tool can open
them. What the STEP files lack is context and editability. Goals: see the parts assembled with the boards,
tweak dimensions in a GUI, hand the design to someone who uses FreeCAD. Code stays the source of truth:
`params.py` holds every dimension, `check.py` gates every change.

## Decisions

- **FreeCAD.** Runs on Linux, Python macros, spreadsheet aliases, the only tool where GUI edits can
  round-trip to code.
- **Two phases.** Phase 1 (assembly STEP) pays off on its own and needs no FreeCAD code; phase 2 (sync
  macro) builds on it.
- **Parameter values round-trip, features do not.** A cutout sketched in FreeCAD is ported to
  `insert.py` by hand.
- **Rejected:** a native PartDesign rebuild driven by a spreadsheet. That makes two sources of truth, and
  `check.py` stops gating the real model.

## Phase 1: `insert.py --part assembly`

Writes `out/assembly.step`, one compound with named children:

| Child | Source | Placement |
|---|---|---|
| tray, lid, grille, bushing_* | existing `make_*()` | as modelled (box inner floor origin) |
| pack_board | `kicad-cli pcb export step` | XY centred in the box, Z = `P.pack_z()` |
| carrier_board | same | XY = `P.CARRIER_ORIGIN`, Z = `P.carrier_z()` |
| heltec | placeholder box, `HELTEC_H` | on the carrier |
| lcd | placeholder box, `LCD` x `LCD_DEPTH` | under the lid at `LCD_CENTRE` |
| box | thin shell from `BOX_IN` + `WALL`, 4 `COLUMN_SIZE` columns | origin |

- `--boards pack,carrier` (default). The `_tme` variants share the outlines: `--boards pack_tme,carrier_tme`.
- Board files are looked up in `hardware/kicad/` and then in `hardware/`, so the code works before and
  after the hardware cleanup (`2026-10-11-hardware-cleanup-design.md`).
- Board STEPs are cached in `out/boards/` and only re-exported when the `.kicad_pcb` is newer.
- The guide (drill jig) is left out because it is not part of the assembled insert.
- `--check` adds a pairwise interference test: `a.intersect(b).volume > 0` fails. Flush contact
  passes.

## Phase 2: `hardware/mech/freecad_sync.FCMacro`

**Load.** `ast`-parse `params.py`, collect top-level `NAME = <number>` assignments. Write them into a
`Params` sheet: name, value (aliased `NAME`), comment. Rows with `MEASURE` in the comment are
yellow. Import `out/assembly.step` into an `Assembly` group.

**Sync.**
1. Diff the sheet against the loaded values.
2. Rewrite only the changed value spans in `params.py`, using the `ast` `col_offset`/`end_col_offset`
   positions. Comments and alignment stay byte-identical.
3. Run `uv run insert.py --part all --check`, then `uv run insert.py --part assembly --check`, then
   `/usr/bin/python3 check.py`.
4. All pass: replace the `Assembly` group and report which parameters changed. Any fail: restore
   `params.py` to its original text, show the failing output, keep the sheet edits. `params.py` only
   ever holds values that pass.

**Scope.** Scalars only. Tuples, lists and derived values (`FIT`, `CARRIER_ORIGIN`) are not editable.
No `.FCStd` in git, because the macro rebuilds the document from code.

**Errors.**
- `params.py` hash changed since load: refuse, ask for a reload, overwrite nothing.
- `uv` not found: say so and show the PATH FreeCAD sees (AppImage builds often have a thin PATH).

## Testing

- `/usr/bin/python3 freecad_sync.FCMacro --selftest`: FreeCAD imports live inside the GUI functions, so the
  parse and rewrite logic runs on plain Python. The test changes 3 values in a copy of `params.py` and
  asserts that exactly 3 lines differ and the comments survive.
- Phase 1: `--part assembly --check` passes on the current params.
- Manual: in FreeCAD, change `WALL`, sync, and check that the tray updates. Then set a value that breaks
  a rule and check that `params.py` is restored.

## Prerequisite

FreeCAD is not installed here: `sudo apt install freecad` or the AppImage (version 1.0 or later).

## Deviations and findings during implementation

**The design as built differs from the design above in these ways:**
- **STEP origin.** kicad-cli's default STEP origin is the board's top-left corner with Y flipped up, not the
  board centre. Boards are placed at `(origin_x, origin_y + H, z)`.
- **One board-to-tray mapping.** Every board point goes through `params.board_xy`, because KiCad's Y runs
  down. The troughs, pack posts and carrier holes all use it, and each carrier post derives from its own hole.
- **Gate details.** The clash threshold is 1 mm³ (`CLASH_MM3`, shared with the column check), not 0. The
  bbox prefilter counts containment as overlap, because build123d's `BoundBox.overlaps` excludes it, which
  had hidden 23 pairs.
- **Placeholders.** On top of the Heltec and LCD there are cells, buttons and NFC. The boards export bare
  (KiCad's 3D library is not installed), and the gate says so on every run.
- **Sync order.** The macro runs `check.py` first, through uv. It rebuilds `out/` after a failure only when
  insert.py had started writing. Edits are byte-exact (right to left within a line, ast-compatible line
  splitting, bytes I/O), and child processes drop the AppImage's PYTHONHOME, PYTHONPATH and LD_LIBRARY_PATH.
- **Generated outputs.** `mech/out/*.stl|step` (`assembly.step` included) are gitignored. Only the drill
  templates are tracked, and they regenerate byte-stable.

**Defects the 3D gate or the reviews found, now fixed:**
- **Carrier arms:** the gussets cut through the pack board. They now hang from the arm, `ARM_CLEAR` above it.
- **Cell height:** cells were modelled 3.5 mm through the pack board. `PACK_OVERLAP` is now 0, MEASURE. The
  stack is 52.0 of 78 mm.
- **Tray underside:** rails, clips and gussets started 0.1 mm below it, so the tray could not sit flat.
- **Cell position:** cells sat 0.32 mm off in Y (board Y not mirrored) and 1.5 mm off in X (`PACK[0] / 2`
  instead of the holders' x). Now `HOLDER_X`/`HOLDER_Y` are asserted against `pack.py`.
- **NFC:** it sat on the bottom-right corner column. Buttons moved to x = 56/96 and the NFC to (133.5, 27),
  and a check holds the lid webs at the process minimum wall.
- **Wall holes:** the speaker hole overlapped a corner column. With the new wall layout (key and USB-C on
  x0, SMA on x1, buzzer and speaker on y1), `wall_holes_clear` covers the columns, floor, lid, rim and
  neighbours.
- **Grille:** the O-ring groove was 0.01 mm deep, and a first fix cut it as a ledge. It is now a ring with
  an inner wall, probed in `check_part`.
- **Carrier screw bosses:** they had no pilot hole. The margin posts had one that nothing used.
- **Drill sheets:** one per wall, seen from outside, with a text label and the outer-face outline (top
  edge on the rim).

**Still open (MEASURE or needs hardware):**
- **Component clearances.** The boards are bare, so the gate cannot see components. J_KEY1, a vertical JST
  XH, sits under a carrier gusset with about 6.4 mm of headroom. J_PWR1 sits under the 8 mm carrier
  standoff. Install KiCad's 3D library and delete `out/boards/`.
- **Speaker vs LCD.** The speaker hole top (z 55) is above the LCD bottom (z 54.5), and the LCD ends 5 mm
  from the y1 wall. Device bodies are not modelled.
- **Base slab.** The grille plate's bottom edge assumes the base slab is `WALL` thick (zero margin).
- **Tight margins.** The FDM lid web at button 2's boss sits exactly at 2.0 mm. The LCD-to-Heltec gap is
  2.5 mm against a 2.0 floor (`LCD_DEPTH` is MEASURE).
- **Fab zips.** The quote zips in `fab/` predate these fixes.
