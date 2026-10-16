# Rotating flag: four-plate team flag with a base unit

Date: 2026-10-16
Status: concept approved (3D preview reviewed), not started. Numbers marked "computed" come from the
clearance script described in Part 1; everything under "Open items" is unverified.

3D preview (animated, private artifact): https://claude.ai/artifact/L14upVzvEwPNHU4F415VkW

## Goal

A new device for domination-style games: a **flag head on a 2 m pole** that shows which team holds
the point, readable from every direction and from far away, plus a **base unit** on the same pole
where players capture the point with buttons or player cards.

- The head shows **red, blue or neutral** to everybody at once: no direction may see a different colour.
- It is **passive**: it reads in full sun and holds its colour without power, unlike LEDs.
- The base unit is an **AirsoftCounter** (same carrier, pack board, LCD, buttons, PN532, speaker,
  LoRa, firmware core) with one servo driver module added. No carrier respin.
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

### Dimensions

| Item | Value |
|---|---|
| Square side (axle to axle across) | 360 mm (axles 180 mm from the centre) |
| Plate | 320 x 500 mm, 4 mm thick |
| Colour coverage per side when closed | 320 / 360 = 89 % |
| Swing past each side | 160 mm (half a plate) |
| Plate ends at 90° | 20 mm from the centre |

The plate width was chosen with a 2D clearance check (plates as 8 mm thick segments, 14 mm corner
posts, 0.25° steps, computed):

| Plate width | Min. gap, plates in step | Gap to corner post | Max. step error before plates touch |
|---|---|---|---|
| 330 mm | 13.2 mm | 4.0 mm | 6.5° |
| **320 mm** | **20.3 mm** | **9.0 mm** | **10.5°** |
| 300 mm | 34.4 mm | 19.0 mm | 20.5° |

320 mm tolerates a step error of 10.5°, which is more than one tooth (9°) on the 40T pulleys of Part 2.
So a single skipped tooth cannot make the plates collide.

**No centre mast.** At 90° the plate ends come within 20 mm of the centre, so nothing can pass
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
  4 x 254.6 mm (the straight runs between pulleys) + one pulley circumference (80.0 mm) = 1098 mm, or
  549 teeth.
  - A 180° turn moves the belt only **40 mm**, so a clamped joint in one 254 mm straight run never
    reaches a pulley.
  - The joint clamp doubles as the tensioner (turnbuckle). No closed loop of this exact length needs
    to be found.
- **Servo:** a 20-25 kg·cm metal-gear digital servo with **270°** travel, PWM 500-2500 µs, 6 V (for
  example the DS3218MG 270°; check waterproofing). At 1:1, a 180° plate turn uses 2/3 of its range.
  The pulse widths for 0°, 90° and 180° are calibrated per unit and stored in config.
- **Speed:** firmware ramps the pulse so that 180° takes about 1 s. That gives a gentler current peak
  and less belt load. Full servo speed would be about 0.5 s.

### Holding position

- **Magnetic detent on plate 1's pulley.** A magnet in the pulley face sits over steel screw heads
  in the deck at 0°, 90° and 180°. Because of the belt, it holds all four plates when the servo is
  unpowered. The servo easily overcomes it.
- **Holding policy (configurable):**
  - At 0° and 180°, the default is to switch the servo off after the move. The detent and the closed
    box (stable in wind) hold the plates.
  - At 90°, the servo stays powered: the "+" catches more wind.
- **Re-assert:** while the servo is unpowered, firmware powers it for 0.5 s every 60 s at the current
  pulse, to undo a gust. The interval is configurable; 0 turns it off.
- **Wind estimate** (not measured): at 10 m/s, mid-turn, about 0.5 N·m per plate and 1-2 N·m total,
  which is 10-20 kg·cm. Closed, the torque is near zero (the face-on plate is pushed square, the
  edge-on plates see no load). A 20-25 kg·cm servo covers the forest case; open fields with strong
  gusts need the field test (Open items).

### No position feedback

A hobby servo reports nothing back. Firmware tracks the last commanded position and stores it in
flash, so a reboot does not sweep the plates. If someone turns the plates by hand while the servo is
off, the next power-up moves them back at full speed. Accepted for v1. A hall sensor on plate 1 is a
possible later addition (Open items).

