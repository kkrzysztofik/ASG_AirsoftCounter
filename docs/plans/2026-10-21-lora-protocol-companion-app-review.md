# Review: LoRa protocol, companion and Android app design

Date: 2026-10-22 (review of the 2026-10-21 design)
Target: `docs/plans/2026-10-21-lora-protocol-companion-app-design.md` (442 lines,
"design approved, implementation plan not written yet")

**Verdict: the architecture is sound and most numbers check out, but do not write the
implementation plan yet.** Six P0 issues and about 40 P1 decisions/fixes should go into the design
(or into `docs/protocol.md` where they belong) first. None of them invalidates the architecture:
star + 1-hop relay, the frame format, AES-CCM, the flash event log, the generic companion bridge
and the app split all survive. The P0s are concentrated in four places: **the channel/event-rate
model, game identity in the log, the START deadline, and the BLE key transport**, plus one safety
issue in the companion cell.

## How this review was done

Five independent passes, then a lead synthesis:

| Pass | Scope | Result |
|---|---|---|
| Radio / protocol | Parts 1-4: frame sizes, all airtime cells, channel load, log capacity/wear, retry/relay/replay logic, dump/ETA, regulatory | 2 P0, 14 P1, 21 P2 |
| Security | CCM construction, replay/nonce lifecycle, BLE auth, key flow, threat model | 2 P0, 8 P1, 10 P2 |
| Rust / ESP32 stack | Every crate/API/version/memory/flash claim, host-test feasibility | 0 P0, 9 P1, 8 P2 |
| Hardware / power / Android | V4 facts, cell/switch/connector safety, power arithmetic, app platform, offline map | 1 P0, 12 P1, 14 P2 |
| Lead | Cross-document consistency, milestone/dependency graph, internal contradictions, synthesis | merged below |

Method: every number was recomputed from scratch (the Semtech time-on-air formula in
`hardware/power_budget.py` was used as the reference), external facts were checked against upstream
sources (Heltec datasheets/schematics, Meshtastic board files, crates.io/docs.rs, EN 300 220-2,
NIST SP 800-38C/RFC 3610, Android and MapLibre/OpenFreeMap docs), and the four repo docs that this
one supersedes or depends on were read in full. Raw per-area notes with line-by-line working are in
`.review/{radio,security,stack,hw-app}.md` (untracked; delete when no longer useful).

Severity: **P0** = design is wrong/unsafe or blocks the implementation plan; **P1** = needs a
decision/fix before or during P1-P5, or it will bite in the field; **P2** = clarity, precision, nit.

## Scorecard

| Area | Verdict |
|---|---|
| Frame format, sizes, overhead | ✅ correct (13 B overhead, 39/29/19/239/13/20/53/14/18 B all check) |
| Airtime at SF9 (and the given SF10 cells) | ✅ correct to the millisecond, every cell |
| STATUS baseline load (8.9 % at 10 devices / 30 s) | ✅ correct |
| Channel budget and event/ACK load | ❌ 2-10× optimistic at the doc's own event rate → **P0-6** |
| Replay window concept, ctr skip-ahead | ✅ sound; lifecycle gaps → P1 |
| Event log concept and wear | ✅ concept sound; record layout broken → **P0-5**; capacity 16 k → ~10.9 k |
| START/STOP command path | ❌ underflow, no shared T, serialisation worst case → **P0-4** |
| AES-CCM construction | ✅ legal and sound (NIST SP 800-38C / RFC 3610 / `ccm` U4/U13) |
| Key transport and BLE auth | ❌ key in clear + one-way auth → **P0-1, P0-2** |
| Companion cell and safety | ❌ unprotected cell, no fuse/PTC, 1 A connector → **P0-3**; 18650 does not fit the case |
| Rust/ESP32 stack | ✅ feasible; one dependency-version trap, wrong RAM/log/partition numbers |
| Heltec V4 facts | ✅ display variant exists, pins/Vext/CN3165/CC/20 µA mostly verified; pin the R2/R8 + V4.2/V4.3 revision |
| Android app | ✅ feasible; permissions/FGS section missing, MTU is not guaranteed |
| Power table arithmetic | ✅ correct (17/42/29/71 h); assumptions to fix (pouch, 0 °C, antenna/TX) |

---

## P0 — fix before the implementation plan

### P0-1. The network key is sent in clear over an unencrypted, unpaired BLE link (lines 29, 326-328, 337-343, 352-353)

`SET_NET` carries `net_id, key[16], sf, tx_dbm`; the design explicitly chooses no BLE pairing and
unencrypted BLE ("acceptable, STATUS is on the LoRa air anyway"). A BLE sniffer in range during the
60 s setup window (or any rekey) reads the 16-byte master key. With it: decrypt all LoRa traffic,
forge as `src = 0` or any device, derive `K_ble`, and authenticate to the companion. This also
contradicts the doc's own rejection of "LoRa pairing (sniffable)". The doc's "rekey on loss"
cannot evict an attacker who received the key during the rekey.

**Fix:** pair the phone and companion with **BLE LE Secure Connections Passkey Entry** — the
companion already has an OLED for the 6-digit code and the phone has the keyboard. This is the
NIST SP 800-121r2 §3.2.2.4 model for exactly this setup and solves P0-2 and the setup-window
hole at once. If `trouble-host` cannot pair, use ECDH (P-256, `p256` no_std) over GATT with a
6-digit SAS shown on the OLED and verified on the phone. Do not substitute a code-encrypted
`SET_NET`: a sniffer can brute-force a 6-digit code from the captured ciphertext. Verify the
pairing support in the plan (the stack pass flags it as a P5 blocker).

### P0-2. The app never authenticates the companion, and post-AUTH messages are unauthenticated (lines 325, 337-343, 350-351)

One-way `AUTH` (app → companion) is the only proof. A rogue companion (the app connects to whatever
advertises the service UUID; there is no pairing, address pinning, or verifiable identity) receives
`SET_NET` and gets the key. A BLE relay/MITM passes the one-way proof and can then inject `SEND`
commands and fabricate `RX`/`RESULT`/`STATUS` — the doc's "commands need auth" is false under
MITM. The 4-hex fingerprint cannot help: it is shown after the key has already been handed over.

