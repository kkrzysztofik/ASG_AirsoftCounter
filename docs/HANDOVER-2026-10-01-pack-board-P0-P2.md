# Handover: pack board implementation (P0-P2 done, P3.1 in progress)

Date: 2026-10-01
Branch: `esp32-lora-design` (repo root `/home/kmk/dev/ASG_AirsoftCounter`)
Plan: `docs/plans/2026-10-01-pack-board-implementation.md` (the task list to execute)
Spec: `docs/plans/2026-10-01-pack-board-design.md` (binding design; has the P0 "Parts" section)
Working ledger: `.superpowers/sdd/2026-10-01-pack-board-implementation/progress.md` (git-ignored scratch;
this handover carries the durable version of it)

Goal of the plan: a JLCPCB-ready 4x18650 pack board (`hardware/pack.*`, `hardware/fab/pack/`) generated
by the same flow as the carrier, plus the carrier with its power section moved off (`J_PWR1`).

## State in one line

P0.1, P1.1-P1.5, P2.1, P2.2 are done, verified and committed. P3.1 (pack schematic layout) was started
and reverted because the block layout did not generate; P3.2 through P6.2 are not started. The carrier
still builds and its generated files are byte-identical to the committed routed set.

## Environment / commands

- Run everything from `hardware/`. Use `/usr/bin/python3` (only it has `pcbnew`); `kicad-cli` 9.0.8;
  Freerouting 2.4.1 jar in `hardware/tools/`; Java 25.
- `rtk` rewrites some output; use plain `make`, `/usr/bin/grep -F`, `diff`, `cmp` when output matters.
- Self-checks: `python3 board.py`, `python3 design.py` (carrier), `python3 pack.py` (pack).
- Carrier: `make pcb`, `make all`, `make boards`. Pack: `make BOARD=pack sch|pcb|route|check|fab`.
- `make all` takes ~4 min (autorouting). It rewrites tracked `fab/*.pdf` and the Gerber zip with new
  timestamps; restore them with `git checkout` if you do not intend to commit them.

Carrier byte-identity gate (same_as_base.sh was deleted in P1.5; recreate the check this way):

```sh
cd hardware && make pcb >/dev/null && mkdir -p /tmp/carrier_base && cp carrier.kicad_sch carrier.kicad_pro carrier.kicad_pcb /tmp/carrier_base/
git checkout -- carrier.kicad_pcb carrier.kicad_sch carrier.kicad_pro     # restore routed
# after a change:  make pcb >/dev/null && for f in carrier.kicad_sch carrier.kicad_pro carrier.kicad_pcb; do cmp "$f" "/tmp/carrier_base/$f"; done && git checkout -- carrier.kicad_*
```

## Commits (oldest first, all on `esp32-lora-design`)

| Commit | What |
|---|---|
| `de0e130` | docs: P0.1 part facts (datasheet verification + live LCSC stock) |
| `878ccd9` | `board.py` selects the board module; generators `from board import design` |
| `d9dfef6` | board tables moved into `design.py`; generators read `design.X` |
| `c623c2c` | `board.check_structure(m)` + `design.check()` keeps Heltec checks; `jlc.py` default variant |
| `cc3cdfa` | Makefile `BOARD`/`FAB`/`boards`; `jlc.py`/`check_gerbers.py` read exported `FAB` |
| `224af27` | `pack.py` netlist (124 parts, 76 nets) |
| `d032077` | pack netlist fixes (D1 symbol, L_CHG.2, R_FB2.2) |
| `ed20f0d` | `gen_sch.py` reads `NETCLASS_POWER`; `check_netlist.py` uses `ET.fromstring` |

## What is done

- **P0.1**: `docs/plans/2026-10-01-pack-board-design.md` has a "Parts" section with every chosen part,
  LCSC number, library type, stock and the datasheet fact behind it. "Unverified" trimmed to bench-only
  items. Rulings are in the ledger under P0.1.
- **P1.1-P1.5**: generators are board-agnostic. `board.py` maps `BOARD=carrier -> design.py`,
  `pack -> pack.py`. Every board-specific table (`_driver`, `BLOCKS`, `RAILS`, `PORT_LIB`, `NC_PARTS`,
  `NC_PINS`, `NETCLASS_POWER`, `W/H/CORNER`, `PLACE`, `REF_AT`, `LABELS`, `TEXTS`, `GND_VIAS`,
  `HELTEC_PADS`, `SIZE_MM`, `NPTH_XY`, `NETCLASS_EXPECT`) lives in the board module. Heltec-only PCB
  steps are gated by `if design.HELTEC_PADS:`. `check_structure` lives in `board.py`. The Makefile takes
  `BOARD`; carrier outputs keep their committed paths, the pack writes `fab/pack/`.
