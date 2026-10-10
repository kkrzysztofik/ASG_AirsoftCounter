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