**Fix:** the LE Secure Connections pairing above; otherwise two-sided proof over nonces from both
sides (distinct labels `ASG-BLE-v1-app` / `ASG-BLE-v1-companion`) plus a per-message MAC with a
monotonic session counter on every GATT message (a transparent relay passes proofs but cannot
recompute a MAC).

### P0-3. A bare cell on the Heltec charger with no protection, fuse or PTC (lines 243-248, 266-267, 302, 311-312)

The design relies on firmware UVLO 3.45 V + the inline switch. The V4 has **no protection IC and no
under-voltage cutoff** (its own `hardware/docs/PARTS_REVIEW.md`; the CN3165 is a charger, not a
protector), and the repo's pack and LiPo boards both exist specifically to add fuse + PTC +
per-cell protection. A firmware hang or brownout loop drains the cell to 0 V; a short in the case
is a fire. The battery connector is also at its limit: **Molex PicoBlade 51021 is rated 1 A** and
the ~1 A TX peaks are at that rating.

**Fix (decide before P4):** use a **protected 18650** (button-top with built-in PCB) or protected
LiPo pouch, and state the cell model; if a bare cell is kept, add an XB8089D-class protection board
plus a 1.5-2 A PTC/fuse in the cell + lead (the pack board's 1206L200 is the repo precedent). Keep
firmware UVLO as defence-in-depth. Add a short-circuit bench test and state a charge temperature
range (the V4's TEMP pin is not connected to the cell). Note the naming: the socket is **Molex
PicoBlade 1.25 mm**, not JST SH.

### P0-4. START cannot start 10 devices together, and `start_in_ms` underflows (lines 136, 143-145, 208, 346-347)

`start_in_ms` is `u32` ms and `T − now` goes negative as soon as an attempt happens after T. With a
10 s countdown and two failed attempts: attempt 1 times out at 2.5 s, backoff 2 s, attempt 2 times
out at 7.0 s, backoff 4 s, attempt 3 at **11.0 s** → `start_in_ms = −1000` → as `u32`,
**4 294 966 296 ms ≈ 49.7 days**. If the code saturates instead, the device starts immediately and
the "±50 ms together" property is lost. There is also no single `T`: the app sends 10 separate
`SEND START`s and the companion fixes T per message, while commands are serialised one in flight
(so SEND #10 is dequeued seconds after #1). And "however long delivery takes" is impossible: 24 s
per device worst case × 10 = **240 s**, not "≈4 s best case".

**Fix:** use an absolute start time (or a batch id + one T fixed on the first START, echoed in every
`RESULT`). On the device, `saturating_sub` and `RESULT{ok, detail=late_ms}` when clamped; reject
rather than start after T + grace. Require the app's countdown ≥ `N_devices × 1 s + 5 s`, and
document that a device that misses T starts late or is reported failed. Also allow **one command in
flight per device** (the ACK carries `src`, so ACKs are matchable) — START/STOP-all then takes
~0.5 s, not 4-240 s.

### P0-5. The log record cannot carry `game_id`, so replay and gap-fill can file records under the wrong game (lines 160-164, 176, 114)

The record is `event_id u16 · t_ms u32 · event u8 · team u8 · player u16 · extra[4]` and is
"identical in flash and on air". But:

1. `GAME_START` must log `game_id` **and** GPS UTC in `extra[4]` — 6 B into 4 B. Impossible.
2. There is no `game_id` in the record, so `LOG_GET` cannot scan by `(game_id, from_id)`.
   `event_id` restarts at 1 per game: after a log clear or ring wrap, `LOG_GET(old_game, from=1)`
   returns the new game's records and the app files them under the old game (PK
   `(dev, game_id, event_id)`). The "replay the game from the log" feature silently corrupts.
3. The on-air EVENT/LOG carry `game_id` outside the record, so "identical in flash and on air" is
   already false.

**Fix (keeps the 14 B record and 16 records/LOG):** treat a `GAME_START` record as a segment
header — `extra[0..2] = game_id`, `extra[2..4] = flags`; log a separate `GPS_ANCHOR` record (only
record that needs 4 B of `extra`) whenever a fix is acquired; `LOG_GET` finds the segment for
`game_id` and returns `out_of_range`/`not_found` with `detail = earliest available event_id` when
the segment start is gone (wrap/clear). Alternative: widen the record to 16 B with `game_id u16`
(the crate already pads 14 → 16, so flash cost is unchanged) but then LOG must drop to 15 records
(15 records, 255 B frame, ~12 % more airtime per record). Prefer the segment fix.

### P0-6. The channel/reliability model is 2-10× optimistic; at the target scale the relay and the companion hit their own 10 % cap (lines 148-152, 208-210, 218-225, 290)

The doc's 14 % total assumes "events and ACKs a few tenths" and "relay ~5 %". At the doc's own
event rate ("a few hundred events per device", line 186) and its own forwarding rule ("a relay
forwards everything", line 224):

| Effect | Arithmetic | Result |
|---|---|---|
| 10 devices × 300 events/h, each EVENT + ACK | 3000 × (226.3 + 185.3) ms / 3600 s | **+34 % channel** |
| Companion ACK duty at that rate | 3000 × 185.3 ms / 3600 s | **15.4 %** — over its 10 % cap |
| Relay that hears all 10 devices (open field) | 8.91 % copies + 0.89 % own STATUS | **9.8 % before any EVENT/ACK** |
| Two such relays, no suppression | 2 × 8.91 % copies | **~27 % channel, each at the cap** |
| State-change STATUS at the 5 s floor, 10 devices | 10 × 267.3 ms / 5 s | **53 % channel** |

The doc's 14 % ratio is arithmetically right *given* an unstated "relay hears half the field and
there are almost no captures". Neither is stated, and neither is the deployment. The failure mode
is positive feedback: at the cap, ACKs are delayed, the 2.5 s ACK timeout fires, devices retry, load
rises. The 1189 ms LOG frames make it worse: at 14 % load a hidden terminal collides with
probability ~46 % (1 − e^(−λT)), and LOG has **no retry rule** (R4/R5).

**Fix:** write down the design point (e.g. "≤ 500 events/h network-wide", "a relay is expected to
hear N of 10"), size ACKs against it, and choose one of: drop the per-EVENT ACK (buffer + let the
device retry), piggyback `acked_ctr` on the next companion frame, or make ACKs shorter. Add the
**relay src allowlist now** (it is required at 10 devices, not "if load grows") plus ACK-heard
suppression. Drop or rate-limit the state-change STATUS (the EVENT already carries the change).
Make "all events delivered, duty ≤ limits, bounded latency" the simulator's acceptance criteria,
not just "no duplicates".

---

## P1 — decide/fix before or during implementation

### Protocol and radio

| # | Lines | Finding → fix |
|---|---|---|
| R1 | 116-123, 374-376 | **STATUS has no `game_id`.** `last_event_id` is unqualified: after a new game the app compares game 5's prefix with game 6's tail; a device that missed START/STOP is indistinguishable. Add an optional `game_id u16` (a flag bit + 2 B appended only on the state-change STATUS: periodic STATUS stays 39 B/267 ms, the occasional state-change STATUS becomes 41 B/287.7 ms), or add it always (287.7 ms every 30 s). |
| R2 | 160-164, 170-171, 234 | **`t_ms` cannot survive a reboot; "resumes ... its clock" is impossible** (no RTC; a power cut loses the outage duration, and the mining countdown cannot be recovered). Define `t_ms` as ms-since-boot, add `boot_seq`/pre-reboot `t_ms` to the `REBOOT` record, log `GPS_ANCHOR` UTC per boot, and state the mid-mining reboot policy (recommended: treat interval as elapsed, resume Ready). |
| R3 | 86-90, 211-215 | **Out-of-order delivery can resurrect a stopped game.** The replay bitmap accepts a late START retry (ctr n) after the STOP (ctr n+k); "idempotent" only covers the same game. For `src=0` use a strict monotonic high-water command ctr, persist it, and ignore `START{game_id ≤ last_stopped_game_id}`. |
| R4 | 188, 114 | **LOG stop-and-wait has no timeout/retry**; a lost LOG (46 % chance on a busy channel) stalls the dump forever and the device has no idea. Define timeout ≈ LOG airtime + 2 × ACK timeout (~3.5 s), 3-4 attempts, then `RESULT{timeout}`; the device re-sends the same records for a retried `LOG_GET`. |
| R5 | 181-193 | **Dump/ETA model is inconsistent.** The device only answers under **7 %**, yet the table says "at 10 %" (17.7 min/1000 events, not 12); "3-4 min" is ~200 events; the tracker wording (rolling 1 h total) permits an 85 %-duty burst that the table's arithmetic does not model. Pick token-bucket vs rolling total, recompute, and make records/frame configurable (16 is not always fastest once 46 % loss and the 1.76× collision cross-section are counted; 8 rec can win). |
| R6 | 165, 172 | **"256 KB ≈ 16 000 records" is wrong**: `sequential-storage` costs 8 B header + 16 B padded data = 24 B/record → **~10 880**; 16 000 needs ~384 KB. The wear conclusion survives. Fix the number and the partition size. |
| R7 | 56-58, 245, 290, 388 | **"27 dBm" is used both as the legal ERP limit and as the TX setpoint.** 27 dBm *conducted* + 3.6 dBi = 700 mW ERP (40 % over); the compliant cap is **25.5 dBm conducted** with that antenna (25 dBm with margin; 26 dBm = 556 mW is over). `power_budget.py`'s "~26 dBm" is 0.46 dB over. State two numbers everywhere (conducted setpoint and ERP), clamp in firmware, and specify the companion's antenna and gain (the case has an SMA bay; Part 5 has no antenna at all). Default 20 dBm = 140 mW ERP is 5.5 dB under-used. |
| R8 | 58, 88-90 | **The 1 h tracker resets on reboot → not EN 300 220-2 compliant** (duty cycle is defined over Tobs = 1 h; PRG off is routine). Persist `used_ms` + a boot/save counter and carry the persisted usage forward for the first hour after boot (6 B, no RTC). |
| R9 | 67, 133-143 | **STOP/RESET addressing undefined.** `dst=0xFF` is documented but no message uses it; if STOP/RESET broadcast with ACK, 10 ACKs need ~1.9 s of slots versus the 20-100 ms random window. Define them unicast per device like START, with the failure policy ("app retries failed devices; reconciled by next STATUS"). |
| R10 | 56, 142, 326, 388 | **No network-wide SF change.** `SET_NET.sf` reconfigures only the companion; devices' SF is set nowhere. Changing to SF10 silences every device until each is reconfigured physically, and SF10 doubles everything (LOG 2132 ms, a 1000-event dump 32 min at 7 %). Make `sf` a common CONFIG param with an ACK-then-switch procedure, or remove it from `SET_NET` and document "SF is a per-build constant". |
| R11 | 98, 142, 383 | **No CONFIG read-back.** Write-only CONFIG means the app cannot show current values or verify a change. Add `CONFIG_GET` (or a sentinel write: `param_id` with bit 0x80 set = read) or a 2-byte `config_hash` in STATUS. |
| R12 | 216-225 | **Relay suppression ordering.** The hop=1 copy has the same `(src, ctr)` and would be dropped by the replay window before the suppression check; the 50-300 ms wait is shorter than a 267-1189 ms frame, so two relays usually both transmit. Check a separate "recently forwarded" set (not the window), listen through the whole wait, and cancel on hearing the destination's ACK. |
| R13 | 159, 366-376 | **`game_id` uniqueness is assumed.** It is a sequential u16 assigned by the app; after an app reinstall it restarts at 1 and collides with records retained in device flash (`LOG_GET` returns the old game's records). Make it random/epoch-based (16-bit random is enough for a weekend) and state the rule. |
| R14 | 113-114, 128-129, 176 | **Missing `LOG_GET` result codes**: `from_id` beyond the tail, game cleared, oldest records wrapped — add `out_of_range`/`not_found` so the app can stop gap-filling. Also define `extra[4]` per event, `flags` bits, `state`/`result` enum values, the ACK-bit per type, PING→STATUS matching (PING says "answered by STATUS" but also asks for an ACK), and a protocol version — a `docs/protocol.md` completion list, ideally before P1 starts. |

### Security and key lifecycle

| # | Lines | Finding → fix |
|---|---|---|
| S1 | 64-90, 233, 326, 349 | **Nonce/ctr lifecycle under-specified.** Rekey with a ctr reset (reflash/factory reset), replacing a device with the same `src`, and a torn 256-frame checkpoint can reuse CCM nonces; the skip-ahead has zero margin. Invariant: `ctr` never decreases while `(net_id, key, src)` is unchanged; any event that can erase it requires a **new key and new net_id** (the app already generates both). Reset both sides' windows atomically on rekey; start ctr at a random value on first provisioning; skip-ahead ≥ 2× persist interval; reject `src=0`/duplicate `src`. Free hardening: the 7 unused nonce bytes can carry `dst`, `type` and a key-derived salt. |
| S2 | 233 | **Companion reboot resets replay windows** → a sniffer's replayed STATUS shows a removed device as online/current (battery, position, score, flag colour), and old EVENTs from a new `game_id` are inserted. Persist per-`src` windows (10 × 5 B) next to the companion ctr, or carry a boot epoch and reject regressions in the app; keep window reset only for the authenticated rekey path. |
| S3 | 326, 341-343 | **The 60 s setup window accepts unauthenticated `SET_NET`** (config overwrite for anyone in BLE range during the window) and every device holds the same secret, so any device is also a BLE admin. Pairing (P0-1) fixes the first; for the second, accept and document it, or derive separate `K_ble`/`K_device` roles. |
| S4 | 337-343 | **`hop` is outside the AAD**, so a non-key holder can flip it on a captured frame and suppress relaying (keyless DoS). Limited impact, but document it, and never use `hop` for a security decision unless it moves into the AAD (relays hold the key and could re-tag). |
| S5 | 29, 84-85, 352-353 | **The device WiFi AP config page is a remote key path, and the carrier design specifies no AP/page auth** — weaker than the accepted "physical possession" extraction risk and than the rejected "sniffable" LoRa pairing. Specify WPA2 + a page token (or accept and write it down). The rekey-on-loss procedure is a 20-40 min game abort; a partial rekey leaves old-key devices attacker-controlled. Write the procedure down. |
| S6 | 337-353 | **Missing threat model.** Add assets (game integrity, key, command authority), adversaries (passive LoRa/BLE sniffer, active injector, stolen device, MITM, jammer) and a decision-vs-model matrix; several "acceptable" claims only hold under a model that is nowhere stated. Also define the `JAM` fault (radio jamming is not locally detectable; say what the detection actually is), key display/storage on the phone, and a fresh 128-bit CSPRNG challenge per connection. |

### Rust / ESP32 stack, flash and memory

| # | Lines | Finding → fix |
|---|---|---|
| T1 | 316-317 | **Dependency-version trap.** Released `esp-radio 1.0.0-beta.1` declares `bt-hci ^0.9`, while `trouble-host 0.8.0` needs `^0.10` — as written the BLE stack does not compile. Pin `trouble-host =0.7.0` + `esp-radio =1.0.0-beta.1` (the esp-hal example's `ExternalController` is 0.8-era, so the 0.7 construction path must be verified) and make a compile-only smoke test the first P4 task. BLE is explicitly beta/unstable, consistent with P4 being last. |
| T2 | 173 | **"sequential-storage is already in the stack" is false.** The tree is `core` + a blinky `device`; nothing else is present. Add a stack bring-up task (`esp-storage`, `sequential-storage 8` + `embassy-embedded-hal`, `lora-phy 3.0.1`, `trouble-host`, `ssd1306`, `ccm`/`aes`/`hmac`/`sha2`) and budget a day, not an afternoon; each is a first-build-on-hardware risk. |
| T3 | 232, 348 | **The RAM budget is mis-sized.** 512 KB is the chip; esp-hal gives **333.75 KB** static DRAM (plus 72 KB `dram2`), and the BLE controller needs ~72 KB of heap. The 512 × 234 B ring is 117 KB and fits only with little headroom. Shrink the ring to 256 (~58 KB) and the STATUS table to 16-32 entries (254 is waste for ~10 devices); state the real number. V4 has 2 MB PSRAM, V4-R8 8 MB — but see T4. |
| T4 | 232, 348 | **Flash writes disable the cache, PSRAM access and non-IRAM ISRs** (ESP-IDF SPI1 rule); the log writes on **every** state change, and `esp-storage` read/write uses a hidden **4 KB stack buffer**. So: no BLE/LoRa buffers or ring in PSRAM, log task stack ≥ 12 KB, use `write_nor` with an aligned buffer, batch records where the "at most the last record lost" rule allows, and measure the erase/write stall against the 2.5 s ACK timeout and the 30-50 ms BLE interval. |
| T5 | 243, 349 | **No partition table; the log and config need separate partitions.** The V4-R8 has 16 MB flash and a default table gives a 1 MB app (too small for esp-hal + esp-radio BLE + trouble + lora-phy + ssd1306). Add `partitions.csv`: app ≥ 2 MB, `asg_log` 384 KB, `asg_cfg` 8 KB; generate ranges from the table at boot. |
| T6 | 318-320 | **No fallback if Android grants < 247.** `requestMtu` is a request; Android 14 may force 517 for the first request, other phones cap lower, and write-without-response is silently truncated to the MTU. Read `onMtuChanged`; require ≥ 238 or chunk LOG/`SEND` with an app-level `part i/n`; report the granted MTU in `INFO`. |
| T7 | 349 | **"BLE notifications are reliable while connected" is false.** ATT notifications are unacknowledged; trouble-host's default pool is 16 × 251 B with no backpressure, and everything queued at disconnect is lost. Add a sequence number to `RX`/`RESULT` (or re-`SYNC` after every reconnect and every N frames) and reword to "delivered while the link is up; not end-to-end acknowledged". |
| T8 | 49-51, 430 | **The companion cannot reuse the carrier `board.rs`.** It is the carrier map (LCD I2C 4/3, TCA9534 INT 6, I2S 47/48/**21**, VBAT 1); the V4 display board needs OLED SDA **17**, SCL **18**, RST **21**, Vext **36 (R2) / 40 (R8)** — GPIO21 is already claimed by I2S. `lib.rs` also asserts one of `v4-r2`/`v4-r8`, and `[[bin]]` has no `required-features`, so adding `companion.rs` builds both images. Split `board/carrier.rs` + `board/companion.rs`, add a `companion` feature with `required-features`, pin the R2/R8 and V4.2/V4.3 revision. |

### Companion cell, power and case

| # | Lines | Finding → fix |
|---|---|---|
| H1 | 243, 300-302 | **The recommended 18650 does not fit the case.** The 3MF it is built in is 59.4 × 84.4 × 25.7 mm assembled, with a ~12 mm back-shell bay and ~17-30 mm of free space at the sides/antenna end; an 18650 is Ø18.4 × 65 mm. The concurrent key-switch design assumes a ≤ 5-12 mm LiPo pouch. Recommend a **2000-2500 mAh pouch** (17 h/42 h claims still hold) or re-case for an 18650; update the 3400 mAh row. |
| H2 | 245-250, 439 | **The housing/switch text contradicts the key-switch design that is being implemented.** "Stock Heltec case with the switch in a drilled hole / Skipped: printed case" is wrong: the 3MF is a third-party printable case, lengthened 20 mm with a D-hole and a widened antenna bay. Replace the bullet with a pointer to the key-switch design + plan; add the 868 MHz antenna, SMA bulkhead, pigtail and gain to the BOM; note the case is not IP-rated. |
| H3 | 245-246, 439 | **The switch requirement is not reconcilable with the chosen part.** The doc demands ≥ 2 A DC and calls 0.5 A SS12D07-class too small; the key-switch design picks Blow SWT-06357 with **no electrical rating recorded** (no public datasheet found). The actual load is ~0.14 A RMS / ~1 A peaks, so "≥ 2 A" is over-specified; require a **documented ≥ 1 A DC (2 A preferred) at 3.7 V DC** rating and a hot-switch bench test, and record the rating in the key-switch plan or reject the part. |
| H4 | 264-267, 311-312 | **UVLO 3.45 V is too low and can strand the companion.** Heltec says operation becomes erratic below 3.45 V and the ESP32 reboots at 3.40 V; a 1 A TX burst sags the rail through the cell path, and there is **no VBUS-detect pin**, so on a power bank a deeply discharged cell (54 mA precharge vs ~100 mA load) never recovers, UVLO fires, and only a PRG press wakes it. Use 3.55-3.60 V with hysteresis, measured with the radio idle (or median), a USB-detect heuristic, and a timed auto-wake retry instead of indefinite deep sleep. |
| H5 | 305-312 | **The "no power path / cell held at 4.2 V" claim is wrong for the V4.** The V4.3 schematic has a diode/FET OR between USB and the cell: while USB is present the load runs from USB and the charger sees the cell and terminates (54 mA), which is also why "~640 mA while charging" (540 + 100) is the right number. Replace the paragraph with the OR description and bench-verify (cell current ~0 after termination). |
| H6 | 307-310 | **540 mA charge exceeds a 500 mA USB source; running+charging is ~640 mA.** Fine on a ≥ 1 A charger/power bank (and the doc's own number), but a PC USB-A port or a C-to-C source advertising Default USB (500/900 mA) is overloaded. Require a ≥ 1 A source; charge soft-off from a PC port; bench the CN3165 foldback. |
| H7 | 243, 252-254 | **Vext also feeds the LoRa FEM on a V4.2 (GC1109)** — cutting it to save the OLED kills the radio there; only V4.3 (KCT8103L) has a separate Vfem LDO (GPIO7). Pin the companion to a V4.3 board, or read the revision and never cut Vext on a GC1109. Verify PING/STATUS with the OLED off on both revisions. Also: the OLED controller is **SSD1315** (SSD1306-compatible; the `ssd1306` crate works), not SSD1306; the real reason the display is at 0 mA is "Vext off", not "no burn-in". |
| H8 | 268, 307-312 | **Cell safety in a closed printed case:** the CN3165 is a linear charger dissipating ~0.43 W at 540 mA plus the ESP32, with no NTC (TEMP pin not connected to the cell) — overnight charging in a closed case is the scenario the pack board added NTCs for. With a protected cell + PTC (P0-3), state the charge temperature range and "not unattended overnight"; use the case's existing vent. |
| H9 | 277, 258-263 | **The OLED Devices page cannot show all ~10 devices.** "Paged past 6" with PRG short = next *page* makes devices 7-10 unreachable on the companion — the offline fallback the OLED is for. Auto-rotate the 6-line window (e.g. 3 s), or split Devices A/B. Define the rest of the button state machine (short/hold thresholds, does the wake press advance, what a press does during the 60 s window, what closes it). |

### Android app

| # | Lines | Finding → fix |
|---|---|---|
| A1 | 355-361 | **No permissions/foreground-service section.** Needed: API 31+ runtime `BLUETOOTH_SCAN` (`neverForLocation`) + `BLUETOOTH_CONNECT`, legacy `BLUETOOTH`/`ACCESS_FINE_LOCATION` (maxSdk 30), `FOREGROUND_SERVICE` + API 34 `FOREGROUND_SERVICE_CONNECTED_DEVICE` with `foregroundServiceType="connectedDevice"`, `POST_NOTIFICATIONS` (API 33+), and note FGS cannot start from the background — the service must be started from the visible activity, and process death means "reopen the app". Also request a low-power connection interval and keep `ACCESS_FINE_LOCATION` for the phone's own map position (separate from the BLE `neverForLocation` assertion). |
| A2 | 364-371 | **The Room PK `(dev, game_id, event_id)` drops legitimate records.** `event_id` restarts per game, and records written outside a game (power-on/reboot, low battery, admin card, RESET after STOP) have no game or the previous `game_id` — two such records with the same id collide and `INSERT OR IGNORE` silently drops the later one. Add a boot/session id (or `game_id = 0` rows per boot with a per-boot sequence) and create the `games` row before ingesting. |
| A3 | 390-392 | **Offline map: terms allow it, with caps.** OpenFreeMap permits offline downloads of ≤ 3000 tiles / 50 MB per download, ≤ 4 parallel requests, unique User-Agent; OSM's own tile policy forbids bulk download. The app must estimate the tile count for the bbox/zoom range, refuse or raise `minZoom` above the caps, cap the OkHttp dispatcher, set the UA, pre-bundle or verify glyphs/sprites offline, download via WorkManager with `OfflineRegionStatus`, and keep the `mbtiles:` fallback. Close the open item with the caps in the doc. |
| A4 | 350-351, 384-386 | **Smaller app items:** the all-in-one-attempt `AUTH` needs a retry; `SYNC` needs an explicit end marker (the app cannot tell when the cached-status + buffered-frame burst is done); show the granted MTU + firmware version from `INFO`; define the app language (Polish/English) and share short labels with the field LCD (`CZ`/`NIE`, `GOT`/`GRA`/`KON`); the log fold must be a score projection, not a second full game engine — add fold vectors to `proto/vectors.json` so Rust and Kotlin cannot diverge. |

---

## P2 — nits and precision fixes

| # | Lines | Finding |
|---|---|---|
| 1 | 105, 133-140 | The companion→device table omits the SF10 airtime column the header promises (PING 289, START 371, STOP 289, CONFIG 616, FLAG 289, LOG_GET 330 ms). |
| 2 | 69, 135 | `PING` is "answered by STATUS instead of ACK" but sits under "all ACK requested"; a previously scheduled STATUS can falsely satisfy a lost PING. Match on a echoed `last_cmd_ctr` or answer with a normal ACK. |
| 3 | 122-123 | "`last_event_id` lets the app see lost events at the tail" is inaccurate — the contiguous-prefix check catches mid-log holes too; reword. |
| 4 | 140 | `LOG_GET.count` is `u8` (≤ 255) but a LOG frame carries ≤ 16 records; constrain to 1-16 or define multi-frame behaviour. |
| 5 | 181-184 | 16 records is not the maximum (17 fit: 253 B, 1250 ms); make records/frame configurable and measure 8/12/16 in the field test. |
| 6 | 113-114 | For a relayed frame the companion's `rssi/snr` is the relay's reading, not the device's — the app's "both directions" is misleading for relayed devices; label "via relay". |
| 7 | 65, 75-76 | `hop` outside the AAD also means "was this relayed" is unverifiable; if any telemetry uses it, move it into the AAD (relays hold the key and can re-tag). |
| 8 | 216-225 | A relay is half-duplex: its own ~10 % TX is RX-dead time, so it loses ~10 % of the frames it should forward; budget forwarding efficiency at (1 − own TX duty). |
| 9 | 161, 173-174 | The record's own CRC + pad is redundant: the crate already CRCs and word-pads, so a 14 B record costs the same 24 B as 16 B; delete the extra CRC. |
| 10 | 116-126 | Two fault fields (STATUS `flags` fault and flag kind-tail `fault u8`); define the `game.rs` phase → `state` mapping (idle/ready/running/ended/fault) and keep one fault field. The mining countdown is not in STATUS (derived from the last capture + config) — say so. |
| 11 | 117 | `game_s u16` wraps at 18.2 h; an "unlimited" domination game can exceed it. Use u32 or define the wrap. |
| 12 | 176-177 | A linear scan of ~11 k records while listening stalls RX (esp-storage disables cache/ISRs per access); chunk the scan or build the RAM sector index from the start. |
| 13 | 69 | No protocol version field anywhere; a wire change needs every device reflashed in lockstep. Reserve a VERSION type or a byte in PING/STATUS. |
| 14 | 64 | 1-byte `net_id`: two games in the same area collide with p = 1/256 (tag failure, airtime/noise only). Keep net_id in the app QR, or derive it from the key. |
| 15 | 201-209 | Queue priority is unspecified; when a budget is exhausted, ACKs must not sit behind STATUS/LOG copies. State ACKs > commands > EVENTs > LOG copies > STATUS (drop STATUS first). |
| 16 | 205-209 | The first EVENT backoff is 2 s but the ACK timeout is 2.5 s — two attempts overlap unless the retry is scheduled after the timeout. |
| 17 | 137, 213-214 | Stop vs RESET semantics and "START for a different game while running" are undefined. RESET = score reset + new game_id; a different-game START is rejected/busy. |
| 18 | 172 | "each sector erased once per ~16 000 records" → ~10 900 (R6); conclusion unchanged. |
| 19 | 288-303 | Battery table: 3400 is typical (the repo's model uses 3350 min), so 29/71 h are ~1.5 % optimistic; "~5 % left ≈ a year" holds only for 3400 (2000 → ~7 months); add the 0 °C × 0.8 derate (17 → 13.6 h, 42 → 34 h; claim survives). Measure the EST rows with an inline meter/INA219, not a USB meter (input ≠ cell current). |
| 20 | 288-303 | The 15 mA BLE row is sensitive to the connection interval — request a low-power interval and measure; the white status LED (GPIO35, ~0.9 mA) is not in the table; to reach 20 µA in deep sleep also turn off Vfem (GPIO7), SX1262 sleep and ADC_Ctrl (GPIO37) so the battery divider is off. |
| 21 | 246-248 | "OFF with USB in: runs from USB but does not charge" is true, but the battery node then sits at the CV 4.2 V with no cell (firmware would read "full") and the CN3165 shows DONE rather than cycling; say so. The charge LED on V4.3 is **red**, not orange. |
| 22 | 258-270 | Define the button state machine: short/hold thresholds, whether the wake press also advances the page, what a press does while the 60 s window is open, and whether SET_NET success / phone disconnect closes it. |
| 23 | 272-280 | Define shared short labels for Polish text (OLED vs field LCD vs app) and say whether the app is Polish or Polish+English. |
| 24 | 249-254 | BOM/case omissions: 868 MHz antenna + gain, SMA bulkhead, u.FL pigtail; the 3MFs are untracked third-party meshes (reproducibility); check both PRG and RST are reachable through the printed case (RST pinhole) or recovery means opening it. |
| 25 | 243 | Wording: "LiPo or a single 18650 on the SH1.25 socket" → the socket is Molex PicoBlade 1.25 mm; the cell choice is a decision, not a list. |
| 26 | 421 | Bench current measurement needs an inline cell-lead meter, not a USB meter (which measures input). |
| 27 | 415-416 | The app-side mini-simulation "every EVENT delivered (live or gap-fill), no duplicates" is the right property; add "duty ≤ 10 % per node / 7 % for LOG", "ACK timeout not exceeded in the design point", and the companion-absent/relay-only scenarios. |
| 28 | 429-432 | Milestones: P1/P2 are hardware-free, but P3 depends on carrier M5 (GPS) and M6 (WiFi page) which are not in this table, and the key flow (line 353) depends on M6. Add them as prerequisites (or a bench/OTA key-provisioning fallback), and note the naming: carrier plan says `asg-core::protocol`, this doc says `firmware/core/src/proto.rs`. |

---

## Cross-document changes

1. **`2026-09-28-esp32-lora-carrier-design.md`** — the "Radio protocol" section is marked superseded,
   but the milestone list still presents 4 (LoRa) and 7 (HQ bridge) as live; mark them replaced by
   P3/P4 of this doc. Milestones 5 (GPS) and 6 (WiFi page) are now prerequisites of P3/P5 and are
   missing from this doc's table.
2. **`2026-09-28-esp32-lora-carrier-implementation.md`** — line 1157 names `asg-core::protocol`; this
   doc names `firmware/core/src/proto.rs`. Pick one before P1.
3. **`2026-10-21-companion-key-switch-design.md` and `2026-10-21-companion-key-switch.md`** — must record the Blow SWT-06357
   electrical rating (or replace the part); the two companion-hardware docs currently disagree on
   the housing approach and the switch requirement (H2/H3).
4. **`hardware/power_budget.py`** — the 27 dBm/3.6 dBi comment is 2.6 dB optimistic ("~0.6 W ERP" is
   actually 1.15 W EIRP; the cap is 25.5 dBm conducted, not 26); add the `--companion` mode before P4
   and fix the 26 dBm sentence.
5. **`hardware/docs/OFFBOARD_PARTS.md`** — the 3.6 dBi antenna is the carrier's SMA part; the
   companion's antenna (FPC or SMA through the case) and gain are not in any BOM yet, and the ERP
   cap depends on it.
6. **`.gitignore` / repo** — the companion 3MFs are untracked third-party meshes; decide whether to
   track them (reproducibility) or document the download source.

## Decisions needed before the implementation plan

1. **Event-rate design point** — pick the number the channel budget is sized against (e.g.
   ≤ 500 events/h network-wide) and the ACK strategy that follows from it.
2. **Relay deployment assumption** — is a relay expected to hear all 10 devices? If yes, the src
   allowlist is mandatory, not a future optimisation.
3. **Cell and housing** — protected pouch in the existing case (recommended; 17 h/42 h holds) vs a
   new case for an 18650.
4. **Key transport** — LE Secure Connections passkey via the OLED (recommended) vs ECDH/SAS vs a
   documented, accepted risk. Verify `trouble-host` pairing support either way.
5. **`game_id` in STATUS** — optional field on the state-change STATUS (recommended, no airtime cost)
   vs +2 B always vs a separate STATUS_EXT.
6. **SF** — a per-build constant (simplest) or a network-wide CONFIG procedure.
7. **BLE MTU** — require ≥ 247 and refuse otherwise, or add chunking (needed if any phone caps low).
8. **Companion revision** — V4.3 (KCT8103L) must be pinned; R2 vs R8 changes Vext/LED pins.

## Suggested next steps

1. Apply the six P0 fixes to the design doc (and put the enum/record/retry/ACK tables into
   `docs/protocol.md`) before writing any code plan. The P0s are all design-level; none needs a
   prototype.
2. Answer the eight decisions above (event-rate design point and cell/housing are the two that
   change other numbers).
3. The P1 (host-testable core + vectors + simulation) and P2 (Android on `FakeCompanion`) plans can
   be written immediately after step 1 and are the longest-lead items — start them while the V4.3
   boards are ordered.
4. P4 (companion) is blocked on the `trouble-host` pin/pairing smoke test and the V4.3 revision;
   keep the bench list (UVLO sag, deep-sleep rails, PRG wake, MTU negotiation, power-path
   termination, switch rating) in the implementation plan as explicit exit criteria.

## What checks out (do not relitigate)

- Frame layout, overhead and every message size; **every SF9 airtime cell** (164.9 / 185.3 / 226.3 /
  267.3 / 328.7 / 676.9 / 1188.9 ms) and the four SF10 cells the doc gives (494 / 412 / 330 / 2132 ms).
- STATUS baseline load 8.91 % at 10 devices / 30 s; SF10 @ 60 s ≈ 8.2 %.
- The replay-window concept, keep-ctr relays, retry = new ctr, idempotent handlers, ctr persistence
  every 256 + skip-ahead (concept; lifecycle gaps are S1).
- The event-log concept (append-before-send, survive reset, gap-fill by `event_id`, INSERT OR IGNORE
  dedupe, torn-last-record tolerance), ring/wear behaviour (with R6's number).
- AES-128-CCM with `t=4, n=13, L=2` (NIST SP 800-38C; RustCrypto `ccm` U4/U13), AAD-minus-hop.
- `trouble-host` peripheral + basic GATT server, MTU 247 ⇒ 244 B ⇒ the 234 B message fits (subject
  to T1/T6); `ccm`/`aes`/`hmac`/`sha2`/`ssd1306`/`lora-phy`/`sequential-storage` support the design.
- Heltec V4 display variant exists; OLED SSD1315 on SDA17/SCL18/RST21, powered from Vext; 28 dBm FEM;
  CN3165 540 mA/54 mA; 5.1 k CC pull-downs present (the C-to-C warning is moot); 20 µA battery-only;
  no protection IC/UVLO (which is why P0-3).
- Battery arithmetic: 17.1 h (2000 mAh as-shipped), 43.6 h (optimized, doc says 42 — conservative),
  29.0/74.2 h (3400 — ~1.5 % optimistic, P2 #19).
- EU/PL rule: 869.4-869.65 MHz, 500 mW ERP, 10 % duty *or* polite spectrum access; 869.525 is inside.
- Android: Room IGNORE dedupe, CSV share sheet, QR, one activity, FakeCompanion; MapLibre offline
  regions + `mbtiles:` fallback; OpenFreeMap permits offline with caps (A3).
- Power-budget shape and the "10 h game day / weekend" conclusion on a 2000 mAh pouch (with the
  0 °C derate stated).

## Appendix: airtime verification (independent recomputation)

Semtech formula, BW 125 kHz, CR 4/5, 8-symbol preamble, explicit header, CRC on:

| Frame | Bytes | SF9 | SF10 |
|---|---|---|---|
| PING, STOP, RESET | 13 | 164.9 ms | 288.8 ms |
| FLAG | 14 | 164.9 ms | 288.8 ms |
| LOG_GET | 18 | 185.3 ms | 329.7 ms |
| ACK | 19 | 185.3 ms | 329.7 ms |
| START | 20 | 185.3 ms | 370.7 ms |
| EVENT | 29 | 226.3 ms | 411.6 ms |
| STATUS (counter/flag) | 39 | 267.3 ms | 493.6 ms |
| CONFIG (8 pairs) | 53 | 328.7 ms | 616.4 ms |
| LOG (8 rec) | 127 | 676.9 ms | 1230.8 ms |
| LOG (16 rec) | 239 | 1188.9 ms | 2132.0 ms |

The doc's SF9 column matches every cell; the companion→device SF10 values are simply missing (P2 #1).

---

## Resolution (2026-10-22)

Applied in revision 2 of the design (same file name). User decisions: event design point
**600 events/h network-wide** with per-EVENT ACKs; **app-set relay allowlists**; **LESC passkey on the
OLED with a specified ECDH + committed-SAS fallback**; companion cell **Akyga AKU-06034** (protected
2200 mAh pouch, 59 × 37 × 9 mm). Defaults taken without a question: `game_id` always in STATUS (+2 B),
SF a network constant, MTU ≥ 247 required, companion pinned to V4.3.

| Finding | Resolution (design section) |
|---|---|
| P0-1, P0-2 | LESC passkey + bonding + pinned identity; fallback ECDH with commitment and SAS; mutual HMAC AUTH (Part 6) |
| P0-3 | protected pouch, PCM bench checks, PicoBlade naming, `ponytail:` PTC only if the PCM cannot be confirmed (Part 5) |
| P0-4 | one T per `game_id`, signed `start_in_ms`, backdated game clock, grace + `late`, countdown rule; overlapping commands rejected (half-duplex) (Part 2) |
| P0-5 | segment header records `BOOT` / `GPS_ANCHOR` / `GAME_START` / `GAME_END`; `event_id` never resets; `LOG_GET` by `event_id` (Part 3) |
| P0-6 | design point table, load table ≈ 22 %, allowlists, no state-change STATUS, priority, simulator acceptance (Goal, Parts 2, 4, 8) |
| R1 | `game_id` always in STATUS (41 B, 287.7 ms) |
| R2 | `t_ms` since boot, `BOOT` record, `GPS_ANCHOR`, mid-game reboot policy |
| R3 | strict persisted high-water for companion frames |
| R4 | LOG timeout ≈ 4.9 s, 3 attempts, idempotent re-send |
| R5 | dump table at 7 %, sliding window defined, records/frame configurable |
| R6 | `asg_log` 384 KB ≈ 16 000 records at 24 B |
| R7 | conducted clamp `29.15 − gain`, 25.5 dBm with 3.6 dBi; companion antenna gain setting; `power_budget.py` comment fixed |
| R8 | duty window persisted and carried over boots |
| R9 | all commands unicast; app retries failed devices |
| R10 | SF is a network constant, changed only by rekey |
| R11 | `CONFIG_GET` + device `CONFIG` reply |
| R12 | suppression deleted: a device is on at most one allowlist |
| R13 | random `game_id` from `SecureRandom` |
| R14 | appendix enums (types, ACK bit, results, states, flags, events, kinds, protocol version); `LOG_GET` edge cases defined without new codes |
| S1 | `ctr` invariant, random start, skip-ahead 512, rekey on any reset, duplicate-`src` warning |
| S2 | companion persists per-`src` high-water; app regression checks |
| S3 | `SET_NET` only on a paired/authenticated link; shared device key accepted (BLE still needs the passkey) |
| S4 | documented; `hop` never used for security |
| S5 | WiFi page: admin-card mode, WPA2 per-device password, write-only key; rekey procedure written |
| S6 | threat model table; `JAM` clarified as the servo fault; CSPRNG nonces |
| T1 | pin `esp-radio 1.0.0-beta.1` + `trouble-host 0.7.0`; compile + pair smoke test first in P4 |
| T2 | stack bring-up task (a day); wording fixed |
| T3 | RAM budget: ring 256, STATUS 32 |
| T4 | flash-stall rules and bench measurement |
| T5 | `partitions.csv` (app 3 MB, `asg_log` 384 KB, `asg_cfg` 16 KB) |
| T6 | MTU ≥ 247 required, granted MTU in `INFO`; LOG over BLE ≤ 16 records |
| T7 | per-connection `seq` on companion → app messages; gap → `SYNC` |
| T8 | `board/companion.rs`, `companion` feature with `required-features` |
| H1 | 2200 mAh pouch; battery table recomputed (18.5 / 46 h, 0 °C 14.8 / 37 h) |
| H2, H3 | pointer to the key-switch design; ≥ 1 A DC rating or 1 A hot-switch test, also recorded in the key-switch design |
| H4 | UVLO 3.60 / 3.70 V, median with radio idle, 30 min timer wake |
| H5, H6 | USB/cell OR described, ≥ 1 A source |
| H7 | V4.3 pinned; never cut `Vext` on V4.2; SSD1315 |
| H8 | charge 0-45 °C, not unattended overnight, vent |
| H9, P2-22 | button state table; Devices page auto-scrolls |
| A1 | permissions and FGS section |
| A2 | PK `(dev, event_id)`, `game_id = 0` outside games, `games` row first |
| A3 | OpenFreeMap caps in the doc |
| A4 | AUTH retry, `SYNC_END`, Polish UI + shared labels, projection vectors |
| P2-1 … P2-28 | all applied in place (SF10 column, PING → ACK, wording, `count` 1-16, records/frame 1-16 (17 does not fit BLE), "via relay", half-duplex note, no extra CRC, one fault field + state mapping, `game_s` unwrap, RAM sector index, protocol version in `BOOT`/`INFO`, `net_id` collision note, priority, retry after timeout, STOP/RESET semantics, wear number, battery derate, deep-sleep rails + LED, OFF-with-USB note + red LED, shared labels, BOM/antenna, PicoBlade, inline meter, acceptance criteria, milestone dependencies + `dev-key`) |
| Cross-doc 1-4 | carrier design milestones 4/7 replaced, 5/6 noted; carrier plan names `asg_core::proto`; key-switch design records the rating requirement; `power_budget.py` comment fixed |
| Cross-doc 5 | the companion antenna is an open item in the design (not in the carrier's `OFFBOARD_PARTS.md`) |
| Cross-doc 6 | not changed: tracking the third-party companion 3MFs is the user's call |
