# Rotating flag: four-plate team flag with a base unit

Date: 2026-10-16
Status: concept approved (3D preview reviewed), not started. Numbers marked "computed" come from the
clearance script described in Part 1; everything under "Open items" is unverified.
Updated 2026-10-17: the PWM servo and PCA9685 were replaced by a Feetech STS3215 serial bus servo
(position and load feedback) on an SC16IS750 I2C-to-UART bridge, so GPS keeps UART1.

3D preview (animated, private artifact): https://claude.ai/artifact/L14upVzvEwPNHU4F415VkW

## Goal

A new device for domination-style games: a **flag head on a 2 m pole** that shows which team holds
the point, readable from every direction and from far away, plus a **base unit** on the same pole
where players capture the point with buttons or player cards.

- The head shows **red, blue or neutral** to everybody at once: no direction may see a different colour.
- It is **passive**: it reads in full sun and holds its colour without power, unlike LEDs.
- The base unit is an **AirsoftCounter** (same carrier, pack board, LCD, buttons, PN532, speaker,
  LoRa, GPS, firmware core) with an I2C-to-UART bridge added for the servo. No carrier respin.
- One actuator: **one servo and one belt**.

## Part 1: Mechanism

### Why four plates in a box

A single flag panel, red on one face and blue on the other, shows red to one team and blue to the
team opposite. A "+" of four double-sided plates has the same flaw: every plate shows one face to
each side. Only a closed box, where the faces pointing out are all the same colour and the other
colour faces inward, shows one colour from every direction.

```
 top view   0° RED                 90° NEUTRAL               180° BLUE
         ┌──── R ────┐                  │                 ┌──── B ────┐
         │           │                  │                 │           │
         R           R         ─────────┼─────────        B           B
         │           │                  │                 │           │
         └──── R ────┘                  │                 └──── B ────┘
```

- Four plates, each **red on one face and blue on the other**, one per side of a square.
- Each plate turns about a **vertical axis through its own centre**.
- **0°:** red faces out on all four sides. **180°:** blue faces out. **90°:** the plates form a "+";
  from every direction you see one red and one blue plate, which reads as neutral or contested.
- All four plates must turn **together, by the same angle and in the same direction**. Then they never
  cross: full-width plates would only touch at the corners (0° and 180°) and at the centre (90°).

### Dimensions: A4 plates

Each plate is **A4 portrait (210 x 297 mm)**, so the faces are standard printed or coloured A4
sheets (decided 2026-10-16).

| Item | Value |
|---|---|
| Square side (axle to axle across) | 236 mm (axles 118 mm from the centre) |
| Plate | 210 x 297 mm (A4 portrait), 4 mm thick |
| Colour coverage per side when closed | 210 / 236 = 89 % |
| Face area | 624 cm² per side |
| Swing past each side | 105 mm (half a plate) |
| Plate ends at 90° | 13 mm from the centre |

The box side was chosen with a 2D clearance check: plates as 4 mm thick segments, 12 mm corner posts,
0.5° steps (computed). The table varies the plate width in a 236 mm box:

| Plate width | Min. gap, plates in step | Gap to corner post | Max. step error before plates touch |
|---|---|---|---|
| 200 mm | 21.5 mm | 10.0 mm | 19.0° |
| **210 mm (A4)** | **14.4 mm** | **5.0 mm** | **11.5°** |
| 216 mm (A4 laminating pouch, untrimmed) | 10.1 mm | 2.0 mm | 7.5° |

- **A4 tolerates a step error of 11.5°.** That is more than one tooth (9°) on the 40T pulleys of
  Part 2, so a single skipped tooth cannot make the plates collide.
- **Faces must be trimmed to exactly 210 x 297.** An untrimmed laminating pouch (216 x 303) drops the
  tolerance below one tooth.

**Visibility trade-off.** An A4 face has 39 % of the area of the 320 x 500 mm plate first sketched.
Seen from 50 m, it looks as big as that plate would from about 80 m. That is enough in woods and on
small fields.

**Upgrade path:** A3 portrait plates (297 x 420, two A4 sheets) in a 329 mm box (11.0° tolerance,
computed) keep the same drive, base unit and firmware.

**No centre mast.** At 90° the plate ends come within 13 mm of the centre, so nothing can pass
through the middle of the head. The head sits on top of the pole on its drive deck, and four corner
posts carry the top cap.

## Part 2: Drive

### Servo and belt

