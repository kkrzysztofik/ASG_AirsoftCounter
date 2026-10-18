# Hierarchical Schematics (carrier_tme pilot) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Generate carrier_tme as a hierarchical KiCad schematic:
- a root "system" sheet with the Heltec as one module, every connector, the off-board parts, and wired sheet pins;
- one readable sheet per function.

The netlist, net names and the routed board stay unchanged.

**Architecture:**
- `gen_sch.schematic()` (one `Sheet`, many blocks) is split into `build_sheet(...)`, which runs the existing
  place → port → label → route → name pipeline on any subset of blocks.
- Flat mode (no `SHEETS` in the board module) calls it once, so the output stays byte-identical.
- Hierarchical mode calls it once per function sheet, emitting hierarchical labels for nets that leave the
  sheet. It then builds the root: root parts, `OFFBOARD` symbols, sheet boxes whose pins act as router
  terminals, and global labels that keep net names flat.
- gen_pcb links footprints to `/<sheet uuid>/<symbol uuid>`.

**Tech Stack:**
- Python 3 on `/usr/bin/python3`, with pcbnew for gen_pcb.
- KiCad 10.0.7 (`kicad-cli`).
- Konnect MCP `library` toolset to create the new symbols.
- Assert-based self-checks (`python3 <module>.py`), as `board.py` does. There is no pytest in this repo.

**Rules:**
- Never text-edit `*.kicad_sch`, `*.kicad_pcb`, `*.kicad_sym` or `*.kicad_mod`. They come from the
  generators or from Konnect.
- Run every command from `hardware/`.
- Use `rtk` for git.
- Commit after each task.

---

### Task 0: Baseline the flat boards (regression oracle)

**Files:** none (artifacts in `/tmp/schbase/`).

**Step 1:** Regenerate and hash every flat sheet with the current code:

```bash
mkdir -p /tmp/schbase
for b in carrier pack lipo pack_tme lipo_tme carrier_tme; do
  BOARD=$b /usr/bin/python3 gen_sch.py >/dev/null && cp kicad/$b.kicad_sch /tmp/schbase/$b.kicad_sch
done
sha256sum /tmp/schbase/*.kicad_sch > /tmp/schbase/SHA256
```

Expected: six hashes. (These are gen_sch's own KiCad 9 output, before `make`'s upgrade step. Later tasks
compare raw gen_sch output the same way.)

**Step 2:** `git checkout -- kicad/` to restore the committed (upgraded) sheets.

---

### Task 1: Board-module data model + `OFFBOARD` guard

**Files:**
- Modify: `board.py` (`check_structure` plus the `__main__` self-test)
- Modify: `carrier_tme.py` (add `SHEETS`, `ROOT`, `OFFBOARD`)

**Data formats** (documented in the `carrier_tme.py` comments):

```python
# Function sheets: name -> title, list of BLOCKS indexes. Each block's parts land on that sheet.
SHEETS = {"power": ("Power", [0]), "i2c": ("I2C level shifter, LCD (5 V), NFC (3.3 V)", [3]), ...}
# Root sheet: parts drawn on the system sheet, as {ref: (x, y, rot, mirror)} in root coordinates,
# plus where each sheet box sits: {sheet name: (x, y, w, h)}.
ROOT = {"parts": {...}, "sheets": {...}, "outline": ("Heltec WiFi LoRa 32 V4 (plugs into J2/J3)", (x, y, w, h))}
# Off-board parts: ref -> (value, lib_id, connector ref, {offboard pin: connector pin}, cable note, (x, y, rot, mirror))
OFFBOARD = {"X_LCD": ("LCD 1602 + PCF8574", "local:Module_I2C_4", "J_LCD1",
                      {"1": "1", "2": "2", "3": "3", "4": "4"}, "XH-4", (x, y, 0, None)), ...}
```

**Step 1: Write the failing self-test** in `board.py` `__main__`. It's a namespace with a valid `OFFBOARD`
entry that must pass, plus one whose connector isn't a `J*` connector part (or whose connector pin isn't
on a net) that must fail with `"OFFBOARD"` in the message. Follow the existing `try/except/else` pattern.

**Step 2:** Run `/usr/bin/python3 board.py`. Expected: FAIL (`SystemExit: check_structure accepted ...`).

**Step 3: Implement** in `check_structure`, guarded by `if hasattr(m, "OFFBOARD"):`:
- each ref starts with `X_` and isn't in `PARTS`;
- the connector ref is in `PARTS` and its symbol starts with `Connector`;
- every mapped connector pin appears in some `NETS` member.

**Step 4:** Run `/usr/bin/python3 board.py`. Expected: `board.py self-check ok`.

