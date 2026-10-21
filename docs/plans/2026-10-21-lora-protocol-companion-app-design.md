# LoRa protocol, companion device and Android app

Date: 2026-10-21
Status: design approved, implementation plan not written yet.
Replaces the "Radio protocol" section and milestone 7 (HQ USB-serial bridge) of
`2026-09-28-esp32-lora-carrier-design.md`. Numbers marked EST are guesses until measured.

## Goal

- Field devices (Airsoftcoin counters, the rotating flag, later respawn points, bombs, ...) report to
  and are controlled from **one organizer phone**.
- The phone talks **BLE** to a **companion**: a Heltec V4 (display build) that bridges to LoRa.
- **Star with a 1-hop relay**: 1-2 devices marked as relays repeat frames for devices out of reach.
- Up to **~10 field devices** per game; the address space allows 254.
- App v1: live device list, game control, GPS map (offline), capture log + per-player stats + export.
- Every device keeps a **persistent event log** in flash; the game can be replayed from it, and gaps
  are filled over LoRa.
- Games keep running on the devices when the radio, companion or phone is gone. The radio only
  reports and commands.

## Decisions (and what was rejected)

| Topic | Chosen | Rejected |
|---|---|---|
| Companion link | V4 + BLE GATT | USB-OTG serial (cable), WiFi AP (phone loses internet, more power), Meshtastic (fights game control) |
| Topology | Star + 1-hop relay | Single star (range), several companions (command authority) |
| Channel access | CAD listen-before-talk + configured relays (A) | Companion polling (events wait, nothing moves without the companion), GPS TDMA (two MAC modes) |
| App | Kotlin + Compose, hand-written codec + shared golden vectors | Rust core via uniffi (NDK build), Flutter |
| Keys | App generates; typed into each device's WiFi page; companion gets it over BLE in a setup window | LoRa pairing (sniffable), compiled-in key |
| Full log dump | LoRa only (`LOG_GET`) | WiFi page download, BLE on every device |
| Companion off | PRG soft off (deep sleep) + inline hard switch | Hard switch only |

## Part 1: Architecture and LoRa frame

```
 Android app ──BLE GATT──> Companion (V4 + OLED) ──LoRa 869.525──> field devices (counter, flag, ...)
 (UI, game log,           (crypto, ctr, retries,                   (game runs locally; flash log;
  map, key gen)            dedupe, buffering)                       reports + takes commands)
                                                     ▲
                                        relay device(s) forward hop-0 frames once
```

Code layout:

- `firmware/core/src/proto.rs`: frame codec, AES-CCM, replay window, dedupe, airtime tracker, retry
  state, relay decision, log record. no_std, host-tested.
- `firmware/device/src/bin/companion.rs`: companion binary in the device crate (reuses `board.rs` and
  the radio setup).
- `android/`: the app.
- `docs/protocol.md`: the living wire spec (this doc stays the historical design record).
- `proto/vectors.json`: golden vectors shared by the Rust and Kotlin tests.

Radio: 869.525 MHz (g3 sub-band, 10 % duty, ≤ 500 mW ERP), SF9, BW125, CR4/5, explicit header, CRC on,
8-symbol preamble. TX power from config (default 20 dBm, capped so ERP ≤ 27 dBm). Every node, relays
included, keeps a rolling 1 h airtime tracker and never exceeds 10 %.

### Frame (little-endian)

| Bytes | Field | Notes |
|---|---|---|
| 1 | `net_id` | cheap filter before any crypto |
| 1 | `hop` | 0 = original, 1 = relayed. **Not authenticated**, so relays never re-encrypt |
| 1 | `src` | 0 = companion, 1-254 = devices |
| 1 | `dst` | 0 = companion, 0xFF = all |
| 4 | `ctr` | per-sender frame counter |
| 1 | `type` | message class (7 bits) + ACK-request bit 0x80 |
| n | payload | AES-CCM encrypted |
| 4 | tag | CCM MIC |

Overhead 13 B. Max LoRa payload 255 B.

- **Crypto:** AES-128-CCM, one network key. Nonce = `net_id | src | ctr`, zero-padded to 13 B. AAD =
  header without `hop`. A 4 B tag is ~1 in 4·10⁹ per forgery try against a duty-limited channel
  (LoRaWAN uses the same MIC size).
- **Replay window:** per `src`, highest `ctr` + 32-bit bitmap (relayed copies arrive out of order).
  It also drops relay duplicates, since a relay keeps `ctr` unchanged.
