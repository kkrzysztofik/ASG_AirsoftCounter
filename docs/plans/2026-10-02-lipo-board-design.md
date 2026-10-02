# AirsoftCounter LiPo board: 2S/3S airsoft LiPo instead of the 18650 pack

Date: 2026-10-02
Status: design approved, hardware not started. A third power board next to the 18650 pack variants A
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
                                               ├─ buck A -> 4.0 V -> VBAT_SW ─┐
                                               └─ buck B -> 5.1 V -> +5V ─────┤ J_PWR1 6-pin XH
both buck EN = key (pull-up) AND MCU_OK (open-drain)                          │ to the carrier
balance 4-pin XH ─ dividers (MCU-gated) ─ MCU ADC; MCU = I2C slave 0x30 ──────┘
```

## Blocks

### Input
- **XT60 pigtail**: a short 14 AWG lead soldered to the board (or into a 2-pin XH; settle with
  the holes and current rating), with a female XT60 panel or inline connector. T-plug users use an
  adapter lead.
- **Fuse 5 A** SMD, first part after the input. A LiPo short is hundreds of amps.
- **Reverse polarity**: P-FET in the positive lead, gate to GND through a resistor, zener gate clamp.
- **TVS** across the input, standoff above 12.6 V (3S full), clamp below the bucks' absolute max.
- Input range to design for: **5.5-17 V working, >= 20 V absolute** (2S empty to 4S full, so 4S
  could be added later without new parts).

### Bucks
- **One IC type used twice**, >= 20 V input, >= 3 A, with an EN pin that has a defined threshold.
  Pick the part with datasheet facts and live stock, like P0 of the pack plan.
- **Buck A -> 4.0 V on `VBAT_SW`**: Heltec battery socket and amp (1.5 A peaks). 4.0 V is below
  4.2 V, so a plugged-in Heltec USB charges into the buck output harmlessly (the buck cannot
  sink; its output rises and it stops switching). Keep `VBAT_SW` bulk capacitance at the amp as on
  the carrier.
- **Buck B -> 5.1 V on `+5V`**: LCD, LEDs, buzzer. Two bucks convert more efficiently than a buck
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
| GPIO out | divider enable (a FET that disconnects the dividers between samples), buck EN override |
| I2C slave 0x30 | on the carrier bus over `J_PWR1`; pull-ups on the carrier (no back-powering) |
| Flashing | SWD pads + BOOT0; no USB on this board |

### Balance input
- **One 4-pin XH header**: a 2S balance plug (3-pin XH) fits its pins 1-3. Pin 4 (3S tap) gets a
  pull-down, so a 2S pack reads about 0 V there.
- Dividers sized for 4.2 V x 3 at the top tap, switched off between samples so a LiPo left
  plugged in sees only the LDO and the MCU's Stop current.

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
dividers off: **about 100 uA**, so more than a year to drain a 1300 mAh pack. A LiPo left plugged
in is not drained in practice.

## Left out
Charging, balancing, coulomb counting (no current sense), 4S (the input rating leaves room).

## Repo effort
- `hardware/lipo.py` as a board module, built with `make BOARD=lipo all` into `fab/lipo/`. Reuse
  the MCU block from `pack.py` by import if it separates cleanly, as `pack_b.py` does; otherwise copy it.
- Firmware: a `firmware/lipo` sibling of the deferred pack firmware (ADC, thresholds, one GPIO,
  I2C slave). Deferred together with the pack firmware.

## Unverified
- Buck and HV LDO part choice (input rating, EN threshold, stock).
- XT60 pigtail termination: solder pads vs 2-pin XH, rated for the 3 A at 4 V draw (about 1.5 A
  from the LiPo at 8 V).
- STM32C071 system bootloader over I2C (AN2606): if it is supported, the Heltec could flash the
  board over `J_PWR1` and the SWD pads would be for recovery only.
- Debounce time and thresholds with a real amp load on a worn pack.
