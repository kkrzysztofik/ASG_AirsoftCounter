# Pawbol S-BOX 416-P insert: base tray and lid panel

Date: 2026-10-02
Status: design approved in review 2026-10-02. Model not written yet. Every number below is either
read from a source named beside it, or listed under "Must be measured" / "Unverified".

The budget tier's Pawbol enclosure ships as an empty tub: **no mounting plate, no brass inserts, no
knockouts**. This spec adds two printed PETG parts so a unit can be assembled by dropping parts in
and turning four screws, instead of measuring standoffs into base bosses.

Follows the same generator philosophy as the boards (`design.py` -> `gen_sch.py`/`gen_pcb.py`): one
Python module holds the numbers, one command emits the artefacts.

## Goal

- Give the pack board, its four 18650 cells, the carrier and all off-board parts a defined home.
- Keep the assembly reversible and the enclosure unmodified apart from the holes the panel devices
  need anyway.
- Close the risk the pack design already flags: "spring-contact holders can open momentarily under
  shock (airsoft use) ... add a strap or lid". The printed cradle is that strap.

## Scope

In: the base tray, the lid panel, the speaker grille, drill templates, and the build tooling.

Out: the carrier and pack PCBs, the panel devices themselves, the Deluxe Kradex ZP240.190 enclosure
(240 x 191 x 106, has its own plate), the firmware.

## The enclosure: facts

Source: Pawbol *KARTA KATALOGOWA, Puszka instalacyjna serii S-BOX 190x140x70 / bez dławików*,
S-BOX 416_416B_416-P, fetched 2026-10-02. The drawing carries the note **"Wymiary A, B, C są
wymiarami wewnętrznymi S-BOX"** — A, B and C are inside dimensions.

| Quantity | Value | Origin |
|---|---|---|
| Inside (A x C x B) | 190 x 140 x **70** mm | drawing note; the 70 is the **base** interior, the lid recess sits on top of it |
| Outside | 196 x 146 mm, base height 78 mm | drawing |
| Wall thickness | **3 mm** | (196 − 190) / 2, confirmed by (146 − 140) / 2 |
| Corner screws | 4, plastic, through the **lid** into full-height corner columns | drawing + product photo |
| Corner column thread depth | about 50 mm (drawing dimension "50") | drawing, unverified |
| Seal | gasket between lid and rim, IP65 | product description |
| Body / lid | PS/ABS RAL 7035 / transparent, −25…+60 °C | catalog table |
| Supplied | **bare tub.** No plate, no inserts, no glands | shop listing, `COSTS.md` |
| Internal features | central cross rib with slots, round floor bosses | drawing |

**The box being ordered has plain side walls — no Ø37 PG29 membranes.** The shop's listing for
416-P advertises 10 knockouts at Ø37/PG29, but the version on order has none (confirmed
2026-10-02). Every wall penetration is therefore a hole that gets drilled. Treat *all* internal
floor features as unverified: do not design anything that depends on the rib or the floor bosses.

## Decisions

| Decision | Choice | Basis |
|---|---|---|
| Part split | **base tray + lid panel**, two prints | keeps the transparent lid face intact, so the LCD needs no window and no gasket |
| Retention | tray legs slide **inside the 4 corner columns**, flange rests on the column top. Screw stack: lid -> panel ear -> tray flange -> column thread | reuses the column's existing thread; each added layer costs ~3 mm of screw |
| LCD | 20x4 pressed against the inside of the clear lid by a printed frame | same call as the Kradex design (`2026-09-28-esp32-lora-carrier-design.md`): "LCD behind clear lid (no window)" |
| NFC | PN532 in a panel pocket, tapped through the clear lid | carrier design: 3–5 cm expected through 3 mm PC; keep >=20 mm off the LCD frame |
| Buttons | 2 x Ø16 in the **lid**, drilled with a printed 1:1 template | user 2026-10-02; matches the panel's button bosses |
| Speaker | 50 mm in a **wall**, printed **mesh grille** plate outside, foam gasket | user 2026-10-02 |
| Wall sealing | one printed bushing + O-ring per penetration, plus an internal backing block | user 2026-10-02; 3 mm PS/ABS cannot carry a tightened nut |
| Cells | printed cradle with 4 troughs and a **snap hold-down bar** | pack design's shock-dropout risk |
| Panel vent | **none** | YAGNI. If the speaker sounds boxy in the sealed tub, add the small second mesh panel then |

