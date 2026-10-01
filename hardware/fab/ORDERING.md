# Ordering the PCBs from JLCPCB (bare board or assembled)

**Two boards.** The carrier is `fab/carrier_gerbers_jlcpcb.zip` (90 x 60 mm, sections 1-6 below).
The 4x18650 pack board is `fab/pack/pack_gerbers_jlcpcb.zip` (96 x 90 mm, section 7). They are two
separate orders; the Economic setup fee is per order per Extended part type, so the totals below are
per board.

Regenerate everything with `cd hardware && make boards` (both boards; it exits non-zero if ERC, DRC
or the gerber check fails, for either board).

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
| Min track / clearance | 0.25 mm signal / 0.8 mm power tracks (0.15 mm rule, for necks into the fine-pitch U1/U2/U3 pads); 0.2 mm clearance |
| Vias | 0.6 mm pad / 0.3 mm drill, tented (56 vias, 8 of them GND), plus 4 thermal vias of the same size in U3's exposed pad |
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
4. Check the parts matching. There are 14 BOM lines, and each should match the LCSC number in its row with stock for your quantity. Nothing should be left unmatched or skipped.
5. Open the 3D placement preview and do the checks below before you confirm.

**Through-hole parts are included**: J2/J3 (1x18 sockets) and the 9 JST-XH headers. JLC solders them by wave soldering and charges per THT joint on top of the SMD assembly. The price shows on the form. The old THT electrolytics (220 µF C_BULK1, 100 µF C_NFC1) are gone: the bulk capacitors are now 1206 ceramics (2x 47 µF on VBAT_SW, 100 µF on 3V3).

**Setup fees.** Economic PCBA charges a setup (feeder loading) fee, about $3 per order, for each **SMD Extended** part type. Basic and Preferred Extended parts don't have it, and through-hole parts don't either (JLC lists them as Extended, but they are wave-soldered). This board has:

- **2 SMD Extended types (fee):** U2 (TCA9534PWR, C783615) and U3 (NS4168, C910588). About $6 per order. (U4, U1, L1 and F1 moved to the pack board in P5; see section 7.)
- **3 through-hole Extended types (no loading fee, per-joint THT charge instead):** J2/J3 socket (C2905422), the JST-XH 4-pin used for the off-board connectors (C144395) and J_PWR1 (JST-XH 6-pin, C144397).
- None of the two SMD Extended types has a Basic or Preferred replacement (JLC parts API, 2026-09-30: I2C expanders and I2S/class-D amps were searched). The only ways to cut the
  fee are the Budget variant (no U3) or hand-soldering some of them yourself.
- Cheaper alternatives for U2 and U3 that were considered are in `PART_ALTERNATIVES.md`; other review findings are in `PARTS_REVIEW.md`.
- **2 Preferred Extended types (no fee):** BSS138 (Q_SDA1/Q_SCL1 and the three low-side drivers, C7420339) and the 75k resistor (R_FB1, C17819).
- **8 Basic types:** everything else, including the ceramic bulk capacitors C_BULK1/C_BULK2 (47 µF 10 V, C96123) and C_NFC1 (100 µF 6.3 V, C15008), and the 0 Ω LED jumpers R_LLR1/R_LLB1 (C17477).

**Placement preview checks.** The CPL uses KiCad's rotations with no JLC corrections. Sources disagree on the SOT-23 offset (180° or −90°), and JLC's engineers correct rotation using the silkscreen polarity marks. Mid X/Y is the centre of each part's courtyard, so the through-hole parts sit on their holes. In the preview, check:

| Part | What to check |
|---|---|
| U1 (SOT-23-6) | The pin-1 dot sits at the silkscreen pin-1 mark. |
| U2 (TCA9534, TSSOP-16) | The pin-1 dot sits at the silkscreen pin-1 mark (top left, on the R_SD1 side). |
| U3 (NS4168, eSOP-8) | The pin-1 dot sits at the silkscreen pin-1 mark (U3 is rotated 90°: pin 1 is at the lower left, towards J_BTN_B1). The exposed pad is centred on the square pad with its vias. |
| Q_SDA1, Q_SCL1, Q_LR1, Q_LB1, Q_BZ1 (SOT-23) | The single pin (drain, pin 3) is on the single-pad side. These are the parts most likely to be off by 90° or 180°. |
| D1 (SMA), D_FLY1 (SOD-123) | The cathode band is on the silkscreen band side. |
| U4 (XB8089D, SOIC-8-EP) | gone: the protector is on the pack board now (section 7). |
| J2, J3 | Pin 1 is on the square pad at the USB end, and the socket covers all 18 holes. |
| J_PWR1 (6-pin XH) | The latch/key side faces the board edge, and pin 1 is at the left (see the silkscreen "PACK" label: GND GND BAT 5V SDA SCL). |
| JST-XH headers | The latch/key side faces the same way as the silkscreen outline. |

