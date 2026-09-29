# Off-board parts (per device)

These are the parts the carrier PCB does not carry. Codes and URLs were checked live on
2026-09-29; stock changes, so re-check before ordering. Sources are TME (tme.eu) and
Botland (botland.com.pl) where possible; anything else is marked **other**.

| # | Part | Qty | Shop | Code | URL | Notes |
|---|---|---|---|---|---|---|
| 1 | Heltec WiFi LoRa 32 V4 (863–870 MHz, no display, S3R2 or S3R8) | 1 | **other: Heltec** (DE warehouse) | variant selector | https://heltec.org/project/wifi-lora-32-v4/ | Not sold at Botland or TME. Confirm the no-display build is selectable; the page says "custom orders without OLED" go through sales. Pick R2 or R8 deliberately (different firmware build). The 28 dBm version needs EU TX-power capping in firmware. |
| 2 | Heltec L76K GNSS module | 1 | **other: Heltec** | – | https://heltec.org/project/l76-gnss-module/ | 1.25 mm 8-pin cable included. Mount under the clear lid, facing the sky. |
| 3 | PN532 NFC module | 1 | Botland | MOD-08240 | https://botland.com.pl/moduly-i-tagi-rfid/8240-modul-rfidnfc-pn532-1356mhz-i2cspi-karta-i-brelok-5904422375775.html | Check the photo shows the red "V3" board with I2C DIP switches. |
| 4 | NTAG213 player cards | per player | TME | RFID-GW-NTAG213 | https://www.tme.eu/pl/details/rfid-gw-ntag213/moduly-i-czytniki-rfid/goodwin/pvc-white-card-ntag213-thermal-s-n/ | Alternative: stickers RFID-STICK-NT213. Write `ASG1:R:017` with any phone NFC app. |
| 5 | 20x4 LCD + I2C (PCF8574) | 1 | Botland | LCD-02640 | https://botland.com.pl/wyswietlacze-alfanumeryczne/2640-wyswietlacz-lcd-4x20-znakow-niebieski-konwerter-i2c-lcm1602.html | 5 V, 98x60 mm, M3 holes on a 93x55 mm grid. Blue only. |
| 6 | Red button, IP67, 19 mm, 6 V ring LED | 1 | TME | V19-11R-06R-S | https://www.tme.eu/pl/details/v19-11r-06r-s/przelaczniki-przyciskane/onpow/las1-agq-11e-r-6v/ | ONPOW LAS1-AGQ-11E/R/6V. Use COM+NO. The LED has a built-in resistor, so the carrier's R_LLR1 is 0 Ω. Test brightness at 5 V. |
| 7 | Blue button, IP67, 19 mm, 6 V ring LED | 1 | TME | V19-11R-06B-S | https://www.tme.eu/pl/details/v19-11r-06b-s/przelaczniki-przyciskane/onpow/las1-agq-11e-b-6v/ | As #6 (R_LLB1 is 0 Ω). |
| 8 | Buzzer, panel piezo with generator, 3–28 V, 90 dB | 1 | TME | BZ-38 | https://www.tme.eu/pl/details/bz-38/sygnalizatory-piezoelektr-z-generatorem/ | No IP rating: seal it to the wall with a gasket or silicone. |
| 9 | Loudspeaker, waterproof IP65, 8 Ω 2 W, 50 mm | 1 | TME | VS-K50WP-8 | https://www.tme.eu/pl/details/vs-k50wp-8/glosniki/visaton/2915/ | VISATON K 50 WP. Mount behind a grille of holes with a front gasket. **Never connect a speaker lead to GND** (BTL output). Smaller option: VS-K36WP-8 (36 mm, 1 W). |
| 10 | Key switch, IP65, 22 mm, 2 maintained positions | 1 | TME | 82-6121.2000 | https://www.tme.eu/pl/details/82-6121.2000/stacyjki-i-zamki/eao/ | EAO; only 5 were in stock. Check the datasheet for a rating of at least 1 A at 5 V DC. |
| 11 | 18650 holder, single cell | 2 | Botland | DNG-16516 | https://botland.com.pl/koszyki-na-baterie/16516-koszyk-na-1-akumulator-typu-18650-bez-przewodow-5904422344597.html | Wire both holders **in parallel**. Unprotected cells only (protected cells are longer). |
| 12 | 18650 cell, Samsung INR18650-35E | 2 | Botland | BAL-15216 | https://botland.com.pl/akumulatory-li-ion/15216-ogniwo-18650-li-ion-samsung-inr18650-35e-3400mah-5904422343071.html | Buy both in one order and match their voltages before paralleling. |
| 13 | USB-C panel extension, IP67 with cap, male–female, about 30 cm | 1 | **other: Allegro / AliExpress** | – | – | None suitable at TME or Botland. Generic ones are IP67 only with the cap closed. |
| 14 | u.FL (IPEX) to SMA pigtail, 150 mm | 1 | TME | GSM-IPX/SMA-150 | https://www.tme.eu/pl/details/gsm-ipx_sma-150/anteny-gps/sr-passives/ | Check in the datasheet that it is SMA (not RP-SMA) female bulkhead with a nut. Alternative: Botland SPF-02942 (10 cm). |
| 15 | 868 MHz antenna, SMA male | 1 | TME | ANT-868-CW-RCS-SMA | https://www.tme.eu/pl/details/ant-868-cw-rcs-sma/anteny-rf/linx-technologies-te-connectivity/ | 3.6 dBi. Short stub alternative: 2J0C15-868-C885G. Avoid RP-SMA antennas. |
| 16 | Heltec battery plug: Molex PicoBlade 2-pin housing | 1 | TME | MX-51021-0200 | https://www.tme.eu/pl/details/mx-51021-0200/zlacza-sygnalowe-raster-1-25mm/molex/51021-0200/ | Heltec's "SH1.25" mates with **PicoBlade 1.25 mm**, not JST SH or GH. **Check polarity with a meter.** |
| 17 | PicoBlade crimp contacts | 2 (+spares) | TME | MX-50079-8000 | https://www.tme.eu/pl/details/mx-50079-8000/zlacza-sygnalowe-raster-1-25mm/molex/50079-8000/ | 26–28 AWG wire only; keep the lead short. |
| 18 | JST XHP-2 housing | 6 | TME | XHP-2 | https://www.tme.eu/pl/details/xhp-2/zlacza-sygnalowe-raster-2-50mm/jst/ | BAT, KEY, HELTEC_BAT, BUZ, SPK, plus a spare. |
| 19 | JST XHP-4 housing | 4 | TME | XHP-4 | https://www.tme.eu/pl/details/xhp-4/zlacza-sygnalowe-raster-2-50mm/jst/ | LCD, NFC, BTN_R, BTN_B. |
| 20 | JST SXH-001T-P0.6 crimp contacts | ~30 | TME | SXH-001T-P0.6 | https://www.tme.eu/pl/details/sxh-001t-p0.6/zlacza-sygnalowe-raster-2-50mm/jst/ | 28–22 AWG. No crimper? Botland kit JUS-19558 (clone parts, contacts still need crimping). |
| 21 | M3 brass standoff kit | 1 | Botland | KAB-09700 | https://botland.com.pl/tuleje-dystansowe/9700-tuleja-dystansowa-mosiezna-rozne-rozmiary-m3-zestaw-120szt-5904422308179.html | Carrier (4 holes) and LCD (4 holes). |
| 22 | Enclosure Kradex ZP240.190.105SJp, clear lid, IP67 | 1 | Botland (in stock) / TME | KDX-16650 / ZP240190105SJP-PC | https://botland.com.pl/obudowy/16650-kradex-hermetyczna-obudowa-zp240190105sjp-ip67-tm-abs-240x190x105mm-z-mosieznymi-tulejami-jasnoszara-przezroczysta-5905275016433.html | Botland's has an ABS base. TME's all-PC version was out of stock. |
| 23 | Kradex ZP240.190-PCB mounting plate | 1 | TME | ZP240.190-PCB | https://www.tme.eu/pl/details/zp240.190-pcb/obudowy-akcesoria-pozostale/kradex/ | "While stocks last" (38 in stock). |
| 24 | Harness wire, 24 AWG stranded | – | any | – | – | XH contacts take up to 0.34 mm² and PicoBlade up to 0.13 mm². |
