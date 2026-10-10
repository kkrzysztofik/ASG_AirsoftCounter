# Hardware Folder Cleanup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reorganise `hardware/` per `docs/plans/2026-10-11-hardware-cleanup-design.md` with zero change
to any generated design output.

**Architecture:** Four commits: retire pack_b, make carrier an ordinary board, move the generated
KiCad projects into `kicad/`, move the hand-written docs out of `fab/`. Python modules stay in the root
(they import each other). Every move is `git mv`.

**Tech Stack:** GNU make, KiCad 9 `kicad-cli` + `pcbnew` (system `/usr/bin/python3`), Freerouting.

---

## Ground rules

- Work in `hardware/` (`cd /home/kmk/dev/ASG_AirsoftCounter/hardware`).
- Old `docs/plans/*` and `docs/HANDOVER-*` are history: never edit them.
- Use plain `/usr/bin/grep`, `git diff --exit-code` where exact output or exit codes matter (rtk
  compacts output).
- **Regeneration is deterministic** (checked 2026-10-11: `make BOARD=lipo all` on a clean tree
  changed only the zip and the two PDFs, which carry timestamps). So git is the snapshot: no copies.

### VERIFY (run at the end of every task, after staging that task's edits with `git add`)

```bash
cd /home/kmk/dev/ASG_AirsoftCounter/hardware
make boards > /tmp/boards.log 2>&1 || { tail -30 /tmp/boards.log; echo VERIFY FAILED; }
/usr/bin/python3 tme_all.py
/usr/bin/python3 power_budget.py --tme | tail -3
/usr/bin/python3 mech/check.py | tail -3
git restore -- '*.zip' '*.pdf'    # timestamp-only churn; restores from the index, so staged moves survive
git diff --exit-code --stat -- . && echo VERIFY OK
```

Expected: `VERIFY OK`. `make boards` takes about 5 min (6 boards x ~45 s): use a 600 s timeout.
Any unstaged diff in a `.kicad_*`, `.csv` or `.png` means the task changed an output: stop and find out
why before going on. Stage the task's edits **before** VERIFY, because VERIFY treats every
unstaged change as a regression.

---

### Task 0: Baseline

**Step 1:** `git status --short .` → empty (the repo-root `.serena/` is outside `hardware/`).

**Step 2:** Run VERIFY. Expected `VERIFY OK`. If not, the tree is already off: stop and report.

No commit.

---

### Task 1: Retire pack_b and the orphan renders

**Files:**
- Delete: `pack_b.py`, `pack_b.kicad_{sch,pcb,pro}`, `fab/pack_b/`, `fab/placed_top.png`, `fab/placed_bottom.png`
- Modify: `Makefile:3,78`, `board.py:1-2,12`, `tme.py:91`, `tme_all.py:9`

**Step 1: Delete**

```bash
git rm -q pack_b.py pack_b.kicad_sch pack_b.kicad_pcb pack_b.kicad_pro fab/placed_top.png fab/placed_bottom.png
git rm -rq fab/pack_b
```

**Step 2: Drop the references**

- `Makefile:3` comment: `BOARD=carrier (default), pack, pack_b or lipo` → `BOARD=carrier (default), pack, lipo or a *_tme board`
- `Makefile:78`: delete the `$(MAKE) BOARD=pack_b all` line.
- `board.py:1-3` docstring: drop `pack_b (pack_b.py, the no-pack-MCU variant), `.
- `board.py:12`: drop `"pack_b": "pack_b", ` from the dict (Task 2 replaces the dict anyway).
- `tme.py:91`: delete `    "pack_b": [("NTCS0603E3103FLT", 1)],`
- `tme_all.py:9`: `pack/pack_b/pack_tme` → `pack/pack_tme`

**Step 3: Check nothing else names it**

```bash
/usr/bin/grep -rn pack_b --include=*.py --include=Makefile --include=*.md . ; echo "exit $?"
```
Expected: only `fab/*.md` hits, if any (those are fixed in Task 4); `exit 1` if none.

**Step 4:** `git add -u .`, then run VERIFY → `VERIFY OK`.

**Step 5: Commit**