## Interfaces

### A. Corner screw stack

The lid screws are plastic and thread into the corner columns. The tray leg is a sleeve that rides
down inside each column, with a flange resting on the column's top face. The screw passes through
the lid, the panel ear and the tray flange before it reaches the original thread.

Screw length must grow by roughly (panel + flange) = **6 mm**, or the original screw is reused if its
thread engagement still satisfies the PS/ABS column. **Screw thread (M4?) and the column's inner
size are unmeasured** — the coupon in Verification settles both.

### B. Board patterns

Read from the board modules, not invented here:

| Board | Outline | M3 hole raster | Source |
|---|---|---|---|
| Pack | 96 x 90 mm | (4, 4) (92, 4) (4, 86) (92, 86) — 88 x 82 | `hardware/pack.py:434,482` |
| Carrier | 90 x 60 mm | (3.5, 3.5) (86.5, 3.5) (3.5, 56.5) (86.5, 56.5) — 83 x 53 | `hardware/design.py:272,278` |

Both are `MountingHole_3.2mm_M3`. The tray posts are PETG, sized for an M3 self-tapping screw.
The pack board's own corner raster is still flagged provisional in the pack design doc, so the tray
posts are a parameter, not a constant.

### C. Cell cradle

Four troughs at the MYOUNG holder pitch, **21.66 mm** (pack design doc: holders 77 x 20.7 x 14.9 mm
bodies at 21.66 mm pitch), trough radius for an 18.4 mm cell plus clearance, with a snap bar over
the top. The pack board sits on posts above the cells and its holders sit in the troughs, so the
cradle takes the recoil load off the holder contacts.

### D. Wall penetrations

| Device | Hole | Notes |
|---|---|---|
| Key switch | Ø22.3 | EAO 82-6121.2000 / KS22; bushing also gives it something to tighten against |
| Speaker K50 | Ø50 | printed mesh grille plate outside, foam gasket; **the only hole that also gets a printed drill guide ring** |
| USB-C panel extension | Ø12.2 nominal, **measure the actual barrel thread** | IP67 only while capped or mated |
| SMA bulkhead | Ø6.5 | O-ring plus star washer, hex pocket inside to hold the nut |
| Buzzer BZ-38 | measure the body | no IP rating of its own — bushing + O-ring is what seals it |

Positions are free parameters; the defaults keep the SMA high on a long wall, away from the u.FL pad
and the LCD.

### E. Lid

- 2 x Ø16 button holes, 1:1 printed template, backed by the panel's button bosses.
- LCD frame presses the 20x4 against the clear face.
- PN532 pocket, >=20 mm from the LCD metal frame.
- 4 corner ears in the screw stack of interface A.

## What gets printed

| Part | Qty | Material | Purpose |
|---|---|---|---|
| Base tray | 1 | PETG | corner legs, cell cradle + snap bar, board posts, cable clips, wall backing blocks |
| Lid panel | 1 | PETG | LCD frame, button bosses, NFC pocket, 4 corner ears |
| Speaker grille plate | 1 | PETG | 50 mm mesh, covers the wall hole from outside, foam gasket |
| Drill guide ring | 1 | PETG | clamps to the wall for the Ø50 holesaw only |
| Drill templates | — | paper | 1:1 sheets, same style as the existing `fab/print_1to1.pdf` |

## The height budget

Measured from the tray floor up:

| Item | mm |
|---|---|
| Tray floor | 2.4 |
| 18650 cell | 18.4 |
| Pack board | 1.6 |
| Standoffs, pack -> carrier | 8 |
| Carrier | 1.6 |
| Heltec in its 2x18 headers | 15 |
| **Subtotal from the floor** | **47.0** |
| LCD + HW-61 backpack (hangs from the lid) | 12–20 |
| Lid panel | 3 |
| **Total** | **62–70** |

Against 70 mm of base interior plus the unmeasured lid recess. It fits, with the lid recess as the
margin. This replaces the first estimate, which wrongly assumed the 70 mm included the lid.

## Parts and repo layout

```
hardware/mech/
  insert.py      # parameters + the tray, panel, grille and template builders
  out/           # generated *.step/*.stl (gitignored); print_1to1.pdf is committed,
                 #   as fab/print_1to1.pdf already is for the boards
```