## Part 3: Head construction

```
   top cap  ─────────────────  608 bearings (4), corner posts screw in
   plates   ║  ║  ║  ║          4 x 320 x 500 mm, slotted hubs top and bottom
   deck     ═════════════════  420 x 420 mm, 608 bearings (4), servo on plate 1
   belt     (under the deck)   40T pulleys, GT2 loop, detent, cover tray
   pole     │                  head socket onto the tube, cable inside or clipped
```

- **Plates:** 4 mm corrugated PP (coroplast), with the flutes vertical. Use a red sheet with blue
  vinyl on the other face, or two 2 mm sheets glued back to back. About 105 g each.
- **Hubs instead of a through-axle:** 3D-printed slotted hubs clamp the centre of each plate at the
  top and bottom edges, with 8 mm stub shafts in sealed 608-2RS bearings. A rod cannot pass through
  4 mm flutes, and the light plates carry the small torque from bottom to top on their own.
- **Drive deck:** a 420 x 420 mm plate (8 mm HDPE or marine plywood, too large to 3D-print in one
  piece) with printed bearing blocks.
  - The belt, pulleys, detent and servo horn coupling sit under the deck in a shallow cover tray.
  - The servo hangs under plate 1's axle.
  - The deck sheds rain. Only the servo needs to be weatherproof (Open items).
- **Corner posts:** 4 x 14 mm aluminium tube (or 8 mm rod with printed sleeves) between the deck and
  the top cap. The top cap carries the four upper bearings and keeps rain off them.
- **Mounting:** a pole socket under the deck slides onto the tube and is locked with a bolt.
  - Pole: 2 m to the deck, in two 1 m sections with a joiner for transport.
  - Anchoring: ground spike plus three guy lines, or straps to a tree.
  - Plate tops end about 2.6 m above the ground.
- **Mass:** about 0.4 kg of plates plus 0.6-0.8 kg of deck, cap and servo, so 1.0-1.2 kg on the pole top.
- **Assembly indexing:** mark each plate and each pulley. Fit the belt with all four plates at 0°
  (red out), then calibrate.

A FreeCAD model (`hardware/mech/`, same flow as the enclosure) follows after the mock-up (milestone F0).

## Part 4: Base unit

The base unit is an AirsoftCounter in its usual enclosure, clamped to the pole at about 1 m with its
lid facing out. Any variant with **buttons and RFID** works (Deluxe, or Budget plus the rfid module).

### Added parts (off-board, no carrier change)

| Part | Where | Purpose |
|---|---|---|
| PCA9685 16-channel PWM module | On the 3V3 I2C bus, chained between `J_NFC1` and the PN532 (the modules have pass-through headers) | ch0 = servo pulse, ch1 = servo boost enable (full on/off) |
| Boost module, 3.0-4.2 V in, 6.0 V out, ≥ 2 A, with an EN pin | In the base box | Servo supply. Must not load the pack's 5 V MT3608, which feeds the LCD |
| 1 A polyfuse in the 6 V servo line | In the base box | Limits a jammed servo |
| Y-lead on the pack-to-carrier harness | `J_PWR1` cable | Takes `VBAT_SW` and GND for the boost |
| 3-pin weatherproof connector (e.g. GX16-3) + cable gland | Base box wall | Head detaches for transport |
| 3-core outdoor cable, 0.5 mm² (≈ 2.5 m) | Up the pole | 6 V, GND, PWM. At 1 A the 6 V drop is about 0.2 V |

Why this split:

- **No spare native GPIO is reachable.** GPIO43/44 are not routed on this carrier revision, and GPIO43
  toggles at boot (the plates would twitch).
- **The PCA9685 powers up safe.** After reset it is asleep with every output low, so the boost stays
  off and the servo gets no pulse until firmware has set the right pulse.
- **The boost and PWM stay in the base box**, which is easier to service, and only a standard
  3-wire servo signal goes up the pole.
- **I2C does not go up the pole.** About 2 m of cable carrying servo current next to a 50 kHz bus
  would be fragile.

### I2C addresses

