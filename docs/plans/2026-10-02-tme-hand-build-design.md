# TME hand-build variants: carrier, pack A, LiPo (design)

Date: 2026-10-02. Status: approved, not started.

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
| Audio, carrier | NS4168 (eSOP-8, I2S class-D) | **PCM5100APWR** (TSSOP-20 I2S DAC on +3V3, PLL from BCK, no MCLK) + **PAM8302AASCR** (SOP-8 class-D on VBAT_SW), DAC L/R driven in antiphase into the amp's differential input, input resistors set the gain; expander AMP_SD drives the amp SD. Firmware stays I2S. |
| LDO, LiPo | HT7533-1 (SOT-89, 30 V) | **AP7381-33Y-13** (SOT-89, 40 V, VOUT/GND/VIN pin order) |

Everything else maps 1:1 through the `tme.py` table (the substitutes there: Kingbright LEDs,
1N5819HW-7-F, ERJ8BWFR010V shunts, DFE322520FD-1R5M inductor, ZL262-18SG sockets, 1206L200PR PTC).
All packages are leaded or chip passives; the BQ25601 is the one exposed-pad QFN and gets the iron
footprint.

Rejected: LTC4002 leaded charger (no power path, no I2C control), Charger 6 Click module MIKROE-4576
(same BQ25601 but 62 PLN, out of stock, bulky), STM32G0B1KBT6 (higher Stop current), STM32C031K6T6
(no I2C2/USB), INA219 (12-bit, no accumulator), PDM-to-RC audio (firmware change, weaker), MCP1703AT
(18 V abs max under the 24 V TVS clamp).

## Facts to confirm before layout (P0)

- STM32L072: system bootloader interfaces (AN2606: USB DFU, I2C1 address), Stop current with RTC and
  the I2C3 wake-up, LQFP-32 pin table against the KiCad symbol `MCU_ST_STM32L0:STM32L072KZTx`.
- INA228: A0/A1 address table, ALERT open-drain, shunt range with 10 mOhm, shutdown current.
- PCM5100A: pin straps (FMT, FLT, DEMP, XSMT), charge-pump caps, 3.3 V-only supply, standby current
  with clocks stopped.
- PAM8302A: input impedance and gain formula (to size the input resistors against the DAC's 2.1 Vrms),
  SD threshold at 3.3 V logic from the expander.
- MCP1640: output current at 3.0 V in / 5.0 V out (needs >= 82 mA peak +5V load, the reason TPS61040
  was rejected), inductor value.
- AP7381: dropout at the LiPo's lowest input, output capacitor stability range.
- BQ25601 iron footprint: TI land pattern for RTW and the extension; hole size against the 2.6 mm EP.
- Every new TME symbol: present in the catalogue (stock is checked at order time).

## Verification

- `make BOARD=<board>_tme all` per board: design check, netlist parity, ERC, DRC (schematic parity),
  Gerber check, TME BOM written.
- Each module's self-check (`/usr/bin/python3 <board>_tme.py`), including pin-role checks like the
  originals (USB on PA11/PA12, I2C ports, ADC pins, INA228 addresses distinct).
- `power_budget.py`: L072 Stop current, 4x INA228, PCM5100A standby; the weekend target must still pass.
- Before ordering: 1:1 print fit check of the THT USB-C, tact switches and the BQ25601 footprint.

## Firmware impact (deferred, noted for the C-tasks)

Pack and LiPo firmware target STM32L072 instead of STM32C071 (embassy-stm32 supports both); the pack
reads four INA228s instead of one PAC1934. Carrier audio stays I2S; the amp enable stays on the expander.