- **The servo turns plate 1's axle directly.** A GT2 belt over one pulley on each of the four axles
  turns plates 2 to 4. All pulleys are the same size (1:1).
- The belt runs on the **outside** of all four pulleys. That makes every pulley turn in the same
  direction, which is the condition for the plates never crossing.
- **Pulleys: 40T GT2** (25.46 mm pitch diameter). Each pulley has 90° of belt wrap, so 10 teeth are in
  mesh.
- **Belt: GT2, 6 mm, glass-fibre core, open length joined into a loop.** The pitch length is
  4 x 166.9 mm (the straight runs between pulleys) + one pulley circumference (80.0 mm) = 748 mm, or
  about 374 teeth.
  - A 180° turn moves the belt only **40 mm**, so a clamped joint (about 30 mm long) in one 167 mm
    straight run never reaches a pulley.
  - The joint clamp doubles as the tensioner (turnbuckle). No closed loop of this exact length needs
    to be found.
- **Servo: Feetech STS3215, 7.4 V version** (also sold as Waveshare ST3215). It is a serial bus servo:
  - About 19 kg·cm at 7.4 V, so about 4x the A4 wind estimate.
  - Magnetic encoder, 4096 counts per turn, 360° position range.
  - Half-duplex TTL UART on one data wire. It reports position, speed, load, voltage and temperature.
- **Calibration:** at 1:1 a 180° plate turn is 2048 counts.
  - Put plate 0° at about count 1024, so that 180° falls at about 3072, well away from the
    0/4095 wrap.
  - The counts for 0°, 90° and 180° are calibrated per unit and stored in config.
- **Speed:** firmware sets the servo's goal speed and acceleration so that 180° takes about 1 s. That
  gives a gentler current peak and less belt load.
- **Torque limit:** the servo's own torque-limit register caps the current. A4 plates need little
  torque, so the limit starts at about 50 % and is tuned in F1.

### Holding position

- **Magnetic detent on plate 1's pulley.** A magnet in the pulley face sits over steel screw heads
  in the deck at 0°, 90° and 180°. Because of the belt, it holds all four plates while the servo's
  torque is off. The servo easily overcomes it.
- **Holding policy (configurable):**
  - At 0° and 180°, the default is torque off after the move. The detent and the closed box (stable
    in wind) hold the plates.
  - At 90°, torque stays on: the "+" catches more wind.
- **Watch:** while a game runs, the servo stays powered (torque off is fine) and firmware reads its
  position once a second.
  - If a gust or a hand moves the plates more than 5° off target, torque goes on and the servo moves
    them back.
  - This replaces blind periodic re-positioning.
  - A low-power mode checks every 30 s instead, and switches the servo supply off in between.
- **Wind estimate** (not measured):
  - Wind torque scales with plate area times plate width. For A4 that is about a quarter of the
    320 x 500 mm plate's.
  - At 10 m/s, mid-turn, that gives about 0.25-0.5 N·m total (2.5-5 kg·cm).
  - Closed, the torque is near zero: the face-on plate is pushed square, and the edge-on plates see no
    load.
  - The STS3215 (about 19 kg·cm) leaves about 4x margin, even with the torque limit at 50 %. The
    field test confirms it (Open items).

### Position feedback

- **At boot,** firmware reads the real position, so nothing is stored in flash. Plates turned by hand
  are noticed, and the first move starts from where they actually are, at the ramped speed.
- **Jam detection:** firmware reads the servo's load during a move. If it stays above the limit for
  200 ms (a hand, a branch, ice), firmware stops the servo where it is, switches torque off and
  reports `JAM` to the LCD and HQ. It retries once after 2 s.
  - The servo's built-in overload protection is a second layer behind this.
- **Belt slip on plates 2-4 is not visible.** The encoder sees only plate 1. A skipped tooth leaves
  the plates crooked but cannot make them collide (11.5° tolerance against 9° per tooth, Part 1).
  - A hall sensor on plate 3 could confirm the closed positions. It would use one of the bridge's
    spare GPIOs, but needs two more wires up the pole, so it is left for later (Open items).

## Part 3: Head construction

```
   top cap  ─────────────────  608 bearings (4), corner posts screw in
   plates   ║  ║  ║  ║          4 x A4 (210 x 297 mm), slotted hubs top and bottom
   deck     ═════════════════  290 x 290 mm, 608 bearings (4), servo on plate 1
   belt     (under the deck)   40T pulleys, GT2 loop, detent, cover tray
   pole     │                  head socket onto the tube, cable inside or clipped
```

