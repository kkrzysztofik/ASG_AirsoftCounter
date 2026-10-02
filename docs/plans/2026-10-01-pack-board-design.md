# AirsoftCounter pack board: 4x18650 power subsystem

Date: 2026-10-01
Status: hardware done 2026-10-01 (pack.py generated, routed and fabbed; `make boards` green). Pack
firmware is designed here but its implementation is deferred. Lines marked "verified" were checked
against a source; everything else is listed under "Unverified" at the end. The generated board is
96 x 90 mm with the four holders (MYOUNG BH-18650-A6AJ012, THT) on the **bottom** side and every SMD
part on top (2026-10-01 rework; the first layout, 140 x 100 mm with Keystone 1042 holders on top,
placed parts under the holder floor). Re-check the holder against its drawing and the hole pattern
against the ZP240.190 plate before ordering.

This is **variant A** (pack MCU). Variant B, the same pack with no MCU and the Heltec as I2C master,
is `2026-10-02-pack-board-variant-b-design.md` (hardware generated from `hardware/pack_b.py`; not fabbed); both are kept.

## Simplification delta (2026-10-02)

The first quote was about $140 for 5 assembled boards, mostly Extended setup fees (15 types x ~$3) and
per-board chip cost. Changes, regenerated with `make BOARD=pack all` (ERC/DRC/gerbers green):

- **No protector IC.** The four XB8089D (and their 1k/100nF) are gone; holder- goes straight to GND.
  Each job it did is covered elsewhere: short circuit by the per-cell 5 A fuse and the output PTC;
  overcharge by the BQ25601 (CV 4.208 V plus its battery over-voltage cutoff at 104 % of VREG,
  103-105 %, verified 2026-10-02 in the datasheet's BATOVP table); over-discharge by the default-off switches (a dead or reset MCU leaves every cell
  open through `R_PD`) and the firmware UV limit; reversed cell by the crowbar and fuse, as before.
  Remaining gap: firmware that runs but keeps a switch closed below 2.5 V. The firmware must run the
  IWDG and host-test the UV disconnect in `asg-core`.
- **One shared protector was rejected.** With the switches open the pack rail is at 0 V, the protector
  stays off and cuts the cells' negative from GND, so the MCU (powered through the diode-OR) never boots
  to close a switch: a lock-out.
- **Diode-OR:** 3x BAT54C (Extended) -> 5x B5819W SOD-123 (C8598, Basic), one per cell (`D_OR1-4`, in
  each cell's band) and one for SYS (`D_OR5`).
- **TS bias:** 5.23k/30.9k (Extended) -> 5.1k/30k (C27834/C17621, Basic). With the 10k B3435 NTC the
  thresholds move from 0/60 C to 0.5/60.8 C.
- **Sense taps** `R_SNSF*`/`R_SNSS*`: 0R -> 10R (C17415, Basic). Holder- is now solid GND, so a reversed
  cell's crowbar holds `CELL_F` at about -0.5 to -1 V until the fuse clears (ms), below the monitor's
  -0.3 V input limit; 10 Ohm limits the clamp current (PAC1934: +-100 mA per pin).
- **Monitor: 2x INA3221 -> 1x PAC1934T-I/JQ** (C623960, UQFN-16 4x4, Extended, 583 in stock), four
  channels in one chip, `Sensor_Energy:PAC1934x-xJQ`. Cell n on channel n; ADDRSEL to GND = 0x10;
  SLOW/ALERT -> MCU pin 28 (`R_ALERT` pull-up), PWRDN -> MCU pin 29 (`R_PWRDN` pull-up, so it runs
  without firmware). On-chip power accumulators do the coulomb counting. Facts under Datasheet facts.
- **Shunt 20 -> 10 mOhm** (FMF06FTHR010-LH, C105362, 1 W, 1 %): the PAC1934's differential limit is
  500 mV (INA3221: 26 V). Without the protector a hard short drives about 25 A per cell until the fuse
  clears; 10 mOhm keeps that at 0.25 V and gives a +-10 A full scale.
- **Result:** 11 SMD Extended types instead of 15, 104 placements instead of 115, 13 parts fewer per
  board. Assemble 2 of the 5 boards at JLC to cut the per-board chip cost further.
- Not changed: per-cell switching (any 1-4 cell combination), per-cell current/voltage/temperature,
  the MCU, charger, boost and connectors. The INA3221 and XB8089D datasheet notes further down are
  kept for the record; this section overrides them.

## Goal

Move all battery and power management off the carrier (`2026-09-28-esp32-lora-carrier-design.md`)
onto a separate **pack board** that holds four 18650 cells and manages each cell:

- **Runtime:** 4 x 3.35 Ah (Samsung INR18650-35E) = about 13.4 Ah, about double the current 2 cells.
  With `power_budget.py` (2026-10-01, still with the 100 mA backlight estimate): 33 h deluxe game with
  the backlight on and 60 h with it off at 20 C; 78 days parked with the key left on; 109 uA and so
  about 12 years for the pack's own electronics with the key off (cell self-discharge dominates after
  a season). The ~150 mOhm branch drop is not modelled: below 0.3 V at these currents, inside the
  0.84 usable-capacity derate.
