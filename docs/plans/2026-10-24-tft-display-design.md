# AirsoftCounter display: 3.5" ILI9488 SPI TFT replaces the Newhaven 20x4

Date: 2026-10-24
Status: design approved, no implementation plan yet.
Supersedes: the Newhaven NHD-0420D3Z-FL-GBW-V3 choice (2026-10-02 power-efficiency design) and the
I2C LCD on J_LCD1 / level shifter (2026-09-28 carrier design, Parts 1 and 6). No Newhaven fallback:
the old 4-pin LCD header goes away.

## The part

AliExpress 1005001999296476: "3.5 inch IPS SPI 480x320 TFT ILI9488, 4-wire resistive touch, 65K".
The listing's spec table is JS-rendered, so outline, hole grid, depth, supply and the backlight pin
circuit are **unknown until the module is in hand** (see "Checks on arrival").

User decisions:
- **Touch unused.** The display sits behind the sealed clear lid (IP65); a resistive panel needs a
  direct press. MISO, T_CS, T_IRQ, T_CLK and the SD slot stay unconnected. Buttons stay the input.
- **Proper connection and dimming** (native CS and PWM backlight) over the cheaper expander option.

Known trade-off: a transmissive IPS panel is unreadable with the backlight off and weaker than the
transflective Newhaven in direct sun. Accepted.

## Heltec V4 pins (verified on the V4.3 schematic and Heltec pin map, 2026-10-24)

- The V4 has two extra **2-pin headers** at the antenna end, either side of the IPEX:
  **P4 = GPIO15/16**, **P5 = GPIO17/18** (datasheet "2*2*2.54 header pins"; not a 1x4 strip, and
  not on the J2/J3 grid).
- GPIO15/16 (XTAL_32K_P/N): no 32 kHz crystal is fitted; they go only to P4 and the expansion FPC.
- GPIO17/18 (OLED_SDA/SCL): only reach the OLED FPC, no pull-ups on the main board. Free on the
  no-OLED counter boards (the OLED companion does not drive this display).
- GPIO43/44 (U0TXD/U0RXD): free, the V4 has native USB and no USB-UART chip.
- The expander INT stays on GPIO6; the radio keeps SPI2 on GPIO8-14.

| Signal | GPIO | Heltec pin | Notes |
|---|---|---|---|
| SCK | 17 | P5 | SPI3 via the GPIO matrix, 20 MHz (ILI9488 write limit) |
| MOSI | 18 | P5 | |
| CS | 15 | P4 | |
| DC | 16 | P4 | |
| BL (PWM) | 44 | J2-5 | LEDC; input at boot, carrier pull-down keeps the backlight dark until firmware runs |
| RST | 43 | J2-6 | ROM boot log toggles it (only resets the display); firmware resets it cleanly in init |

## Carrier changes (carrier and carrier_tme)

- **J_LCD1: XH-4 -> XH-8**, pinout GND, 5V, SCK, MOSI, CS, DC, RST, BL. 22.4 mm wide (was 12.4), so
  the top-edge connector row (J_LCD1, J_NFC1) is re-placed.
- **Two 1x2 female sockets** (same H8.5 height as the J2/J3 sockets) under Heltec P4/P5, positions
  from Heltec's STEP model (`HTIT-WB32LAF_V4.3.1.step`). The user solders 1x2 male pins onto P4/P5.
- **BL pull-down** (10k-class) on the carrier.
- **I2C level shifter removed** (Q_SDA1, Q_SCL1, R_SDA5, R_SCL5): it only existed for the 5 V
  Newhaven. The bus is 3.3 V only now (PN532, TCA9534) and can run at 400 kHz.
- Module powered from +5V (its own 3.3 V regulator; logic is 3.3 V, no shifting). To confirm on arrival.

## Mechanical

- `mech/params.py`: `LCD`, `LCD_HOLES`, `LCD_DEPTH` (and pilot size) become MEASURE placeholders
  for the TFT until measured; 3.5" SPI modules are typically ~98x55 mm, close to the Newhaven 98x60.
- Gate: add the P4/P5 sockets and male pins, and check them against the **Heltec GNSS connector**,
  which is on the underside at the same antenna end (faces the carrier) in the deluxe build. This is
  the main risk of the native-pin option.

## Power

`power_budget.py`: `LCD_ON_5V` ~80 mA EST (MEASURE), `LCD_IDLE_5V` = controller asleep with the
backlight off (MEASURE), `BACKLIGHT_DUTY` = 1.0 (transmissive). What-if run on 2026-10-24 with the
optimized firmware: 190 mA game current with 80 mA at full backlight vs a 353 mA weekend budget,
PASS. Dimming only adds margin.

## Firmware

The Newhaven task (carrier plan Task C3) becomes an ILI9488 driver: `mipidsi` + `embedded-graphics`
on SPI3 (verify the ILI9488 model in the pinned `mipidsi` version). SPI mode is 18-bit colour
(3 B/px): a full frame is 460 KB, ~180 ms at 20 MHz and too big for R2 RAM, so the UI redraws only
changed regions. Backlight level is LEDC PWM on GPIO44.

## Docs

OFFBOARD_PARTS #5 (part, link, checks), the J_LCD1 pigtail row (8-pin, straight to the module
header), #21 standoffs (hole size from the measurement), and the I2C address notes (no 0x28 LCD).

## Checks on arrival (before ordering carrier PCBs)

1. **LED pin**: does the module switch the backlight with its own transistor (pin draws a few mA)?
   If not, the carrier needs a high-side MOSFET on BL; GPIO44 cannot source the backlight.
2. Outline, hole grid and diameter, depth below the panel -> `mech/params.py`.
3. Supply: VCC range (5 V via onboard regulator vs 3.3 V only) and header pinout/order.
4. Current at 5 V: full backlight, minimum PWM, backlight off -> `power_budget.py`.