- **Plates:** a 3-4 mm corrugated PP (coroplast) core cut to 210 x 297 mm, with the flutes vertical.
  - **Faces:** a red A4 sheet on one side and a blue one on the other, laminated or printed on
    waterproof media and trimmed flush to the core (see the pouch row in Part 1).
  - Instead of plain colour, the faces can carry a team logo or a point letter. Swapping a face means
    swapping a sheet.
  - Each plate weighs about 50 g.
- **Hubs instead of a through-axle:** 3D-printed slotted hubs clamp the centre of each plate at the
  top and bottom edges, with 8 mm stub shafts in sealed 608-2RS bearings. A rod cannot pass through
  4 mm flutes, and the light plates carry the small torque from bottom to top on their own.
- **Drive deck:** a 290 x 290 mm plate with printed bearing blocks. It is cut from 8 mm HDPE or marine
  plywood, or printed in two halves: it is larger than a 256 mm print bed.
  - The belt, pulleys, detent and servo horn coupling sit under the deck in a shallow cover tray.
  - The servo hangs under plate 1's axle.
  - The deck sheds rain. Only the servo needs to be weatherproof (Open items).
- **Corner posts:** 4 x 14 mm aluminium tube (or 8 mm rod with printed sleeves) between the deck and
  the top cap. The top cap carries the four upper bearings and keeps rain off them.
- **Mounting:** a pole socket under the deck slides onto the tube and is locked with a bolt.
  - Pole: 2 m to the deck, in two 1 m sections with a joiner for transport.
  - Anchoring: ground spike plus three guy lines, or straps to a tree.
  - Plate tops end about 2.4 m above the ground.
- **Mass:** about 0.2 kg of plates plus 0.4-0.5 kg of deck, cap and servo, so 0.6-0.7 kg on the pole top.
- **Assembly indexing:** mark each plate and each pulley. Fit the belt with all four plates at 0°
  (red out), then calibrate.

A FreeCAD model (`hardware/mech/`, same flow as the enclosure) follows after the mock-up (milestone F0).

## Part 4: Base unit

The base unit is an AirsoftCounter in its usual enclosure, clamped to the pole at about 1 m with its
lid facing out. Any variant with **buttons and RFID** works (Deluxe, or Budget plus the rfid module).

### Added parts (off-board, no carrier change)

| Part | Where | Purpose |
|---|---|---|
| SC16IS750 I2C-to-UART module (14.7456 MHz crystal) | On the 3V3 I2C bus, chained between `J_NFC1` and the PN532 | UART for the servo, plus 8 GPIOs (GPIO0 = servo boost enable) |
| 74LVC1G126 tri-state buffer + 10k pull-up on the data line | Small perfboard next to the bridge | Joins TX and RX onto the servo's single data wire; the bridge's RTS enables the buffer while it transmits |
| 100k pull-down on the boost EN line | Same perfboard | The bridge's GPIOs come up as inputs, so the boost stays off until firmware drives GPIO0 |
| Boost module, 3.0-4.2 V in, 7.4 V out, ≥ 2 A, with an EN pin | In the base box | Servo supply. Must not load the pack's 5 V MT3608, which feeds the LCD |
| 1 A polyfuse in the 7.4 V servo line | In the base box | Backs up the servo's torque limit |
| Y-lead on the pack-to-carrier harness | `J_PWR1` cable | Takes `VBAT_SW` and GND for the boost |
| 3-pin weatherproof connector (e.g. GX16-3) + cable gland | Base box wall | Head detaches for transport |
| 3-core outdoor cable, 0.5 mm² (≈ 2.5 m) | Up the pole | 7.4 V, GND, DATA. At 1 A the drop is about 0.2 V |

Why this split:

- **GPS stays.** The flag device keeps its L76K on UART1 and the Heltec GNSS connector, unchanged.
- **No spare native UART pin is reachable.** GPIO43/44 (UART0) are not routed on this carrier
  revision, and GPIO43 prints the boot log at power-up. The bridge adds a UART over I2C instead.
- **Half-duplex in hardware.** In its RS-485 mode the bridge drives RTS on every transmit, and RTS
  enables the buffer, so firmware never times the direction switch.
- **115200 baud.** The 14.7456 MHz crystal divides exactly to 115200. The servo ships at 1 Mbaud and
  is set to 115200 once, on the bench (its baud register is in EEPROM). A 10 Hz poll of position and
  load is a few hundred bytes per second, easy over the 50 kHz I2C bus.