- **Counter persistence:** senders save `ctr` every 256 frames and skip ahead 256 on boot (LoRaWAN
  style), plus on clean shutdown. Devices also persist the companion's last accepted `ctr` (commands
  are rare), so an old START cannot be replayed after a device reboot.

### Device kinds and extensibility

`type` is the message class only (~11 used of 128). Device and event kinds live in the payload:

- STATUS starts with `kind u8` (counter, flag, respawn, bomb, ...).
- EVENT records carry `event u8` (capture, block mined, flag captured, respawn used, ...).
- CONFIG carries `(param_id u8, value i32)` pairs: ids 0-31 common to all kinds, 32+ kind-specific.

The companion forwards STATUS / EVENT / LOG / CONFIG by class and never parses kind-specific bytes, so a
**new device kind needs no companion update**: only its firmware and the app's kind table.

## Part 2: Message catalogue

Airtime at SF9 / 125 kHz (SF10 in brackets).

### Device → companion

| type | Payload | Frame | Airtime |
|---|---|---|---|
| `STATUS` | common 20 B + kind tail | 39 B (counter, flag) | 267 ms (494) |
| `EVENT` (ACK req) | `game_id u16` + log record 14 B | 29 B | 226 ms (412) |
| `ACK` | `acked_ctr u32, result u8, detail u8` | 19 B | 185 ms (330) |
| `LOG` (answers `LOG_GET`) | `game_id u16` + up to 16 log records | ≤ 239 B | ≤ 1189 ms (2132) |

STATUS common part (20 B): `kind u8 · state u8 · flags u8 · batt_mV u16 · game_s u16 · lat i32 ·
lon i32 · gps_age_s u8 · rssi i8 · snr i8 · last_event_id u16`

- `state`: idle / ready / running / ended / fault. `flags`: relay on, GPS fix, low battery, fault.
- `lat`/`lon` in 1e-7 °. `rssi`/`snr` = last companion frame as heard by the device; the companion adds
  its own reading when forwarding, so the app has both directions.
- `last_event_id` lets the app see lost events at the **tail** of the log (nothing later arrives to
  reveal the hole).

Kind tails: counter `red u16 · blue u16 · left u16`; flag `pos u8 · fault u8 · red_hold_s u16 ·
blue_hold_s u16`.

`ACK.result`: ok, busy (`detail` = retry seconds), bad_param (`detail` = first unknown id),
unknown_type.

### Companion → device (all ACK requested)

| type | Payload | Frame | Airtime |
|---|---|---|---|
| `PING` | none; answered by STATUS instead of ACK | 13 B | 165 ms |
| `START` | `game_id u16, start_in_ms u32, mode u8` | 20 B | 185 ms |
| `STOP`, `RESET` | none | 13 B | 165 ms |
| `CONFIG` | up to 8 × `(param_id u8, value i32)` | ≤ 53 B | ≤ 329 ms |
| `FLAG` | R / N / B / AUTO | 14 B | 165 ms |
| `LOG_GET` | `game_id u16, from_id u16, count u8` | 18 B | 185 ms |

- Relay on/off, TX power and STATUS interval are common CONFIG params (no SET_RELAY message).
- **START is unicast per device**, not broadcast (10 ACKs to one broadcast collide). The companion
  sets `start_in_ms = T − now` on every attempt, so all devices start together (± ~50 ms) however long
  delivery takes.
- STATUS every 30 s (configurable) plus one jittered STATUS right after a state change, min 5 s apart.

### Channel load

10 devices × 267 ms / 30 s ≈ 8.9 %, relay copies of about half ≈ +4.5 %, events and ACKs a few
tenths: **≈ 14 % of the channel**. Per device ~1 % of its own 10 %, a relay ~5 %. At SF10 raise the
STATUS interval to 60 s for the same load.

## Part 3: Device event log

- **Every state change is an EVENT, appended to flash before it is sent:** START, STOP, RESET, config
  changes, captures, blocks mined, flag moves, power-on/reboot, low battery, faults (JAM), admin card
  actions, shutdown. Replaying a game's records from the first rebuilds the game; the app folds them
  and checks the result against STATUS.
- **Record (14 B, identical in flash and on air):** `event_id u16 · t_ms u32 · event u8 · team u8 ·
  player u16 · extra[4]`. In flash a CRC (and padding to 16 B) is added.