- **P2.1/P2.2**: `hardware/pack.py` holds the full 1S4P netlist and passes `python3 pack.py`
  (`pack ok: 124 parts, 76 nets`). `check_branches()` asserts holder+ -> fuse -> shunt -> back-to-back
  P-FET -> pack rail per cell. Deliberate-break test caught `cell 1: fuse -> shunt / IN+`.

## Rulings made (cost if wrong)

- 5 A fuse (C48332) sits **below** the XB8089D's 10 A/10 ms trip; it is the backup layer, not "above the
  trip". The crowbar relies on the protector (40 A/75 us). Cost: a crowbar event leans on that protector.
- Charger switcher node is `SW_CHG`, not `SW`; the boost already owns `SW`. Cost: a net rename.
- No INA3221 input filter R/C (datasheet makes it conditional on >1 MHz); averaging handles it.
  Cost: more current-measurement noise.
- Tank switch is C720477 (TS-1088-AR02016, Basic, 2-pad), replacing P0's C318884 (4-pad) so
  `Switch:SW_Push` pairs with a 2-pad footprint. Design doc updated.
- `VBUS` and `VMCU_IN` must join `RAILS`/`PORT_LIB` (plan listed only GND/+3V3/+5V/VBAT_SW/VPACK),
  because `U_CHG.VBUS` and the LDO input are `power_in` and a PWR_FLAG can only sit on a net with a
  power port. `power:VBUS` and `power:VDC`/`power:+BATT` are all present in the stock library.
- `jlc.py` finds its output dir from the Makefile-exported `FAB` env var (plan put `FAB` in the
  Makefile), default `fab`. Cost: `python3 jlc.py` by hand for the pack writes to `fab/`.
- **pi-lens / Pyright / Semgrep are out of scope.** This repo has no type-check or lint config and
  `gen_sch.py` alone has ~12 pre-existing Pyright errors. Genuine items were fixed (ruff import
  sorting, `# pyright: ignore[reportMissingImports]` on the `pcbnew` C extension and the sibling
  `board` module, `ET.fromstring` for the XXE rule). Do not chase the remaining noise.

## Remaining work (P3.1 -> P6.2)

### P3.1 pack schematic layout — IN PROGRESS, blocked on layout tuning

`make BOARD=pack sch` runs `pack.py` and the symbol lookup correctly. What is missing is the layout
section in `pack.py`: `RAILS`, `PORT_LIB`, `NETCLASS_POWER`, a cell helper and `BLOCKS`, plus the
`W/H/CORNER/PLACE/REF_AT/LABELS/TEXTS/GND_VIAS/HELTEC_PADS/NETCLASS_EXPECT` stubs. A 7-block version
with a 4x4 `_cell()` helper was tried and reverted; `make BOARD=pack sch` reported ~40 clash classes:

- tags at relative coords outside their block or overlapping each other (CELL*_F/CELL*_S in the cell
  and monitoring blocks; SCL_INT/SDA_INT/CHG_*/INA_*/SW*_DRV/NTC* in the monitoring and MCU blocks);
- PWR_FLAG/#PWR power ports overlapping parts or other ports (U_CHG, U_LDO, C_MCU1, R_CC2,
  SW_BOOT/SW_RST, C_OUT1/2);
- `J_USB1` outside its block / over the title; `SW_RST` overlapping `SW_BOOT`;
- `*.1 stub zone clashes with GND` on crowded pins.

Recipe that should work:

1. Rebuild `BLOCKS` with a title strip at the top (parts start at `y + 12.7`) and a free
   tag/flag strip (~20 mm) at the bottom, tags spaced >= 10.16 mm apart.
2. Part pitch: vertical 2-pin parts >= 12.7 mm in y at the same x; horizontal parts >= 12.7 mm in x
   (7.62 mm makes two parts share a pin cell). Big symbols need their own areas: `U_CHG` 25.4 x 48.3,
   `U_MCU` 20.3 x 53.3, `INA3221` 25.4 x 33.