```bash
rtk git commit -m "hw: retire pack_b (variant B) and the stale placed_* renders

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Carrier is just another board

**Files:**
- Rename: `design.py` → `carrier.py`; carrier outputs `fab/*` → `fab/carrier/*`
- Modify: `Makefile:11-21`, `board.py`, `carrier_tme.py`, `jlc.py:1-4,29`, `tme.py:22`, `tme_all.py:52`,
  `check_gerbers.py:9,42`, `check_netlist.py:1,38`, `gen_sch.py:8,521`, `pack.py:3`, `power_budget.py:5`,
  `mech/check.py:16,39-48`, `mech/params.py:110`, `.gitignore`

**Step 1: Rename the module**

```bash
git mv design.py carrier.py
```

**Step 2: Move carrier's fab outputs** (`tme_bom_all.csv` and `offboard/` stay in `fab/`; the `.md` files move in Task 4)

```bash
mkdir -p fab/carrier
git mv fab/bom.csv fab/bottom.png fab/top.png fab/carrier_gerbers_jlcpcb.zip fab/print_1to1.pdf \
  fab/schematic.pdf fab/jlc_bom.csv fab/jlc_cpl.csv fab/jlc_bom_budget.csv fab/jlc_cpl_budget.csv \
  fab/tme_bom.csv fab/tme_other.csv fab/tme_bom_budget.csv fab/tme_other_budget.csv fab/carrier/
ls fab   # expect: carrier carrier_tme lipo lipo_tme offboard pack pack_tme + the 5 .md + tme_bom_all.csv
```

**Step 3: Makefile.** Replace lines 11-21 (the comment and the `ifeq ... endif` block plus `export FAB`) with:

```make
# Every board writes under fab/<board>/; its data module is <board>.py.
FAB = fab/$(BOARD)
BOARD_PY = $(BOARD).py
```

`export FAB` goes: jlc.py and tme.py derive the same path from BOARD (Step 5).

**Step 4: board.py.** Line 12-14 dict → `design = importlib.import_module(NAME)`. Docstring
lines 1-3: `BOARD=carrier (default, design.py), pack (pack.py), lipo (lipo.py, the 2S/3S LiPo power
board), or the hand-built TME variants ...` → `BOARD=<name> loads <name>.py: carrier (default), pack,
lipo (the 2S/3S LiPo power board), or the hand-built TME variants carrier_tme / pack_tme / lipo_tme
(nothing machine-placed).` Line 18: `(design.py or pack.py)` → `(<board>.py)`.

**Step 5: FAB from the board name, not the environment**

- `jlc.py:29`: `FAB = Path(os.environ.get("FAB", "fab"))` → `FAB = Path("fab") / design.NAME`
  (drop `import os` if nothing else uses it). Docstring lines 3-4: `fab/jlc_` → `fab/<BOARD>/jlc_`.
- `tme.py:22`: `FAB = HERE / os.environ.get("FAB", "fab")` → `FAB = HERE / "fab" / board.NAME`
  (drop `import os` if unused). `HAND` stays keyed by `FAB.name`, which is still the board name.
- `tme_all.py:52`: `[FAB / "tme_bom.csv" if b == "carrier" else FAB / b / "tme_bom.csv" for b in boards]`
  → `[FAB / b / "tme_bom.csv" for b in boards]`
- `check_gerbers.py:42`: default `f"fab/{design.NAME}_gerbers_jlcpcb.zip"` →
  `f"fab/{design.NAME}/{design.NAME}_gerbers_jlcpcb.zip"`; line 9 docstring likewise
  (`fab/<BOARD>/<BOARD>_gerbers_jlcpcb.zip`).

**Step 6: carrier_tme.py imports carrier**

```bash
sed -i 's/^import design$/import carrier/; s/\bdesign\./carrier./g; s/Derived from design\.py/Derived from carrier.py/' carrier_tme.py
/usr/bin/grep -n design carrier_tme.py   # expect: no hits
```

**Step 7: mech/check.py.** In `rasters_match()`: `import design` → `import carrier`,
`(design, "carrier")` → `(carrier, "carrier")`, message `design.py and pack.py` → `carrier.py and pack.py`.
Line 16 comment and `mech/params.py:110` comment: `design.py` → `carrier.py`.

**Step 8: Remaining docstrings**

- `carrier.py:4`: `python3 design.py` → `python3 carrier.py`
- `pack.py:3`, `power_budget.py:5`: `design.py` → `carrier.py`
- `check_netlist.py:1`: `matches design.py` → `matches the board module`; line 38 message
  `"netlist matches design.py"` → `f"netlist matches {design.NAME}.py"`
- `gen_sch.py:8`: `the netlist is design.py's` → `the netlist is the board module's`;
  `gen_sch.py:521`: `design.py names` → `the board module's names`
- `jlc.py:1`: `from design.py` → `from the board module`

**Step 9: .gitignore.** Delete the `fab/gerbers/` line (`fab/*/gerbers/` now covers every board).

**Step 10: Check**

```bash
/usr/bin/grep -rn -E 'design\.py|import design\b|== *"carrier"' --include=*.py --include=Makefile . ; echo "exit $?"
```
Expected: `exit 1` (no hits).

**Step 11:** `git add -A . ':!build'`, then run VERIFY → `VERIFY OK`. The rebuilt `fab/carrier/*.csv`
must match the moved files byte for byte.

**Step 12: Commit**

```bash
rtk git commit -m "hw: carrier is an ordinary board (carrier.py, fab/carrier/)

design.py -> carrier.py, carrier outputs move to fab/carrier/, the Makefile's ifeq carrier and
board.py's name map go; jlc.py/tme.py take fab/<BOARD>/ from the board name instead of \$FAB.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: KiCad projects into kicad/

**Files:**
- Move: the 18 `<board>.kicad_{sch,pcb,pro}`, `fp-lib-table`, `sym-lib-table`, `local.kicad_sym`, `local.pretty/` → `kicad/`
- Modify: `gen_sch.py:23,95,848-850`, `gen_pcb.py:16,50`, `jlc.py:30`, `tools/handsolder_qfn.py:1,19`,
  `Makefile` (kicad-cli paths), `check_netlist.py:3`

The lib tables use `${KIPRJMOD}`, so they need no edit when they move with the projects.

**Step 1: Move**

```bash
mkdir kicad
git mv *.kicad_sch *.kicad_pcb *.kicad_pro fp-lib-table sym-lib-table local.kicad_sym local.pretty kicad/
ls *.kicad_* 2>/dev/null; echo "exit $?"   # expect exit 2: none left in the root
```

**Step 2: gen_sch.py.** After `HERE = Path(__file__).parent` (line 23) add:

```python
KICAD = HERE / "kicad"  # the generated projects, their lib tables and the local libs
```

- line 95: `(HERE if lib == "local" else SYMDIR)` → `(KICAD if lib == "local" else SYMDIR)`
- lines 848-849: `(HERE / f"{design.NAME}.kicad_sch")` / `.kicad_pro` → `(KICAD / ...)`
- line 850: `wrote {design.NAME}.kicad_sch, ...` → `wrote kicad/{design.NAME}.kicad_sch, kicad/{design.NAME}.kicad_pro`
- `build/` stays under `HERE` (lines 841-842 unchanged).

**Step 3: gen_pcb.py** (already imports gen_sch)

- line 16: `PCB = HERE / f"{design.NAME}.kicad_pcb"` → `PCB = gen_sch.KICAD / f"{design.NAME}.kicad_pcb"`
- line 50: `HERE / "local.pretty"` → `gen_sch.KICAD / "local.pretty"`

route.py reads `gen_pcb.PCB` and `gen_pcb.HERE / "tools"`: unchanged.

**Step 4: jlc.py:30**: `PCB = HERE / f"{design.NAME}.kicad_pcb"` → `PCB = HERE / "kicad" / f"{design.NAME}.kicad_pcb"`

**Step 5: tools/handsolder_qfn.py**: line 19 `DEST = HERE.parent / "local.pretty"` →
`DEST = HERE.parent / "kicad" / "local.pretty"`; line 1 docstring `local.pretty/` → `kicad/local.pretty/`.

**Step 6: Makefile**

```bash
sed -i 's#\$(BOARD)\.kicad_#kicad/$(BOARD).kicad_#g' Makefile
/usr/bin/grep -c 'kicad/$(BOARD).kicad_' Makefile   # expect 11
```

**Step 7: check_netlist.py:3** docstring: `<BOARD>.kicad_sch` → `kicad/<BOARD>.kicad_sch`.

**Step 8: Self-check the QFN generator** (it rebuilds the footprint; the result must equal the moved file)

```bash
/usr/bin/python3 tools/handsolder_qfn.py && git diff --exit-code --stat -- kicad/local.pretty && echo QFN OK
```

**Step 9:** `git add -A . ':!build'`, then run VERIFY → `VERIFY OK`.

**Step 10: Manual check (user).** Open `kicad/pack.kicad_pro` in KiCad: the 18650 holders and NTC
footprints show (the `local` lib resolves).

**Step 11: Commit**

```bash
rtk git commit -m "hw: generated KiCad projects and local libs move to kicad/

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Docs out of fab/

**Files:**
- Move: `fab/{COSTS,OFFBOARD_PARTS,ORDERING,PARTS_REVIEW,PART_ALTERNATIVES}.md` → `docs/`
- Modify: the moved docs (paths), `power_budget.py:6,63`

**Step 1: Move**

```bash
mkdir docs
git mv fab/COSTS.md fab/OFFBOARD_PARTS.md fab/ORDERING.md fab/PARTS_REVIEW.md fab/PART_ALTERNATIVES.md docs/
```

**Step 2: Fix carrier fab paths and old names in the moved docs** (paths in them are relative to `hardware/`)

```bash
sed -i -E \
  -e 's#fab/(carrier_gerbers|jlc_|print_1to1|bom\.csv|schematic\.pdf|top\.png|bottom\.png|tme_bom\.csv|tme_bom_budget|tme_other)#fab/carrier/\1#g' \
  -e 's#hardware/design\.py#hardware/carrier.py#g' \
  docs/*.md
/usr/bin/grep -n -E 'design\.py|pack_b|\.kicad_(sch|pcb|pro)|Other files in .fab/' docs/*.md
```

Fix each remaining hit by hand:
- `.kicad_*` paths → `kicad/...`
- `pack_b` mentions: drop the sentence or note that variant B was retired 2026-10-11
- ORDERING.md "Other files in `fab/`" (line ~149) → "Other files in `fab/carrier/`"

Sibling links between these five docs stay valid (they moved together).

**Step 3: Fix pointers to the docs**

```bash
sed -i 's#fab/PARTS_REVIEW\.md#docs/PARTS_REVIEW.md#; s#fab/OFFBOARD_PARTS\.md#docs/OFFBOARD_PARTS.md#' power_budget.py
/usr/bin/grep -rn -E 'fab/(COSTS|OFFBOARD_PARTS|ORDERING|PARTS_REVIEW|PART_ALTERNATIVES)' --include=*.py --include=*.md --include=Makefile . ; echo "exit $?"
```
Expected: `exit 1`.

**Step 4: Final sweep** (must be empty)

```bash
/usr/bin/grep -rn -E 'design\.py|pack_b|fab/(jlc_|carrier_gerbers|print_1to1|placed_)' --include=*.py --include=*.md --include=Makefile . ; echo "exit $?"
ls
```
Expected `exit 1`, and `ls` shows: `Makefile board.py carrier.py carrier_tme.py check_gerbers.py
check_netlist.py docs fab gen_pcb.py gen_sch.py jlc.py kicad lipo.py lipo_tme.py mech pack.py
pack_tme.py power_budget.py route.py tme.py tme_all.py tools` (plus gitignored `build/`).

**Step 5:** `git add -A . ':!build'`, then run VERIFY → `VERIFY OK`.

**Step 6: Commit**

```bash
rtk git commit -m "hw: hand-written docs move from fab/ to docs/

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Wrap-up

- Update the auto-memory status file (`airsoftcounter-v2-status.md`): pack_b retired, carrier module is
  `carrier.py`, KiCad files in `hardware/kicad/`, carrier fab in `hardware/fab/carrier/`, docs in
  `hardware/docs/`.
- Ask the user before pushing.
