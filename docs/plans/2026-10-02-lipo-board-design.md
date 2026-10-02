# AirsoftCounter LiPo board: 2S/3S airsoft LiPo instead of the 18650 pack

Date: 2026-10-02
Status: hardware generated (`make BOARD=lipo all` into `fab/lipo/`). A third power board next to the 18650 pack variants A
(`2026-10-01-pack-board-design.md`) and B (`2026-10-02-pack-board-variant-b-design.md`). Fit one
power board per build; the carrier does not change.

## Goal

Run the device from the 2S/3S LiPo an airsoft player already carries (XT60 or T-plug, with a balance
lead). **No charging**: players charge on their own balance charger. The board must protect the
LiPo from over-discharge per cell, without relying on the Heltec firmware.

## Why a separate board

Putting a LiPo input on the 18650 pack board was rejected: feeding a buck into SYS lets the
BQ25601 BATFET charge the 18650s from the LiPo with nothing controlling it. Avoiding that needs
ideal-diode ORing before the key, a second ADC and board space the 96 x 90 mm pack does not have.
A separate board has no cells, charger or per-cell switches, so it is small.

A "dummy cell" (a buck module whose output goes into an 18650 holder) was rejected: it has no LVC.

## Why it keeps an MCU

The system is 1S throughout (`VBAT_SW` 3.0-4.2 V feeds the Heltec battery socket and the amp), so
the board bucks the LiPo down to a fake single cell. The low-voltage cutoff must **latch**: a cutoff
that removes its own supply restarts and trips again in a loop until the pack is flat (this kills
the "ADS1115 ALERT pulls buck EN" idea, and any Heltec-driven cutoff). An always-on MCU holds the
cutoff and does a per-cell check through the balance lead. Three comparators, a reference and a
latch would cost more parts than one STM32C071, and that chip is already used in variant A.

## Block diagram

```
XT60 pigtail ─ fuse 5 A ─ rev-pol P-FET ─ TVS ─┬─ HV LDO 3.3 V (Iq <= 5 uA) ── STM32C071 [always on]
                                               ├─ buck A -> 4.10 V -> VBAT_SW ─┐
                                               └─ buck B -> 5.07 V -> +5V ────┤ J_PWR1 6-pin XH
both buck EN = key (pull-up) AND MCU_OK (open-drain)                          │ to the carrier
balance 4-pin XH ─ dividers (always on) ─ MCU ADC; MCU = I2C slave 0x30 ──────┘
```

## Blocks

### Input
- **XT60 pigtail**: a short 14 AWG (1.5 mm2) lead soldered to the 1.5 mm2 2-pad solder-jumper
  footprint, with a female XT60 panel or inline connector. T-plug users use an adapter lead.
- **Fuse 5 A** SMD, first part after the input. A LiPo short is hundreds of amps.
- **Reverse polarity**: P-FET in the positive lead, gate to GND through a resistor, zener gate clamp.
- **TVS** across the input, standoff above 12.6 V (3S full), clamp below the bucks' absolute max.
- Input range to design for: **5.5-17 V working, >= 20 V absolute** (2S empty to 4S full, so 4S
  could be added later without new parts).

### Bucks
- **One IC type used twice**, >= 20 V input, >= 3 A, with an EN pin that has a defined threshold.
  Pick the part with datasheet facts and live stock, like P0 of the pack plan.
- **Buck A -> 4.10 V on `VBAT_SW`**: Heltec battery socket and amp (1.5 A peaks). 4.10 V is below
  4.2 V, so a plugged-in Heltec USB charges into the buck output harmlessly (the buck cannot
  sink; its output rises and it stops switching). Keep `VBAT_SW` bulk capacitance at the amp as on
  the carrier.
- **Buck B -> 5.07 V on `+5V`**: LCD, LEDs, buzzer. Two bucks convert more efficiently than a buck
  to 4 V plus the MT3608 boost back up, for the same part count.

### Always-on supply
- HV LDO 3.3 V, >= 20 V input, Iq <= 5 uA, feeding only the MCU and the divider gate.

### Enable
- **EN = key AND MCU_OK**: the off-board key (`J_KEY`, same connector as the pack boards) supplies
  the EN pull-up, so only microamps pass through it. The MCU pulls EN low through an open-drain pin
  to cut both bucks. Check the EN pin's voltage rating against the pull-up source.

### MCU (STM32C071)
| Function | Use |
|---|---|
| ADC | 3 balance taps + pack total, through dividers |
| GPIO out | buck EN override (open-drain kill FET) |
| I2C slave 0x30 | on the carrier bus over `J_PWR1`; pull-ups on the carrier (no back-powering) |
| Flashing | SWD pads + BOOT0; no USB on this board |

### Balance input
- **One 4-pin XH header**: a 2S balance plug (3-pin XH) fits its pins 1-3. Pin 4 (3S tap) gets a
  pull-down, so a 2S pack reads about 0 V there.
- Dividers sized for 4.2 V x 3 at the top tap, always on: with Basic megohm values they draw
  about 10 uA, next to the MCU's 85 uA Stop current. Each ADC pin gets a 100 nF cap for a low
  source impedance. The top tap is also the pack total, so no separate total divider.