If a part is wrong, fix its `Rotation` in `fab/jlc_cpl.csv` (degrees, counter-clockwise positive) and upload the file again. You can also leave it and note it in the order, because JLC's engineers follow the silkscreen polarity marks. Don't edit the CSVs by hand as a long-term fix: `make all` rewrites them.

**Stock.** The J2/J3 socket (about 2.8k in stock) and L1 (about 3.2k), as of 2026-09-29, are the parts most likely to run out. Verified backups: socket C2897381, JST-XH 4-pin clone C37815, BSS138 C82045. (The old PTC backup C5358568 is a 1 A part and no longer fits F1.) To switch, change the number in `LCSC` in `design.py` and run `make all`. Check the new part's package and pinout on its LCSC page first.

**Budget variant.** The same board, assembled without the speaker and NFC modules (see `design.py` `VARIANTS`
and `COSTS.md`). Order the same Gerber zip, then upload **`fab/jlc_bom_budget.csv`** and
**`fab/jlc_cpl_budget.csv`** instead. Differences from the steps above:

- 13 BOM lines and 36 placements (Deluxe: 14 and 43). Nothing else in the form changes.
- **1 SMD Extended type**, not 2: U3 (NS4168, C910588) is not fitted, so its setup fee is gone. The Preferred (1) and Basic (8) counts are unchanged.
- Not fitted: U3, C_AMP1, C_AMP2, R_SD1, J_SPK1 and J_NFC1. In the placement preview, check that none of them appear.
- Buy the speaker and the PN532 only if you add those modules later; the footprints stay empty on the board.

## 6. Parts

A bare board ships without parts. `fab/bom.csv` lists the on-board parts to buy separately, grouped by value and footprint. The DNP pull-ups R_SDA5/R_SCL5 are left out on purpose.
Off-board parts (details in `docs/plans/2026-09-28-esp32-lora-carrier-design.md`, Parts 1–3 and 5):

- Heltec WiFi LoRa 32 V4 (no display, EU868) and an L76K GNSS module
- PN532 NFC module ("NFC V3", I2C mode)
- 20x4 I2C LCD with PCF8574 backpack
- 2x ONPOW LAS1-AGQ-11E/x/6V IP67 pushbuttons (6 V ring LED with a built-in resistor, so R_LLR1/R_LLB1 are 0 Ω jumpers; fit a resistor there to dim an LED)
- Active 5 V buzzer
- Weatherproof **8 Ω, 2 W speaker** on J_SPK (see below)
- IP65 key switch (its lead goes to the pack board's J_KEY1)
- 4x MYOUNG BH-18650-A6AJ012 holders and 4x MF52 10k B3435 bead NTCs (hand-soldered on the pack board's
  bottom side) and 4 matched INR18650-35E cells
- JST-XH 6-pin cable, straight 1:1, carrier J_PWR1 <-> pack J_PWR1 (pin 1 to pin 1)
- IP67 USB-C panel extension
- u.FL-to-SMA bulkhead pigtail and an 868 MHz antenna
- SH1.25-to-XH battery pigtail (for the Heltec battery input)
- JST-XH housings and crimps
- M3 standoffs
- Kradex ZP240.190.105SJp enclosure and ZP240.190-PCB mounting plate

**Speaker.** U3 (NS4168) drives J_SPK as a bridge-tied load (BTL): both pins switch, and neither is ground. Connect the speaker's two leads straight to J_SPK (pin 1 OUT-, pin 2 OUT+, as on the silkscreen) and **never connect either lead to GND, the enclosure or a shared return wire**: that shorts an output stage. Use an **8 Ω, 2 W** speaker (Visaton K 50; roughly 0.6 W into 8 Ω from a 1S cell, estimated from the datasheet's 1.2 W into 4 Ω at 3.6 V), plus an ePTFE acoustic vent in the enclosure wall if needed.

Other files in `fab/`: `schematic.pdf`, `top.png`/`bottom.png` (3D renders), `gerbers/` (created by `make all` and not committed: the unzipped Gerbers plus drill maps and a Gerber job file, which are not in the zip).

## 7. The pack board (4 x 18650)