- **Game identity:** START carries `game_id` (assigned by the app). The device logs a `GAME_START`
  record with `game_id` and GPS UTC when it has a fix, anchoring the relative `t_ms`. `event_id`
  restarts at 1 per game; `(dev, game_id, event_id)` is globally unique.
- **Persistent:** a dedicated flash partition (256 KB ≈ 16 000 records), append-only ring. Survives
  reboots, crashes and battery swaps. Records go only when the ring wraps (oldest first) or on an
  explicit "Wyczyść log" in the admin menu (admin card). STOP and RESET never clear it; older games stay
  readable by `game_id`.
- **Power cuts:** each record is written immediately; at most the record being written is lost. On
  boot the device scans the log, ignores a torn last record and resumes the game, its clock and the
  next `event_id`, then logs a `REBOOT` event.
- **Wear:** 64 sectors of 4 KB, each erased once per ~16 000 records; negligible against ~100 k cycles.
- **Storage code:** `sequential-storage`'s `queue` (already in the stack for config): CRC-checked,
  append-only; pop-before-push when full. Verify its iterate-without-pop API in the plan before
  writing anything custom.
- **Lookup:** `LOG_GET` scans for `(game_id, from_id)`. `ponytail:` linear scan of ~16 000 records,
  add a RAM index of sector start ids if it is slow.

### Gap-fill and full dumps (LoRa only)

| LOG frame | Size | Airtime | 1000 events: airtime | wall time at 10 % |
|---|---|---|---|---|
| 8 records | 127 B | 677 ms | 85 s | ~14 min |
| 16 records (chosen) | 239 B | 1189 ms | 74 s | ~12 min |

A typical game is a few hundred events per device, so a full dump is ~3-4 min per device.

- **Stop-and-wait:** one `LOG_GET` in flight; the `LOG` reply is its ACK.
- **Lowest priority:** a device answers `LOG_GET` only while its hourly airtime is under 7 %; 3 % stays
  reserved for STATUS / EVENT / ACK. Otherwise it replies `ACK{busy, retry_s}`.
- **Pacing:** the companion runs one dump at a time; the app shows progress. Gap-fills of small holes
  run during a game; the app suggests full dumps after STOP. Relayed devices cost double airtime; the
  app shows the longer ETA.

## Part 4: Reliability and relay rules

Channel access (all nodes):

- **CAD before every TX** (~8 ms at SF9). Busy: random 100-600 ms backoff, up to 8 tries. A STATUS
  that still cannot go is dropped (the next replaces it); anything else is requeued.
- **The airtime tracker has the last word:** a frame that would exceed 10 % (7 % for LOG) waits.

ACKs and retries:

- The receiver ACKs after CAD + random 20-100 ms.
- **ACK timeout 2.5 s fixed** (worst path: frame → relay delay → copy → ACK → relay delay → copy
  ≈ 1.5 s + slack).
- **Commands:** 4 attempts, backoff 2 / 4 / 8 s + jitter, then `RESULT{timeout}` to the app.
- **EVENTs:** retried forever, backoff doubling 2 s → 60 s cap. RAM queue of 32; on overflow the newest
  stay only in flash and gap-fill brings them. **A capture is never lost, only late.**
- **A retry is a new frame with a new `ctr`** (the same `ctr` would hit the replay window and never be
  re-ACKed if only the ACK was lost). The sender accepts an ACK for any `ctr` of its attempts.
- **All handlers are idempotent:** `START{game_id}` for the running game just ACKs; STOP, RESET,
  CONFIG, FLAG, LOG_GET repeat harmlessly; EVENTs dedupe on `(dev, game, event_id)`.

Relay rules (CONFIG `relay = 1`):

- Forward when `net_id` matches, `hop = 0`, the tag is valid, `src` and `dst` are not the relay, and the
  frame is new to its replay window.
- Set `hop = 1`, wait random 50-300 ms, CAD, send.
- **Suppression:** if another relay's `hop = 1` copy of the same `(src, ctr)` is heard during the wait,
  cancel.
- Relayed copies keep `ctr`, so every node's replay window drops the second copy.
- `ponytail:` a relay forwards everything (≈ 14 % load at 10 devices); add a per-relay src/dst
  allowlist if load grows.

Degraded modes:

| Situation | Behaviour |
|---|---|
| Companion out of range / off | Games run on. STATUS keeps its schedule. EVENT retries slow to 60 s. On return the queue drains and gap-fill closes holes. |
| Phone disconnected from companion | The companion still ACKs on LoRa and buffers frames for the app (RAM ring, 512 entries); replays on reconnect. Overflow is recovered by gap-fill. |
| Companion reboots | Replay windows reset (first frame per `src` accepted). Own `ctr` resumes with skip-ahead. Devices still reject replayed commands (persisted companion `ctr`). |
| Device reboots mid-game | Resumes from the flash log, sends a `REBOOT` event. |

RX: devices listen continuously (~5 mA SX1262). `ponytail:` SX1262 duty-cycled RX needs a longer
preamble; consider it in carrier task C8 if `power_budget.py` says the weekend is tight.

## Part 5: Companion

### Hardware

- Heltec WiFi LoRa 32 **V4 with OLED** (SSD1306 128×64), LiPo or a single 18650 on the SH1.25 battery
  socket, charged over USB-C.
- **Inline hard switch** in the cell's + lead (≥ 2 A DC: TX at 27 dBm peaks ~1 A, so 0.5 A SS12D07-class
  slides are too small; part picked in the plan). OFF = 0 µA, for storage, transport and a firmware hang
  RST does not cure. OFF with USB in: the board runs from USB but **does not charge** (cell
  disconnected). Normal use: leave it ON, use the PRG soft off.
- Housing: a stock Heltec V4 case with the switch in a drilled hole for now. `Skipped:` a printed case
  (can reuse the `mech/` P2S flow).
- Onboard LED: slow blink = no phone, steady = phone authenticated, fast blink = setup window.
- **Verify on the V4.3 schematic:** OLED pins (SDA/SCL/RST) and that the OLED is on `Vext` (firmware cuts
  it to 0 mA); the 5.1 k CC pull-downs on USB-C (without them a C-to-C cable from a power bank gives
  nothing; USB-A-to-C always works).

### Buttons

| Action | Effect |
|---|---|
| **On:** PRG (or RST) | Wake from deep sleep (GPIO0 is an RTC pin, ext0 wake; Meshtastic does this on Heltec boards) |
| PRG short | Wake the OLED / next page |
| **PRG hold 3 s, any page but Setup** | **Off:** `Wyłączanie… 3 2 1` (release cancels), `SHUTDOWN` event to the app, save `ctr`, Vext + SX1262 off, deep sleep (20 µA) |
| PRG hold 3 s on the Setup page | Open the 60 s setup window. The footer says what holding does on each page (`przytrzymaj: WYŁĄCZ` / `przytrzymaj: SETUP`) |
| RST | Hard reboot |

- **Firmware UVLO:** the V4 has no UVLO. Below 3.45 V: `BATERIA!`, `SHUTDOWN{low_batt}`, deep sleep. At
  20 µA a cell with ~5 % left takes about a year to empty.
- Charging while soft-off works (CN3165 charges on its own; orange charge LED).
- PRG held while pressing RST enters USB download mode (harmless, RST again). Put it in the manual.
- **Bench check:** waking from deep sleep with PRG must not latch download mode.

### OLED pages (Polish, like the field LCDs)

| Page | Contents |
|---|---|
| 1 Overview | phone ✓/✗, battery % + mV, game state + time, devices online `7/9`, airtime used % |
| 2 Devices | one line each: `D3 C RUN 12s -97` (id, kind letter, state, last seen, RSSI); paged past 6 |
| 3 Events | last 6: `12:03 D3 PRZEJ R p17` |
| 4 Radio | SF, TX dBm, TX/RX counts, queue depth, CAD-busy % |
| Setup | `SETUP 58s`, `net_id`, **4-hex key fingerprint** (the app shows the same one) |

- Off by default; a button press wakes it for 30 s (saves ~10 mA, avoids OLED burn-in). Waking on
  events is a config flag.
- Read-only. `Skipped:` game control from the companion alone (STOP-all menu), add if a dead phone
  mid-game becomes a real problem.
- Drivers: `ssd1306` + `embedded-graphics` (check async / embedded-hal 1.0 support in the plan).

### Battery life (EST; add a `--companion` mode to `hardware/power_budget.py`)

Assumes ~200 ACKs + commands per hour at 27 dBm (~1 % TX duty).

