# AirsoftCounter pack board, variant B: no pack MCU (Heltec is the master)

Date: 2026-10-02
Status: hardware generated (`hardware/pack_b.py`, `make BOARD=pack_b all` into `fab/pack_b/`); the
Heltec firmware still to come. Variant A (pack MCU, STM32C071) is
`2026-10-01-pack-board-design.md` and stays the built and fabbed design; this doc only lists what
variant B changes. Both are kept so they can be compared and either one ordered. Facts marked
"verified" were read from the datasheet named next to them on 2026-10-02.

## Goal

Same pack functions as variant A (1S4P, per-cell switch in any 1-4 combination, per-cell voltage,
current and temperature, own USB-C charging, key-off charging), with no microcontroller and no
firmware on the pack. The Heltec reads and drives the pack over the I2C pair already on `J_PWR1`.

Why: one firmware instead of two, no DFU/USB data path, no option-byte and boot-pin handling, and
the pack's key-off drain drops from about 112 uA to about 30 uA (the STM32C071 Stop current, 85 uA,
was most of it).

## What changes against variant A

| Block | Variant A | Variant B |
|---|---|---|
| Brain | STM32C071 on the pack, I2C slave 0x30 to the Heltec | Heltec (`asg-device`), I2C master of the pack chips |
| Switch drive | 4 MCU GPIOs | **TCA9534** I/O expander (C783615, the carrier's part), address **0x21** |
| Switch default | OFF (`R_PD` 100k pulls the BSS138 gate low) | **ON** (1M pull-up to +3V3 on each BSS138 gate) |
| Cell NTCs | MCU ADC, divider fed by a GPIO | **ADS1115** (C37593), 4 single-ended channels, address **0x48**; divider fed by an expander pin |
| PAC1934 | always on, MCU puts it to sleep | **PWRDN held high only with the key on** (divider from `VBAT_SW`) |
| Charger /CE, /INT, PAC ALERT | MCU pins | expander pins, polled by the Heltec |
| Internal I2C bus + 4k7 pull-ups | yes | no: the pack chips sit on the carrier bus (pull-ups on the carrier) |
| USB-C | data to the MCU (DFU) | CC resistors only; D+/D- unconnected |
| Removed | | STM32C071, C_MCU1/2, C_NRST, R_BOOT, SW_BOOT, SW_RST, LED_MCU + R, 4 test pads, R_SCL_INT, R_SDA_INT |

Unchanged: the cell branches (fuse, 10 mOhm shunt, back-to-back AO3401A, crowbar, 10R sense taps),
the B5819W diode-OR into the XC6206 LDO, the BQ25601 with its own board NTC on TS, the boost, the key
connector, the 6-pin XH and the carrier. **The carrier needs no change**: `J_PWR1` pins 5/6 simply
reach three pack chips instead of the pack MCU.

### Expander pin map (TCA9534, 0x21)

| Pin | Use | Direction / default |
|---|---|---|
| P0-P3 | SW1-SW4 BSS138 gate (cell switch) | output; at power-up an input (high-Z, *no internal pull-ups*, verified TCA9534 pin table), so the 1M pull-up turns the cell **on**. Write 0 to open a cell |
| P4 | NTC divider supply (4x 10k NTC + 10k) | output high only while sampling (4 x 165 uA otherwise) |
| P5 | BQ25601 /CE | output; at power-up high-Z, `R_CE` 10k pull-down keeps charging enabled |
| P6 | BQ25601 /INT | input, 10k pull-up |
| P7 | PAC1934 SLOW/ALERT | input, 10k pull-up (SLOW high = 8 samples/s until reprogrammed as ALERT) |

TCA9534 standby 0.9 uA typ at 3.6 V (verified). It runs from the always-on +3V3 (diode-OR -> LDO), so
it keeps the chosen cell set while the Heltec is off, through key-off and Heltec reboots; it only
returns to "all on" after the pack loses power completely.

### I2C map on the carrier bus

0x10 PAC1934 (pack), 0x20 TCA9534 (carrier), **0x21 TCA9534 (pack)**, 0x24 PN532, 0x27/0x3F LCD
backpack, **0x48 ADS1115 (pack)**, **0x6B BQ25601 (pack)**. No collisions. 0x30 (pack MCU) is free.

### Power-up and the boot lock-out

Variant A needed the pack MCU, fed from the cells through the diode-OR, to close the default-off
switches; without an MCU nothing would close them, the pack rail would stay at 0 V and the Heltec
(fed from SYS through the key) could never boot. Variant B avoids this by making the switches
**default on**, like an ordinary power bank: insert cells, the rail comes up, the Heltec boots and
opens whatever cell its policy rejects. The diode-OR stays, so the expander, ADC and LDO stay powered
even when the Heltec opens every cell.

### Temperature

The 4 bead NTCs stay in the holder floor windows and are read by the ADS1115 (per-cell temperature
is kept). ADS1115 power-down 0.5 uA typ, its power-up default (verified, ADS111x 7.4 and table 5.5).

Rejected: the 4 NTCs in parallel on the BQ25601 TS pin. Computed with the TS window
(VT1 73.3 %, VT5 34.2 % of REGN, verified BQ25601 table): a bias that trips at 60 C with all four
cells at 60 C (RT1 1.3k, RT2 7.5k) trips only at **about 101 C for one hot cell** with the others at
25 C. A parallel network does not follow the hottest cell closely enough.

The BQ25601 keeps its own board NTC `TH_CHG` on TS, so charging still stops on temperature with the
Heltec off.

### PAC1934 power

With the key off nothing can put the PAC1934 to sleep (the Heltec is unpowered), and at its
power-up rate it draws 585 uA (16 uA with SLOW high). Its PWRDN pin is therefore driven from the
key-switched rail: a divider from `VBAT_SW` (for example 10k/47k: 4.2 V -> 3.46 V, 3.3 V -> 2.72 V)
keeps it running only while the key is on; with the key off it is in power-down (0.1 uA, verified).
PWRDN drops the configuration and the accumulators (verified, section 4.1.6), so the Heltec
configures it on every boot (bidirectional channels, sample rate, ALERT).

## Functionality kept and lost

| Function | Variant A | Variant B |
|---|---|---|
| Any 1-4 cell combination | yes | yes |
| Per-cell V, I, temperature | yes | yes (key on) |
| Coulomb counting | continuous | key on only; charge added with the key off is estimated from the charger's "done" state or rest voltage |
| Supervision with the key off (incl. key-off charging) | per-cell policy in the pack MCU | **none per cell**: the charger's CV, BATOVP (104 % of VREG, verified) and board-NTC TS limit, plus the fuses |
| Connect-check before a cell joins | yes (default off) | **no**: a cell joins as soon as it is inserted (power-bank behaviour; buy matched cells) |
| Reaction to a short / alert | MCU interrupt, ms | Heltec polling (about 1 s); the fuses handle hard shorts |
| Pack firmware, DFU | needed | none |
| Key-off drain (est.) | 112 uA | about 30 uA: TCA9534 1, ADS1115 0.5, PAC1934 0.1, BQ25601 4.5, LDO 1, 4 x 1M gate pull-ups 4.2 each |

Option, not in the baseline: supervise key-off charging by letting USB power wake the Heltec. The
BQ25601 /PG (open-drain, low = good input) could drive an AO3401A that bridges SYS to `VBAT_SW`
around the key. The catch is that the Heltec then cannot tell whether the key is on (both feed the
same node); it needs a second key contact on the spare `J_KEY1` pins 3-4, which depends on the EAO
switch having one (unverified).

## Cost

| | Variant A | Variant B |
|---|---|---|
| SMD Extended types (about $3 each per order) | 11 | **12**: minus STM32C071, plus TCA9534 and ADS1115 |
| Main chips per board (rough) | STM32C071 | TCA9534 + ADS1115 (somewhat more) |
| Placements | 104 | about 98 (11 MCU-side parts out, about 5 in) |

Variant B is **not cheaper to order**; it is simpler to own (no second firmware) and draws less
with the key off. B without the ADS1115 (no per-cell temperature, board NTC only) would be 11 types.
A single chip that does both jobs exists, ADS7128 (8 pins, each ADC or GPIO, C2867992, 1297 in
stock), but it has no KiCad symbol and the GPIO power-up state is unchecked.

## Firmware

The `asg-core` `pack` module (connection policy, disable rules, coulomb counting) is unchanged in
substance but runs on the Heltec in `asg-device` instead of a pack MCU, and the register-map
section of variant A becomes a set of drivers: PAC1934 (configure on boot, REFRESH, read
accumulators), TCA9534 (switches, /CE, polling P6/P7), ADS1115 (single-shot per NTC with P4 on),
BQ25601 (status, watchdog kick or disable). The policy must open a cell when the Heltec sees it fail,
since nothing else will while the key is on.

## Repo effort

Keep both: a second board module `hardware/pack_b.py` that imports `pack.py` and edits its
`PARTS`/`NETS`/placement (remove the MCU block, swap `R_PD*` for pull-ups, add `U_EXP`/`U_ADC` and
the PWRDN divider), built with `make BOARD=pack_b all` into `fab/pack_b/`. `pack.py` (variant A)
stays as it is.

## Unverified

- ADS7128 GPIO power-up state (only matters if it replaces TCA9534 + ADS1115).
- A second contact on the EAO 82-6121.2000 key switch (only for the USB-wakes-Heltec option).
- I2C behaviour with the key off: the pack chips are powered while the carrier pull-ups are not, so
  SDA/SCL sit low; check on the bench that no pack chip misreads the key-on/key-off edges.
- Cable length and bus capacitance: three more chips on the carrier bus over the XH cable; 100 kHz
  should be fine at 20-30 cm.
