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

## Unverified (check before building)

- XB8089D overcurrent trip and release/recovery behaviour (datasheet unreadable from the dev environment).
- Fuse rating vs XB8089D trip and crowbar I2t; Schottky surge rating.
- STM32C071: USB DFU on the LQFP-32, two I2C peripherals, Stop-mode current, embassy USB support.
- BQ25601 default charge current and TS behaviour with a 10k NTC; LDO choice and total quiescent current.
- AO3401A RDS(on) at -3.0 V gate drive (empty cell).
- Holder dimensions and the Kradex plate pattern; 6-pin XH LCSC part and stock.
- 18650 capacity (3350 mAh is the datasheet minimum used by `power_budget.py`).