**Step 5:** In `carrier_tme.py`, add `OFFBOARD` for X_PACK, X_HBAT, X_LCD, X_NFC, X_BTN_R, X_BTN_B, X_BUZ and
X_SPK, using the pin maps from the design §3. Use placeholder positions; Task 7 tunes them. Add `SHEETS`
grouping today's `BLOCKS` (power, i2c, expander, drivers, audio, debug). Add `ROOT` holding J2, J3, J_PWR1,
J_HBAT1, J_LCD1, J_NFC1, J_BTN_R1, J_BTN_B1, J_BUZ1, J_SPK1 and H1–H4.
- Add a `check()` assert: every `PARTS` ref is on exactly one of `ROOT["parts"]` or a `SHEETS` block.

Run `/usr/bin/python3 carrier_tme.py`. Expected: `carrier_tme ok: ...`.

**Step 6:** Commit: `hardware: carrier_tme SHEETS/ROOT/OFFBOARD data and OFFBOARD guard`.

---

### Task 2: New library symbols (Konnect)

**Files:** `kicad/local.kicad_sym`, written by Konnect only.

**Step 1:** `load_toolset("library")`, then fetch the tool schemas with ToolSearch `select:`.

**Step 2: Create the Heltec header symbols.**
- Compute pin names with a throwaway script:
  `HELTEC_GPIO` → `GPIO<n>`, plus the role (`RX`, `TX`, `RST`) where the V4 map names one;
  `HEADER_POWER` → `GND` / `3V3`; `HEADER_NC` → `5V (charger, NC)`, `Ve`.
- Create `local:Heltec_V4_J2` and `local:Heltec_V4_J3`: 18 passive pins each, numbered 1–18, at 2.54 mm
  pitch, pins on the side facing the module outline (J2 right, J3 left), a body rectangle, and Reference `J`.

**Step 3: Create the off-board symbols:**
- `local:Module_I2C_4`: pins 1 GND, 2 VCC, 3 SDA, 4 SCL;
- `local:Pack_Link_6`: GND, GND, VBAT, 5V, SDA, SCL;
- `local:Button_LED_4`: SW, COM, LED+, LED−.

All pins passive at 2.54 mm pitch on the left. `X_HBAT` uses stock `Connector_Generic:Conn_01x02`;
`X_BUZ` and `X_SPK` use stock `Device:Buzzer` / `Device:Speaker`.

**Step 4: Verify.** Re-query each symbol through Konnect (pin list and numbers), then run
`/usr/bin/grep -c '(symbol "Heltec_V4_J2"' kicad/local.kicad_sym` (a read-only check). Expected: 1.

**Step 5:** In `carrier_tme.py` only, override `PARTS["J2"]`/`PARTS["J3"]` to the new symbols. The flat
carrier keeps `Conn_01x18` until it migrates.

**Step 6:** Commit: `hardware: Heltec V4 header and off-board module symbols (via Konnect)`.

---

### Task 3: `check_netlist.py` ignores off-board refs

**Files:** modify `check_netlist.py`.

**Step 1:** Add a `__main__`-reachable self-test: feed `check()` a tiny KiCad XML string with an extra
`X_LCD` comp and node on `SDA_5V`. Expected: an `unexpected component` error today.

**Step 2:** Implement. Read `off = set(getattr(design, "OFFBOARD", {}))`, drop nodes and comps whose ref is
in `off` before comparing, and give `check()` an `offboard=` parameter so the self-test can pass its own set.

**Step 3:** Run the self-test. Expected: pass. Then run
`BOARD=carrier_tme /usr/bin/python3 check_netlist.py build/carrier_tme.xml`.
Expected: `netlist matches carrier_tme.py`. The schematic is still flat at this point.

**Step 4:** Commit: `hardware: check_netlist ignores OFFBOARD documentation symbols`.

---

### Task 4: gen_sch refactor: `build_sheet`, flat output byte-identical

**Files:** modify `gen_sch.py:238-251` (`Sheet`), `gen_sch.py:676-783` (`schematic`), and `main`.

**Step 1: Refactor without changing behaviour.**
- `Sheet.__init__(self, path=())` keeps `root`. It gains `path` (a tuple of sheet uuids) used by
  `instances()`. `instances(root, ref)` becomes `instances(sh, ref)` with path
  `"/" + "/".join([sh.root, *sh.path])`.
- Move the body of `schematic()` into `build_sheet(sh, blocks, parts, nets, exits)`:
  - `blocks`: list of block dicts.
  - `exits`: `{net: kind}` for nets that leave the sheet, where `kind` is `"global"` (flat) or
    `"hier"` (hierarchical).
  - Return `(body, w, h)`.