### Carrier connector
`J_PWR1`, unchanged from the pack boards: 1-2 GND, 3 `VBAT_SW`, 4 `+5V`, 5-6 SDA/SCL.

## LVC policy (firmware, defaults to tune with real packs)

- At power-up detect the cell count: 3S tap below 0.5 V means 2S. Reject a pack with a cell below
  the cutoff (stay off, flag it).
- **Warn** at 3.5 V per cell under load (flag for the Heltec to show).
- **Cut** at 3.3 V on any cell, debounced about 2 s so amp peaks do not trip it. The cutoff
  **latches**: EN held low through key cycles.
- **Release** only when every cell rests above 3.7 V (in practice: a fresh pack was plugged in).
- No balance lead: run on the total voltage with the cell count unknown, so warn and stay off (or
  allow with an assumed count; decide during firmware).

Register map: a subset of variant A at 0x30 (version, flags, cell mV x3, cell count, state,
cutoff reason), so the Heltec driver and the `asg-core` `pack` register definitions carry over.

## Key-off drain

STM32C071 Stop about 85 uA (variant A figure) + LDO <= 5 uA + bucks in shutdown (a few uA) +
dividers always on (about 10 uA): **about 110 uA**, so more than a year to drain a 1300 mAh pack.
A LiPo left plugged in is not drained in practice.

## Left out
Charging, balancing, coulomb counting (no current sense), 4S (the input rating leaves room).

## Repo effort
- `hardware/lipo.py` as a board module, built with `make BOARD=lipo all` into `fab/lipo/`. Reuse
  the MCU block from `pack.py` by import if it separates cleanly, as `pack_b.py` does; otherwise copy it.
- Firmware: a `firmware/lipo` sibling of the deferred pack firmware (ADC, thresholds, one GPIO,
  I2C slave). Deferred together with the pack firmware.

## Parts (verified 2026-10-02)

Sources: vendor datasheets and the live JLCPCB parts API (type: B Basic / P Preferred / E Extended).

| Item | Decision | Source | Date |
|---|---|---|---|
| Buck (x2) | TPS54302DDCR, TSOT-23-6, C311983 (E): VIN 4.5-28 V rec / 30 V abs; VREF 0.596 V typ; EN rising 1.23-1.28 V, EN abs max 7 V (rec max 5.5 V); shutdown 2 uA; HS current limit 4/5/6 A; 100% duty at 6 V in / 4.1 V out; fSW 400 kHz | TI SLVSDG6C (rev. 2026-03) | 2026-10-02 |
| EN node | R_EN1 100k / R_EN2 47k: EN = 0.32 x VIN -> 4.17 V at 13.05 V and 5.37 V at 4S 16.8 V, under the 5.5 V recommended max and 7 V abs max | TI SLVSDG6C | 2026-10-02 |
| Feedback | Vout = 0.596 x (1 + Rtop/Rbot). Buck A 30k/5k1 -> 4.10 V; buck B 75k/10k -> 5.07 V. Datasheet recommends Rtop ~ 100k (Table 7-2); the Basic 30k/75k tops give exact E24 ratios at ~100 uA divider current while the key is on (bucks are off when the key is open) | TI SLVSDG6C Table 7-2 | 2026-10-02 |
| Output filter | 10 uH + 2 x 22 uF 25V per buck (Table 7-2: 10 uH, 44 uF at 5 V) | TI SLVSDG6C | 2026-10-02 |
| Inductor (x2) | Bourns SRN6045TA-100M, C2046332 (E): 10 uH +-20%, DCR 52 mOhm, Irms 3.20 A (40 C rise), Isat 4.60 A (30% L drop) >= 3.5 A, so one part for both bucks | Bourns SRN6045TA datasheet | 2026-10-02 |
| Always-on LDO | Holtek HT7533-1, SOT-89-3, C14289 (B): supply abs max -0.3..33 V, VIN max 30 V, Iq 2.5 uA typ / 4.0 uA max, 100 mA; pins 1 GND, 2 VIN, 3 VOUT; C_in = C_out = 10 uF | Holtek HT75xx-1 Rev 2.40 | 2026-10-02 |
| LDO series R | none: the 33 V abs max is above the SMBJ15A 24.4 V clamp | Holtek + Littelfuse | 2026-10-02 |
| Reverse FET | AO3401A, SOT-23, C15127 (B): VDS -30 V, VGS +-12 V, RDS(on) 60 mOhm at VGS -4.5 V, ID -4 A; pinout 1 G, 2 S, 3 D. Was AO3407A (E, VGS +-20 V); the 10 V gate clamp keeps VGS inside +-12 V | AOS AO3401A datasheet; JLCPCB API | 2026-10-02 |
| Input TVS | SMBJ15A, DO-214AA, C19077569 (P, hongjiacheng; was C113988 E): VRWM 15 V (above 12.6 V 3S full), VBR 16.7-18.5 V, VC 24.4 V at 24.6 A, 600 W; below the buck 30 V and LDO 33 V abs max | Littelfuse / Diodes SMBJ15A | 2026-10-02 |
| Gate clamp | MMSZ5240B, SOD-123, C19077425 (P): 9.5-10.5 V, 500 mW. Below the AO3401A's 12 V VGS limit, also with VIN at the 24.4 V TVS clamp (0.14 mA through R_REV1). Replaces BZT52C12 (E); the earlier "no Preferred 12 V zener" note was wrong (MMSZ5242B C19077426 is Preferred) | JLCPCB API | 2026-10-02 |
| Input leads | Connector_Wire:SolderWire-1.5sqmm_1x02_P6mm_D1.7mm_OD3mm, 14 AWG / 1.5 mm2: the ~3 A worst case at 2S empty is marginal on 1 mm2 (17 AWG); 1.5 mm2 matches common XT60 pigtails and the 1.7 mm hole takes 14 AWG | design-doc current; KiCad footprint | 2026-10-02 |
| Balance header | one B4B-XH-A (C144395): JST XH is a 2.5 mm friction-lock box-shrouded header; a 3-circuit XHP housing seats on pins 1-3 and locks on the full-length shroud wall. Tap 3 then reads 0 V on a 2S pack | JST XH series drawing | 2026-10-02 |
| Dividers | Basic 1M (C17514) / 470k (C17709): tap1 470k/1M -> x0.680, tap2 1M/470k -> x0.320, tap3 2M/470k -> x0.190; at 4.35 V/cell (13.05 V pack) the taps read 2.96 / 2.78 / 2.48 V, all under the 3.3 V ADC ref | design values | 2026-10-02 |

