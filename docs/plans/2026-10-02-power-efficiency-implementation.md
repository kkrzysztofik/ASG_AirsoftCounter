# Power Efficiency Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Put the design in `2026-10-02-power-efficiency-design.md` into the repo: the power model
gets a weekend check, the off-board parts and ordering notes switch to the Newhaven
NHD-0420D3Z-FL-GBW-V3, and the firmware C-tasks carry the power requirements.

**Architecture:** No board changes. One Python model (`hardware/power_budget.py`, self-checking
`__main__`), three Markdown docs. Firmware is still paused until the Heltec V4 arrives, so the
firmware work is plan text, not code.

**Tech Stack:** Python 3 stdlib (`/usr/bin/python3`), Markdown.

**Repo notes:** use `/usr/bin/grep -F` for exact matches (the `rtk` wrapper reformats output).
`power_budget.py` has no test file: its `__main__` asserts are the check, and it must run green.

---

### Task E1: power_budget.py, Newhaven LCD, optimized firmware, weekend check

**Files:**
- Modify: `hardware/power_budget.py`

**Step 1: Write the failing checks.** In the `if __name__ == "__main__":` block, add after the
existing asserts (before `main()`):

```python
    # Weekend budget: 2 x 10 h games + 1 night parked, 0 C, cells aged to 80 %. ~350 mA.
    assert 300 < weekend_ma() < 400, weekend_ma()
    # The optimized firmware (design doc table 2) must pass with 30 % margin, backlight duty included.
    assert sum(scenario(True, True, BACKLIGHT_DUTY, opt=True).values()) * 1.3 < weekend_ma()
    # A backlight left on must cost more than one on a timeout.
    assert sum(scenario(True, True, 1.0).values()) > sum(scenario(True, True, BACKLIGHT_DUTY).values())
```

**Step 2: Run it, expect failure.**

Run: `cd hardware && /usr/bin/python3 power_budget.py`
Expected: `NameError: name 'weekend_ma' is not defined`

**Step 3: Implement.**

a) Replace the `LCD_LOGIC_5V` and `LCD_BACKLIGHT_5V` constants (and their comments) with:

```python
LCD_ON_5V = 32.0  # Newhaven NHD-0420D3Z-FL-GBW-V3, LCD + backlight at level 8: 21/32/44 mA
                  # min/typ/max (datasheet). Its PIC PWMs the backlight (0xFE 0x53, levels 1-8).
LCD_IDLE_5V = 5.0  # EST: PIC16F690 + ST7066U with the backlight at level 1 (off). Measure it
                   # (fab/OFFBOARD_PARTS.md item 5).
BACKLIGHT_DUTY = 0.05  # EST: firmware lights it for a button, card or game event, then times out.
                       # Transflective panel, so it reads in daylight with the backlight off.
```

b) After `HELTEC_SLEEP`, add the optimized-firmware targets:

```python
# Optimized firmware targets (power-efficiency design, table 2). EST until measured.
HELTEC_RX_OPT = 20.0  # 80 MHz + automatic light sleep, SX1262 RX duty cycle
GNSS_OPT = 1.0  # one fix at boot, then VGNSS off (backup domain only)
NFC_POLL_OPT = 5.0  # PN532 PowerDown between polls, polls only when a card is expected
```

c) Replace `scenario()` so `backlight` is a duty from 0 to 1 and `opt` selects the targets:

```python
def scenario(deluxe, game, backlight, status_s=30, clip_duty=0.05, opt=False):
    """backlight: share of time the LCD backlight is on (0..1). opt: optimized firmware targets."""
    ma = {"Heltec awake, LoRa RX": HELTEC_RX_OPT if opt else HELTEC_RX}
    ma["LoRa STATUS TX"], _ = lora_avg(status_s)
    if deluxe:
        ma["GNSS"] = GNSS_OPT if opt else GNSS
        ma["PN532"] = (NFC_POLL_OPT if opt else NFC_POLL) if game else NFC_IDLE
        ma["Amp (on only for clips)"] = (AMP_ON + AMP_PLAYING) * clip_duty if game else 0.0
    five = LCD_IDLE_5V + (LCD_ON_5V - LCD_IDLE_5V) * backlight
    if game:
        five += (1 if opt else 2) * LED_RING_5V + BUZZER_5V * READY_BUZZ_DUTY  # opt: one ring lit
        ma["Gate pull-downs"] = GATE_PD
    ma["5 V rail via boost"] = from_5v(five) + BOOST_IDLE
    return ma
```

d) Move the parked dict out of `main()` to module level (below `scenario()`), with the LCD idle
figure, and add the weekend budget:

```python
# Key left on, firmware asleep: what still draws from the cells
PARKED = {"Heltec deep sleep": HELTEC_SLEEP, "PN532 module idle": NFC_IDLE,
          "LCD idle via boost": from_5v(LCD_IDLE_5V) + BOOST_IDLE}
GAME_H, DAYS = 10, 2  # a weekend: two 10 h game days and the night between them parked
NIGHT_H = 12
AGED = 0.8  # cells at 80 % of rated capacity (end of the 35E's rated cycle life)


def weekend_ma():
    """Highest mean game-time current that lasts the weekend at 0 C (-20 %) on aged cells."""
    night = sum(PARKED.values()) * NIGHT_H * (DAYS - 1)
    return (CELLS_MAH * USABLE * 0.8 * AGED - night) / (DAYS * GAME_H)
```

e) In `main()`:
- Change the three `scenario(..., True)` / `scenario(..., False)` backlight arguments: "backlight on"
  becomes `1.0`, "backlight off" becomes `0.0`, the "waiting for HQ" one `0.0`.
- Add `show("Deluxe, game, optimized firmware, backlight on a timeout", scenario(True, True, BACKLIGHT_DUTY, opt=True))`.
- WiFi setup: `from_5v(LCD_ON_5V) + BOOST_IDLE`.
- Delete the "backlight unknown" block (the Newhaven current is in its datasheet).
- Parked block: use `PARKED` instead of the local dict.
- Add the weekend check at the end:

```python
    budget = weekend_ma()
    print(f"\nWeekend ({DAYS} x {GAME_H} h game + {NIGHT_H} h parked, 0 C, cells at {AGED:.0%}): "
          f"game current must stay under {budget:.0f} mA")
    for name, kw in (("today's firmware, backlight on", dict(backlight=1.0)),
                     ("today's firmware, backlight on a timeout", dict(backlight=BACKLIGHT_DUTY)),
                     ("optimized firmware, backlight on a timeout", dict(backlight=BACKLIGHT_DUTY, opt=True))):
        total = sum(scenario(True, True, **kw).values())
        print(f"  {name:44} {total:4.0f} mA  {'PASS' if total < budget else 'FAIL'}"
              f"  ({100 * (budget / total - 1):+.0f} % margin)")
```

f) Update the module docstring: "The one worth measuring first is LCD_BACKLIGHT_5V" becomes
"Measure LCD_IDLE_5V and HELTEC_RX first".

**Step 4: Run it, expect green.**

Run: `cd hardware && /usr/bin/python3 power_budget.py`
Expected: no assertion error. The last block prints a budget of ~350 mA. All three lines PASS, and
the optimized one shows a margin above +30 %. Read the numbers: if "today's firmware, backlight on"
fails, that is a finding to report, not a bug to hide.

**Step 5: Commit.**

```bash
rtk git add hardware/power_budget.py
rtk git commit -m "hardware: power model with the Newhaven LCD and a weekend check"
```

---

### Task E2: off-board parts and ordering switch to the Newhaven LCD

**Files:**
- Modify: `hardware/fab/OFFBOARD_PARTS.md` (row 5 of the parts table, row 5 of the cost table)
- Modify: `hardware/fab/ORDERING.md:131`
- Modify: `docs/plans/2026-09-28-esp32-lora-carrier-design.md:15` and `:128`

