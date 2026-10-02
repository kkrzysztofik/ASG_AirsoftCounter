# TME hand-build variants: carrier, pack A, LiPo (design)

Date: 2026-10-02. Status: built (T0-T6); the three boards pass `make boards`. Layout deviations are
recorded at the end of "Changes against this design".

## Goal

A second version of the carrier, pack A (MCU) and LiPo boards that can be built **by hand with
an iron only** from parts **TME (tme.eu) stocks**. JLCPCB makes bare PCBs; nothing is machine-placed.
The JLC-assembled originals (`design.py`, `pack.py`, `pack_b.py`, `lipo.py`) and their fab files stay
as they are. Pack B gets no TME version (not requested).

## Why the parts change

`hardware/tme.py` (commit cf7939c) maps the JLC BOMs to TME. Not at TME: STM32C071KBT6 (pack A,
LiPo), MT3608 (pack A), NS4168 (carrier), TS-1088 (pack A). Not iron-solderable: BQ25601 (QFN-24)
and PAC1934 (UQFN-16), both with exposed pads.

## Structure

- New board modules `carrier_tme.py`, `pack_tme.py`, `lipo_tme.py`. Each imports its original and edits
  PARTS/NETS/placement, the same way `pack_b.py` derives from `pack.py`. `board.py` and the Makefile learn
  `BOARD=carrier_tme|pack_tme|lipo_tme`; outputs go to `hardware/fab/<board>/`.
- Each module carries a `TME` table `(value, footprint) -> TME symbol` instead of `LCSC`, and `assembled()`
  returns no parts. `board.check_structure` requires every non-mechanical part to have a TME symbol when
  the module has a `TME` table (and keeps the LCSC rule for the JLC boards).