### Plan-time changes

- Balance dividers are always on: no divider switch and no separate pack-total divider (the top tap
  is the pack total). With Basic megohm values they draw about 10 uA, next to the MCU's 85 uA Stop
  current; each ADC pin gets a 100 nF cap for a low source impedance.
- No reset/boot buttons and no status LED: SWD pads only (a blank STM32C0 boots its ROM bootloader
  by itself). Saves the TACT and LED and their drain.
- The bucks default ON when the key is on: the kill FET's gate has a pull-down (R_GK), so the bucks
  run with the MCU unflashed (bring-up) and the firmware latches them off.
- One 10 uH inductor (`L_A` = `L_B`, C2046332) for both bucks: its 4.6 A Isat covers buck A's peaks.

## Generated

`hardware/lipo.py` -> `make BOARD=lipo all` writes `lipo.kicad_sch`, `lipo.kicad_pcb` and the JLCPCB
package into `fab/lipo/` (gerber zip, BOM/CPL, schematic and renders). Freerouting: 462 tracks/vias,
0 unrouted; ERC 0, DRC 0 violations, 0 schematic-parity issues; gerbers 11 files, 70 x 50 mm,
4 x 3.2 mm NPTH. The 49 placed parts are 38 Basic, 4 Preferred (75k C17819, BSS138 C7420339, MMSZ5240B C19077425, SMBJ15A C19077569) and
7 Extended LCSC numbers (9 placements): 4 SMD types (5 A fuse C48332, TPS54302 x2 C311983,
SRN6045TA x2 C2046332, STM32C071 C42116633) and the
3 through-hole XH headers (KEY C158012, BAL C144395, PWR C144397). Economic PCBA charges one
feeder-setup fee per SMD Extended type; the XH headers are per-joint.

**SW node width (whole-branch review, 2026-10-02).** The two switch nodes route at the Default
0.25 mm, not the Power 0.8 mm the plan listed: the TSOT-23-6 SW pad at 0.95 mm pitch only admits a
necked exit, so no class width widens the run (Freerouting left it unrouted at 0.8 mm). `SW_A`'s
~8 mm run carries buck A's inductor current, ~1.5-2 A RMS (Heltec TX peaks plus brief amp peaks);
0.25 mm / 1 oz is about 0.9-1.4 A at a 10-30 C rise, i.e. at the edge of its rating. It is accepted
for the bursty airsoft duty on a short run with GND pours on both layers; a manual neck-and-widen
(the autorouter cannot express it) is the upgrade path if a wider margin is wanted.

## Bring-up

Bench supply on `J_IN1` at 7.4 V with a 100 mA limit:
1. Key open: only the LDO runs. `TP_3V3` reads 3.3 V and the input current is a few hundred uA with a
   blank MCU (STM32C0 Stop ~85 uA + LDO ~2.5 uA + dividers ~10 uA + buck shutdown).
2. Key closed: `VBAT_SW` 4.10 V and `+5V` 5.07 V. The bucks default on because `R_GK` pulls the kill
   FET's gate low; the firmware latches them off later.
3. Reversed supply: no current (the reverse P-FET blocks; the TVS should not conduct).
4. Then a real 2S pack and a real 3S pack, reading the three balance taps through the firmware.

## Unverified
- STM32C071 system bootloader over I2C (AN2606): if it is supported, the Heltec could flash the
  board over `J_PWR1` and the SWD pads would be for recovery only.
- Debounce time and thresholds with a real amp load on a worn pack.
