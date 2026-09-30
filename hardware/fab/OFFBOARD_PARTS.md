# Off-board parts (per device)

These are the parts the carrier PCB does not carry. Codes and URLs were checked live on
2026-09-29; stock changes, so re-check before ordering. Sources are TME (tme.eu) and
Botland (botland.com.pl) where possible; anything else is marked **other**. Prices and
cheaper alternatives per row are in the section below the table.

| # | Part | Qty | Shop | Code | URL | Notes |
|---|---|---|---|---|---|---|
| 1 | Heltec WiFi LoRa 32 V4 (863–870 MHz, no display, S3R2 or S3R8) | 1 | **other: Heltec** (DE warehouse) | variant selector | https://heltec.org/project/wifi-lora-32-v4/ | Not sold at Botland or TME. Confirm the no-display build is selectable; the page says "custom orders without OLED" go through sales. Pick R2 or R8 deliberately (different firmware build). The 28 dBm version needs EU TX-power capping in firmware. |
| 2 | Heltec L76K GNSS module | 1 | **other: Heltec** | – | https://heltec.org/project/l76-gnss-module/ | 1.25 mm 8-pin cable included. Mount under the clear lid, facing the sky. |
| 3 | PN532 NFC module | 1 | **other: kamami.pl** | Czytnik RFID/NFC PN532 13,56MHz Mifare I2C/SPI + brelok i karta | https://kamami.pl/szukaj?controller=search&s=PN532 | **24.90 zł, verified 2026-09-29.** Same boxed red "V3" board with card and fob as Botland MOD-08240, which is 59.90 zł. Check the photo shows the I2C DIP switches; keep the LCD backpack off address 0x24. |
| 4 | NTAG213 player cards | per player | TME | RFID-GW-NTAG213 | https://www.tme.eu/pl/details/rfid-gw-ntag213/moduly-i-czytniki-rfid/goodwin/pvc-white-card-ntag213-thermal-s-n/ | Alternative: stickers RFID-STICK-NT213. Write `ASG1:R:017` with any phone NFC app. |
| 5 | 20x4 LCD + I2C (PCF8574) | 1 | Botland | LCD-02640 | https://botland.com.pl/wyswietlacze-alfanumeryczne/2640-wyswietlacz-lcd-4x20-znakow-niebieski-konwerter-i2c-lcm1602.html | 5 V, 98x60 mm, M3 holes on a 93x55 mm grid. Blue only. The part is a generic **2004A** panel on an **HW-61** (PCF8574T) backpack, neither of which has a datasheet for the backlight. **☐ On arrival: measure the backlight current** — 5.0 V into VCC with the backlight on, read mA, then switch the backlight off and subtract; that number replaces the 100 mA planning guess in `power_budget.py` (`LCD_BACKLIGHT_5V`). Also record whether the HW-61 `LED` solder jumper is fitted: if it is, firmware cannot switch the backlight off. |
| 6 | Red button, IP67, 19 mm, 6 V ring LED | 1 | TME | V19-11R-06R-S | https://www.tme.eu/pl/details/v19-11r-06r-s/przelaczniki-przyciskane/onpow/las1-agq-11e-r-6v/ | ONPOW LAS1-AGQ-11E/R/6V. Use COM+NO. The LED has a built-in resistor, so the carrier's R_LLR1 is 0 Ω. Test brightness at 5 V. |
| 7 | Blue button, IP67, 19 mm, 6 V ring LED | 1 | TME | V19-11R-06B-S | https://www.tme.eu/pl/details/v19-11r-06b-s/przelaczniki-przyciskane/onpow/las1-agq-11e-b-6v/ | As #6 (R_LLB1 is 0 Ω). |
| 8 | Buzzer, panel piezo with generator, 3–28 V, 90 dB | 1 | TME | BZ-38 | https://www.tme.eu/pl/details/bz-38/sygnalizatory-piezoelektr-z-generatorem/ | No IP rating: seal it to the wall with a gasket or silicone. |
| 9 | Loudspeaker, waterproof IP65, 8 Ω 2 W, 50 mm | 1 | TME | VS-K50-8 | https://www.tme.eu/pl/details/vs-k50-8/glosniki/visaton/2901/ | VISATON K 50 (2901), 10.23–14.20 zł, 829 in stock 2026-09-30; the WP (2915) is out of stock, only a narrower 250 Hz–10 kHz band. Mount behind a grille of holes with a front gasket. **Never connect a speaker lead to GND** (BTL output). Smaller option: VS-K36WP-8 (36 mm, 1 W). |
| 10 | Key switch, IP65, 22 mm, 2 maintained positions | 1 | TME | 82-6121.2000 | https://www.tme.eu/pl/details/82-6121.2000/stacyjki-i-zamki/eao/ | EAO; only 5 were in stock. Check the datasheet for a rating of at least 1 A at 5 V DC. |
| 11 | 18650 holder, single cell | 2 | Botland | DNG-16516 | https://botland.com.pl/koszyki-na-baterie/16516-koszyk-na-1-akumulator-typu-18650-bez-przewodow-5904422344597.html | Wire both holders **in parallel**. Unprotected cells only (protected cells are longer). |
| 12 | 18650 cell, Samsung INR18650-35E | 2 | Botland | BAL-15216 | https://botland.com.pl/akumulatory-li-ion/15216-ogniwo-18650-li-ion-samsung-inr18650-35e-3400mah-5904422343071.html | Buy both in one order and match their voltages before paralleling. |
| 13 | USB-C panel extension, IP67 with cap, male–female, about 30 cm | 1 | **other: Allegro / AliExpress** | – | – | None suitable at TME or Botland. Generic ones are IP67 only with the cap closed. |
| 14 | u.FL (IPEX) to SMA pigtail, 150 mm | 1 | TME | GSM-IPX/SMA-150 | https://www.tme.eu/pl/details/gsm-ipx_sma-150/anteny-gps/sr-passives/ | Check in the datasheet that it is SMA (not RP-SMA) female bulkhead with a nut. Alternative: Botland SPF-02942 (10 cm). |
| 15 | 868 MHz antenna, SMA male | 1 | TME | ANT-868-CW-RCS-SMA | https://www.tme.eu/pl/details/ant-868-cw-rcs-sma/anteny-rf/linx-technologies-te-connectivity/ | 3.6 dBi. Short stub alternative: 2J0C15-868-C885G. Avoid RP-SMA antennas. |
| 16 | Heltec battery plug: Molex PicoBlade 2-pin housing | 1 | TME | MX-51021-0200 | https://www.tme.eu/pl/details/mx-51021-0200/zlacza-sygnalowe-raster-1-25mm/molex/51021-0200/ | Heltec's "SH1.25" mates with **PicoBlade 1.25 mm**, not JST SH or GH. **Check polarity with a meter.** |
| 17 | PicoBlade crimp contacts | 2 (+spares) | TME | MX-50079-8000 | https://www.tme.eu/pl/details/mx-50079-8000/zlacza-sygnalowe-raster-1-25mm/molex/50079-8000/ | 26–28 AWG wire only; keep the lead short. |
| 18-19 | JST XHP-4 housing | 10 | TME | XHP-4 | https://www.tme.eu/pl/details/xhp-4/zlacza-sygnalowe-raster-2-50mm/jst/ | All 9 board connectors are 4-pin. LCD, NFC, BTN_R, BTN_B use all 4 positions. BAT, KEY, HELTEC_BAT, BUZ, SPK use positions 1-2 only (leave 3-4 empty). Plus a spare. |
| 20 | JST SXH-001T-P0.6 crimp contacts | ~30 | TME | SXH-001T-P0.6 | https://www.tme.eu/pl/details/sxh-001t-p0.6/zlacza-sygnalowe-raster-2-50mm/jst/ | 28–22 AWG. No crimper? Botland kit JUS-19558 (clone parts, contacts still need crimping). |
| 21 | M3 brass standoffs | 8 | Botland | KAB-09700 (120-pc kit) | https://botland.com.pl/tuleje-dystansowe/9700-tuleja-dystansowa-mosiezna-rozne-rozmiary-m3-zestaw-120szt-5904422308179.html | Carrier (4 holes) and LCD (4 holes), so 8 standoffs. The kit is 52.90 zł for 120 pcs: buy loose standoffs, or the kit only when building several units. |
| 22 | Enclosure Kradex ZP240.190.105SJp, clear lid, IP67 | 1 | Botland (in stock) / TME | KDX-16650 / ZP240190105SJP-PC | https://botland.com.pl/obudowy/16650-kradex-hermetyczna-obudowa-zp240190105sjp-ip67-tm-abs-240x190x105mm-z-mosieznymi-tulejami-jasnoszara-przezroczysta-5905275016433.html | Botland's has an ABS base. TME's all-PC version was out of stock. |
| 23 | Kradex ZP240.190-PCB mounting plate | 1 | TME | ZP240.190-PCB | https://www.tme.eu/pl/details/zp240.190-pcb/obudowy-akcesoria-pozostale/kradex/ | "While stocks last" (38 in stock). |
| 24 | Harness wire, 24 AWG stranded | – | any | – | – | XH contacts take up to 0.34 mm² and PicoBlade up to 0.13 mm². |
| 25 | Pre-crimped pigtails, JST-XH and PicoBlade | 1 set | **other: AliExpress** | – | – | Alternative to #16–20. Arrives already terminated, so **no crimper is needed**. Cheaper and faster than hand-crimping ~30 contacts. |

