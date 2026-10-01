# AirsoftCounter pack board: 4x18650 power subsystem

Date: 2026-10-01
Status: design approved 2026-10-01. Hardware is next; pack firmware is designed here but its
implementation is deferred. Lines marked "verified" were checked against a source; everything else is
listed under "Unverified" at the end.

## Goal

Move all battery and power management off the carrier (`2026-09-28-esp32-lora-carrier-design.md`)
onto a separate **pack board** that holds four 18650 cells and manages each cell:

- **Runtime:** 4 x 3.35 Ah (Samsung INR18650-35E) = about 13.4 Ah, about double the current 2 cells.
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
       └─ SYS ─┬─ LDO 3.3 V (low Iq) ── STM32C071, INA3221 x2          [always on]
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
3. **Four cell holders**, THT, hand-soldered (none at JLC; e.g. Keystone 1042P). Polarity on silkscreen.
4. **Per-cell chain (x4)**, see below.
5. **MCU: STM32C071KBT6** (C42116633, LQFP-32, 600 in stock), see below.
6. **Boost and rails moved from the carrier:** MT3608 with L1, D1, R_FB1/2, C_IN1, C_OUT1/2, the
   2 A PTC F1 at the start of `VBAT_SW`, and the key-switch connector.

### Per-cell chain

```
holder+ ─ fuse ─┬─ shunt 20 mOhm ─┬─ back-to-back P-FET (2x AO3401A) ─ pack rail
                │                 │    gates: 1M to source (4 uA when on), pulled low by an N-FET <- MCU GPIO
                │                 └─ INA3221 IN-/bus = this cell's voltage, also when switched off
                ├─ crowbar Schottky to holder- (a reversed cell blows the fuse)
                └─ BAT54C diode-OR -> LDO -> MCU
holder- ─ XB8089D (C79928, own 1k/100nF) ─ GND        NTC under each cell -> MCU ADC
```

- **Switch on the positive side, shunt on the cell side of it.** INA3221 measures bus voltage at IN-;
  with the shunt between cell and switch each channel reads its own cell even while it is disconnected,
  which the connect check needs. (The earlier FS8205-in-the-negative-lead idea read only the pack rail.)
- **Switch defaults to OFF.** A dead MCU leaves an open pack; the XB8089D protects regardless.
  Each switch has a **DNP 0 Ohm bypass** footprint for bring-up without firmware.
- **MCU power does not depend on the switches:** the four cell+ nodes and SYS are diode-ORed (3x BAT54C) into the
  LDO, so the MCU runs from the highest cell at uA load even with every switch open, and from USB with no cells (DFU).
- **Shunt 20 mOhm:** 1.2 mV (30 LSB at 40 uV) for 60 mA per cell, 8 A full scale (one cell carrying all
  load plus charge). INA3221 offset is a few mA, so thresholds need margin.
- **Fuse about 5 A fast-blow:** above the XB8089D overcurrent trip, and must clear the crowbar current
  before the Schottky fails.
- Series resistance per branch (fuse, shunt, two FETs, XB8089D) is about 150 mOhm, larger than the cell IR
  (about 35 mOhm) and matched between branches, so it helps current sharing.
- AO3401A and BAT54C are JLC Basic. FS8205A is no longer used.

### MCU

| Function | Pins / parts |
|---|---|
| USB DFU | PA11/PA12 <- USB-C D-/D+ (crystal-less USB, ROM DFU, flashed with `dfu-util`) |
| Internal I2C (master) | INA3221 x2 (0x40, 0x41), BQ25601 (0x6B); pull-ups to pack 3.3 V |
| External I2C (slave 0x30) | to the 6-pin XH; no pull-ups on the pack (the carrier's 3V3 ones are used) |
| GPIO out | 4x switch drive, BQ25601 /CE, one status LED |
| GPIO in / EXTI | BQ25601 /INT, INA3221 Critical/Warning |
| ADC | 4x cell NTC (divider fed from a GPIO, off between samples) |
| BOOT0 (PA14, shared with SWCLK), NRST (PF2) | BOOT0 button to 3V3 and a reset button: the MCU runs from the cells, so replugging USB does not reset it. A blank chip boots DFU by itself; later firmware can jump to DFU on command |
| SWD | 3 test pads |

Two I2C buses keep the Heltec the only master on the carrier bus. The slave pins are open-drain and the
pull-ups are on the carrier, so the pack cannot back-power the carrier through SDA/SCL with the key off.

## Pack firmware (designed, implementation deferred)

- Crate `firmware/pack` (embassy-stm32). The pure logic goes in an `asg-core` `pack` module (no_std,
  host-tested): connection sequence, disable policy, coulomb counting, and the register map, so the
  Heltec and the pack MCU share one definition.
- Loop: wake every few seconds (key off) or every second (load or charging), INA3221 one-shot then
  power-down, apply policy, kick the BQ25601 watchdog, Stop mode. INA3221 alerts wake it early.
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
  to 4.2 V, per-cell protectors in the path). With the key off it feeds only `VBAT_SW` loads, as today.

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

- Board about 90 x 85 mm (four holders side by side, about 77 mm long): measure the real holder and
  check the ZP240.190-PCB plate and enclosure.
- Holders are hand-soldered THT; keep all SMD parts on one side for JLCPCB single-side assembly.
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
   - XB8089D trips: UV/OV with the PSU, short via the PSU limit; observe whether it recovers by itself.
   - Reversed "cell": PSU at low current limit confirms the crowbar path; then one sacrificial cell with the
     real fuse.
   - Once firmware exists: switches close in order, a cell 200 mV off stays open; 2 A charge of four
     matched cells with per-cell current log (sharing, termination with key on).
