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

## U3: MAX98357AETE+T (I2S class-D amp, C910544)

| Option | Fit | Notes |
|---|---|---|
| NS4168 (Nsiway) | Cheaper I2S amp with integrated DAC, about 2.5 W (MAX98357A: about 3.2 W) | Not footprint-compatible. Gain and channel/enable pins differ, so `AMP_SD`, the gain strap and the amp block (`U3`, `C_AMP1`, `C_AMP2`, `R_SD1`) need redoing. LCSC number and Basic/Extended status not checked. |
| No amp | Budget variant (`VARIANTS` in `design.py`) | Already drops `U3` and its setup fee. |

Into 8 ohm the board delivers about 1 W either way, so the NS4168 costs no real output.

**Decision:** keep the MAX98357A for now. Revisit the NS4168 only if the speaker stays and the fee matters, after the layout is settled.

## To verify before acting

- Basic/Preferred/Extended status, stock and price of PCF8574T/PW, PCA9534, PCA9554 and NS4168 on JLCPCB.
- NS4168 pinout, footprint and gain/enable behaviour against the datasheet.
