# Off-board parts (per device)

These are the parts the carrier and pack PCBs do not carry. Codes and URLs were checked live on
2026-09-29; stock changes, so re-check before ordering. Sources are TME (tme.eu) and
Botland (botland.com.pl) where possible; anything else is marked **other**. Prices and
cheaper alternatives per row are in the section below the table.

| # | Part | Qty | Shop | Code | URL | Notes |
|---|---|---|---|---|---|---|
| 1 | Heltec WiFi LoRa 32 V4 (863–870 MHz, no display, S3R2 or S3R8) | 1 | **other: Heltec** (DE warehouse) | variant selector | https://heltec.org/project/wifi-lora-32-v4/ | Not sold at Botland or TME. Confirm the no-display build is selectable; the page says "custom orders without OLED" go through sales. Pick R2 or R8 deliberately (different firmware build). The 28 dBm version needs EU TX-power capping in firmware. |
| 2 | Heltec L76K GNSS module | 1 | **other: Heltec** | – | https://heltec.org/project/l76-gnss-module/ | 1.25 mm 8-pin cable included. Mount under the clear lid, facing the sky. |
| 3 | PN532 NFC module | 1 | **other: kamami.pl** | Czytnik RFID/NFC PN532 13,56MHz Mifare I2C/SPI + brelok i karta | https://kamami.pl/szukaj?controller=search&s=PN532 | **24.90 zł, verified 2026-09-29.** Same boxed red "V3" board with card and fob as Botland MOD-08240, which is 59.90 zł. Check the photo shows the I2C DIP switches; the PN532 sits at 0x24 and the Newhaven LCD is fixed at 0x28, so they do not clash. |
| 4 | NTAG213 player cards | per player | TME | RFID-GW-NTAG213 | https://www.tme.eu/pl/details/rfid-gw-ntag213/moduly-i-czytniki-rfid/goodwin/pvc-white-card-ntag213-thermal-s-n/ | Alternative: stickers RFID-STICK-NT213. Write `ASG1:R:017` with any phone NFC app. |
| 5 | 20x4 serial LCD, transflective yellow-green | 1 | Mouser | 763-0420D3ZFLGBW-V3 (Newhaven NHD-0420D3Z-FL-GBW-V3) | https://www.mouser.com/c/?q=NHD-0420D3Z-FL-GBW-V3 | ~$17 (also Newhaven direct, DigiKey NHD-0420D3Z-FL-GBW-V3-ND; TME has none). 5 V, 98x60 mm PCB, 13.5 mm max depth, **4x Ø2.5 mm holes** on a 93x55 mm grid (M2.5, not M3; see #21). STN(+) transflective: readable in daylight with the backlight off. Backlight 1-8 by I2C command. I2C 0x28 (7-bit), **50 kHz max**, 10k pull-ups on the module (carrier R_SDA5/R_SCL5 stay DNP). **☐ Before wiring: bridge jumper R1 (I2C mode)** — it ships in RS-232 mode. **☐ On arrival: measure** 5.0 V supply current at backlight level 8 and level 1; those replace `LCD_ON_5V` and `LCD_IDLE_5V` in `power_budget.py`. I2C is on **J2** (2.54 mm holes, no pins fitted: 1 SPISS, 2 SDO, 3 SCL, 4 SDA, 5 VSS, 6 VDD), not J1 (RS-232). The order differs from J_LCD1, so solder the XHP-4 pigtail crossed: XH 1 GND -> J2.5, XH 2 5V -> J2.6, XH 3 SDA -> J2.4, XH 4 SCL -> J2.3; J2.1/J2.2 open. |
| 6 | Red button, IP67, 19 mm, 6 V ring LED | 1 | TME | V19-11R-06R-S | https://www.tme.eu/pl/details/v19-11r-06r-s/przelaczniki-przyciskane/onpow/las1-agq-11e-r-6v/ | ONPOW LAS1-AGQ-11E/R/6V. Use COM+NO. The LED has a built-in resistor, so the carrier's R_LLR1 is 0 Ω. Test brightness at 5 V. |
| 7 | Blue button, IP67, 19 mm, 6 V ring LED | 1 | TME | V19-11R-06B-S | https://www.tme.eu/pl/details/v19-11r-06b-s/przelaczniki-przyciskane/onpow/las1-agq-11e-b-6v/ | As #6 (R_LLB1 is 0 Ω). |
| 8 | Buzzer, panel piezo with generator, 3–28 V, 90 dB | 1 | TME | BZ-38 | https://www.tme.eu/pl/details/bz-38/sygnalizatory-piezoelektr-z-generatorem/ | No IP rating: seal it to the wall with a gasket or silicone. |
| 9 | Loudspeaker, waterproof IP65, 8 Ω 2 W, 50 mm | 1 | TME | VS-K50-8 | https://www.tme.eu/pl/details/vs-k50-8/glosniki/visaton/2901/ | VISATON K 50 (2901), 10.23–14.20 zł, 829 in stock 2026-09-30; the WP (2915) is out of stock, only a narrower 250 Hz–10 kHz band. Mount behind a grille of holes with a front gasket. **Never connect a speaker lead to GND** (BTL output). Smaller option: VS-K36WP-8 (36 mm, 1 W). |
| 10 | Key switch, IP65, 22 mm, 2 maintained positions | 1 | TME | 82-6121.2000 | https://www.tme.eu/pl/details/82-6121.2000/stacyjki-i-zamki/eao/ | EAO; only 5 were in stock. Check the datasheet for a rating of at least 1 A at 5 V DC. Its two leads run to the **pack board's J_KEY1** (not the carrier, since P5); current is the whole pack, so keep the leads short and thick. |
| 11 | 18650 holder, MYOUNG BH-18650-A6AJ012 (THT, flat stainless contacts) | 4 | LCSC | C19184084 | https://www.lcsc.com/product-detail/C19184084.html | **Hand-soldered on the pack board's bottom side** (not in the JLC BOM/CPL): two THT tabs plus three snap pegs per holder; drawing MY-CP-0373 is what the footprint follows. Order it with the JLC parts (LCSC) or separately. Unprotected cells only (protected cells are longer). Polarity is on the bottom silkscreen. Fallback with a KiCad footprint: MPD BH-18650-PC (taller, 21.3 mm; needs a footprint swap). Avoid generic coil-spring holders (uneven contact resistance, loose pin pitch). |
| 11a | Bead NTC, MF52A103F3435 (10k, B3435, 1 %) | 4 | LCSC | C84036 | https://www.lcsc.com/product-detail/C84036.html | TH1-TH4, hand-soldered on the bottom side in each holder's floor window, before the holders; the bead should touch the cell. |
| 12 | 18650 cell, Samsung INR18650-35E | 4 | Botland | BAL-15216 | https://botland.com.pl/akumulatory-li-ion/15216-ogniwo-18650-li-ion-samsung-inr18650-35e-3400mah-5904422343071.html | Buy all four in one batch and match their voltages before inserting. Parallel cells that differ will fight through the protectors (design doc, Risks). |
| 13 | USB-C panel extension, IP67 with cap, male–female, about 30 cm | 1 | **other: Allegro / AliExpress** | – | – | None suitable at TME or Botland. Generic ones are IP67 only with the cap closed. |
| 14 | u.FL (IPEX) to SMA pigtail, 150 mm | 1 | TME | GSM-IPX/SMA-150 | https://www.tme.eu/pl/details/gsm-ipx_sma-150/anteny-gps/sr-passives/ | Check in the datasheet that it is SMA (not RP-SMA) female bulkhead with a nut. Alternative: Botland SPF-02942 (10 cm). |
| 15 | 868 MHz antenna, SMA male | 1 | TME | ANT-868-CW-RCS-SMA | https://www.tme.eu/pl/details/ant-868-cw-rcs-sma/anteny-rf/linx-technologies-te-connectivity/ | 3.6 dBi. Short stub alternative: 2J0C15-868-C885G. Avoid RP-SMA antennas. |
| 16 | Heltec battery plug: Molex PicoBlade 2-pin housing | 1 | TME | MX-51021-0200 | https://www.tme.eu/pl/details/mx-51021-0200/zlacza-sygnalowe-raster-1-25mm/molex/51021-0200/ | Heltec's "SH1.25" mates with **PicoBlade 1.25 mm**, not JST SH or GH. **Check polarity with a meter.** |
| 17 | PicoBlade crimp contacts | 2 (+spares) | TME | MX-50079-8000 | https://www.tme.eu/pl/details/mx-50079-8000/zlacza-sygnalowe-raster-1-25mm/molex/50079-8000/ | 26–28 AWG wire only; keep the lead short. |
| 18-19 | JST XHP housings | 4 x XHP-4, 4 x XHP-2 (+spares) | TME | XHP-4, XHP-2 | https://www.tme.eu/pl/details/xhp-4/zlacza-sygnalowe-raster-2-50mm/jst/ | Pin count matches the wires. Carrier XHP-4: LCD, NFC, BTN_R, BTN_B (all four positions used). Carrier XHP-2: HELTEC_BAT, BUZ, SPK. Pack XHP-2: KEY. Search TME for the XHP-2 in the same series. Plus a spare of each. |
| 18b | JST XHP-6 housing and cable, carrier <-> pack | 2 housings, 1 cable | TME | XHP-6 | https://www.tme.eu/pl/details/xhp-6/zlacza-sygnalowe-raster-2-50mm/jst/ | The power link: **straight 1:1, pin 1 to pin 1** on both boards (GND GND BAT 5V SDA SCL). Both boards' J_PWR1 are pin-1-left on the top edge, so a straight cable keeps the polarity. Make it short and use 24 AWG; it carries the pack current. Check pin 1 with a meter before plugging in. |
| 20 | JST SXH-001T-P0.6 crimp contacts | ~30 | TME | SXH-001T-P0.6 | https://www.tme.eu/pl/details/sxh-001t-p0.6/zlacza-sygnalowe-raster-2-50mm/jst/ | 28–22 AWG. No crimper? Botland kit JUS-19558 (clone parts, contacts still need crimping). |
| 21 | M3 brass standoffs | 8 | Botland | KAB-09700 (120-pc kit) | https://botland.com.pl/tuleje-dystansowe/9700-tuleja-dystansowa-mosiezna-rozne-rozmiary-m3-zestaw-120szt-5904422308179.html | Carrier (4 holes) and LCD (4 holes), so 8 standoffs. **The Newhaven LCD holes are Ø2.5 mm: M3 does not fit, so its 4 standoffs must be M2.5** (or drill the LCD holes out to 3.2 mm, clear of traces). The kit is 52.90 zł for 120 pcs: buy loose standoffs, or the kit only when building several units. |
| 22 | Enclosure Kradex ZP240.190.105SJp, clear lid, IP67 | 1 | Botland (in stock) / TME | KDX-16650 / ZP240190105SJP-PC | https://botland.com.pl/obudowy/16650-kradex-hermetyczna-obudowa-zp240190105sjp-ip67-tm-abs-240x190x105mm-z-mosieznymi-tulejami-jasnoszara-przezroczysta-5905275016433.html | Botland's has an ABS base. TME's all-PC version was out of stock. |
| 23 | Kradex ZP240.190-PCB mounting plate | 1 | TME | ZP240.190-PCB | https://www.tme.eu/pl/details/zp240.190-pcb/obudowy-akcesoria-pozostale/kradex/ | "While stocks last" (38 in stock). |
| 24 | Harness wire, 24 AWG stranded | – | any | – | – | XH contacts take up to 0.34 mm² and PicoBlade up to 0.13 mm². |
| 25 | Pre-crimped pigtails, JST-XH | 1 set | **other: msalamon / Allegro** | – | see "Ready-made cables" below | Alternative to #16–20. Arrives already terminated, so **no crimper is needed**. Per-lead list and links below. |

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
| 5 | ~$17 (Mouser) | generic yellow-green 2004A + PCF8574 backpack, ~25 zł | ~45 zł | **high** — on/off backlight only, transmissive (unreadable in sun with the backlight off), firmware needs the HD44780 driver back |
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