- **Per-cell management:** short/overcurrent, over/under-voltage, temperature and current
  monitoring, and disabling a failing cell, so shorts, imbalance and ageing are caught.
- **Own USB-C charging** (about 2 A), so the Heltec USB-C becomes programming-only.
- **Key-off charging**: charger and pack sit upstream of the key switch.
- **Frees the carrier**, which is full.

## Topology

**1S4P** (all four cells in parallel, 3.0-4.2 V). Chosen because the load is under 1 W, the
runtime goal is capacity not voltage, and parallel cells cannot drift apart in voltage, so no
balancing is needed. Series stacks were rejected: they need a boost-capable charger, multi-cell
protection and balancing, and the 5.1 V boost already works from one cell.

Parallel-specific risks (not imbalance): inrush when joining unequal cells, a failing cell fed
by the healthy ones, and ageing mismatch (shows as slightly less runtime).

## Block diagram

```
USB-C (5.1k CC; D+/D- to the MCU for DFU)
  └─ BQ25601 charger (I2C to pack MCU, TS <- board NTC, ~2 A)
       ├─ BAT ── pack rail (1S4P, per-cell chain below)
       └─ SYS ─┬─ LDO 3.3 V (low Iq) ── STM32C071, PAC1934             [always on]
               └─ J_KEY (off-board) ─ F1 ─ VBAT_SW ─┬─ MT3608 boost ─ +5V ─┐
                                                    └──────────────────────┼─ 6-pin XH to carrier
                                                                           │  GND,GND,VBAT_SW,+5V,SDA,SCL
carrier: VBAT_SW -> J_HBAT1 -> Heltec battery socket;  VBAT_SW -> amp;  +5V -> LCD, LEDs, buzzer
```

## Pack board blocks

1. **USB-C input**, 5 V, 5.1k CC pull-downs (3 A bricks advertise 3 A to them). D+/D- go to the MCU.
2. **Charger: BQ25601RTWR** (C468236, 5877 in stock on 2026-10-01). Switching (little heat beside the
   cells), NVDC power path, I2C, /CE, /INT, TS input. Its power-on defaults (about 2 A, 4.208 V) charge
   correctly with a dead or unflashed MCU; its I2C watchdog restores them if the MCU hangs. A fifth NTC on
   TS gives the charger its own temperature limits without the MCU.
3. **Four cell holders**, MYOUNG BH-18650-A6AJ012 (LCSC C19184084), THT on the bottom side, hand-soldered.
   Polarity on the bottom silkscreen.
4. **Per-cell chain (x4)**, see below.
5. **MCU: STM32C071KBT6** (C42116633, LQFP-32, 600 in stock), see below.
6. **Boost and rails moved from the carrier:** MT3608 with L1, D1, R_FB1/2, C_IN1, C_OUT1/2, the
   2 A PTC F1 at the start of `VBAT_SW`, and the key-switch connector.

### Per-cell chain

```
holder+ ─ fuse ─┬─ shunt 10 mOhm ─┬─ back-to-back P-FET (2x AO3401A) ─ pack rail
                │                 │    gates: 1M to source (4 uA when on), pulled low by an N-FET <- MCU GPIO
                │                 └─ PAC1934 SENSE-; SENSE+ (= VBUS) on the fuse side reads this cell, also when off
                ├─ crowbar Schottky to holder- (a reversed cell blows the fuse)
                └─ B5819W diode-OR -> LDO -> MCU
holder- ─ GND (no protector IC since 2026-10-02)       bead NTC on each cell -> MCU ADC
```

- **Switch on the positive side, shunt on the cell side of it.** The PAC1934 measures bus voltage at SENSE+;
  with the shunt between cell and switch each channel reads its own cell even while it is disconnected,
  which the connect check needs. (The earlier FS8205-in-the-negative-lead idea read only the pack rail.)
- **Switch defaults to OFF.** A dead MCU leaves an open pack, which is also the over-discharge protection.
  Each switch has a **DNP 0 Ohm bypass** footprint for bring-up without firmware.
- **MCU power does not depend on the switches:** the four cell+ nodes and SYS are diode-ORed (5x B5819W) into the
  LDO, so the MCU runs from the highest cell at uA load even with every switch open, and from USB with no cells (DFU).