## Prices and cheaper alternatives

Checked 2026-09-29. The Botland and kamami figures were read live from the shop pages.
TME blocks scripted fetches (HTTP 403), so TME figures are **estimates — verify before
ordering**. Swaps marked **no** are not viable: the `J_NFC` I2C port, the L76K GNSS pinout
and the Heltec V4 pin map are frozen by the carrier.

| # | Price (2026-09-29) | Cheaper option | Saving | Risk |
|---|---|---|---|---|
| 1 | est. ~95 zł (Heltec) | V4 → V3 | ~25 zł | **no** — pins, FEM pins and R2/R8 PSRAM differ |
| 2 | est. ~65 zł (Heltec) | ATGM336H / NEO-6M | ~35 zł | **no** — L76K-specific EN/RST/STANDBY pins |
| 3 | **24.90 zł** (kamami, verified) | AliExpress clone, 10–20 zł | 35 zł vs Botland | none — same red V3 board |
| 4 | est. ~3 zł each | NTAG213 stickers (#4 alternative) | ~2.5 zł each | low — cards get handled, stickers do not |
| 5 | **34.90 zł** (Botland, verified) | bare 20x4 LCD + separate PCF8574 backpack | ~13 zł | low |
| 6, 7 | est. ~35 zł each (TME) | generic 19 mm IP67 6 V ring-LED | ~30 zł total | low — must be **6 V**, not 12 V |
| 8 | est. ~15 zł (TME) | generic active 5 V piezo with generator | ~10 zł | low |
| 9 | est. ~45 zł (TME) | generic IP65 8 Ω 2 W speaker | ~25 zł | low — the amp only makes ~1 W into 8 Ω |
| 10 | est. ~90 zł (TME) | generic 22 mm IP65 2-position keyswitch | ~60 zł | low — it carries only ~250 mA |
| 12 | **29.90 zł each** (Botland, verified) | cheaper 2600 mAh cell | ~30 zł | **no** — eats the 24 h runtime |
| 14 | est. ~15 zł (TME) | AliExpress u.FL→SMA pigtail | ~10 zł | low |
| 15 | est. ~70 zł (TME) | any 863–870 MHz SMA whip | ~45 zł | **medium** — this one sets LoRa range |
| 16–20 | est. ~10 zł total | pre-crimped pigtails (row 25) | see row 25 | none |
| 21 | **52.90 zł** (Botland, verified, 120-pc kit) | buy 8 standoffs | ~40 zł | none |
| 22 | **119.90 zł** (Botland, verified) | generic IP65 clear-lid box | ~30–60 zł | **high** — clear lid, 105 mm depth and 20x4 LCD constrain the fit |
| 23 | est. ~15 zł (TME) | 3 mm acrylic cut to size | ~15 zł | low |
| 25 | est. ~15 zł set | — | avoids a crimper | none |

**The crimper is the biggest single line and is not in the table.** A usable JST/PicoBlade
crimper is 60–250 zł. Pre-crimped pigtails (#25) cost ~15 zł and remove that purchase,
which is more than every other swap here combined. Order them before anything else.