PCA9685 at **0x40** (all address pins low). Firmware clears ALLCALL in MODE1, so 0x70 is not used.
No clash with the carrier bus: 0x10 PAC1934 (pack-internal), 0x20 expander, 0x24 PN532, 0x28 LCD,
0x30 pack MCU, 0x48 ADS1115.

### Power

| Load | Battery-side estimate |
|---|---|
| PCA9685 awake | ~6 mA (asleep: µA) |
| Servo move, ramped (~0.5 A at 6 V for ~1 s) | ~1 A peak; ~9 mA average at 30 moves/h |
| Servo holding at 90° (contested) | ~25 mA while held |
| Re-assert pulses (0.5 s every 60 s) | ~5 mA |

That is about 20-40 mA on top of the counter's budget, so the 350 mA weekend target still holds
(the counter models 74-236 mA). These rows are added to `power_budget.py` in milestone F1, and the
real values are measured there. The pack's 2 A path has to carry a servo peak plus LoRa TX: check
this in F1 (Open items).

## Part 5: Firmware

### Device

- **Detection:** the PCA9685 is probed at 0x40 at boot, like the other modules. If found, the `flag`
  task starts and the domination mode becomes selectable. No new cargo feature is needed.
- **`flag` task** (device crate), the only owner of the PCA9685:
  1. Write the **current** position's pulse to ch0, then wake the chip (prescale 121 = 50 Hz,
     totem-pole outputs, ALLCALL off).
  2. Turn on the boost (ch1 full on) and wait 100 ms. The servo holds where it is instead of jumping.
  3. Ramp the pulse to the target (180° in about 1 s), then hold for 300 ms.
  4. Depending on the holding policy, switch the boost off and put the chip to sleep, or stay powered.
  5. Store the new position in config (sequential-storage).
  - If a new target arrives mid-move, it replaces the old one and the ramp continues from the current
    pulse.
- **Calibration:** pulse widths for 0°, 90° and 180°, the holding policy and the re-assert interval
  are in config. They are edited on the WiFi config page, with live "move to" buttons.

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

- **STATUS** gains the flag position (red, neutral, blue, moving) and both hold times.
- **New command `FLAG` (HQ → device):** force red, neutral or blue, or `AUTO` to give control back to
  the game. It is ACKed and retried like the others, and the override shows on the LCD.

## Milestones

- **F0 Mechanical mock-up.** Deck, four plates, belt and a hand-turned pulley. Check:
  - the clearances against Part 1 (1:1 printed template);
  - belt tension and the joint;
  - detent strength;
  - how it looks at 50 m and 100 m.
- **F1 Servo bench.** PCA9685 + boost + servo on a working carrier. Covers:
  - the move sequence and calibration;
  - current at the battery during moves, holding and stall;
  - the pack's 2 A path with LoRa TX at the same time;
  - the `power_budget.py` rows.
- **F2 `core::domination`** with host tests, plus the flag mapping for both modes.
- **F3 Device integration:** probe, `flag` task, config and WiFi calibration page.
- **F4 LoRa:** STATUS fields and the `FLAG` command.
- **F5 Field test:** wind, rain, a full weekend on one charge, visibility.
- **F6 FreeCAD model** of the head in `hardware/mech/`.

Out of scope for now: LED lighting for night games (a strip along the corner posts is the obvious
place), position feedback, a second head driven by one base unit.

## Open items

- Servo: a 270° 20-25 kg·cm model that is waterproof, or a cover for it under the deck. Check the
  real pulse range and the travel at 500-2500 µs.
- Boost module: pick a type with an EN pin, ≥ 2 A at 6 V from 3.0 V input, and low quiescent current
  when off.
- The pack's 2 A path (PTC on the pack board) with a servo peak plus LoRa TX plus audio.
- Wind torque against the servo and detent: measure in F0/F5. Decide whether 90° needs the servo
  powered all the time.
- How strong the magnetic detent should be (magnet size) without stalling a ramped move.
- Mass and stiffness of the 2 m pole with 1.2 kg on top; the guy-line layout.
- PCA9685 module pass-through header order against the PN532 cable (`J_NFC1`: GND, 3V3, SDA, SCL).
- Visibility of an 89 %-covered face at 100 m, and whether the corner gaps need cover strips.
- Hall sensor on plate 1 for position feedback: needs an input, and none is free on this carrier
  revision.