- **Shunt 10 mOhm:** 0.6 mV (200 LSB at 3 uV, bidirectional mode) for 60 mA per cell, +-10 A full scale
  (one cell carrying all load plus charge). The PAC1934 cancels its offset in the averaged result.
- **Fuse 5 A fast-blow:** above the per-cell working current (about 2 A); with no protector IC it is the
  hardware short-circuit protection. It must clear the crowbar current before the Schottky fails (see the
  fuse ruling under Datasheet facts).
- Series resistance per branch (fuse, shunt, two FETs) is about 130 mOhm, larger than the cell IR
  (about 35 mOhm) and matched between branches, so it helps current sharing.
- AO3401A and B5819W are JLC Basic. FS8205A is no longer used.

### MCU

| Function | Pins / parts |
|---|---|
| USB DFU | PA11/PA12 <- USB-C D-/D+ (crystal-less USB, ROM DFU, flashed with `dfu-util`) |
| Internal I2C (master) | PAC1934 (0x10), BQ25601 (0x6B); pull-ups to pack 3.3 V |
| External I2C (slave 0x30) | to the 6-pin XH; no pull-ups on the pack (the carrier's 3V3 ones are used) |
| GPIO out | 4x switch drive, BQ25601 /CE, one status LED |
| GPIO in / EXTI | BQ25601 /INT, PAC1934 SLOW/ALERT (pin 28) |
| GPIO out (monitor) | PAC1934 PWRDN (pin 29), pulled up |
| ADC | 4x cell NTC (divider fed from a GPIO, off between samples) |
| BOOT0 (PA14, shared with SWCLK), NRST (PF2) | BOOT0 button to 3V3 and a reset button: the MCU runs from the cells, so replugging USB does not reset it. A blank chip boots DFU by itself; later firmware can jump to DFU on command |
| SWD | 3 test pads |

Two I2C buses keep the Heltec the only master on the carrier bus. The slave pins are open-drain and the
pull-ups are on the carrier, so the pack cannot back-power the carrier through SDA/SCL with the key off.

## Pack firmware (designed, implementation deferred)

- Crate `firmware/pack` (embassy-stm32). The pure logic goes in an `asg-core` `pack` module (no_std,
  host-tested): connection sequence, disable policy, coulomb counting, and the register map, so the
  Heltec and the pack MCU share one definition.
- Loop: wake every few seconds (key off) or every second (load or charging), PAC1934 REFRESH then
  SLEEP (5 uA; PWRDN loses the configuration), apply policy, kick the BQ25601 watchdog, Stop mode. The
  PAC1934 ALERT wakes it early. Set the channels bidirectional (NEG_PWR register): charge current is negative.
- **Connection sequence:** read all four cells, close the median one, then every cell within about 50 mV
  of the rail. Others stay open and are flagged; no on-board equalising, rebalance such a cell externally.
- **Disable policy:** a cell is disconnected and flagged when, for longer than a debounce time, its current
  differs strongly from the mean of the others, its temperature rises well above the others or crosses an
  absolute limit, it carries near-zero current while the others carry load, or its voltage leaves the safe
  window. Thresholds are compile-time constants, set with real cells.
- Per-cell currents give real charge termination even with the key on (the charger only sees the sum).

Register map (little-endian, one burst read):

| Reg | Content |
|---|---|
| 0x00 | version |
| 0x01 | flags: per cell connected / disabled and reason (OV, UV, temp, mismatch, no-current, never connected) |
| 0x02.. | cell mV x4, cell mA x4 (signed), cell degC x4, pack SOC %, charger state |
| 0x40 | command: reconnect cell n, enter DFU |

## Heltec power feed (verified)

Source: `HTIT-WB32LAF_V4.3.pdf` from resource.heltec.cn, read 2026-10-01.

- The header "5V" pin (JP4 pin 2) is **`VUSB`**, wired directly to USB-C VBUS ahead of F1, with no diode.
  Feeding it would put pack power on the VBUS of any attached cable (back-feeding an unpowered host).
  **Do not use it.**
- The battery socket (JP2) is `VBAT`; Q1 (AO3401A) connects VBAT to the system rail when `VDD_5V` is absent,
  and D2 (LMBR340) diode-ORs USB in. Feeding JP2 from `VBAT_SW` is the configuration the board is designed for.
- **Decision:** the Heltec keeps its feed through `J_HBAT1` from `VBAT_SW`. While the Heltec USB is plugged
  in, its CN3165 (540 mA, `I=1188/R13`) charges the pack in parallel with the BQ25601; harmless (both CC/CV
  to 4.2 V, BQ25601 OVP and the MCU switches in the path). With the key off it feeds only `VBAT_SW` loads, as today.

## Carrier changes

Remove: `J_BAT1`, `J_KEY1`, `F1`, `U4`, `R_PROT1`, `C_PROT1`, the boost (`U1`, `L1`, `D1`, `R_FB1/2`,
`C_IN1`, `C_OUT1/2`). Merge `BAT_N` into `GND`.

Keep: `J_HBAT1` on `VBAT_SW` (Heltec feed, above) and `C_BULK1/2` on `VBAT_SW` beside the amp, whose 1.5 A
peaks now arrive through a cable and the key switch. The Heltec 5V pin stays unconnected.

Add one **6-pin XH** `J_PWR1`:

| Pin | Signal |
|---|---|
| 1-2 | GND |
| 3 | `VBAT_SW` (amp, Heltec battery socket) |
| 4 | `+5V` (LCD, LEDs, buzzer) |
| 5-6 | SDA, SCL (carrier 3V3 bus) |

Addresses on the carrier bus: 0x20 (expander), 0x24 (PN532), 0x27/0x3F (LCD backpack), 0x30 (pack MCU).
A 6-pin XH is a new Extended part (setup fee per order; see `ORDERING.md`). `power_budget.py` needs 4 cells,
the pack quiescent current and the branch series drop.

## Mechanical and assembly

- Board 96 x 90 mm: four holders (77 x 20.7 mm bodies, 21.66 mm pitch) on the bottom, all SMD parts on
  top above them; check the ZP240.190-PCB plate and enclosure (cells hang under the board).
- Holders and the four cell bead NTCs are hand-soldered THT on the bottom; all SMD parts stay on the top
  side for JLCPCB single-side assembly.
- Spring-contact holders can open momentarily under shock (airsoft use): choose holders with positive
  retention and add a strap or lid. Four parallel cells ride through a brief dropout of one.
- Keep the charger, boost and inductor away from the cells; NTCs must touch the cells.
- Unprotected cells: mark polarity and keep exposed contacts covered.

## Verification and bring-up

1. Generator checks: `check_netlist.py` / `check_gerbers.py` for the pack board, plus an assertion that
   every cell branch is fuse -> shunt -> switch -> rail in that order.
2. Bench, with a current-limited PSU in place of cells:
   - USB DFU enumerates (`dfu-util -l`).
   - With bypasses fitted: rail, LDO and charger come up; key-off quiescent current (target tens of uA).
   - BQ25601 stops at 4.208 V and its battery OVP trips with the PSU above it; firmware opens a cell
     at its UV limit; a short through the PSU limit is seen by the PAC1934 alert.
   - Reversed "cell": PSU at low current limit confirms the crowbar path; then one sacrificial cell with the
     real fuse.
   - Once firmware exists: switches close in order, a cell 200 mV off stays open; 2 A charge of four
     matched cells with per-cell current log (sharing, termination with key on).
3. Carrier: `make all` green after the removals; the Heltec boots from `J_HBAT1` fed by the pack.

## Risks

- **No protector IC (2026-10-02).** Over-discharge protection is firmware plus the default-off switches;
  a running MCU with wrong firmware can over-discharge a cell. Mitigated by the IWDG, a host-tested UV
  disconnect and the Heltec's own brown-out cutting the load with the key on.
- **Reversed cell.** Crowbar Schottky plus fuse; the fuse and Schottky I2t are unverified.
- **Ageing mismatch:** use matched cells from one batch and check capacity before building a pack.
- **No MCU, no power:** a firmware fault leaves the pack open until watchdog reset; bypass footprints exist
  for bring-up only.

## Repo effort

The hardware flow is generator-based (`design.py` -> `gen_sch.py`/`gen_pcb.py` -> KiCad -> `fab/`). A second
board means a second design definition and a second set of fab outputs, plus removing the parts listed
above from the carrier (and regenerating its BOM/CPL and `power_budget.py`).

## Parts (settled 2026-10-01, from datasheets and live JLCPCB stock)

Every LCSC number below was queried live against the JLCPCB parts API on 2026-10-01;
library type (B = Basic, P = Preferred Extended, E = Extended), maker and stock are recorded.

### Chosen parts

| Item | Decision | LCSC | Type | Stock | Source |
|---|---|---|---|---|---|
| MCU | STM32C071KBT6, LQFP-32, `MCU_ST_STM32C0:STM32C071KBTx` | C42116633 | E | 600 | JLCPCB API |
| Charger | BQ25601RTWR, QFN-24, `Battery_Management:BQ25601` | C468236 | E | 5877 | JLCPCB API |
| Current monitor | PAC1934T-I/JQ, UQFN-16 4x4, `Sensor_Energy:PAC1934x-xJQ` (was 2x INA3221 C181255) | C623960 | E | 583 | JLCPCB API 2026-10-02 |
| Cell protector | none since 2026-10-02 (was XB8089D C79928, see the simplification delta) | | | | |
| LDO | XC6206P332MR, SOT-23-3, `Regulator_Linear:XC6206PxxxMR` | C5446 | B | 474563 | JLCPCB API |
| P-FET (x8) | AO3401A, SOT-23, `Transistor_FET:AO3401A` | C15127 | B | 782223 | JLCPCB API |
| N-FET | BSS138, SOT-23, `Transistor_FET:BSS138` | C7420339 | P | (carrier part) | `design.py` |
| Diode-OR (x5) | B5819W (SL), SOD-123, `Device:D_Schottky` (was BAT54C C37704) | C8598 | B | 512045 | JLCPCB API 2026-10-02 |
| Crowbar + boost diode | SS34, SMA, `Diode:SS34` | C8678 | B | 4440087 | JLCPCB API |
| Charger inductor | Murata DFE322512F-1R5M, 1210, 1.5 uH, Irms 3.0 A, Isat 3.9 A, DCR 48 mOhm | C703084 | E | 4596 | Murata dynamic-model list + JLCPCB API |
| Boost IC / L / caps | MT3608 + 10 uH 2 A + 22 uF 25 V, copied from the carrier | C84817 / C2046332 / C12891 | E / E / B | | `design.py` |
| Branch fuse | Bourns SF-1206F500-2, 1206, 5 A fast, I2t 0.966 A2s | C48332 | E | 9975 | Bourns SF-1206F datasheet + JLCPCB API |
| Shunt | FOJAN FMF06FTHR010-LH, 1206, 10 mOhm 1% 1 W (was RLS12FTCR020 20 mOhm C163047) | C105362 | E | 244330 | JLCPCB API 2026-10-02 |
| NTC (charger TS) | Nanjing Shiheng CMFB 103F3435, 0805, 10k B3435 1% | C2889056 | E | 15625 | JLCPCB API |
| Tact switch (BOOT0, NRST) | XUNPU TS-1088-AR02016, SMD 4x3 mm, 2-pad, `Button_Switch_SMD:SW_SPST_TS-1088-xR020` | C720477 | B | 787409 | JLCPCB API |
| LED red (STAT) | NCD0805R1, 0805 | C84256 | B | 4820981 | JLCPCB API |
| LED green (MCU status) | KT-0805G, 0805 | C2297 | B | 3140725 | JLCPCB API |
| USB-C receptacle | HCTL HC-TYPE-C-16P-01A, `Connector_USB:USB_C_Receptacle_HCTL_HC-TYPE-C-16P-01A` | C2894897 | E | 43482 | JLCPCB API |
| USB-C symbol | `Connector:USB_C_Receptacle_USB2.0_14P` | | | | KiCad 9.0.8 |
| 6-pin XH | JST B6B-XH-A(LF)(SN), `Connector_JST:JST_XH_B6B-XH-A_1x06_P2.50mm_Vertical` | C144397 | E | 43646 | JLCPCB API |
| 18650 holder | MYOUNG BH-18650-A6AJ012, `local:BatteryHolder_MYOUNG_BH-18650-A6AJ012` (from drawing MY-CP-0373), bottom side, hand-soldered | C19184084 (off-board) | E | 3748 | JLCPCB API + MYOUNG drawing |
| Cell NTC (x4) | MF52A103F3435 bead, `local:NTC_Bead_P2.54mm`, bottom side, hand-soldered | C84036 (off-board) | E | 32878 | JLCPCB API |
| 4-pin XH | JST B4B-XH-A(LF)(SN), carrier part | C144395 | E | | `design.py` |

Pack-only passives (Basic where noted, all live-checked 2026-10-01): 1M 0805 C17514, 100k 0805 C149504,
5.1k 0805 C27834 (also CC1/CC2), 10 uF 0805 C15850, 4.7 uF 0805 C1779, 1 uF 0805 C28323,
47 nF 0805 C53134. TS bias resistors were the datasheet values 5.23 kOhm C17739 and 30.9 kOhm
C204398 (both Extended; kept exact because they set the JEITA window). The 5.2 mm-pitch TS-1187A
was dropped for the 2-pad TS-1088 so the symbol (`Switch:SW_Push`) pairs with a 2-pad footprint
without unconnected pads.

The `BAT54C` guess in the plan ("C47546 or similar") is wrong: C47546 is a BAT54**S** (series), not
common-cathode. Use C37704. There is no Basic BAT54C at JLC; it is Extended.

### Datasheet facts

**STM32C071KBT6** (DS14693 Rev 2, 2025-04; RM0490 Rev 5; both read 2026-10-01)

- LQFP-32 pin numbers (KiCad symbol cross-checked against DS14693 Table 12 and Figure 6):
  VDD 4, VSS 5, PF2-NRST 6, PA0-PA3 7-10, PA4 11, PA5 12, PA6 13, PA7 14, PB0 15, PB1 16, PB2 17,
  PA8 18, PA9 19, PC6 20, PA10 21, PA11 22, PA12 23, PA13 24, PA14-BOOT0 25, PA15 26, PB3 27,
  PB4 28, PB5 29, PB6 30, PB7 31, PB8 32. Unused/NC: PB8, PB9, PC14, PC15, PA9, PA10, PC6.
- USB FS device on PA11/PA12 is **crystal-less** (DS14693 section 3.20: "USB 2.0 FS device
  (crystal-less)"); the HSI48 oscillator plus CRS (SOF-based clock recovery) covers USB clock
  accuracy (DS14693 sections 3.16.2/3.20). No crystal parts.
- **Internal DP pull-up exists**: USB electrical table 67 gives `R_PU` on PA12 (USB_DP) 0.9-1.575 kOhm
  (typ 1.25 k). No external 1.5 k.
- ROM bootloader over USB on PA11/PA12 (DS14693 section 3.5). Boot selection (RM0490 Table 9 and
  FLASH_OPTR, 0x1FFF7800): the factory **option bytes are nBOOT_SEL = 1, NBOOT0 = 1, NBOOT1 = 1**,
  i.e. the **PA14-BOOT0 pin is ignored by default** and the NBOOT0 option bit selects main flash.
  Because a blank chip has the FLASH EMPTY flag set, first power-up is forced to system memory (USB
  DFU). Consequence: the BOOT0 button only does anything after an option-byte change that sets
  nBOOT_SEL = 0 (legacy BOOT0 pin) or NBOOT0 = 0; the board still works unflashed. Keep the button
  as a convenience for later firmware, not as the DFU entry path.
- NRST: factory `NRST_MODE = 11` (bidirectional reset, legacy NRST pin), so PF2-NRST works as an
  input with the 100 nF + reset button. It has an embedded weak pull-up (DS14693 pin table).
- Stop-mode current (DS14693 Table 32, 3 V, 25 C): typ **85.5 uA** all clocks off, 86.0 uA with
  RTC + LSE bypass; Standby typ 7.2 uA (Table 33); Shutdown lower (Table 34). A "tens of uA"
  pack quiescent target is **not** reachable with the MCU in Stop mode: budget about 85 uA for the MCU.

**BQ25601** (SLUSCK5A, March 2017, revised March 2023; read 2026-10-01)

- Application circuit (section 10.2, Figure 10-1): SW-BTST bootstrap 0.047 uF, PMID 10 uF ceramic to
  GND (pin table), SYS 10 uF, BAT 10 uF, REGN 4.7 uF / 10 V; inductor 1.5 MHz switcher,
  `ISAT >= ICHG + IRIPPLE/2` (eq. 3), ripple 20-40 % of ICHG (section 10.2.2.1). Chosen 1.5 uH / 3.9 A.
- Charging defaults with no host (Table 9-2): **ICHG 2.048 A, VREG 4.208 V**, precharge/termination
  180 mA, JEITA profile, 10 h safety timer. The I2C watchdog restores these defaults if the MCU hangs.
- PSEL (pin 2): **high = 500 mA, low = 2.4 A** input current limit in default mode (pin table, Table 9-1).
  Tie PSEL to GND for the ~2 A charge target.
- TS (pin 11, section 9.3.7.4 and Figure 9-5): resistor network from REGN to TS to GND in parallel with
  the thermistor. TI's worked 0-60 C example for a 103AT gives **RT1 = 5.23 kOhm (REGN-TS) and
  RT2 = 30.9 kOhm (TS-GND)** with the 10k B3435 NTC. Use those values (TH_CHG). Check at 25 C:
  RT2||NTC = 30.9k||10k = 7.56k, VTS/VREGN = 59 % inside the VT1/VT5 window.
- STAT (pin 4): open-drain, **6 mA sink** (Table: STAT output sink current), 10k + LED to a logic rail
  (pin table), LOW = charging, HIGH = done/disabled, blinking = fault (section 9.3.7).
- /CE (pin 9): LOW = charging enabled. Pull down 10k so charging runs with the MCU unpowered.
- /INT (pin 7): open-drain, 10k pull-up.
- /PG (pin 3): open-drain power-good. Not used: leave unconnected.
- /QON (pin 12): has an **internal 200 kOhm pull-up** (section 9.4.4.4), so it is safe to leave
  unconnected; not used.
- VAC is pin 1, VBUS is pin 24 (separate pins on the symbol): tie both to USB VBUS.

**PAC1934** (Microchip DS20005850E; read 2026-10-02)

- Pins (table 3-1, UQFN-16): SLOW/ALERT 1, VDD 2, GND 3, SM_CLK 4, SM_DATA 5, ADDRSEL 6, SENSE3- 7,
  SENSE3+ 8, SENSE4- 9, SENSE4+ 10, SENSE1+ 11, SENSE1- 12, SENSE2+ 13, SENSE2- 14, VDD I/O 15,
  PWRDN 16, EP 17 (not connected inside, "recommended" to GND). Matches `Sensor_Energy:PAC1934x-xJQ`.
- VDD 2.7-5.5 V, VDD I/O 1.62-5.5 V, 100 nF on each. Active 585 uA at 1024 samples/s, 16 uA at 8/s,
  SLEEP 5 uA, PWRDN 0.1 uA, but PWRDN keeps no configuration or data (section 4.1.6).
- Address (table 5-1): ADDRSEL resistor to GND, 0 Ohm = 0x10 ... tie to VDD = 0x1F.
- VBUS is measured at **SENSE+** (section 4); SENSE+ goes on the supply side of the shunt.
- Limits: SENSE pins -0.3 to 40 V absolute, common mode -0.2 to 32 V; **|SENSE+ - SENSE-| 500 mV
  absolute**; +-100 mA into any pin; back-to-back ESD diodes between SENSE+/- with 1 kOhm in series.
- VSENSE +-100 mV full scale; bidirectional per channel (NEG_PWR, 1Dh), default unipolar.
- SLOW/ALERT: input at power-up (high forces 8 samples/s); can be reprogrammed as open-drain ALERT.

**INA3221** (SBOS576C, revised September 2026; read 2026-10-01; replaced by the PAC1934 on 2026-10-02)

- A0 straps (Table 7-1): **GND = 0x40, VS = 0x41, SDA = 0x42, SCL = 0x43**. So U_INA1 A0 = GND (0x40),
  U_INA2 A0 = +3V3 (0x41).
- Pin numbers (Table 5-1): IN+1 12, IN-1 11, IN+2 15, IN-2 14, IN+3 2, IN-3 1; VS 4, GND 3, VPU 16,
  PV 10, Critical 9, Warning 8, TC 13, SDA 7, SCL 6, A0 5. Matches `Power_Management:INA3221`.
- **VPU (pin 16)** is the power-valid pull-up rail; the typical application connects it to the supply
  rail. Tie VPU to +3V3 (same as VS) with the 100 nF bypass (section 9.3: 0.1 uF close to VS/GND).
- Unused channels (section 7.4.2): connect the unused-channel **IN- externally to a used channel** and
  **float IN+**, or leave the channel unmonitored. For U_INA2 only ch1 is used, so short IN+2/IN-2 and
  IN+3/IN-3 together onto the ch1 IN- net (cell-4 sense); differential 0 V, common mode within range.
- Absolute maximum (section 6.1): differential (IN+)-(IN-) +/-26 V; **common-mode (IN+ + IN-)/2
  -0.3 V to 26 V**. The -0.3 V floor is the crowbar-event limit called out in the design.
- Input filter (section 7.4.3, Figure 7-8): **series R <= 10 Ohm** per input plus 0.1-1 uF to GND.
  **Not fitted** (ruling in `docs/HANDOVER-2026-10-01-pack-board-P0-P2.md`): the datasheet makes the
  filter conditional on noise above 1 MHz and the INA's averaging covers it. The sense taps
  (`R_SNSF*`/`R_SNSS*`, 0805) were 0R; since 2026-10-02 they are 10 Ohm, because without the protector
  holder- is solid GND and a reversed cell's crowbar pulls the INA inputs below -0.3 V until the fuse
  clears (simplification delta). No filter caps are fitted.

**XB8089D** (XySemi datasheet Apr 2022; read 2026-10-01)

- Protection thresholds: overcharge 4.25 V typ (4.2-4.3), overcharge release 4.10 V,
  overdischarge 2.5 V typ, overdischarge release 3.0 V. FET R_SS(ON) 20 mOhm typ.
- Overcurrent (section "Detection Current" / "Detection Delay Time"): **Overdischarge Current 1
  typ 10 A, delay 10 ms; Overdischarge Current 2 typ 15 A, delay 0.4 ms; Load Short-Circuit typ
  40 A, delay 75 us.** Current consumption in normal operation 6-12 uA.
- Recovery: overdischarge is released by charging (VDR) or by removing the load; overcurrent/
  short-circuit release when the load is removed (VM pin returns to GND). No latch, no host reset.
- **Fuse ruling.** The plan/design text said "5 A fast-blow, above the XB8089D overcurrent trip".
  The datasheet trip is 10 A, so a 5 A fuse is *below* it. The correct rule, and what the board uses:
  the fuse sits **above the maximum per-cell current** (about 2 A) and **below the crowbar fault
  current**, so it is the slow backup to the protector rather than a nuisance blow. Crowbar check:
  Bourns SF-1206F500-2 melting I2t = 0.966 A2s; at 20-30 A it clears in 0.966/400 .. 0.966/900 =
  **1.1-2.4 ms**. SS34 non-repetitive surge is **100 A for 8.3 ms** (Vishay/onsemi SS32-SS39), i.e.
  I2t about 41 A2s, so the diode sees under 3 A2s during clearing. The XB8089D short-circuit trip
  (40 A, 75 us) normally acts first; the fuse covers a sustained 10-15 A that the protector times out
  on and a failed protector during a reversed cell.

**XC6206P332MR** (Torex XC6206 series datasheet; read 2026-10-01): Iq **1.0 uA typ (3.0 uA max)**,
VIN 1.8-6.0 V, IOUT 200 mA (500 mA current limit). Confirmed C5446 is the -G SOT-23-3 Basic part.

**AO3401A** (AOS datasheet; read 2026-10-01): RDS(ON) **<= 85 mOhm at VGS = -2.5 V (typ 60 mOhm)**,
<= 60 mOhm at -4.5 V, ID -4.0 A. Back-to-back at a 3.0 V cell is about 120-130 mOhm per branch.

**Gate resistor:** 1 MOhm per cell (4 uA at 4.2 V, 16 uA for four) as already in the per-cell diagram.

### Footprints

All named footprints/symbols exist in KiCad 9.0.8: `Connector_USB:USB_C_Receptacle_HCTL_HC-TYPE-C-16P-01A`,
`Connector_JST:JST_XH_B6B-XH-A_1x06_P2.50mm_Vertical`,
`Battery:BatteryHolder_Keystone_1042_1x18650`,
`Package_DFN_QFN:QFN-24-1EP_4x4mm_P0.5mm_EP2.6x2.6mm` (BQ25601),
`Package_DFN_QFN:Texas_RGV0016A_VQFN-16-1EP_4x4mm_P0.65mm_EP2.1x2.1mm` (INA3221 RGV, no longer used),
`Package_DFN_QFN:UQFN-16-1EP_4x4mm_P0.65mm_EP2.6x2.6mm` (PAC1934, since 2026-10-02).

**18650 holder:** MYOUNG BH-18650-A6AJ012 (drawing MY-CP-0373, 2023-09-01): body 77 x 20.7 x
14.9 mm, flat SUS304 contacts (0.35 mm), THT tabs in plated slots 1.3 x 2.6 mm at 71.45 mm pitch, snap
pegs d3.3 at (+27.6, -8) / (-27.6, +8) and d2.4 at (+35.8, +8) mm (top view, + on the right). The bottom
view shows a floor window about 67 x 8 mm (scaled from the drawing, not dimensioned) that the bead NTC
uses. The Keystone 1042 used first is only 14.86 mm tall around an 18.3 mm cell, so its floor lies on
the board: the SMD parts placed under it in the first layout could not have fitted.

## Unverified (check before building)

Closed on 2026-10-01 by the datasheet and stock check above: XB8089D trip/release, fuse and Schottky
I2t, STM32C071 USB DFU / crystal-less USB / Stop current, BQ25601 defaults and TS network, AO3401A
RDS(on) at low gate voltage, holder and 6-pin XH LCSC/stock.

Still open, and only answerable with real hardware or the pack firmware:

- Long-term reliability of protected cells in parallel and the crowbar protection once a real fuse
  and a sacrificial cell are used (bench item).
- Pack quiescent current as built: the model puts the MCU Stop contribution at about 85 uA, so the
  "tens of uA" target is revised upward and measured on the bench (P6.1).
- Total LDO + monitor quiescent current as built.
- 18650 capacity (3350 mAh is the datasheet minimum used by `power_budget.py`) for the actual cells.
- embassy-stm32 support level for STM32C071 USB and Stop mode (firmware, deferred).
- ZP240.190 plate and enclosure hole pattern (M3 corners of the 96 x 90 mm board are provisional).
- BH-18650-A6AJ012 on the 1:1 print: tab slots, pegs, and the floor window (size and position are
  scaled from the drawing) leaving room for the bead NTC to reach the cell.