3. Carrier: `make all` green after the removals; the Heltec boots from `J_HBAT1` fed by the pack.

## Risks

- **Protected cells in parallel can fight.** After one cell trips on over-discharge, the others try to charge
  it back through the protector. Mitigated by the MCU switches (default off, voltage check) and per-cell fuses.
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
| Current monitor | INA3221AIRGVR, VQFN-16, `Power_Management:INA3221` | C181255 | E | 8652 | JLCPCB API |
| Cell protector | XB8089D, SOP-8-EP, `local:XB8089D` | C79928 | E | 9381 | JLCPCB API |
| LDO | XC6206P332MR, SOT-23-3, `Regulator_Linear:XC6206PxxxMR` | C5446 | B | 474563 | JLCPCB API |
| P-FET (x8) | AO3401A, SOT-23, `Transistor_FET:AO3401A` | C15127 | B | 782223 | JLCPCB API |
| N-FET | BSS138, SOT-23, `Transistor_FET:BSS138` | C7420339 | P | (carrier part) | `design.py` |
| Diode-OR | BAT54C,215 (Nexperia), SOT-23, `Diode:BAT54C` | C37704 | E | 351362 | JLCPCB API |
| Crowbar + boost diode | SS34, SMA, `Diode:SS34` | C8678 | B | 4440087 | JLCPCB API |
| Charger inductor | Murata DFE322512F-1R5M, 1210, 1.5 uH, Irms 3.0 A, Isat 3.9 A, DCR 48 mOhm | C703084 | E | 4596 | Murata dynamic-model list + JLCPCB API |
| Boost IC / L / caps | MT3608 + 10 uH 2 A + 22 uF 25 V, copied from the carrier | C84817 / C2046332 / C12891 | E / E / B | | `design.py` |
| Branch fuse | Bourns SF-1206F500-2, 1206, 5 A fast, I2t 0.966 A2s | C48332 | E | 9975 | Bourns SF-1206F datasheet + JLCPCB API |
| Shunt | TA-I RLS12FTCR020, 1206, 20 mOhm 1% | C163047 | E | 26562 | JLCPCB API |
| NTC (x5) | Nanjing Shiheng CMFB 103F3435, 0805, 10k B3435 1% | C2889056 | E | 15625 | JLCPCB API |
| Tact switch (BOOT0, NRST) | XKB TS-1187A-B-A-B, SMD 5.1x5.1 mm | C318884 | B | 477769 | JLCPCB API |
| LED red (STAT) | NCD0805R1, 0805 | C84256 | B | 4820981 | JLCPCB API |
| LED green (MCU status) | KT-0805G, 0805 | C2297 | B | 3140725 | JLCPCB API |
| USB-C receptacle | HCTL HC-TYPE-C-16P-01A, `Connector_USB:USB_C_Receptacle_HCTL_HC-TYPE-C-16P-01A` | C2894897 | E | 43482 | JLCPCB API |
| USB-C symbol | `Connector:USB_C_Receptacle_USB2.0_14P` | | | | KiCad 9.0.8 |
| 6-pin XH | JST B6B-XH-A(LF)(SN), `Connector_JST:JST_XH_B6B-XH-A_1x06_P2.50mm_Vertical` | C144397 | E | 43646 | JLCPCB API |
| 18650 holder | Keystone 1042, `Battery:BatteryHolder_Keystone_1042_1x18650`, hand-soldered | none (off-board) | | | KiCad footprint |
| 4-pin XH | JST B4B-XH-A(LF)(SN), carrier part | C144395 | E | | `design.py` |

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

**INA3221** (SBOS576C, revised September 2026; read 2026-10-01)

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
  Use 10 Ohm + 100 nF on each used IN+/IN- pair; place the filter at the shunt (Kelvin).

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
`Package_DFN_QFN:Texas_RGV0016A_VQFN-16-1EP_4x4mm_P0.65mm_EP2.1x2.1mm` (INA3221 RGV).

**18650 holder:** the Keystone 1042 footprint F.Fab body is **77.78 x 21.37 mm** (x = ±38.89,
y = ±10.685); the contact-tab guides reach x = ±43.94. Four holders side by side are about
**85.5 mm** wide (4 x 21.37 mm) plus margin, and 77.8 mm long. That fixes the board outline in P4.1;
the plan's "77 mm long" is the holder body, not the footprint.

## Unverified (check before building)

Closed on 2026-10-01 by the datasheet and stock check above: XB8089D trip/release, fuse and Schottky
I2t, STM32C071 USB DFU / crystal-less USB / Stop current, BQ25601 defaults and TS network, AO3401A
RDS(on) at low gate voltage, holder and 6-pin XH LCSC/stock.

Still open, and only answerable with real hardware or the pack firmware:

- Long-term reliability of protected cells in parallel and the crowbar protection once a real fuse
  and a sacrificial cell are used (bench item).
- Pack quiescent current as built: the model puts the MCU Stop contribution at about 85 uA, so the
  "tens of uA" target is revised upward and measured on the bench (P6.1).
- Total LDO + protector + monitor quiescent current as built.
- 18650 capacity (3350 mAh is the datasheet minimum used by `power_budget.py`) for the actual cells.
- embassy-stm32 support level for STM32C071 USB and Stop mode (firmware, deferred).
- ZP240.190 plate and enclosure hole pattern; the holder footprint fixes the board outline (P4.1).
