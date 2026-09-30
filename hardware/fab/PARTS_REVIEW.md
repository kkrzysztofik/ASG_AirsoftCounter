# Parts review notes (2026-09-30)

Findings from reviewing the fuse, capacitors, resistors and diodes. Datasheet figures are typical
values, not checked against the exact LCSC parts. JLCPCB stock/price was not checked (API unreachable).

## Changed

- Driver gate resistors 100R -> 1k and gate pull-downs 100k -> 10k (`design.py`): removes two BOM
  lines (C17408, C149504); every 0805 resistor is now 10k, 1k, 4k7, 0R or the 75k feedback part.
  The gate divider sets the FET gate to about 3.0 V (3.3 V x 10k / 11k) instead of 3.3 V. That is
  still well above the BSS138 threshold for ~15 mA loads. Costs about 0.3 mA per active driver.
- Both parts were Basic, so this saves no setup fee, only BOM lines.

## Open: battery protection (not resolved)

- `F1` (2 A hold PTC, 1206L200/16NR) is the only protection on the unprotected 18650 cells.
  PTC hold current drops with temperature: typically about 1.4 A at 60 C, against a worst-case
  load of about 1.5 A (LoRa TX + 1 W speaker + 5 V loads). A hot closed enclosure could cause nuisance
  trips. A 2.5-3 A hold part in the same 1206 footprint would add margin; no LCSC part checked.
- No under-voltage cutoff is on this board. `VBAT_SW` feeds the boost (`U1`, EN tied to VIN, so it is
  always on while the key switch is on) and the amp directly. Whether the Heltec V4 cuts off a
  discharged cell is **unverified**: Heltec's datasheets were unreachable from the build environment.
  Check the V4 schematic.
- Options if the Heltec does not protect: fit protected 18650 cells (check they fit the holders, they
  are longer); or add a firmware cutoff on the VBAT sense (GPIO1) that turns off the speaker
  (`AMP_SD`) and LCD and goes to deep sleep. The boost cannot be shut off in firmware today. Wiring `U1`
  EN to a spare expander pin (P6/P7, `U2.11`/`U2.12`) with a pull-up to `VBAT_SW` would allow that.

## Checked, no change

- Capacitors: 22 uF 25 V on the boost and amp (25 V keeps capacitance under 5 V DC bias), 47 uF 10 V
  bulk on `VBAT_SW` (about 25-30 uF effective each), 100 uF 6.3 V on 3V3 for the PN532, 100 nF
  decoupling. All Basic. Optional: use the 100 uF 6.3 V part for `C_BULK1/2` to drop one line (less
  margin for battery hot-plug spikes).
- `D1` SS34 (SMA, 40 V, 3 A Schottky, Basic): boost output is 5.1 V (0.6 V x (1 + 75k/10k)) at well
  under 1 A average. Ample margin; polarity (K on +5V, A on SW) is right.
- `D_FLY1` 1N4148W (Basic): flyback across the buzzer. The BZ-38 is a piezo with a built-in generator
  (about 8 mA), so it does not strictly need it, but it allows a magnetic buzzer later. Keep, or drop to
  save one line. Polarity (K on +5V) is right.
