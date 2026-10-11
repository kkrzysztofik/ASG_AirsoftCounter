# Pre-purchase de-risking for the P2S build: design and plan

The mech parts are printed on the user's own Bambu P2S in PETG, not at JLC3DP. With KiCad 3D models in the
assembly gate (`make models`), the first real component clash showed up: the right carrier arm over the pack
board's 2-pin vertical JST (J_KEY1). A headroom survey showed worse: a pack 6-pin JST under the carrier with
1.0 mm to spare (a plug can never go in), and carrier JSTs whose plugs and wires would reach the LCD. This
round makes the gate see those things before anything is bought, and gives the user a coupon to calibrate the
printer.

## Decisions (user, 2026-10-11)

- **Printing:** Bambu P2S, PETG, 0.4 mm nozzle. The JLC profiles stay for a possible quote later.
- **Supports:** allowed where needed (Bambu tree supports), so overhangs are not gated.
- **Boards:** can change. Connector moves are proposed and shown before any regeneration.
- **Scope:** A (connector plug keep-outs + fixes), B (wall-device bodies), D (test coupon). F (JLC quote) is
  dropped.

## P2S process profile

`PROCESS_RULES["p2s"]`, the new default for `MECH_PROCESS`:

| Rule | Value | Source |
|---|---|---|
| Name | "PETG (Bambu P2S, 0.4 mm)" | |
| Minimum wall | 1.2 mm at every size | 3 perimeters of a 0.4 mm line |
| `clear` / `hole_tol` | 0.2 mm per side, so `FIT` = 0.5 | Calibrated by the coupon |
| `min_build` | (0, 0, 0) | No service minimum |
| `max_build` | (256, 256, 256) | P2S build volume |
| `escape` | 0 | No powder |

- check.py's `jlc_*` checks read `RULES`, so they apply the P2S numbers. Their messages name the process.
- `quote.py` refuses the p2s process with a clear message: nothing to quote.

## A: connector plug keep-outs

- `PLUG_KEEPOUT` is the height above a vertical XH header's top that a mated XHP plug plus a wire bend needs.
  It comes from the JST XH datasheet (mated height minus header height, plus a bend allowance) and carries a
  MEASURE comment citing the source.
- For every solid on either board whose label is a vertical JST XH header, `placeholders()` adds a keep-out
  box over that solid's XY footprint, from its top to its top + `PLUG_KEEPOUT`. It is named
  `plug_<board>_<n>` and the FAIL line says where it is.
- Expected: the gate fails, listing every connector a plug cannot reach. Each failure becomes a fix proposal
  for the user: a connector moved on `pack.py` / `carrier.py`, or a mechanical change. Nothing is regenerated
  without approval.

## B: wall-device bodies

- `WALL_PARTS` and `SPEAKER_WALL` gain the device's body behind the wall: a diameter or box and a depth from
  the wall's inner face, plus `CABLE_ALLOWANCE` for a connector or cable leaving the back.
- Exact parts come from the off-board order lists in the repo, sizes from their datasheets. Each value cites
  its source, or is MEASURE when no datasheet gives it.
- `placeholders()` adds `body_<device>` envelopes placed with `wall_frame`, reaching inward. The gate then
  checks speaker vs LCD, buzzer vs LCD, key vs pack, and so on.

## D: test coupon

`--part coupon` (built by `make mech`, `out/coupon.stl`) is one plate, at most 100 × 60 mm, built from the
real params and helpers:

- **Fit sweep:** pegs and holes at 0.15 / 0.20 / 0.25 / 0.30 / 0.40 mm per side, each labelled in raised text.
  The user picks the one that slides and sets `clear` from it.
- **Screw post:** one `post()` with the real M3 pilot (`POST_PILOT`, `PILOT_DEPTH`).
- **Groove:** a sector of the grille face with the real O-ring groove ring.
- **Saddle:** one cell-saddle scallop (radius `CELL_D/2 + SADDLE_CLEAR`) about 15 mm long, to seat a real
  18650.
- **Lid strip:** a lid-thickness strip with the thinnest lid web the check allows, plus one LCD boss with its
  pilot.
- `check_part` covers it: one solid, fits the bed.

## Plan

Batches run in order. Each is implemented by a subagent, then gets a spec review and a quality review.

1. **P2S profile + coupon.**
   - Add the p2s profile, make it the default, and have quote.py refuse it.
   - Add `make_coupon` and `--part coupon`, included in `all`.
   - Verify: check.py passes on p2s, mjf and fdm, every part `ok`, and the coupon is 1 solid within 100 × 60.
2. **A + B keep-outs and bodies.** Add the datasheet-sourced params with citations, then the placeholders.
   Run the gate with models and record every FAIL. Expected: it fails, and that is the deliverable.
3. **Fix proposals.** For each clash: the cause, two options and a recommendation, to the user. Then apply
   the approved board moves with the PCB generator flow (regenerate, re-route, DRC, gerbers) and the mech
   changes, until `make mech` passes with models.
