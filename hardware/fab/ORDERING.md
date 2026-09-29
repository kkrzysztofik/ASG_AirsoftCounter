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

1. Print `fab/print_1to1.pdf` at 100 % (no "fit to page"). Check the scale on the J2/J3 header holes: the centres of the first and last hole in a row are **43.2 mm** apart (17 x 2.54 mm), and the two header rows are **22.86 mm** apart. The board is plotted from the page's top-left corner, so the top and left board edges may not print. That is expected, so don't use the outline as the scale reference.
2. Push the Heltec header pins through the paper at J2/J3. All 18 pins of each row should go straight through.
3. Orientation: the Heltec's USB-C end goes at the **left** end of the header rows (pin 1, towards the middle of the board), and the antenna end points at the right board edge. **J3 (GPIO1–7) is the top row**; the print labels the rows "Heltec_J3" and "Heltec_J2" at their right ends. A mirrored or reversed module would put GND/3V3 on GPIO pins. The black-and-white print doesn't show the "USB" and "ANT →" silkscreen labels because they sit on the GND pour, but they will be on the real board.

## 5. Parts

The board ships bare. `fab/bom.csv` lists the on-board parts to buy separately, grouped by value and footprint. The DNP pull-ups R_SDA5/R_SCL5 are left out on purpose.
Off-board parts (details in `docs/plans/2026-09-28-esp32-lora-carrier-design.md`, Parts 1–3 and 5):

- Heltec WiFi LoRa 32 V4 (no display, EU868) and an L76K GNSS module
- PN532 NFC module ("NFC V3", I2C mode)
- 20x4 I2C LCD with PCF8574 backpack
- 2x IP67 anti-vandal pushbuttons with 5 V LED
- Active 5 V buzzer
- IP65 key switch
- 2x18650 holder and matched cells
- IP67 USB-C panel extension
- u.FL-to-SMA bulkhead pigtail and an 868 MHz antenna
- SH1.25-to-XH battery pigtail (for the Heltec battery input)
- JST-XH housings and crimps
- M3 standoffs
- Kradex ZP240.190.105SJp enclosure and ZP240.190-PCB mounting plate

Other files in `fab/`: `schematic.pdf`, `top.png`/`bottom.png` (3D renders), `gerbers/` (the unzipped Gerbers plus drill maps and a Gerber job file, which are not in the zip).