`fab/pack/pack_gerbers_jlcpcb.zip`, 96 x 90 mm, 2 layers, 1.6 mm, rounded corners, top-side
assembly only (the cell holders go on the bottom, by hand). Upload it as its own order and fill in the form as in section 2 (JLC auto-detects the
size and layer count; if it shows something else, stop). Schematic `fab/pack/schematic.pdf`, renders
`fab/pack/top.png` / `bottom.png`.

**Assembly.** Same Economic PCBA flow. BOM `fab/pack/jlc_bom.csv` (37 lines), CPL
`fab/pack/jlc_cpl.csv` (104 placements, all top side). The DNP 0R bring-up bypasses R_BYP1-R_BYP4 are
left off on purpose. **By hand, after the board arrives:**
1. **Bead NTCs TH1-TH4** (MF52A103F3435, LCSC C84036) on the **bottom** side, bead in the middle of each
   holder outline (it sits in the holder's floor window and touches the cell), leads soldered on top.
   Fit them before the holders.
2. **Holders BT1-BT4** (MYOUNG BH-18650-A6AJ012, LCSC C19184084) on the **bottom** side: the snap pegs
   locate them, the two tabs are soldered on top. The bottom silkscreen `+` marks the positive end; all
   four face the same way.
The holders and NTCs are not in the BOM/CPL (JLC's Economic PCBA is top side only).

**Setup fees (SMD Extended types, about $3 each).** 11 types, about $33 per order:
BQ25601RTWR (C468236), STM32C071KBTx (C42116633), PAC1934T-I/JQ (C623960),
MT3608 (C84817), the 1.5 uH charger inductor (C703084), the 10 uH boost inductor (C2046332),
the USB-C receptacle (C2894897), the 10 mOhm shunt (C105362), the 10k NTC (C2889056),
the 5 A fuse (C48332) and the 2 A PTC (C22374899). None has a Basic replacement at JLC (parts API,
2026-10-02). The 2026-10-02 simplification removed the XB8089D, BAT54C and the 5.23k/30.9k TS pair
and replaced the two INA3221s with one PAC1934
(design doc, "Simplification delta"). To cut the per-board chip cost, assemble 2 of the 5 boards. **2 through-hole Extended types** (no loading fee, per-joint charge):
J_KEY1 (XH 4-pin, C144395) and J_PWR1 (XH 6-pin, C144397). **Preferred (no fee):** 75k (C17819) and
BSS138 (C7420339). Everything else is Basic.

**Placement preview checks** (the CPL carries KiCad rotations, no JLC corrections):

| Part | What to check |
|---|---|
| U_CHG (BQ25601, QFN-24) | The pin-1 dot sits at the silkscreen pin-1 mark. |
| U_MCU (STM32C071, LQFP-32) | The pin-1 dot sits at the silkscreen pin-1 mark. |
| U_MON (PAC1934, UQFN-16) | The pin-1 dot sits at the silkscreen pin-1 mark; the exposed pad is centred. |
| Q_A*/Q_B*/Q_N* (SOT-23) | The single pin (drain, pin 3) is on the single-pad side. Most likely to be off by 90/180 deg. |
| D_CB*, D_OR*, D1 (SMA / SOD-123) | The cathode band is on the silkscreen band side. |
| J_USB1 (USB-C) | The opening faces the right board edge (the "USB" silk); the shield pads straddle their holes. |
| BT1-BT4, TH1-TH4 (bottom side) | Not in the CPL: hand-soldered (see Assembly above). |
| LED_STAT, LED_MCU | The cathode (bar) is on the silkscreen band side. |

**Board facts.** 96 x 90 mm, 1 oz; 142 vias of 0.6/0.3 mm (tented); signal tracks 0.25 mm, power
0.8 mm (0.15 mm rule for necks into the fine-pitch QFN/LQFP/UQFN pads); NPTH: 4 x 3.2 mm M3
mounting, 12 holder snap pegs (3.3/2.4 mm) and 2 USB-C shell pins (0.65 mm); PTH: 8 plated holder-tab
slots 1.3 x 2.6 mm, 0.95/1.0 mm (J_KEY1/J_PWR1), 0.8 mm (bead NTCs) and 0.6 mm (the USB-C shell).
GND pours on both layers.

**Note.** The M3 hole pattern is provisional (the ZP240.190 plate is unmeasured). With the cells under
the board, standoffs need about 20 mm plus clearance (holder 14.9 mm, the cell top sits higher). Before paying
for boards, put a real BH-18650-A6AJ012 on the 1:1 print (`fab/pack/print_1to1.pdf`): check the tab
slots and pegs, and that the floor window leaves room for the bead NTC (design doc, Unverified).
