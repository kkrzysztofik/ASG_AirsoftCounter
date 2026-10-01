# AirsoftCounter pack board: 4x18650 power subsystem

Date: 2026-10-01
Status: brainstorm agreed, design not started. Nothing here is verified against datasheets
unless a line says so. See "Unverified" at the end.

## Goal

Move all battery and power management off the carrier (`2026-09-28-esp32-lora-carrier-design.md`)
onto a separate **pack board** that holds four 18650 cells and manages each cell:

- **Runtime:** 4 x 3.35 Ah (Samsung INR18650-35E) = about 13.4 Ah, about double the current 2 cells.
- **Per-cell management:** short/overcurrent, over/under-voltage, temperature and current
  monitoring, and disabling a failing cell, so shorts, imbalance and ageing are caught.
- **Own USB-C charging**, so the Heltec USB-C becomes programming-only.
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
USB-C 5 V ─ charger + power path ─┬─ pack rail (1S4P)
                                  │     per cell: holder ─ fuse ─ shunt ─ protector ─ FET switch
                                  │     per cell: NTC, current monitor (INA3221 x2)
                                  ├─ key switch (J_KEY, off-board) ─ VBAT_SW ─┬─ MT3608 boost ─ +5V
                                  │                                           └─ to carrier (amp)
                                  └─ MCU (always powered, supervises while key off)
                                                │ I2C slave
                                                └──> carrier power connector (SDA, SCL)
```

## Blocks on the pack board

1. **USB-C input**, 5 V, CC resistors sized for the charge current.
2. **Charger with power path**, BQ24074-class: about 1-1.5 A (0.1 C of 13 Ah), NTC input, no I2C needed.
   Output behaviour and JLCPCB stock not checked.
3. **Four cell holders**, THT, soldered directly to the board, with polarity marked on the silkscreen.
4. **Per-cell chain** (x4): fuse or PTC, shunt of about 20-50 mOhm, protection stage.
5. **Protection:** one XB8089D (C79928, as already on the carrier) per cell in the negative lead.
   Autonomous: no firmware needed for over-discharge, overcharge or short.
6. **Per-cell soft-disable (second layer):** back-to-back N-FET pair per cell (FS8205-type, the part
   `PARTS_REVIEW.md` lists as C32254), gated by the MCU. The MCU closes a switch only after checking
   that cell's voltage against the pack, which handles first-connection inrush and a reversed cell.
7. **Monitoring:** 2 x INA3221 (3 channels each) for the four shunts plus two spare channels; four NTCs
   on the board beside each holder. At about 250 mA load each cell carries about 60 mA, which is only
   about 1-3 mV across the shunt, so shunt value needs care (charging currents are higher and easier).
8. **MCU** (always powered): watches the cells while the key is off and the Heltec is unpowered (that is
   when charging happens), runs the disable logic, and exposes an I2C slave interface. A fuel gauge is
   optional because the MCU can integrate current. MCU part not chosen.
9. **Boost and rails moved from the carrier:** MT3608 with L1, D1 and feedback resistors,
   bulk caps, `F1`, the key-switch connector.

### Disable policy (firmware, on the pack MCU)

A cell is disconnected (and flagged in STATUS) when any of these holds for longer than a debounce time:
its current differs strongly from the mean of the other three; its temperature rises well above the
others or crosses an absolute limit; it shows near-zero current while the others carry load; its voltage
is outside the safe window. Thresholds to be set with real cells. The hardware protectors act regardless.

## Carrier changes

Remove from the carrier: `J_BAT1`, `J_KEY1`, `J_HBAT1`, `F1`, `U4`, `R_PROT1`, `C_PROT1`, the boost
(`U1`, `L1`, `D1`, `R_FB1/2`, `C_IN1`, `C_OUT1/2`), `C_BULK1/2`. Merge `BAT_N` into `GND`.

Add one **6-pin XH** power connector:

| Pin | Signal |
|---|---|
| 1-2 | GND (two pins for current) |
| 3 | `VBAT_SW` (amp supply, peaks about 1.5 A) |
| 4 | `+5V` (LCD, LEDs, buzzer, and the Heltec 5V pin through a Schottky) |
| 5-6 | SDA, SCL to the pack MCU |

A 6-pin XH is a new part type on the BOM (new Extended setup fee per order; see `ORDERING.md`).
SDA/SCL join the carrier's 3V3-side bus. Addresses already used: 0x20 (expander), 0x24 (PN532),
0x27/0x3F (LCD backpack). INA3221 would be 0x40/0x41 and the pack MCU any free address, but the MCU is
the only device the Heltec sees, since it is the slave on the shared bus.

## Heltec power feed (open)

The Heltec battery socket is no longer used, so the Heltec must be fed another way. Candidate: the
5V pin, from `+5V` through a Schottky (SS34) so the carrier cannot back-feed a USB host. With nothing
on its battery socket the Heltec CN3165 has nothing to charge. Programming over the Heltec USB-C with
the pack running may push current into `+5V` (the Schottky blocks the reverse direction). Not verified:
whether the V4 runs from the 5V pin with no battery, whether LoRa TX peaks are fine through the boost, and
the effect on the power budget (the whole system would run through the boost, about 85% efficiency).

## Mechanical and assembly

- Board about 90 x 85 mm (four holders side by side, about 77 mm long): measure the real holder and
  check the ZP240.190-PCB plate and enclosure.
- Holders are large THT parts soldered by hand; keep all SMD parts on one side so JLCPCB single-side
  assembly still works.
- Spring-contact holders can open momentarily under shock or vibration (airsoft use): choose holders with
  positive retention and add a strap or lid. Four parallel cells ride through a brief dropout of one.
- Keep the charger, boost and inductor away from the cells; NTCs must touch the cells.
- Unprotected cells, so mark polarity and keep exposed contacts covered.

## Risks

- **Protected cells in parallel can fight.** After one cell trips on over-discharge, the others try to charge
  it back through the protector. Inrush is limited only by cell resistance and the fuses. Mitigations: match
  voltage before connecting, MCU-gated switches, fuses per cell.
- **Reversed cell.** Holders do not prevent it; the MCU voltage check before closing each switch should.
- **Ageing mismatch:** use matched cells from one batch and check capacity before building a pack.

## Repo effort

The hardware flow is generator-based (`design.py` -> `gen_sch.py`/`gen_pcb.py` -> KiCad -> `fab/`). A second
board means a second design definition and a second set of fab outputs, plus removing the parts listed
above from the carrier (and regenerating its BOM/CPL and `power_budget.py`).

## Unverified (check before building)

- Heltec V4 power architecture: running from the 5V pin without a battery (needs the V4 schematic; the
  Heltec resource site was unreachable from the dev environment).
- XB8089D release/recovery behaviour (datasheet unreadable from the dev environment): decides whether a
  tripped cell comes back on its own.
- Charger output voltage behaviour, INA3221 resolution at 60 mA/cell, and MCU choice.
- JLCPCB stock and Basic/Extended status for: charger, INA3221, MCU, FS8205, 6-pin XH, 18650 holder.
- Holder dimensions and the Kradex plate pattern.
- 18650 capacity (3350 mAh is the datasheet minimum used by `power_budget.py`).

## Next steps

1. Get the Heltec V4 schematic power page and settle the feed.
2. Pick the cell holder, charger and MCU; check stock.
3. Decide whether layer 2 (MCU-gated switches) is in the first revision.
4. Draft the pack-board schematic and update `power_budget.py` and the carrier BOM.