**Step 1: Check the outline before writing it down.** Open the datasheet drawing
(https://newhavendisplay.com/content/specs/NHD-0420D3Z-FL-GBW-V3.pdf, page 3). Record the module
outline, the mounting-hole grid and hole diameter, and the P1 pin order. The current doc assumes
98x60 mm with M3 on 93x55: if the Newhaven differs, write the real numbers and flag the enclosure
row (item 22) and the 4 LCD standoffs (item 21).

**Step 2: Replace parts-table row 5** with:

```
| 5 | 20x4 serial LCD, transflective yellow-green | 1 | Mouser | 763-0420D3ZFLGBW-V3 (Newhaven NHD-0420D3Z-FL-GBW-V3) | https://www.mouser.com/c/?q=NHD-0420D3Z-FL-GBW-V3 | ~$17 (also Newhaven direct, DigiKey NHD-0420D3Z-FL-GBW-V3-ND; TME has none). 5 V, <outline from step 1>. STN(+) transflective: readable in daylight with the backlight off. Backlight 1-8 by I2C command. I2C 0x28 (7-bit), **50 kHz max**, 10k pull-ups on the module (carrier R_SDA5/R_SCL5 stay DNP). **☐ Before wiring: bridge jumper R1 (I2C mode)** — it ships in RS-232 mode. **☐ On arrival: measure** 5.0 V supply current at backlight level 8 and level 1; those replace `LCD_ON_5V` and `LCD_IDLE_5V` in `power_budget.py`. Wire P1 VSS/VDD/SDA/SCL to the J_LCD1 XHP-4 (GND 5V SDA SCL). |
```

**Step 3: Replace cost-table row 5** with: `| 5 | **~$17** (Mouser) | generic yellow-green 2004A + PCF8574 (~25 zł) | ~-45 zł | high — on/off backlight only, transmissive, the firmware needs the HD44780 driver back |`

**Step 4:** `ORDERING.md:131`: `20x4 I2C LCD with PCF8574 backpack` becomes
`20x4 serial LCD Newhaven NHD-0420D3Z-FL-GBW-V3 (bridge R1 for I2C)`.

**Step 5:** Carrier design doc: line 15 `a **20x4 I2C LCD**` becomes
`a **20x4 transflective I2C LCD** (Newhaven NHD-0420D3Z-FL-GBW-V3, see the power-efficiency design)`.
Line 128 (LCD driver row) becomes
`| LCD | own driver for the Newhaven command set (0xFE prefix) | I2C 0x28 at 50 kHz, 100 ms power-up delay |`.

**Step 6: Verify nothing still points at the blue part.**

Run: `/usr/bin/grep -rn -E "LCD-02640|HW-61|PCF8574" hardware/fab docs/plans/2026-09-28-esp32-lora-carrier-design.md`
Expected: only the cost-table alternative mentions PCF8574.

**Step 7: Commit.**

```bash
rtk git add hardware/fab/OFFBOARD_PARTS.md hardware/fab/ORDERING.md docs/plans/2026-09-28-esp32-lora-carrier-design.md
rtk git commit -m "docs: Newhaven transflective LCD replaces the blue 2004A"
```

---

### Task E3: firmware C-tasks carry the power requirements

**Files:**
- Modify: `docs/plans/2026-09-28-esp32-lora-carrier-implementation.md` (C2 conventions, C3, C4,
  C6, and a new C8 at the end of phase C)

**Step 1: C2 shared-I2C convention.** `at **100 kHz** (for the PCF8574 and the level shifter)`
becomes `at **50 kHz** (the Newhaven LCD's maximum; the bus traffic is light)`.

**Step 2: Rewrite C3** (keep its heading, Files, and the "redraw only changed lines" step):
- Step 1: `lcd.rs` drives the Newhaven over I2C 0x28: wait 100 ms after power-up; every command is
  `0xFE, cmd[, arg]`. Needed: clear `0x51` (1.5 ms), set cursor `0x45 pos` (row starts
  `0x00, 0x40, 0x14, 0x54`), brightness `0x53 1..8` (100 us), display on `0x41`. Text is plain
  ASCII bytes. Wait each command's execution time *after* sending it.
- Step 2 (replaces the 0x27/0x3F probe): a zero-length write to 0x28. If it NAKs, check jumper R1
  first, then log an error and keep running.
- New step: **backlight policy.** `lcd_task` holds the level at 1 (off) and raises it to the
  configured level (default 6) for 15 s after any button, card or game event, then drops back. The
  core's "blink once per second when depleted" toggles between 1 and the configured level.

**Step 3: C4** gets a note: `CPU at 80 MHz with automatic light sleep from the start (esp-hal
power management); measure the Heltec current before and after. Light only the ring that carries
information (the owning or the active team), never both steadily.`

**Step 4: C6** gets a note: `PN532: send PowerDown (0x16) between polls, poll only while a card is
expected (game armed, admin menu open). Target ~5 mA average.`

**Step 5: Append Task C8 (power) after the last C-task:**

```markdown
### Task C8: Power: GNSS and LoRa duty cycle, then measure the weekend

**Step 1:** GNSS: power VGNSS (GPIO34) at boot, wait for a fix (timeout 5 min), store it, power
off. Re-fix only on admin request.
**Step 2:** LoRa: SX1262 RX duty-cycle mode (SetRxDutyCycle). The sleep window must be shorter than
HQ's preamble; set both in one shared constant and note it in the protocol docs.
**Step 3:** Measure with pack variant A's PAC1934 (per-cell energy accumulators) and a USB meter
on J_PWR1 as a cross-check: 30 min per `power_budget.py` scenario. Replace every EST figure
with the measurement and re-run `power_budget.py`.
**Step 4:** Pass: the weekend check passes with the optimized firmware at >= 30 % margin.
**Step 5:** Soak: full charge, game-loop firmware until the pack MCU disconnects. Record the hours
next to the model's prediction in the power-efficiency design doc.
**Step 6:** Commit: `git commit -m "device: GNSS one-shot fix, LoRa RX duty cycle, power measured"`
```

**Step 6: Verify.**

Run: `/usr/bin/grep -n -F "0x27" docs/plans/2026-09-28-esp32-lora-carrier-implementation.md`
Expected: no hits in C3 (other tasks may mention it only historically; check each hit).

**Step 7: Commit.**

```bash
rtk git add docs/plans/2026-09-28-esp32-lora-carrier-implementation.md
rtk git commit -m "docs: firmware C-tasks carry the power requirements"
```

---

### Task E4: status

**Step 1:** In `2026-10-02-power-efficiency-design.md`, set `Status:` to
`docs and model done (E1-E3); firmware C2-C8 and validation wait for the hardware.`
**Step 2:** Commit: `rtk git commit -am "docs: power efficiency status"`