| Load | As-shipped firmware | Optimized (light sleep) |
|---|---|---|
| ESP32 awake + LoRa RX | 75 mA (datasheet, `HELTEC_RX`) | 20 mA EST (`HELTEC_RX_OPT`) |
| BLE connected (~50 ms interval) | 15 mA EST | 10 mA EST |
| LoRa TX (ACKs, commands) | 7.5 mA | 7.5 mA |
| OLED (~10 % on) | 1 mA EST | 1 mA EST |
| **Total** | **≈ 100 mA** | **≈ 40 mA** |
| 2000 mAh LiPo (× 0.84 usable) | ≈ 17 h | ≈ 42 h |
| 3400 mAh 18650 | ≈ 29 h | ≈ 71 h |

Recommendation: one 18650 (3000-3500 mAh): a 10 h game day even with as-shipped firmware, a weekend
with the optimized one.

### Power bank

- Charging works: 5V pin = VUSB, CN3165 at ~540 mA; a 3400 mAh cell refills in ~6-7 h overnight.
- Running in a pocket on a power bank works: ~640 mA while charging keeps any bank awake.
- When full the draw falls to ~100 mA and some banks auto-off below ~100 mA: harmless, the cell takes
  over without a reboot (the load sits on the cell node).
- No power path: with the ~100 mA load above the CN3165's 54 mA termination current, a full cell is held
  at 4.2 V instead of the charger stopping. Fine for a weekend; unplug for storage.

### BLE protocol

- Stack: `esp-radio` BLE controller + `trouble-host` (Embassy). **Verify in the plan:** GATT server on
  the S3 and MTU 247 (Android `requestMtu(247)`).
- GATT: one service (custom 128-bit UUID); `rx` = write-without-response (app → companion), `tx` =
  notify (companion → app). One message per write / notify, no fragmentation: the largest (decrypted
  LOG, ~234 B) fits the 244 B ATT payload.
- Message: `[msg u8][req_id u16][body]`.

| App → companion | Body | Reply |
|---|---|---|
| `AUTH` | `cmac(K_ble, challenge)[16]` | `INFO` or disconnect |
| `SET_NET` | `net_id, key[16], sf, tx_dbm` | `RESULT`; only in the setup window or when authenticated with the old key |
| `SEND` | `dst, type, body` (a Part 2 payload) | `RESULT{req_id, ok / timeout / busy / bad, detail}` |
| `SYNC` | none | cached last STATUS per device, then the buffered RX frames |

| Companion → app | Body |
|---|---|
| `CHALLENGE` | `nonce[16]`, right after connect |
| `RX` | `src, type, hop, rssi, snr, body` for every accepted STATUS / EVENT / LOG (ACKs are consumed) |
| `RESULT` | outcome of a `SEND` |
| `INFO` | firmware version, battery mV, airtime %, queue depths |

- **Auth:** `K_ble = AES(key, "ASG-BLE-v1")` (key separation from LoRa CCM). Nothing but `AUTH` (and
  `SET_NET` in the setup window) is accepted before a valid `AUTH`. No BLE pairing is needed from the
  stack; BLE traffic is unencrypted, which is acceptable (STATUS is on the LoRa air anyway; commands
  need auth).
- **Generic bridge:** the companion handles `ctr`, crypto, replay windows, CAD, retries and the airtime
  budget, never kind-specific payloads. The one special case: in `SEND START` it subtracts the elapsed
  time from `start_in_ms` before each attempt.
- Commands are serialized, one in flight (START to 10 devices ≈ 4 s best case).
- RAM: last STATUS per device, RX ring (512) for the app, command queue, replay windows. Flash
  (`sequential-storage`): network config, own `ctr`.
- No app-level ACK: BLE notifications are reliable while connected; anything lost at a disconnect is
  covered by repeating STATUS and EVENT gap-fill.
- **Key flow:** the app generates `net_id` + key and shows them as text + QR → typed into each device's
  WiFi page once → PRG setup window on the companion → the app sends `SET_NET`.

## Part 6: Android app

- Kotlin + Jetpack Compose, one activity, minSdk 29.
- BLE: platform `BluetoothGatt` behind a small coroutine wrapper (connect, `requestMtu(247)`, discovery,
  notify, write-without-response). `ponytail:` Nordic Android-BLE-Library if operation queueing gets
  painful.
- A foreground service (type `connectedDevice`) holds the connection with the screen off.
- Room database; CSV export via the share sheet.

| Table | Key | Contents |
|---|---|---|
| `games` | `game_id` | start UTC, mode, config, device set |
| `devices` | `dev` | kind, user name, last position |
| `events` | `(dev, game_id, event_id)` | the 14 B record fields + received time |

