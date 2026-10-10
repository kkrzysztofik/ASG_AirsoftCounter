# Hardware folder cleanup: design

`hardware/` grew to 7 boards in a flat root: 21 generated KiCad files next to 11 generator scripts,
carrier special-cased (`design.py`, outputs loose in the `fab/` root), and `fab/` mixing outputs,
hand-written docs and orphans. This is a pure reorganisation: no design, part or output changes.

## Decisions

- **Retire pack_b.** The boards that stay: carrier, pack, lipo (JLC) and carrier_tme, pack_tme,
  lipo_tme (TME hand-build), plus `mech/`. pack_b stays recoverable from git history.
- **Layout A: generated KiCad files move to `kicad/`, Python stays in the root.** Board modules
  import each other (`lipo` -> `pack`, `*_tme` -> base + `tme`) and every generator does
  `from board import design`, so splitting the `.py` files across folders would need `PYTHONPATH`
  on every command. The KiCad files are only written, never imported, so moving them costs a few path
  constants. Rejected: a role split (`boards/ gen/ kicad/`, PYTHONPATH friction) and per-board folders
  (fights the cross-imports, 6 copies of the lib tables).
- **Carrier is just another board.** `design.py` -> `carrier.py`, outputs under `fab/carrier/`, no
  `ifeq carrier` in the Makefile, `board.py` loads `import_module(NAME)`.
- **Docs leave `fab/`.** `fab/*.md` -> `hardware/docs/`.
- **Old plans and handovers are history.** `docs/plans/*` and `docs/HANDOVER-*` keep their old paths;
  only live docs (hardware docs, Makefile comments, docstrings) are updated.

## Target layout

```
hardware/
  Makefile  board.py  gen_sch.py  gen_pcb.py  route.py  check_netlist.py  check_gerbers.py
  jlc.py  tme.py  tme_all.py  power_budget.py
  carrier.py  pack.py  lipo.py  carrier_tme.py  pack_tme.py  lipo_tme.py
  kicad/   <board>.kicad_{sch,pcb,pro}, fp-lib-table, sym-lib-table, local.kicad_sym, local.pretty/
  fab/     <board>/ (carrier included), offboard/, tme_bom_all.csv
  docs/    ORDERING.md COSTS.md PARTS_REVIEW.md PART_ALTERNATIVES.md OFFBOARD_PARTS.md
  mech/  tools/   unchanged
```

The lib tables use `${KIPRJMOD}`, so they move with the projects unedited. Schematic UUIDs are seeded
from keys, not paths, so the rename does not change them.

## Steps (one commit each, `make boards` green before the next)

1. **Retire:** `git rm` pack_b.{py,kicad_*}, `fab/pack_b/`, the orphaned `fab/placed_*.png`; drop
   pack_b from Makefile, board.py, tme.py, tme_all.py.
2. **Carrier:** `git mv design.py carrier.py`, fix `import design`; carrier outputs `fab/` ->
   `fab/carrier/`; `FAB = fab/$(BOARD)` for all; `board.py` -> `import_module(NAME)`.
3. **kicad/:** move the 18 project files, lib tables and `local.*`; fix the `HERE`-relative paths in
   gen_sch, gen_pcb, route, jlc, tools/handsolder_qfn.py and the Makefile's kicad-cli calls.
4. **Docs:** `git mv fab/*.md docs/`, fix cross-links.

All moves use `git mv` to keep history.

## Verification

Before step 1, snapshot every `.kicad_{sch,pcb,pro}` and `fab/**/*.csv`. After each step run
`make boards` and `tme_all.py`: every regenerated KiCad file and CSV must be byte-identical to its
snapshot at the new path (only intended path strings may differ). ERC/DRC, check_gerbers,
check_netlist and `power_budget.py --tme` stay green. Zips/PNGs/PDFs carry timestamps and are not
diffed.
