# Ordering the carrier PCB from JLCPCB (bare board or assembled)

Regenerate everything with `cd hardware && make all` (it exits non-zero if ERC, DRC or the gerber check fails).

## 1. Upload

Go to https://jlcpcb.com/, click "Order now" and upload **`fab/carrier_gerbers_jlcpcb.zip`** (9 Gerber layers + PTH/NPTH Excellon drill files).
JLC should detect **90 x 60 mm, 2 layers** on its own. If it shows a different size or layer count, stop and don't order.
Check the Gerber viewer: the outline has rounded corners, there are 4 mounting holes 3.5 mm in from each edge, and both sides have a GND pour.

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
| Min via hole size/diameter | 0.3mm/(0.4/0.45mm), the default | The design uses 0.3 mm drill vias with a 0.6 mm pad. |
| Board outline tolerance | ±0.2 mm (Regular) | |
| Mark on PCB | Default (order number) | JLC prints its order number somewhere on the silkscreen. Placing it at a chosen spot needs a marker text on the board, which this design doesn't have. Removing it is a paid option. It is harmless for this board. |
| Electrical test | Flying Probe Fully Test | Free for small boards. |
| Gold fingers | No | |
| Castellated holes | No | |
| Edge plating | No | |
| Impedance control | No | |
| Confirm production file | Optional | "Yes" means you approve JLC's processed files before production. It is slower, but a useful extra check on a first order. |
| PCB assembly / stencil | Off for a bare board | For an assembled board, see section 5. |

Leave the other fields at their defaults. Price and lead time follow from these choices. Compare the options on the form itself.

## 3. Board facts (for capability questions)

| Item | Value |
|---|---|
| Size / layers | 90 x 60 mm, 2 copper layers, rounded corners |
| Material / thickness | FR-4, 1.6 mm, 1 oz outer copper |
| Min track / clearance | 0.25 mm signal / 0.8 mm power tracks, necked to 0.19 mm at the fine-pitch U1/U2/U3 pads (0.15 mm rule); 0.2 mm clearance |
| Vias | 0.6 mm pad / 0.3 mm drill, tented (43 vias), plus 4 thermal vias of the same size in U3's exposed pad |
| Plated component holes | 0.95 / 1.0 mm (the U3 thermal vias are 0.3 mm, like the vias) |
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
3. Orientation: the Heltec's USB-C end goes at the **"USB"** label (the left end of the header rows, where pin 1 is the **square** pad in each row), and the antenna end points at **"ANT →"** and the right board edge. **J3 (GPIO1–7) is the top row**; the rows are labelled J3/J2 at the left and "Heltec_J3"/"Heltec_J2" at the right. A mirrored or reversed module would put GND/3V3 on GPIO pins.

## 5. Assembly (PCBA, optional)

JLC can assemble every on-board part, SMD and through-hole, from `fab/jlc_bom.csv` (parts with LCSC numbers) and `fab/jlc_cpl.csv` (placements). Both are written and checked by `make all` (`jlc.py`). The DNP pull-ups R_SDA5/R_SCL5 and the mounting holes are left out on purpose.

**Service.** Use **Economic** PCBA. It solders through-hole parts by wave soldering and takes 2 to 50 boards (older JLC pages say 30). Standard PCBA needs a board of at least 70 x 70 mm, and at 90 x 60 mm this one only fits as a panel. Sources: https://jlcpcb.com/capabilities/pcb-assembly-capabilities and https://jlcpcb.com/help/article/pcb-assembly-faqs

**Steps**

1. Upload `fab/carrier_gerbers_jlcpcb.zip` and fill in the form as in section 2.
2. Turn on "PCB Assembly". Choose **Economic**, assemble the **Top** side, and set how many boards to assemble (2 or all 5).
3. Upload **`fab/jlc_bom.csv`** as the BOM and **`fab/jlc_cpl.csv`** as the CPL / pick-and-place file.
4. Check the parts matching. There are 23 BOM lines, and each should match the LCSC number in its row with stock for your quantity. Nothing should be left unmatched or skipped.
5. Open the 3D placement preview and do the checks below before you confirm.

**Through-hole parts are included**: J2/J3 (1x18 sockets) and the 9 JST-XH headers. JLC solders them by wave soldering and charges per THT joint on top of the SMD assembly. The price shows on the form. The old THT electrolytics (220 µF C_BULK1, 100 µF C_NFC1) are gone: the bulk capacitors are now 1206 ceramics (2x 47 µF on VBAT_SW, 100 µF on 3V3).

**Setup fees.** Economic PCBA charges a setup (feeder loading) fee for each **Extended** part type. Basic and Preferred Extended parts don't have this fee. This board has:

