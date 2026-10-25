# AirsoftCounter display: 3.5" ILI9488 SPI TFT replaces the Newhaven 20x4

Date: 2026-10-24
Status: carrier hardware done 2026-10-24 (pin map revised after the GNSS clash, see below); firmware not started.
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

## Heltec V4 pins (verified on the V4.3 schematic, pin map and STEP model, 2026-10-24)

First choice was native pins on the V4's extra headers, **rejected after the 3D check**:
- The V4 has two extra 2-pin headers at the antenna end, P4 = GPIO15/16 (no 32 kHz crystal fitted) and
  P5 = GPIO17/18 (OLED I2C, free on no-OLED boards). STEP: holes Ø0.9 at x = pin 18 + 2.54 mm, y ±3.33
  and ±5.87 from the module centreline; the module PCB ends 5.08 mm past pin 18.
- The **GNSS receptacle** sits on the module's underside at x 36.6-41.9 (pin 18 at 45.34), 15 mm wide,
  centred, and its **opening faces +X** (sliced in the STEP). The deluxe GPS plug and cable therefore
  leave toward P4/P5; carrier sockets there (x 46.6-49.2, y ±2..±7) would block them.

Chosen instead (user, 2026-10-24): everything on the main headers, DC and reset on the expander.
Native pins left after radio, I2S, PSRAM, strapping and GNSS are GPIO43, 44 and 6: hardware SPI needs
SCK + MOSI native and PWM dimming one more, so the expander's INT pin gives up GPIO6 (buttons are
polled) and DC goes over I2C (it only toggles between command and data phases: ~0.4 ms per redraw
rectangle at 400 kHz).

| Signal | Where | J_LCD1 pin | Notes |
|---|---|---|---|
| VCC | +5V | 1 | module's own 3.3 V regulator (check on arrival) |
| GND | GND | 2 | |
| CS | GND | 3 | tied low: only device on SPI3 |
| RST | TCA9534 P7 (U2.12) | 4 | |
| DC | TCA9534 P6 (U2.11) | 5 | |
| MOSI | GPIO44 (J2.5) | 6 | SPI3 via the GPIO matrix, 20 MHz (ILI9488 write limit) |
| SCK | GPIO43 (J2.6) | 7 | the ROM boot log toggles it; harmless with RST held by firmware init |
| LED (BL) | GPIO6 (J3.17) | 8 | LEDC PWM; R_BLPD1 10k pull-down keeps it dark until firmware runs |

J_LCD1 pin order = the first 8 pins of the usual red 3.5" SPI module header (VCC GND CS RST DC MOSI
SCK LED), so the lead is straight. Touch, MISO and SD stay unconnected.

## Carrier changes (carrier and carrier_tme, built 2026-10-24)

- J_LCD1 XH-4 -> **XH-8** (B8B-XH-A: LCSC C157972, TME B8B-XH-A), same top-edge spot; **J_NFC1 moved to
  the bottom edge** (rot 180, below the J2 row) into the strip J_UART1 left.
- **Removed:** the I2C level shifter (Q_SDA1, Q_SCL1, R_SDA5, R_SCL5: the bus is 3.3 V only now and can
  run at 400 kHz), R_INT1 + the EXP_INT net (U2 INT not connected), J_UART1 (GPIO43/44 are the display's;
  the V4 logs over native USB).
- **Added:** R_BLPD1 (10k, where R_INT1 was).
- Light sleep can no longer wake on a button edge: firmware polls the expander (or wakes on a timer).
- `make BOARD=carrier all` / `make BOARD=carrier_tme all`: 0 unrouted, ERC/DRC/parity 0. `make mech`: 23
  checks + both assembly gates (pack_xiao and pack) green, no interference.

## Mechanical (lid rebuilt 2026-10-25)

Dimensions from the LCDWiki MSP3520 (https://www.lcdwiki.com/3.5inch_SPI_Module_ILI9488_SKU:MSP3520) outline drawing (V1.0), which matches the listing (ILI9488, SPI, resistive touch):
PCB 98.00 x 56.34, 4x Ø3.2 holes on 92.00 x 49.50, touch VA 77.84 x 50.56, LCD AA 73.44 x 48.96 (off-centre
along the long side), 4.2 mm glass stack in front of the PCB, 5.8 mm total without the header, 14.18 with it.

- `LCD` 98 x 56.34, `LCD_HOLES` 92 x 49.5, `LCD_PILOT` = M3 self-tapping (2.7), `LCD_BOSS_R` 3.0 (the
  backlight edge is 3.5 mm from a hole centre), `LCD_BOSS_H` 4.5 (touch panel 0.3 mm off the lid).
- New `LCD_WINDOW` 80 x 51, centred: the lid opening is now the viewing area, not the whole PCB, so the
  bosses stand in solid panel (with the PCB-size cut they would have hung on 0.08 mm). Centred covers the
  active area with the module either way round.
- `LCD_DEPTH` 11.5: 5.8 + 2.5 header body + ~3 mm of cut pins with the lead soldered on. 4.0 mm over the
  Heltec (was 2.0). `make mech`: 23 checks + both assembly gates green, lid is one solid.

## Power

`power_budget.py`: `LCD_ON_5V` 80 mA EST (MEASURE), `LCD_IDLE_5V` 5 mA EST, `BACKLIGHT_DUTY` now means
the mean PWM level, 0.5 EST (bright on events, dimmed, never off). Weekend budget 353 mA: JLC/TME
builds 312 mA at full brightness with today's firmware, 253 dimmed, 131 optimized + dimmed (PASS). XIAO
build: 359 / 300 / 178 mA: full brightness with today's firmware fails by 2 %, so dimming is required.

## Firmware

The Newhaven task (carrier plan Task C3) becomes an ILI9488 driver: `mipidsi` + `embedded-graphics`
on SPI3 (verify the ILI9488 model in the pinned `mipidsi` version). SPI mode is 18-bit colour
(3 B/px): a full frame is 460 KB, ~180 ms at 20 MHz and too big for R2 RAM, so the UI redraws only
changed regions. Backlight level is LEDC PWM on GPIO6; DC/RST are
expander P6/P7 (an `OutputPin` over the shared I2C bus); the buttons are polled.

## Docs

OFFBOARD_PARTS #5 (part, link, checks), the J_LCD1 pigtail row (8-pin, straight to the module
header), #21 standoffs (hole size from the measurement), and the I2C address notes (no 0x28 LCD).

## Checks on arrival (before ordering carrier PCBs)

1. **LED pin**: the MSP3520 schematic has an S8050 (Q1) on it, so GPIO6 only drives a base. Confirm Q1
   is on the delivered module; without it the carrier needs a high-side MOSFET on BL.
5. Header order matches VCC GND CS RST DC MOSI SCK LED (else re-pin the lead, not the board).
2. Outline, hole grid and diameter against the MSP3520 drawing (`mech/params.py` uses it).
3. Supply: VCC range (5 V via onboard regulator vs 3.3 V only) and header pinout/order.
4. Current at 5 V: full backlight, minimum PWM, backlight off -> `power_budget.py`.