- `schematic()` becomes the flat wrapper, calling `build_sheet` with `design.BLOCKS`, every net, and the
  current global-label behaviour.

**Step 2: Regression.**

```bash
for b in carrier pack lipo pack_tme lipo_tme carrier_tme; do
  BOARD=$b /usr/bin/python3 gen_sch.py >/dev/null && cp kicad/$b.kicad_sch /tmp/schnew-$b.kicad_sch
done
for b in carrier pack lipo pack_tme lipo_tme carrier_tme; do cmp /tmp/schbase/$b.kicad_sch /tmp/schnew-$b.kicad_sch && echo "$b same"; done
git checkout -- kicad/
```

Expected: all six `same`. Any difference is a bug in the refactor: fix it before going on.

**Step 3:** Commit: `hardware: gen_sch build_sheet refactor (flat output unchanged)`.

---

### Task 5: gen_sch hierarchical mode

**Files:** modify `gen_sch.py` (new helpers, `main`) and `Makefile` (`sch` upgrade loop).

**Step 1: Hierarchical labels.**
- `glabel(sh, net, c, d, kind="global")` emits `["hierarchical_label", q(net), ["shape", "passive"], ...]`
  when `kind == "hier"`, with the same cells, angle and justify. The uuid key gets a kind prefix.
- `label_on_pin` and tag handling pass the kind through.

**Step 2: Sheet membership.**
- `sheet_of(ref)`: the `SHEETS` name, or `"root"`.
- A net *exits* a sheet if it has members elsewhere: in another sheet, in a root part, or on an `OFFBOARD`
  connector pin.
- Rails never exit; they stay power ports on every sheet.

**Step 3: Child sheets.**
- For each sheet: `sh = Sheet(path=(uid_raw(f"sheet/{name}"),))`, then `build_sheet(...)` with
  `exits={net: "hier"}`.
- Write `kicad/<NAME>-<name>.kicad_sch`: no `sheet_instances`, its own file uuid `uid("file/<name>")`,
  paper from its content.
- Record each sheet's hierarchical labels: `(net, cell, dir)`. They become the sheet box's pins.

**Step 4: Root.**
- `sh = Sheet()`. Place `ROOT["parts"]` with `place_part` and the `OFFBOARD` symbols with a variant of
  `place_part` that takes `(value, lib_id)` from `OFFBOARD` and emits `in_bom no`, `on_board no` and
  `uid(f"sym/{ref}")`.
- Draw the Heltec outline rectangle and its title.
- For each sheet box, emit `["sheet", at, ["size", w, h], stroke, fill, uuid uid("sheet/<name>"),
  property Sheetname, property Sheetfile "<NAME>-<name>.kicad_sch", pins..., instances(project, path
  "/<root>" page N)]`:
  - each sheet pin is `["pin", q(net), "passive", at(x, y, angle), font(justify), uuid]`;
  - pins go on the left edge if their root target lies left of the box centre, otherwise on the right;
  - pins are sorted by target y so root wires don't cross;
  - mark the box cells hard, and set `sh.term`/`sh.pins` for each pin cell (stub direction outward).
- Route each exiting net on the root over its terminals: root part pins, `OFFBOARD` pins and sheet pins.
  Use the existing `route()` with whole-root bounds.
- Name each routed root net with one global label via `name_label`, so net names stay flat.
- Root rails get `rail_ports`, as in flat mode.
- Off-board pins join the net of their connector pin. Add each as a terminal of that net, so `route()`
  draws the cable wire. On rails, the connector pin keeps its port and the off-board pin is routed to it.
- Add a cable-note text near each off-board part.
- `sheet_instances` sits on the root only: `/` page 1, then each sheet page 2..N.

**Step 5: `main`.**
- With `SHEETS` present: build the children, then the root. Clashes from any sheet → write
  `build/<NAME>_bad*.kicad_sch` and fail, as today.
- Write all files, plus `.kicad_pro`.

**Step 6: Makefile `sch` step.** Upgrade every file of the board:

```make
	for f in kicad/$(BOARD).kicad_sch kicad/$(BOARD)-*.kicad_sch; do [ -e "$$f" ] && kicad-cli sch upgrade "$$f"; done
```

The dash keeps `carrier-*` from matching `carrier_tme-*`.

**Step 7: Regression and smoke test.**
- Re-run the Task 4 Step 2 loop: flat boards must still be `same`. carrier_tme now differs (it has
  `SHEETS`), so leave it out of the `cmp` loop.
- Run `make BOARD=carrier_tme sch`. Expected: `upgraded` for the root and 6 children, then
  `netlist matches carrier_tme.py`. Placeholder layout clashes are allowed to fail here; Task 7 fixes the
  layout. If it fails on clashes, fix only the ones in structural code.