- **Powers up safe.** Boost EN is pulled down and the bridge's GPIOs reset to inputs, so the servo
  has no power until firmware enables it.
- **The bridge and boost stay in the base box**, which is easier to service. Only the standard
  3-wire bus-servo cable goes up the pole.
- **I2C does not go up the pole.** About 2 m of cable carrying servo current next to a 50 kHz bus
  would be fragile.

### I2C addresses

SC16IS750 at **0x4C**, set with the module's A0/A1 jumpers. The chip's range is 0x48-0x57, and 0x48
is taken by the ADS1115.

No clash with the carrier bus: 0x10 PAC1934 (pack-internal), 0x20 expander, 0x24 PN532, 0x28 LCD,
0x30 pack MCU, 0x48 ADS1115.

### Power

| Load | Battery-side estimate |
|---|---|
| SC16IS750 + buffer | ~2 mA |
| Boost + servo powered, torque off (watch mode) | ~20-35 mA |
| Servo move (~0.4 A at 7.4 V for ~1 s) | ~1 A peak; ~9 mA average at 30 moves/h |
| Servo holding at 90° with torque on (contested) | +10-30 mA while held, depending on wind |

That is about 30-70 mA on top of the counter's budget. The counter models 74-236 mA, so the
350 mA weekend target still holds, but with little margin if the backlight is always on. Low-power
watch mode (Part 2) cuts the second row to a few mA.

These rows are added to `power_budget.py` in milestone F1, and the real values are measured there.
The pack's 2 A path has to carry a servo peak plus LoRa TX: check this in F1 (Open items).

## Part 5: Firmware

### Device

- **Detection:** the bridge is probed at 0x4C at boot, like the other modules: write and read back
  its scratchpad register. If found, firmware powers the servo and pings it.
  - If the servo answers, the `flag` task starts and the domination mode becomes selectable. No new
    cargo feature is needed.
  - If the bridge answers but the servo does not, firmware reports `NO SERVO` (LCD and STATUS).
- **Servo protocol in `core` (`core::sts`):** packet encode and decode, checksum, and the few
  registers used (torque enable, acceleration, goal position, goal speed, torque limit, present
  position, load, voltage, temperature, moving).
  - It is pure and host-tested, like `core::card`.
  - Register addresses come from the Feetech STS memory table: check them against the servo in F1.
- **`flag` task** (device crate), the only owner of the bridge:
  1. Enable the boost (bridge GPIO0) and wait about 200 ms for the servo to start. Ping it.
  2. Read the present position and write it as the goal, then enable torque. The servo holds where
     it is instead of jumping.
  3. Write the goal speed and acceleration (180° in about 1 s), then the target position.
  4. Poll position and load at 20 Hz until the servo reports it has stopped moving. Too much load for
     200 ms means a jam (Part 2).
  5. Hold for 300 ms, then apply the holding policy: torque off at 0° and 180°, torque on at 90°.
  6. Watch mode (Part 2): poll once a second and correct drift above 5°.
  - If a new target arrives mid-move, it simply becomes the new goal position.
- **Calibration:** the encoder counts for 0°, 90° and 180°, the torque limit, the holding policy and
  the watch mode are in config.
  - They are edited on the WiFi config page, which has live "move to" buttons and a read-out of the
    current count.
  - A one-time "prepare servo" button sets a new servo's ID and its baud rate to 115200. The bridge
    first talks to it at 1 Mbaud: with the 14.7456 MHz crystal that is not an exact divisor, so check
    it in F1, or prepare the servo once with Feetech's USB adapter.

### `core`: new domination mode (`core::domination`)

The original Arduino code only named a domination mode (`GameType::DOMINATION`) and never implemented
it. The new mode is pure logic like `core::game`: time in, effects out, host-tested.

- **Config:** capture time (s, default 5), game length (min, 0 = unlimited), target hold time
  (min, 0 = none).
- **Phases:** `Intro`, `Neutral` (no owner), `Owned(team)`, `Capturing { team, until, owner }`, `Ended`.
- **Capturing:**
  - Hold your team's button, or **keep your player card on the reader** (the PN532 poll sees it
    present), for the capture time. A beep sounds every second.
  - Letting go cancels and returns to the previous owner.
  - The other team pressing during a capture cancels it too.
  - A card capture credits the player id, which goes to HQ as an ACKed event like Airsoftcoin
    captures.