- **8 Extended types:** U1 (MT3608, C84817), L1 (C2046332), F1 (2 A PTC 1206L200/16NR, C22374899), J2/J3 socket (C2905422), JST-XH 2-pin (C158012), JST-XH 4-pin (C144395), U2 (TCA9534PWR, C783615) and U3 (MAX98357AETE+T, C910544).
- **2 Preferred Extended types (no fee):** BSS138 (Q_SDA1/Q_SCL1, C7420339) and the 75k resistor (R_FB1, C17819).
- **13 Basic types:** everything else, including the ceramic bulk capacitors C_BULK1/C_BULK2 (47 µF 10 V, C96123) and C_NFC1 (100 µF 6.3 V, C15008), and the 0 Ω LED jumpers R_LLR1/R_LLB1 (C17477).

**Placement preview checks.** The CPL uses KiCad's rotations with no JLC corrections. Sources disagree on the SOT-23 offset (180° or −90°), and JLC's engineers correct rotation using the silkscreen polarity marks. Mid X/Y is the centre of each part's courtyard, so the through-hole parts sit on their holes. In the preview, check:

| Part | What to check |
|---|---|
| U1 (SOT-23-6) | The pin-1 dot sits at the silkscreen pin-1 mark. |
| U2 (TCA9534, TSSOP-16) | The pin-1 dot sits at the silkscreen pin-1 mark (top left, on the R_SD1 side). |
| U3 (MAX98357A, TQFN-16 3x3) | The pin-1 dot sits at the silkscreen pin-1 mark (U3 is rotated 180°: pin 1 is at the lower right, towards C_OUT2). The exposed pad is centred on the square pad with its 4 vias. |
| Q_SDA1, Q_SCL1, Q_LR1, Q_LB1, Q_BZ1 (SOT-23) | The single pin (drain, pin 3) is on the single-pad side. These are the parts most likely to be off by 90° or 180°. |
| D1 (SMA), D_FLY1 (SOD-123) | The cathode band is on the silkscreen band side. |
| J2, J3 | Pin 1 is on the square pad at the USB end, and the socket covers all 18 holes. |
| JST-XH headers | The latch/key side faces the same way as the silkscreen outline. |

If a part is wrong, fix its `Rotation` in `fab/jlc_cpl.csv` (degrees, counter-clockwise positive) and upload the file again. You can also leave it and note it in the order, because JLC's engineers follow the silkscreen polarity marks. Don't edit the CSVs by hand as a long-term fix: `make all` rewrites them.

**Stock.** The J2/J3 socket (about 2.8k in stock) and L1 (about 3.2k), as of 2026-09-29, are the parts most likely to run out. Verified backups: socket C2897381, JST-XH clones C20079 (2-pin) and C37815 (4-pin), BSS138 C82045. (The old PTC backup C5358568 is a 1 A part and no longer fits F1.) To switch, change the number in `LCSC` in `design.py` and run `make all`. Check the new part's package and pinout on its LCSC page first.

## 6. Parts

A bare board ships without parts. `fab/bom.csv` lists the on-board parts to buy separately, grouped by value and footprint. The DNP pull-ups R_SDA5/R_SCL5 are left out on purpose.
Off-board parts (details in `docs/plans/2026-09-28-esp32-lora-carrier-design.md`, Parts 1–3 and 5):

- Heltec WiFi LoRa 32 V4 (no display, EU868) and an L76K GNSS module
- PN532 NFC module ("NFC V3", I2C mode)
- 20x4 I2C LCD with PCF8574 backpack
- 2x ONPOW LAS1-AGQ-11E/x/6V IP67 pushbuttons (6 V ring LED with a built-in resistor, so R_LLR1/R_LLB1 are 0 Ω jumpers; fit a resistor there to dim an LED)
- Active 5 V buzzer
- Weatherproof **4 Ω, 2–3 W speaker** on J_SPK (see below)
- IP65 key switch
- 2x18650 holder and matched cells
- IP67 USB-C panel extension
- u.FL-to-SMA bulkhead pigtail and an 868 MHz antenna
- SH1.25-to-XH battery pigtail (for the Heltec battery input)
- JST-XH housings and crimps
- M3 standoffs
- Kradex ZP240.190.105SJp enclosure and ZP240.190-PCB mounting plate

**Speaker.** U3 (MAX98357A) drives J_SPK as a bridge-tied load (BTL): both pins switch, and neither is ground. Connect the speaker's two leads straight to J_SPK (pin 1 OUT-, pin 2 OUT+, as on the silkscreen) and **never connect either lead to GND, the enclosure or a shared return wire**: that shorts an output stage. Use a 4 Ω, 2–3 W speaker (about 1.5–2 W from a 1S cell at 12 dB gain), plus an ePTFE acoustic vent in the enclosure wall if needed.

Other files in `fab/`: `schematic.pdf`, `top.png`/`bottom.png` (3D renders), `gerbers/` (created by `make all` and not committed: the unzipped Gerbers plus drill maps and a Gerber job file, which are not in the zip).