## Ready-made cables (no crimper)

Checked 2026-10-02. Every board connector is a JST XH 2.5 mm header (B*B-XH-A). Shops sell the mating
XHP housing on a wire as a "JST-XH 2,54 **męski**, przewód 20 cm + gniazdo" set: the wired plug is what
you need; the loose PCB socket in the bag is a spare. "XH2.54" and "XH2.5" are the same series. All
pigtails below are single-ended (bare tinned ends), 26 AWG, 20 cm: solder and heat-shrink the far end.

| Lead | Board end | Far end | Buy | Qty | Link | Notes |
|---|---|---|---|---|---|---|
| Carrier J_PWR1 <-> pack / LiPo J_PWR1 | XHP-6 | XHP-6 | 2 x 6-pin pigtail, joined wire-to-wire **1:1** | 2 | [msalamon 6-pin, 2.68 zł](https://sklep.msalamon.pl/produkt/przewod-gniazdo-jst-xh-254mm-20cm-6-pin/) | Cut both to ~7 cm and join same colour to same colour, so pin 1 meets pin 1. Ready double-ended cables exist ([Keszoox 6-pin, 22 AWG, "Same Side"](https://keszoox.com/products/jst-xh-2-54mm-6pin-cable-connector-both-sided), ~$4.26, often sold out), but **never buy a "Reverse Side" one**: it swaps BAT with I2C. 26 AWG is enough for a 15 cm link; 22-24 AWG if you can get it. |
| J_LCD1 | XHP-4 | LCD I2C pins | 4-pin pigtail | 1 | [msalamon 4-pin, 2.37 zł](https://sklep.msalamon.pl/produkt/przewod-gniazdo-jst-xh-254mm-20cm-4-pin/) | **Newhaven NHD-0420D3Z:** solder into the J2 holes (no pins fitted), crossed: XH 1 GND -> J2.5, XH 2 5V -> J2.6, XH 3 SDA -> J2.4, XH 4 SCL -> J2.3. **Fallback 2004A + PCF8574 backpack (HW-61):** its header is GND VCC SDA SCL, so it is straight; solder to the pins or use an XH-to-Dupont-female lead ([Abra](https://abra-electronics.com/interconnects/connectors/jst-connectors/jst-xh/con-jst-xh-4d-connector-jst-4-pin-xh2-54-to-dupont-jumper-connector-female-4x1-pin-20cm.html), [Funduino](https://funduinoshop.com/en/components/cable-systems/kabeltypen/jst-system/jst-xh2.54-male-to-dupont-female-cable-4p-24awg-150cm)). |
| J_NFC1 | XHP-4 | PN532 I2C header | 4-pin pigtail | 1 | as J_LCD1 | Solder straight into the PN532 holes instead of the supplied pin strip; the V3 board's I2C header is GND VCC SDA SCL, same as J_NFC1. |
| J_BTN_R1, J_BTN_B1 | XHP-4 | button lugs | 4-pin pigtail | 2 | as J_LCD1 | Solder to the ONPOW lugs (COM/NO, LED +/-) per the carrier silkscreen. |
| J_BUZ1, J_SPK1, pack J_KEY1 | XHP-2 | buzzer leads, speaker tabs, key switch | 2-pin pigtail | 3 | [Gotronik 6-pack, 14.15 zł](https://www.gotronik.pl/wtyczka-jst-xh254-z-przewodem-20cm-gniazdo-x-6szt-p-5042.html) / [msalamon 2-pin, 2.16 zł](https://sklep.msalamon.pl/produkt/przewod-gniazdo-jst-xh-254mm-20cm-2-pin/) (out of stock 2026-10-02) | Allegro has the same for ~2 zł ("JST XH 2.54 2pin z przewodem 20cm"). |
| J_HBAT1 | XHP-2 | Heltec battery socket (1.25 mm) | 2-pin XH pigtail + **the battery cable that ships with the Heltec V4** | 1 | as above | The V4 box contains two SH1.25 leads (battery, solar). Join one to an XH-2 pigtail: XH 1 = VBAT (+), XH 2 = GND. **Check the Heltec lead's polarity with a meter** before joining; 1.25 mm leads have no standard colours. Spares: Allegro "Micro JST 1.25 2PIN" (PicoBlade-compatible; avoid "GH1.25", which does not mate). Makes #16-17 unnecessary. |
| LiPo J_IN1 | solder pads | battery XT60 | XT60 **female** (gniazdo) with 14 AWG, 10 cm | 1 | [Botland 7517](https://botland.store/wires-and-power-connectors/7517-xt60-socket-with-cable-10cm-5904422335854.html) / [modele.sklep.pl, 3.99 zł](https://modele.sklep.pl/gniazdo-xt-60-z-przewodem-14awg-10-cm-czarny-czerwony-msp-p-3526.html) | Battery packs carry the male XT60, so the board lead is the female. Matches the 1.7 mm pad holes (14 AWG). |
| LiPo J_BAL1 | B4B-XH | battery balance plug | **nothing** | – | – | The pack's balance plug (XHP-4 for 3S, XHP-3 for 2S on pins 1-3) plugs straight in. |

Per device: 2 x 6-pin, 4 x 4-pin, 4 x 2-pin pigtails, plus the XT60 lead for the LiPo build; about 25 zł
with spares. Before the first plug-in, **meter every lead pin 1 to pin 1**: cheap pigtails use random colours.