The build123d model is one module in the repo's style: all dimensions as named top-level parameters,
one `main()` that writes every artefact, one self-check that runs on plain `python3` without
build123d installed.

```bash
make mech          # new target in hardware/Makefile, next to `boards`
```

**Toolchain:** `uv` with PEP-723 inline script metadata, so `uv run hardware/mech/insert.py` resolves
build123d without a venv or a requirements file. Verified 2026-10-02: build123d 0.13.0 imports under
`uv run --with build123d` on this machine.

## Parameters (named, with defaults)

| Parameter | Default | Status |
|---|---|---|
| `BOX_IN` | (190, 140, 70) | firm |
| `WALL` | 3.0 | firm |
| `COLUMN_XY`, `COLUMN_SIZE` | — | **must measure** |
| `SCREW_RASTER` | — | **must measure** |
| `SCREW_THREAD` | M4 assumed | **must measure** |
| `LID_T`, `LID_RECESS` | — | **must measure** |
| `PACK_XY`, `PACK_HOLES` | (96, 90), 4 mm inset | from `pack.py` |
| `CARRIER_XY`, `CARRIER_HOLES` | (90, 60), 3.5 mm inset | from `design.py` |
| `CELL_PITCH`, `CELL_D` | 21.66, 18.4 | pack design doc |
| `STANDOFF_H` | 8.0 | stack budget |
| `FIT` (drop-in clearance) | 0.4 | tune on the coupon |
| `BUTTON_D` | 16.0 (19.0 Deluxe) | `COSTS.md` |
| `SPEAKER_D` | 50.0 | `OFFBOARD_PARTS.md` |
| `MESH_OPEN` (open area) | >= 40 % | acoustic floor for a printed grille |

## Must be measured before the first real print

1. Corner column: outer size, inner bore, depth, wall-to-column gap.
2. Corner screw: thread, length, how deep it engages.
3. Lid: thickness, the internal corner posts, and the recess depth above the base rim.
4. 20x4 LCD + HW-61 backpack depth.
5. Heltec V4 board-to-header-top height when seated in the carrier.
6. Button body depth and thread length; USB-C barrel thread; SMA thread length.

## Verification

1. **Self-check** (`python3 -c` importable without build123d): bounding box fits `BOX_IN` minus
   clearance, the two post rasters equal the board modules' `PLACE["H*"]` coordinates, and the stack
   total in the table above is <= the base interior.
2. **Fit coupon first** — a single small print carrying one corner leg, one column sleeve and one
   board post. It settles interface A (the only interface with no second chance: a wrong column
   means a reprint of the whole tray). Print the coupon before the tray, always.
3. **1:1 paper templates** against the real box for the button and wall holes, before any drilling.
4. `make mech` green, plus a 1:1 outline print of the tray to lay on the box floor.

## Risks

- **Corner column unmeasured.** The leg is the one feature that cannot be salvaged after printing.
  Mitigated by the coupon and by `FIT` being a parameter.
- **Lid internal corner posts** may collide with the panel ears. Measure before printing the panel.
- **Screw length.** Adding 6 mm may exceed the original screw. Fallback: four longer plastic screws,
  or a printed captive-nut corner that drops the column's thread entirely.
- **Drilling PS/ABS by hand** crazes or cracks the wall. Use a step drill or holesaw at low speed,
  back the wall, and use the printed guide ring for the Ø50.
- **Printed mesh** attenuates high frequencies. Keep open area >=40 %, slots not round holes, and put
  the grille as close to the speaker as the wall allows.
- **Sealed tub** with the speaker inside: no vent. Accepted for now; the small mesh vent is the
  known upgrade path if it sounds boxy.
- **PETG at 60 °C** (the box's rated top): Tg is about 80 °C, so no creep expected, but the panels
  are clamped, not load-bearing.

## Unverified

- Every `must measure` item above.
- Whether the delivered plain-wall box still has the central cross rib and the floor bosses. Nothing
  in the design depends on them.
- The corner column's thread depth ("50" on the drawing is almost certainly this, but it was read
  from a section view, not from a dimension table).
- The exact 416-P lid screw part. The tray assumes a reusable, standard plastic screw.
