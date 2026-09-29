# Ordering the carrier PCB from JLCPCB (bare board)

Regenerate everything with `cd hardware && make all` (it exits non-zero if ERC, DRC or the gerber check fails).

## 1. Upload

Go to https://jlcpcb.com/, click "Order now" and upload **`fab/carrier_gerbers_jlcpcb.zip`** (9 Gerber layers + PTH/NPTH Excellon drill files).
JLC should detect **90 x 60 mm, 2 layers** on its own. If it shows a different size or layer count, stop and don't order.
Check the Gerber viewer: the outline has rounded corners, there are 4 mounting holes 3.5 mm from the corners, and both sides have a GND pour.

## 2. Form settings

| Field | Setting | Why |
|---|---|---|
| Base material | FR-4 | |
| Layers | 2 | |
| Dimensions | 90 x 60 mm (auto) | |
| PCB Qty | 5 | This is the minimum. |
| Product type | Industrial/consumer electronics | |
| Different design | 1 | |
| Delivery format | Single PCB | No panel needed for hand assembly. |
| PCB thickness | 1.6 mm | Matches the design and the standoffs. |
| PCB color | Green | Cheapest and fastest. Other colours work but can take longer. |
| Silkscreen | White | |
| Surface finish | LeadFree HASL (recommended) or HASL with lead | Leaded HASL is the cheapest and a bit easier to hand-solder. Lead-free is RoHS, which suits an EU build and lead-free solder. ENIG is not needed. |
| Outer copper weight | 1 oz | |
| Via covering | Tented | This is the standard option for small vias. |
| Min via hole size/diameter | 0.3 mm (0.6 mm pad) | |
| Board outline tolerance | ±0.2 mm (Regular) | |
| Mark on PCB | Default (order number) | JLC prints its order number somewhere on the silkscreen. Placing it at a chosen spot needs a marker text on the board, which this design doesn't have. Removing it is a paid option. It is harmless for this board. |
| Electrical test | Flying Probe Fully Test | Free for small boards. |
| Gold fingers | No | |
| Castellated holes | No | |
| Edge plating | No | |
| Impedance control | No | |
| Confirm production file | Optional | "Yes" means you approve JLC's processed files before production. It is slower, but a useful extra check on a first order. |
| PCB assembly / stencil | Off | The board is hand-soldered. |

Leave the other fields at their defaults. Price and lead time follow from these choices. Compare the options on the form itself.

## 3. Board facts (for capability questions)

| Item | Value |
|---|---|
| Size / layers | 90 x 60 mm, 2 copper layers, rounded corners |
| Material / thickness | FR-4, 1.6 mm, 1 oz outer copper |
| Min track / clearance | 0.25 mm track (0.2 mm rule), 0.2 mm clearance |
| Vias | 0.6 mm pad / 0.3 mm drill, tented (24 vias) |
| Plated component holes | smallest 0.8 mm (0.8 / 0.95 / 1.0 mm) |
| Non-plated holes | 4 x 3.2 mm (M3 mounting), in the NPTH drill file |
| Copper to board edge | 0.5 mm |
| Silkscreen | text 0.8–1.0 mm, 0.15 mm stroke, top only |
| Copper pours | GND on top and bottom |
| Components | top side only (SMD + THT), no bottom-side parts |
| Special features | none: no castellations, edge plating, gold fingers or impedance control |

## 4. Before paying: Heltec fit check (Task A5)

You can get a price quote now. **Don't pay until the 1:1 paper fit check has passed** with a real Heltec V4:

1. Print `fab/print_1to1.pdf` at 100 % (no "fit to page"). Check that the board outline measures 90 x 60 mm.
2. Push the Heltec header pins through the paper at J2/J3. The first and last holes of each header row are **43.2 mm** apart.
3. Orientation: the USB-C connector goes at the "USB" label, and **J3 (GPIO1–7 row) is the top row**. A mirrored or reversed module would put GND/3V3 on GPIO pins.

## 5. Parts

The board ships bare. `fab/bom.csv` lists the on-board parts to buy separately, grouped by value and footprint. The DNP pull-ups R_SDA5/R_SCL5 are left out on purpose.
The off-board parts are in `docs/plans/2026-09-28-esp32-lora-carrier-design.md`: Part 3 (enclosure, buttons, key switch, USB-C/SMA bulkheads, 18650 holder, GNSS) and Part 5 (PN532 NFC module, cards). You also need the Heltec V4 itself.

Other files in `fab/`: `schematic.pdf`, `top.png`/`bottom.png` (3D renders), `gerbers/` (the unzipped Gerbers plus drill maps and a Gerber job file, which are not in the zip).
