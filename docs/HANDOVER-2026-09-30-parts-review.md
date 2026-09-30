# Handover: PCB parts-list review (2026-09-30)

Branch: `esp32-lora-design` (pushed, latest commit `f516105`). The cloud session had no KiCad, so
**all source changes are made but nothing was regenerated.** Start by running `make all` in
`hardware/` on a machine with KiCad 9 and fixing whatever it reports.

## Commits this session

| Commit | What |
|---|---|
| `a42af2a` | All 9 off-board connectors unified to JST-XH 4-pin B4B-XH-A (C144395); the five 2-wire ones (BAT, KEY, HELTEC_BAT, BUZ, SPK) leave pins 3-4 NC (`design.XH_SPARE`, flagged no-connect in `gen_sch.py`). |
| `89aaec2` | AO3400A dropped; `Q_LR1`, `Q_LB1`, `Q_BZ1` now BSS138 (C7420339), like the I2C shifter. Loads are ~15 mA (ONPOW LAS1-AGQ 6 V ring) and ~8 mA (BZ-38), both from web-search snippets, not datasheets. |
| `7f64a6c` | `hardware/fab/PART_ALTERNATIVES.md`: TCA9534 (U2) and MAX98357A (U3) alternatives, none adopted. |
| `f516105` | Driver gate resistors 100R -> 1k, gate pull-downs 100k -> 10k; `hardware/fab/PARTS_REVIEW.md`. |

`ORDERING.md`, `OFFBOARD_PARTS.md`, `COSTS.md` and the design doc were updated to match. Current
counts: 19 BOM lines Deluxe / 18 Budget, 7 Extended types Deluxe / 6 Budget, 2 Preferred, 10 Basic.
`python3 design.py` passes.

## To do before this is usable (needs KiCad)

1. **`gen_pcb.py` placement.** A 4-pin XH is ~12.4 mm long (2-pin ~7.4 mm). On the top edge
   J_BAT1/J_KEY1/J_HBAT1/J_LCD1 are 9-12 mm apart and will overlap; the left-edge J_SPK1/J_BTN_B1/J_BUZ1
   are tight. Re-place them; the 90x60 mm board may need to grow.
2. **Silkscreen `LABELS`** in `gen_pcb.py` for the now-unused pins 3-4.
3. **`make all`:** regenerates schematic, PCB, routing, ERC/DRC and `fab/*.csv` (`jlc_bom*.csv`,
   `bom.csv`, CPL). Those CSVs are stale until then.
4. **Schematic auto-router:** check `gen_sch.py` copes with the taller 4-pin symbols in the existing
   `BLOCKS` layout (may report clashes; adjust positions/block sizes).
5. **Gate divider:** with 1k gate R and 10k pull-down the FET gate sits at ~3.0 V (3.3 V x 10/11).
   Fine for ~15 mA loads; confirm on the bench.

## Open questions (nothing decided)

- **Battery protection.** F1 (2 A hold PTC) is the only protection on unprotected 18650s. Hold current
  derates to ~1.4 A at 60 C (estimate) vs ~1.5 A worst-case load, so nuisance trips are possible in a
  hot enclosure. There is no under-voltage cutoff on the board and the MT3608 EN is tied to VIN (always
  on). **Whether the Heltec V4 cuts off a discharged cell is unverified** (Heltec's datasheets were
  unreachable): check the V4 schematic. Options: protected cells, or firmware cutoff on VBAT sense
  (GPIO1) plus a boost enable on spare expander pin P6/P7 (`U2.11`/`U2.12`).
- **Optional merges not done:** `C_BULK1/2` to the 100 uF 6.3 V part (drops one line, less hot-plug
  margin); drop `D_FLY1` (BZ-38 is a piezo with generator, not inductive).
- **Alternatives unverified:** JLCPCB Basic/Extended status, stock and price of PCF8574T/PW,
  PCA9534, PCA9554, NS4168 were never checked (jlcpcb.com was unreachable). Decision so far: keep
  TCA9534 (PCF8574 powers up high, which would switch on buzzer/LEDs at reset) and MAX98357A.

## Reasoning recorded in the repo

- `hardware/fab/PART_ALTERNATIVES.md`, `hardware/fab/PARTS_REVIEW.md`
- Why the two ICs exist: MT3608 makes the 5 V rail (LCD, 6 V LED rings, buzzer) that the Heltec does
  not provide; TCA9534 frees GPIOs so I2S (47/48/21) fits, see "Part 6" of
  `docs/plans/2026-09-28-esp32-lora-carrier-design.md`.
- Setup fees apply only to Extended parts, so merging Basic values saves BOM lines, not money.

## Environment notes

- The cloud sandbox blocked jlcpcb.com and heltec.cn; nothing there could be verified.
- Bash tool calls failed intermittently on a safety-check error; retries eventually succeeded.