- **Scoring:** the owner gains hold time every second. The game ends at the game length or when a team
  reaches the target. The winner is the team with more hold time.
- **Flag output:** a new effect, `Flag::{Red, Neutral, Blue}`.

| Phase | Flag |
|---|---|
| Intro, Neutral | Neutral |
| Owned(team) | team |
| Capturing | **Neutral**: from far away the point visibly comes under attack |
| Ended | winner, Neutral on a draw |

- **LCD** (Polish, like the Airsoftcoin screens): `Czerwoni 12:34` / `Niebiescy 08:10` /
  `PUNKT: CZERWONI` or `PRZEJMOWANIE 3s` / `Pozostalo 45:00`.
- **Airsoftcoin on the flag device:** the flag shows the team in the lead, and Neutral on a tie. This
  is one mapping function, no game change.

### LoRa protocol

- **STATUS** gains the flag position as measured (red, neutral, blue, moving), a flag fault (`JAM`,
  `NO SERVO`, servo over-temperature or under-voltage) and both hold times.
- **New command `FLAG` (HQ → device):** force red, neutral or blue, or `AUTO` to give control back to
  the game. It is ACKed and retried like the others, and the override shows on the LCD.

## Milestones

- **F0 Mechanical mock-up.** Deck, four plates, belt and a hand-turned pulley. Check:
  - the clearances against Part 1 (1:1 printed template);
  - belt tension and the joint;
  - detent strength;
  - how it looks at 50 m and 100 m.
- **F1 Servo bench.** SC16IS750 + buffer + boost + STS3215 on a working carrier. Covers:
  - half-duplex comms through the bridge, setting the baud rate and ID;
  - checking the register map;
  - the move sequence, calibration and the torque limit;
  - current at the battery during moves, watch, holding and a forced jam;
  - the pack's 2 A path with LoRa TX at the same time;
  - the `power_budget.py` rows.
- **F2 `core::domination` and `core::sts`** with host tests, plus the flag mapping for both modes.
- **F3 Device integration:** probe, `flag` task (watch mode, jam handling), config and the WiFi
  calibration page.
- **F4 LoRa:** STATUS fields and the `FLAG` command.
- **F5 Field test:** wind, rain, a full weekend on one charge, visibility.
- **F6 FreeCAD model** of the head in `hardware/mech/`.

Out of scope for now: LED lighting for night games (a strip along the corner posts is the obvious
place), a belt-slip hall sensor on plate 3, a second head driven by one base unit (bus servos can share
one wire with different IDs, so this is mostly a mechanical question).

## Open items

- STS3215: no waterproof version, so it needs a cover under the deck. Check stall current at the
  chosen torque limit, idle current with torque off, and that the encoder count survives power cycles
  (absolute, not counted from power-up).
- Servo data-line levels: check that 3.3 V logic from the buffer works with the STS3215. If the line
  needs 5 V, power the buffer from 5 V and divide the RX side down.
- SC16IS750 module: crystal frequency, A0/A1 jumper options for 0x4C, whether RTS and the GPIOs are
  brought out, the RS-485 direction setting (EFCR), and the RTS polarity against the buffer's OE.
- Boost module: pick a type with an EN pin, ≥ 2 A at 7.4 V from 3.0 V input, and low quiescent current
  when off.
- The pack's 2 A path (PTC on the pack board) with a servo peak plus LoRa TX plus audio.
- Wind torque against the servo and detent: measure in F0/F5. Decide whether 90° needs the servo
  powered all the time.
- How strong the magnetic detent should be (magnet size) without stalling a ramped move.
- Mass and stiffness of the 2 m pole with 0.7 kg on top; the guy-line layout.
- I2C chain from `J_NFC1` (GND, 3V3, SDA, SCL) through the bridge module to the PN532: header order
  and whether the bridge module brings its own pull-ups (remove them; the carrier has 4.7k).
- How far an A4 face reads as red or blue (check at 30 / 50 / 80 m in F0), and whether the 13 mm
  corner gaps need cover strips. If A4 is too small in the field, use the A3 upgrade path (Part 1).
- Face material: laminated paper against printed PP or vinyl, for rain and UV over a season.
- Hall sensor on plate 3 for belt slip: one of the bridge's spare GPIOs, plus 3V3 and signal wires up
  the pole (a 5-core cable instead of 3-core).