- `make fab` for a TME board writes the Gerber zip, `tme_bom.csv` (TME Quick Buy `symbol;qty`, straight
  from the module's TME table), the schematic PDF, renders and the 1:1 print. No JLC BOM/CPL.

## Part changes

Approved chip set (all found in the TME catalogue on 2026-10-02):

| Block | JLC version | TME hand-build version |
|---|---|---|
| MCU, pack A + LiPo | STM32C071KBT6 (LQFP-32) | **STM32L072KZT6** (LQFP-32): crystal-less USB on PA11/PA12, I2C1 (PB6/PB7, internal master) + I2C3 (PA8/PB4, carrier link slave), ADC on PA0-PA7/PB0/PB1, Stop ~0.4 uA (C071: ~85 uA) |
| Cell monitor, pack A | PAC1934 (UQFN-16) | **4x INA228AIDGSR** (VSSOP-10): 20-bit, on-chip energy + charge accumulators, addresses 0x40-0x43 by A0/A1, ALERTs open-drain wired together to one MCU EXTI |
| Charger, pack A | BQ25601RTWR | **BQ25601RTWT** (same die, TME), on an iron footprint: pads extended ~0.6 mm beyond the body for drag soldering, 1.5 mm plated hole under the exposed pad soldered from the back. Keeps power path, I2C 0x6B, defaults, TS. |
| USB-C, pack A | HCTL HC-TYPE-C-16P-01A (SMD) | **GCT USB4085-GF-A** (through-hole, USB 2.0) |
| Boost, pack A | MT3608 | **MCP1640T-I/CHY** (SOT-23-6, true output disconnect); FB divider for 1.21 V reference |
| BOOT/RESET buttons, pack A | TS-1088 (SMD 3.9x3) | THT 6x6 mm tact switches |
| Charger NTC TH_CHG, pack A | CMFB 0805 (hand) | **Vishay NTCS0603E3103FLT** (10k B3435 1 %, 0603 on 0805 pads) |
| Audio, carrier | NS4168 (eSOP-8, I2S class-D) | **PCM5100APWR** (TSSOP-20 I2S DAC on +3V3, PLL from BCK, no MCLK) + **PAM8302AADCR** (SO-8 class-D on VBAT_SW), DAC L/R driven in antiphase into the amp's differential input, 240 k input resistors set the gain; expander AMP_SD drives the amp SD and the DAC XSMT. Firmware stays I2S. |
| LDO, LiPo | HT7533-1 (SOT-89, 30 V) | **AP7381-33SA-7** (SOT-23, 40 V, pin order 1 VI / 2 VO / 3 GND) |

Everything else maps 1:1 through the `tme.py` table (the substitutes there: Kingbright LEDs,
1N5819HW-7-F, ERJ8BWFR010V shunts, DFE322520FD-1R5M inductor, ZL262-18SG sockets, 1206L200PR PTC).
All packages are leaded or chip passives; the BQ25601 is the one exposed-pad QFN and gets the iron
footprint.

Rejected: LTC4002 leaded charger (no power path, no I2C control), Charger 6 Click module MIKROE-4576
(same BQ25601 but 62 PLN, out of stock, bulky), STM32G0B1KBT6 (higher Stop current), STM32C031K6T6
(no I2C2/USB), INA219 (12-bit, no accumulator), PDM-to-RC audio (firmware change, weaker), MCP1703AT
(18 V abs max under the 24 V TVS clamp).

## Changes against this design (from the implementation plan)

- LiPo LDO is the SOT-23 **AP7381-33SA-7**, not the SOT-89 AP7381-33Y-13: KiCad has a symbol only for
  the SOT-23 one, TME stocks it, and the LDO carries only the MCU (mA). Pinout 1 VI, 2 VO, 3 GND.
- Amp is **PAM8302AADCR** (SO-8), not AASCR: AAD is the 1.27 mm SOP-8, AAS the 0.65 mm MSOP-8.
- The carrier link uses **I2C1 (PB6/PB7)** on both boards; the pack's internal bus uses **I2C3
  (PA8/PB4)**. I2C1 is the port the ROM bootloader listens on, so the Heltec could flash a pack or
  LiPo MCU over the cable later.
- **PCM5100A XSMT sits on AMP_SD**: the expander line that enables the amp also unmutes the DAC.
- **MCP1640 needs no catch diode** (synchronous): `D1` goes. FB divider 75k/24k -> 1.21 V x 4.125 = 4.99 V.
- Amp input resistors **R_INP = R_INN = 240 k** (see Parts below for the arithmetic).

## Layout deviations (from the T5.2 build)

- **One INA228 per cell block** (schematic), beside that cell's 10R Kelvin split, instead of four in
  the PAC1934's monitor block: four long sense routes disappear and the four monitors stop crowding
  one block. The monitor block keeps only the diode-OR and the 3V3 LDO.
- **`+5V` drops out of the 0.8 mm Power net class** (0.25 mm Default): the MCP1640's VOUT is a
  0.95 mm-pitch SOT-23 pad that cannot take a 0.8 mm track, and the rail's peak is 82 mA. `VBAT_SW`
  stays 0.8 mm.
- **Default clearance 0.15 mm** (was 0.2) on pack_tme: the USB4085's own through-hole pads sit
  0.15 mm apart. JLCPCB's 2-layer minimum is 0.127 mm.
- **The hand-solder QFN's pin-1 silk marker moves to F.Fab**: the extended pads cover it, so the
  marker is printed (F.Fab is in the 1:1 print) instead of clipped by solder mask.
- **Pack placement**: `U_CHG` moves to the holder-free right strip (its exposed pad is filled from
  the back), `J_USB1` pulls in to x 87 so its silk clears the board edge, the THT tact switches sit
  in the left holder-free strip (x 1.6, rotated) and `J_PWR1`/`J_KEY1` shift down to make room.

## Parts (verified 2026-10-02)

Datasheets read on 2026-10-02; TME symbols checked against tme.eu product pages the same day. Stock is
not reserved: it is checked at order time.

- **STM32L072KZT6** (DS10690 Rev3 `stm32l072kz.pdf`, AN2606, RM0367). LQFP-32 7x7 mm; the pin table
  matches the KiCad symbol `MCU_ST_STM32L0:STM32L072KZTx`: 1 VDD, 4 NRST, 5 VDDA, 16/32 VSS, 17 VDD,
  21 PA11/USB_DM, 22 PA12/USB_DP, 18 PA8/I2C3_SCL, 27 PB4/I2C3_SDA, 29 PB6/I2C1_SCL, 30 PB7/I2C1_SDA,
  31 BOOT0 (dedicated pin). USB is crystal-less: HSI48 trimmed by the CRS from the USB SOF signal
  (S3.17.5, S3.18), so no crystal on PA11/PA12. Stop mode IDD 0.43 uA typ / 1.00 uA max at -40..25 C
  (Table 37); the features list gives 0.86 uA typ for Stop + RTC + 20 KB RAM retention. NRST has an
  internal filter and takes a 100 nF external cap (Figure 29). Decoupling: 100 nF per VDD pin plus
  100 nF + 1 uF on VDDA/VREF+ and a bulk cap (Figures 32/33). BOOT0 (pin 31) pull-down 10k keeps the
  main-flash boot. Bootloader: AN2606's STM32L0 table (and ST community reports for L071) give I2C1 on
  PB6/PB7 and USB DFU on PA11/PA12 for LQFP-32; the I2C slave address is set by the master, no hardware
  change (the AN3154/AN4221 protocol is firmware-side, out of scope).
- **INA228AIDGSR** (SBOSA20 `ina228.pdf`). VSSOP-10, 20-bit, on-chip energy and charge accumulators,
  open-drain active-low ALERT, I2C. Address pins A1/A0 (Table 7-2): GND/GND 0x40, GND/VS 0x41,
  GND/SDA 0x42, GND/SCL 0x43 -> cells 1-4 = A1 GND, A0 = GND / +3V3 / SDA_INT / SCL_INT. Shunt full
  scale ADCRANGE=0 is +-163.84 mV = 312.5 nV/LSB, so the 10 mOhm shunt spans +-16 A. Input filtering:
  series R should stay <= 100 Ohm; the datasheet says 10 Ohm in series already protects the inputs up
  to the 40 V differential limit (S8.1.4), so the 10 R split is kept. Shutdown quiescent current 2.8 uA
  typ / 5 uA max; VBUS pin impedance 1 MOhm active, 10 nA leakage in shutdown.
- **PCM5100APWR** (SLAS859C `pcm5100a.pdf`). TSSOP-20, 3.0-3.6 V only on AVDD/CPVDD/DVDD, 2.1 Vrms
  ground-centered line output. Tying SCK to AGND selects the internal PLL clocked from BCK (S9.1,
  Figure 33), i.e. 3-wire I2S, no MCLK. Straps: FMT low = I2S, FLT low = normal latency, DEMP low =
  de-emphasis off; XSMT low = soft mute, high = unmute (tie to AVDD if unused; here AMP_SD). Caps from
  Figure 33: CAPP-CAPM flying cap 2.2 uF, VNEG 2.2 uF, LDOO 0.1 uF, each supply 0.1 uF + 10 uF. Output
  filter 470 R + 2.2 nF to GND (the output load spec assumes 10 kOhm). Standby current with clocks
  stopped: DVDD 3.3 V 0.5 mA typ / 0.8 mA max; the part auto power-downs after BCK/LRCK are low > 1 s
  (S11.5.2).
- **PAM8302AADCR** (DS36130 `pam8302a.pdf`). AAD = SO-8 (1.27 mm), AAS = MSOP-8 (0.65 mm); we use the
  SO-8. Differential gain A = 20 log(150k / (10k + R_IN)): internal R_F = 150 k, R_I = 10 k, so the bare
  part is 23.5 dB and an external R_IN in series at the input pin lowers it. Sizing: the DAC full-scale
  differential signal is 2 x 2.1 Vrms = 4.2 Vrms; the BTL output at VDD 3.6 V can swing about 7.2 Vpp =
  2.55 Vrms, so the gain must be <= 2.55 / 4.2 = 0.607. R_IN >= 150k / 0.607 - 10k = 237 k ->
  **R_INP = R_INN = 240 k** (gain 0.60, 2.52 Vrms out, just under clipping). C_INP/C_INN = 1 uF gives a
  high-pass corner of 1 / (2 pi 250k 1u) = 0.64 Hz. SD: logic low shuts the amp down; V_IH >= 1.2 V,
  V_IL <= 0.4 V, so the 3.3 V expander line drives it directly through the existing 1 k. ISHDN <= 1 uA,
  quiescent 4 mA typ / 8 mA max no-load. VDD 2.0-5.5 V (VBAT_SW about 4.1 V).
- **MCP1640T-I/CHY** (DS20002234 `mcp1640.pdf`). SOT-23-6, V_FB = 1.21 V (1.175/1.21/1.245). Maximum
  output current 350 mA at VIN 3.3 V / VOUT 5.0 V, so the 82 mA +5V peak from `power_budget.py` has more
  than 4x margin. Recommended L = 4.7 uH, C_IN = C_OUT = 10 uF. EN is high above 90 % of VIN, so EN is
  tied to VBAT_SW. The base MCP1640 (no B/C/D suffix) has true output disconnect, so no catch diode.
  L1 becomes a 4.7 uH/2 A part on the existing LRN6045 (6x6 mm) footprint: L peak is well under 1 A, and
  the TME-confirmed SRN6045-4R7Y has Isat 4 A. FB divider 75k/24k -> 1.21 x (1 + 75/24) = 4.99 V.
- **AP7381-33SA-7** (DS39917 `ap7381.pdf`). SOT-23 pin descriptions: 1 VIN, 2 VOUT, 3 GND; this matches
  KiCad's `Regulator_Linear:AP7381-33SA-7` (extends AP7381-28SA-7: 1 VI, 2 VO, 3 GND). VIN 3.3-40 V
  (abs max 45 V); the LiPo VIN is 6.0-12.6 V. Dropout 1000 mV at 100 mA / 3.3 V, so VIN >= 4.3 V at
  100 mA and the 6.0 V floor leaves 1.7 V. Ground current 2.5 uA at 0 A / 25 uA at 100 mA, and the load
  is the MCU only (mA). C_IN 1 uF / C_OUT 2.2 uF typical, low-ESR ceramic compatible, so the 10 uF in
  and out is inside the stable range.
- **BQ25601 RTW land pattern** (SLUSD90 `bq25601.pdf`). WQFN-24 (RTW) 4 x 4 mm x 0.75 mm, 0.5 mm pitch,
  exposed pad 2.6 x 2.6 mm (generic package view 4224801). KiCad's
  `Package_DFN_QFN:QFN-24-1EP_4x4mm_P0.5mm_EP2.6x2.6mm` encodes the land pattern: numbered pads
  0.25 mm wide x 0.825 mm long on 0.5 mm pitch, E pad 2.6 x 2.6 mm. T2.1 extends each numbered pad
  0.6 mm outward and drills a 1.5 mm plated hole through the E pad.

### TME symbols (new parts and values, checked 2026-10-02)

| part / value | TME symbol |
|---|---|
| STM32L072KZT6 | `STM32L072KZT6` |
| INA228AIDGSR | `INA228AIDGSR` |
| PCM5100APWR | `PCM5100APWR` |
| PAM8302AADCR | `PAM8302AADCR` |
| MCP1640T-I/CHY | `MCP1640T-I/CHY` |
| AP7381-33SA-7 | `AP7381-33SA-7` |
| USB4085-GF-A | `USB4085-GF-A` |
| TACT 6x6 (Omron B3F-1000, 4.5x6.5 mm pitch) | `B3F-1000` |
| 24k 0805 | `0805W8F2402T5E` |
| 240k 0805 | `SMD0805-240K-1%` |
| 470R 0805 | `0805W8F4700T5E` |
| 2.2 nF 0805 | `CC0805KRX7R9BB222` |
| 2.2 uF 0805 | `CL21A225KAFNNNE` |
| 1 uF 0805 | `CL21B105KBFNNNE` |
| 10k NTC 0603 | `NTCS0603E3103FLT` |
| 4.7 uH 6x6 | `SRN60454R7Y-BOU-0` |

Every other part maps 1:1 through the `tme.py` table (Kingbright LEDs, 1N5819HW-7-F, ERJ8BWFR010V
shunts, DFE322520FD-1R5M inductor, ZL262-18SG sockets, 1206L200PR PTC).

## Verification

- `make BOARD=<board>_tme all` per board: design check, netlist parity, ERC, DRC (schematic parity),
  Gerber check, TME BOM written.
- Each module's self-check (`/usr/bin/python3 <board>_tme.py`), including pin-role checks like the
  originals (USB on PA11/PA12, I2C ports, ADC pins, INA228 addresses distinct).
- `power_budget.py`: L072 Stop current, 4x INA228, PCM5100A standby; the weekend target must still pass.
- Before ordering: 1:1 print fit check of the THT USB-C, tact switches and the BQ25601 footprint.

## Firmware impact (deferred, noted for the C-tasks)

Pack and LiPo firmware target STM32L072 instead of STM32C071 (embassy-stm32 supports both); the pack
reads four INA228s on I2C3 instead of one PAC1934; the carrier/pack link moves to I2C1 (PB6/PB7) on both
boards. Carrier audio stays I2S; the amp enable stays on the expander. The DAC L/R are driven in
antiphase (the firmware sends the right channel inverted, R = -L) so the amp sees a differential signal;
XSMT is on the same AMP_SD line, so enabling the amp also unmutes the DAC.
