# Parts review notes (2026-09-30)

Findings from reviewing the fuse, capacitors, resistors and diodes. Datasheet figures are typical
values, not checked against the exact LCSC parts. JLCPCB stock/price was not checked (API unreachable).

## Changed

- Driver gate resistors 100R -> 1k and gate pull-downs 100k -> 10k (`design.py`): removes two BOM
  lines (C17408, C149504); every 0805 resistor is now 10k, 1k, 4k7, 0R or the 75k feedback part.
  The gate divider sets the FET gate to about 3.0 V (3.3 V x 10k / 11k) instead of 3.3 V. That is
  still well above the BSS138 threshold for ~15 mA loads. Costs about 0.3 mA per active driver.
- Both parts were Basic, so this saves no setup fee, only BOM lines.

## Battery protection (validated and fixed 2026-09-30)

**Fixed:** `U4` XB8089D (C79928, Extended) sits in the cell's negative lead, with `R_PROT1` 1k and `C_PROT1`
100nF (both existing BOM lines). It is a single-chip version of option (a) below: DW01 + 8205 would
have meant two Extended parts plus a new 100R line. Thresholds: 2.5 V over-discharge (release 3.0 V),
4.25 V overcharge, 10 A overcurrent, 20 mOhm. Firmware should still shut down cleanly well above 2.5 V.

Findings:

- **Heltec V4 has no under-voltage cutoff** (checked in Heltec's V4.2 schematic,
  resource.heltec.cn/download/WiFi_LoRa_32_V4/Schematic/WiFi_LoRa_32_V4.2.pdf). JP2 goes straight to
  VBAT. Q4 (AO3400A, gate pulled to VBAT through 1k) in the battery's negative lead is reverse-polarity
  protection only. There is no DW01 or 8205. The charger is a CN3165 (linear, solar-capable) set to
  540 mA (R13 2.2k); it pre-charges deeply discharged cells, it does not protect them. Field reports
  (Linuxslate forum, Meshtastic #9911) show boot loops and over-discharged cells.
- **Consequence:** with the key left on, nothing stops the cells being drained to 0 V, and the CN3165
  will then try to recharge them. With the key off, nothing draws current.
- **The boost-EN idea does not fix it.** A disabled MT3608 still passes VIN to +5V through L1 and D1, so
  the LCD, LEDs and buzzer stay powered at about VBAT - 0.4 V. It only saves the converter's own
  current. Cutting +5V completely would also stall I2C: the 5 V-side pull-ups of the level shifter
  would pull both buses low.
- **F1 is fine.** The Littelfuse 1206L200 table gives 1.50 A hold at 60 C (1.45 A at 70 C), and trip is
  3.5 A at 20 C. The ~1.5 A worst case is short peaks (LoRa TX, speaker, WiFi), not a steady load.
- Options: (a) DW01 + 8205 on the board, between J_BAT1's negative pin and GND (the same circuit
  protected cells carry; C14213 DW01+G is discontinued at LCSC, C61503 DW01A-G Extended; C32254 FS8205
  SOT-23-6); (b) protected cells, which need longer holders than the Botland DNG-16516;
  (c) a firmware low-battery shutdown on VBAT sense (GPIO1), useful with either (a) or (b) but not
  protection by itself.

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