- Events are inserted with **INSERT OR IGNORE**: relay copies, retries, ring replays and gap-fill all
  collapse on the primary key. The latest STATUS per device is in memory only (rebuilt by `SYNC`).
- **Kind table** `Kinds.kt`, one entry per kind: name, STATUS tail parser, event names, CONFIG params
  (id, label, range, default), a fold function (log → score). Unknown kinds show the common fields.
- **Gap-fill:** per `(dev, game)` compare the highest contiguous `event_id` with STATUS
  `last_event_id`; queue `LOG_GET` per gap, one at a time, progress on the device card. If the folded
  score differs from STATUS, the card shows ⚠ "log incomplete" until gap-fill finishes.
- **Codec:** `Proto.kt` written by hand, tested against `proto/vectors.json`.

Screens:

1. **Devices:** a card per device (name, kind, state, score, battery, RSSI/SNR both ways, last seen,
   relay badge, faults); pull to `SYNC`.
2. **Device detail:** CONFIG edit, `PING`, `FLAG` override, log sync status, full dump.
3. **Game:** new game (mode, config, device checklist), START with countdown, STOP, RESET; each command
   shows per-device `RESULT` with failures marked.
4. **Map:** device markers coloured by holding / leading team, plus the phone's position.
5. **Log:** events filtered by device, team, player, kind; per-player totals; end-of-game summary; CSV.
6. **Settings:** network key generation (text + QR), companion setup (`SET_NET`), LoRa SF + TX power.

Map: MapLibre Native Android with **offline region download** (download the field at home, play with no
signal). **Verify in the plan:** a free tile source whose terms allow offline download (OpenFreeMap or
similar); fallback: a self-made MBTiles file.

`Skipped:` player names (ids only; add a `players` table for nicknames), iOS, several phones per
companion.

## Part 7: Testing

One spec, one set of vectors: `docs/protocol.md` + `proto/vectors.json` (frame bytes ↔ decoded fields
for every message class and BLE message), generated by a Rust test that fails when the file is stale;
the Kotlin tests read the same file.

Host tests in `firmware/core`:

| Area | Check |
|---|---|
| AES-CCM | a NIST SP 800-38C vector (4 B tag); frame round trip; tampered byte; wrong `net_id` |
| Replay window | in order, out of order within 32, too old, duplicate |
| Airtime + duty | matches `power_budget.py`'s self-check values (144 ms SF9 / 10 B); 10 % and 7 % limits |
| Retry / backoff | fake clock: commands stop after 4 attempts; EVENT backoff caps at 60 s |
| Relay decision | every Part 4 rule, including suppression |
| Event log | `sequential-storage` queue on mock flash: append, reboot recovery, torn record, ring wrap |
| Mini simulation | 10 nodes + 2 relays + companion, random loss and collisions, discrete time: every EVENT delivered (live or gap-fill), no duplicates in the "app" table |

App: `Proto.kt` vs vectors, kind fold functions; `FakeCompanion` (a second transport implementation
simulating N devices in memory) so the whole UI is built and tested before any V4 exists.

Bench and field (needs V4s): two V4s (PING / STATUS / START, authenticated commands); three nodes with
one reachable only through the relay; phone ↔ companion (MTU 247, reconnect + `SYNC`, power-bank
charging, PRG deep-sleep wake); a range walk at SF9 and SF10 through forest; companion current with a
USB meter to replace the EST rows.

## Milestones

| | Milestone | Needs hardware |
|---|---|---|
| P1 | `core::proto` + `docs/protocol.md` + vectors + simulation | no, can start now |
| P2 | Android app on `FakeCompanion` (all screens, Room, export, offline map) | no |
| P3 | Field device radio task + flash log (replaces carrier milestone 4) | V4 |
| P4 | Companion firmware: LoRa bridge, BLE, OLED, buttons, power (replaces milestone 7) | V4 with display |
| P5 | App ↔ real companion | phone + V4 |
| P6 | Field test: relay, range, battery life | several V4s |

## Open items

- V4.3 schematic: OLED pins + Vext, USB-C CC pull-downs.
- `trouble-host` GATT server + MTU 247 on esp-radio; `ssd1306` async support.
- `sequential-storage` queue: iterate without pop, mock flash for tests.
- Hard switch part (≥ 2 A DC).
- Offline map tile source terms.
- Bench: PRG deep-sleep wake does not enter download mode.
- Measure: companion current (as-shipped and optimized), BLE share, OLED.