3. Cross-block non-rail nets that each block must tag: `CELL{1..4}_F`, `CELL{1..4}_S` (cell block and
   monitoring block), `SW{1..4}_DRV`, `NTC{1..4}`, `NTC_PWR` (cell blocks and MCU block),
   `SCL_INT`/`SDA_INT` (charger, monitoring, MCU), `INA_CRIT`/`INA_WARN`, `CHG_INT`/`CHG_CE`,
   `USB_DP`/`USB_DM` (USB and MCU), `SYS` (charger, MCU, power-out), `SDA_EXT`/`SCL_EXT` (MCU, J_PWR1).
   `CELL*_F` also enters the MCU block (diode-OR anodes).
4. Iterate `make BOARD=pack sch`; gen_sch prints one line per clash kind and leaves the broken sheet in
   `build/pack_bad.kicad_sch`.
5. **Faster alternative worth trying first:** put every part in a single `BLOCKS` entry. A single block
   means no cross-block nets, so **no tags at all**; only the rails need PWR_FLAGs. Use a coarse grid
   (~25-30 mm) and let the A* router connect everything. If that generates, you can split into blocks
   later or keep it (note the deviation).

Then open `pack.kicad_sch` in KiCad and eyeball it once. Commit.

### P3.2 pack ERC clean

`make BOARD=pack sch` then
`kicad-cli sch erc --severity-all --exit-code-violations -o build/pack_erc.rpt pack.kicad_sch`.
Expect exit 0. Likely fixes: `NC_PINS`/`XH_SPARE`, missing `PWR_FLAG`s, power-input pins without a driver.

### P4.1 pack outline and placement (`pack.py`)

Add `W`, `H` (holder footprint is 77.8 x 21.4 mm; four side by side about 85.5 mm, so ~92 x 88 mm),
`CORNER`, `PLACE` (every ref), `REF_AT`, `LABELS`, `TEXTS`, `GND_VIAS = []`, `HELTEC_PADS = {}`,
`NETCLASS_EXPECT`. `make BOARD=pack pcb`. Ensure `pack ok` and `gen_pcb` assertions pass.

### P4.2 pack route, DRC, fab

`make BOARD=pack check` (Freerouting + ERC + DRC with parity), then `make BOARD=pack fab`
(`check_gerbers.py` with the pack size/holes; `jlc.py` writes `fab/pack/jlc_bom.csv` and
`fab/pack/jlc_cpl.csv`). Then `make boards` to confirm the carrier still builds.

### P5.1/P5.2 carrier change

Remove from `design.py`: `J_BAT1`, `J_KEY1`, `F1`, `U4`, `R_PROT1`, `C_PROT1`, `U1`, `L1`, `D1`,
`R_FB1`, `R_FB2`, `C_IN1`, `C_OUT1`, `C_OUT2`; delete nets `VBAT_RAW`, `BAT_N`, `PROT_VDD`, `VBAT_F`,
`SW`, `FB`; add `J_PWR1` (6-pin XH, C144397) with pins 1-2 GND, 3 VBAT_SW, 4 +5V, 5 SDA_EXT(3V3 bus),
6 SCL_EXT. Update `BLOCKS`/`PLACE`/`REF_AT`/`LABELS` and run `make all`.

### P6.1/P6.2 power model and docs

`power_budget.py`: `CELLS_MAH = 4 * 3350`, add the pack quiescent line (MCU Stop ~85 uA dominates) and
state the branch drop in a comment. Docs: `fab/ORDERING.md`, `fab/OFFBOARD_PARTS.md`, cross-reference
from the carrier design doc, and set the pack design doc status to hardware-done/firmware-deferred.

## Gotchas

- `pack.py` imports `board` lazily inside `check()` (same circular-import dance as `design.py`).
- `board.check_structure` requires `m.assembled()` and `m.LCSC/DNP/MODULES/VARIANTS` to exist.
- Every LCSC entry must be used by an **assembled** part or `check_structure` reports it stale. A DNP-only
  value needs no LCSC entry (e.g. `0R` for `R_BYP1..4` is deliberately absent).
- Holders (`BT1..4`) and test-point pads are in `NOT_ASSEMBLED` (hand-soldered): no LCSC, not in the JLC
  BOM/CPL. `H1..4` are excluded by symbol.
- `gen_pcb` asserts `PLACE.keys() == PARTS.keys()`; every part (except mounting holes) needs a `PLACE`.
- pi-lens re-flags the same stale Pyright/Semgrep findings whenever a touched file is in its set; they are
  not defects. The author (me) already ruled them out of scope.
- `git clean -fdx` would delete the ledger; recover from `git log`.
