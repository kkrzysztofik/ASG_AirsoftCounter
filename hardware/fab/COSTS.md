# Per-unit cost: Deluxe and Budget variants

Checked 2026-09-30, PLN gross. **V** = read from a shop page; **~** = estimate or unverified generic part.
TME hides its exact price, so a TME figure is the high end of its schema price range, which matched the
gross price on the items cross-checked. Excludes the carrier PCB/PCBA (no quote yet), shipping, standoffs
and wire (never priced). Player cards are ~3 zł each on top.

Variants are defined in `hardware/design.py` (`MODULES`, `VARIANTS`); `make fab` writes
`fab/jlc_bom.csv`/`jlc_cpl.csv` (deluxe) and `fab/jlc_bom_budget.csv`/`jlc_cpl_budget.csv`.

## Presets

| Line | Deluxe | Budget | Basis |
|---|---|---|---|
| Heltec V4 (863–870 MHz, no display) | 85 | 85 | V: $17.90–27.50 range, exact option price shown only at checkout |
| LCD 20x4 I2C | 34.90 | 34.90 | V Botland |
| Buttons, 2x | ~93 | ~42 | Deluxe: ONPOW 19 mm IP67, blue 46.46 V, red not stocked (est. same). Budget: generic 16 mm IP65 metal, 5 V LED (Allegro ~20.99 each), IP rating unverified |
| Buzzer | 22 | ~15 | Deluxe: 3–28 V piezo, 13.45–22.22 V (the BZ-38 URL redirected to this part, code unconfirmed) |
| Key switch | 53.33 | 53.33 | V TME AUSPICIOUS KS22-1O/C, 38.11–53.33, 322 in stock; maintained, IP65 |
| 2x 18650 cells | 59.80 | 59.80 | V Botland (2x 29.90) |
| 2x 18650 holders | 7.80 | 7.80 | V Botland (2x 3.90) |
| Antenna + u.FL pigtail | 53.74 | ~30 | Deluxe: Linx 40.51 V + pigtail 13.23 V. Budget: generic whip ~ (sets LoRa range: test first) |
| USB-C panel extension | ~35 | ~35 | ~ IP67 when capped/mated accepted. Fallback: Kamami 32.02 V + rubber plug 1.90 V + gasket |
| JST/PicoBlade connectors | ~10 | ~10 | ~ |
| Enclosure | 178.55 | 65.74 | Deluxe: Kradex ZP240.190.105SJp 119.90 V + plate 58.65 V. Budget: Pawbol S-BOX 416-P, 52.59–65.74 V at TME (36 in stock); 34.05 at elektryczny.pl but 2 in stock |
| L76K GPS | 29 | – | V $8 + cable |
| PN532 NFC | 24.90 | – | V kamami |
| Speaker (VISATON K 50, IP65, 8 Ω 2 W) | 14.20 | – | V TME 10.23–14.20, 829 in stock |
| **Total (priced lines)** | **~700** | **~440** (~390 with a ~5 zł toggle) | Budget: ~305 of it is V |

## Module mix

Add or remove per module. Everything works on the same PCB; only the BOM changes (see `design.MODULES`).

| Module | Adds | Deluxe part | Budget part | On-board parts dropped when absent |
|---|---|---|---|---|
| Buttons | +93 / +42 | ONPOW pair | generic 16 mm pair | 2 BSS138 drivers, 2 RC input filters, `J_BTN_R/B` |
| RFID | +24.90 (+3/card) | PN532 | same | `J_NFC1` |
| Speaker | +14.20 | VISATON K 50 | same | NS4168 (`U3`), its caps, `R_SD1`, `R_SDPD1`, `J_SPK1` |
| GPS | +29 | L76K | same | none (Heltec connector only) |
| Key vs toggle | +53.33 vs ~5 | KS22 | KS22 or toggle | none |
| Enclosure | 178.55 / 65.74 | Kradex + plate | Pawbol | none |

Rules: a variant needs **buttons or RFID** (`design.check()` fails otherwise). RFID without buttons means no
local admin menu. Dropping the speaker also drops the only Extended-part setup fee on the amp (`U3`, C910588);
`U2` (the expander) stays in every variant because the LEDs, buzzer and buttons sit behind it.

## Budget trade-offs

- **Buttons:** IP65 instead of IP67, unbranded, 16 mm hole instead of 19 mm. A 12 V ring LED would be dim on
  our 5 V rail (~3 mA estimated); buy a 5 V-rated one. Buy one pair as a test first.
- **Key switch:** 3 A / 230 V AC rating, no published DC rating (our load is ~250 mA at 4 V).
- **Case:** Pawbol S-BOX 416-P is IP65 (manufacturer catalog), clear PS/ABS/PC lid, 4 plastic screws, IK08.
  The catalog lists **190 x 140 x 70 mm as inside dimensions** (whether the 70 mm includes the lid depth is
  not stated). No brass inserts and no mounting plate: standoffs into the base bosses or glued bases. Wall
  thickness and boss spacing unknown: do a 1:1 mock-up with one box before ordering more.
- **USB-C:** IP67 only while capped or mated; open while charging or flashing. Accepted.

## Open items

- **Red 6 V ONPOW button** (LAS1-AGQ-11E/R/6V, Deluxe): no stocked listing found. Options: ask TME/Piekarz/AVT
  to order it, use another ring colour, or move to a 12 V ring (needs a 12 V rail; dim at 5 V).
- **Budget power switch:** KS22 key (~53) or toggle (~5): undecided. The KS22 stops players switching a unit off.
- **Buzzer:** confirm the exact TME code (BZ-38 vs PK35N29EPQ).
- **USB-C extension:** no verified European listing. Test one threaded 12 mm male-female extension with cap
  and O-ring (Amazon.de or AliExpress); fallback is the Kamami extension + plug.
- Every "~" Budget line is an unverified generic part. Nothing is priced for the carrier PCB/PCBA or standoffs.
- Buttonless build: the expander's P0/P1 inputs have no pull-ups then, so firmware must set them as outputs
  (floating inputs would toggle INT).