**Step 8:** Commit: `hardware: gen_sch hierarchical mode (sheets, sheet pins, root, OFFBOARD)`.

---

### Task 6: gen_pcb footprint paths follow the hierarchy

**Files:** modify `gen_pcb.py:88`.

**Step 1:** Replace with:

```python
sheet = gen_sch.sheet_of(ref)
path = "/" + gen_sch.unq(gen_sch.uid(f"sym/{ref}"))
if sheet != "root":
    path = "/" + gen_sch.unq(gen_sch.uid(f"sheet/{sheet}")) + path
fp.SetPath(pcbnew.KIID_PATH(path))
```

`sheet_of` returns `"root"` for every ref in flat mode, so flat boards are unchanged.

**Step 2: Check without routing.**

```bash
BOARD=carrier_tme /usr/bin/python3 gen_pcb.py
kicad-cli pcb drc --schematic-parity --severity-all -o /tmp/ct.rpt kicad/carrier_tme.kicad_pcb | tail -3
```

Expected: `Found 0 schematic parity issues`. Unconnected items are expected on the unrouted board. Then run
`git checkout -- kicad/carrier_tme.kicad_pcb`.

**Step 3:** Commit: `hardware: gen_pcb links footprints through the sheet path`.

---

### Task 7: carrier_tme layout (root + sheets), audio along the signal path

**Files:** modify `carrier_tme.py` (`SHEETS` block coordinates, `ROOT`, `OFFBOARD` positions, the audio
block).

**Step 1: Audio block.**
- Delete the x = 15.24 tag column, apart from the nets that really leave the sheet: I2S_*, AMP_SD and
  SPK_±. Those become hierarchical labels on the left (inputs) and right (SPK) edges.
- Place parts along the flow, every capacitor beside its own pins, per design §4.
- Internal nets get no tags. If gen_sch's labeler can't find a run, extend `name_label` to fall back to
  `label_on_pin` at the net's first pin instead of the far column. This is a gen_sch change; re-run the
  Task 4 flat regression afterwards.

**Step 2: Root.**
- Heltec outline in the centre.
- Sheet boxes beside the Heltec pins they use: power and i2c top-left, expander and drivers on the right,
  audio bottom-right, debug bottom-left.
- Connectors at the edges, each off-board part beyond its connector.

**Step 3: Iterate.** Run `BOARD=carrier_tme /usr/bin/python3 gen_sch.py` until it reports no clashes.
After each pass, render: `kicad-cli sch export pdf -o /tmp/ct.pdf kicad/carrier_tme.kicad_sch`, then
`pdftoppm -r 80 -png`, one page per sheet. Look at every page.
- Acceptance: no wire crossings in the audio sheet, no label more than one stub from its pin, root wires
  parallel and readable, no empty half-pages.

**Step 4:** Run Konnect `check_schematic_overlaps` on the root and each child file. Expected: 0 overlaps on
each.

**Step 5:** Commit: `hardware: carrier_tme hierarchical layout`.

---

### Task 8: Full build and gates

**Step 1:** Run `make BOARD=carrier_tme all` in the background (it routes). Expected:
- `netlist matches carrier_tme.py`;
- ERC `Found 0 violations`;
- DRC `Found 0 violations`, `0 unconnected`, `0 schematic parity issues`;
- `gerbers ok`.

**Step 2: Board unchanged apart from paths.**
- Compare footprint positions and net assignments between HEAD and the new board with a pcbnew script:
  load both, then compare `(ref, position, rotation, {pad: net})`.
- Expected: identical.
- Routing may differ slightly, since Freerouting reruns, but DRC is the gate.

**Step 3: Regression.** Rebuild the flat boards' sheets (`make BOARD=<b> sch` for carrier, pack, lipo,
pack_tme, lipo_tme). Expected: `git status` shows no `kicad/*.kicad_sch` changes for them.

**Step 4:** Run Konnect `run_design_review` on carrier_tme. Expected: 0 errors; MPN noise only.

---

### Task 9: Docs, memory, push

**Files:**
- Modify: `docs/plans/2026-10-18-hierarchical-schematics-design.md` (status: implemented on carrier_tme)
- Modify: `hardware/docs/ORDERING.md` (TME section: the schematic is now multi-page; off-board parts are
  marked "not on board")
- Modify: `Makefile` comment

**Step 1:** Write the doc updates.

**Step 2:** Commit `hardware: carrier_tme hierarchical schematic`, then `rtk git push`.

**Step 3:** Update the memory notes `kicad10-migration` / `airsoftcounter-v2-status` with the new mode and
the sheet-file naming.
