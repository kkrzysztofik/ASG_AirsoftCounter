# Part alternatives considered (not adopted)

Ideas from the parts-list review (2026-09-30). **Nothing here is built or verified on the board.**
JLCPCB stock, price and Basic/Extended status were not checked (the parts API was unreachable);
LCSC numbers below come from a web search and need confirming on jlcpcb.com/parts before use.

**Why bother:** U2 and U3 are Extended parts, so each carries a one-off setup fee on the order
(see `ORDERING.md`, "Setup fees"). Per-unit chip prices matter little at 2-5 boards. A swap only
pays off if the replacement is Basic or Preferred Extended (no fee), or is dropped outright.

## U2: TCA9534PWR (I2C GPIO expander, C783615)

| Option | Fit | Notes |
|---|---|---|
| PCF8574T (SOIC-16, C398075), PCF8574PW (TSSOP-16, C1542493) | Same pinout and 0x20 address range as the TCA9534 | See the differences below. Basic/Preferred status unverified. |
| PCA9534, PCA9554 | Same registers and pinout family as the TCA9534 | Only worth it if one is Preferred or Basic. No LCSC numbers found. |

**PCF8574 differences:**
- No direction/config registers, so the firmware changes.
- Quasi-bidirectional outputs: high is a weak (~100 uA) pull-up.
- Every pin **powers up high**. That would switch on the `Q_LR1`, `Q_LB1` and `Q_BZ1` gates and `AMP_SD`
  at every reset until the firmware writes to it. The TCA9534 powers up as inputs, and the 10k
  gate pull-downs keep those loads off.

**Decision:** keep the TCA9534. The saving is a setup fee, and the PCF8574 would need extra hardware or firmware to hold the buzzer and LEDs off at reset.

## U3: MAX98357AETE+T (I2S class-D amp, C910544), replaced by the NS4168

| Option | Fit | Notes |
|---|---|---|
| NS4168 (Nsiway) | Cheaper I2S amp with integrated DAC, about 2.5 W (MAX98357A: about 3.2 W) | Not footprint-compatible. Gain and channel/enable pins differ, so `AMP_SD`, the gain strap and the amp block (`U3`, `C_AMP1`, `C_AMP2`, `R_SD1`) need redoing. LCSC number and Basic/Extended status not checked. |
| No amp | Budget variant (`VARIANTS` in `design.py`) | Already drops `U3` and its setup fee. |

Into 8 ohm the board delivers about 1 W either way, so the NS4168 costs no real output.

**Decision (2026-09-30):** switched to the **NS4168** (C910588, Extended, $0.38 vs $1.33 at LCSC; same setup fee).
Symbol in `local.kicad_sym`, footprint `HSOP-8-1EP_3.9x4.9mm_P1.27mm_EP2.3x2.3mm_ThermalVias` (package EP is
2.0 mm). What changed with it:
- **CTRL instead of SD_MODE:** below 0.4 V = off, 0.9-1.15 V = left slot, 1.5 V-VDD = right slot. The expander
  drives it high, so **the firmware must put audio in the right I2S slot** (or both). CTRL's absolute maximum is
  VDD, so R_SD1 (1k) stays in series; `R_SDPD1` (10k to GND on `AMP_SD`) holds it off at reset, since no
  internal pull-down is documented. Pulses of 1-12 us on CTRL set the input high-pass filter; I2C expander
  writes are far slower, so the default filter stays.
- **No gain pin:** gain is fixed; volume is digital, as before.
- **13 mA quiescent when on** (MAX98357A: 2.4 mA): the firmware should hold CTRL low between clips.
- **C_AMP1** is now the 100 uF 6.3 V part (datasheet: ~100 uF + 1 uF at VDD; VBAT_SW stays under 4.2 V).

## To verify before acting

- Basic/Preferred/Extended status, stock and price of PCF8574T/PW, PCA9534, PCA9554 and NS4168 on JLCPCB.
- NS4168 pinout, footprint and gain/enable behaviour against the datasheet.
