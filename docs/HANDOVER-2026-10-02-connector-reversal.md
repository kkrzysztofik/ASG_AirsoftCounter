# Handover: 2-wire connectors back to XH-2 (2026-10-02)

Reversed the 2026-09-30 `a42af2a` decision that unified every off-board connector on JST-XH 4-pin
B4B-XH-A (C144395), leaving pins 3-4 no-connect on the 2-wire loads. A 2-wire load now gets a 2-pin
B2B-XH-A (C158012); the four 4-wire connectors (LCD, NFC, BTN_R, BTN_B) and the 6-pin pack link
(J_PWR1, B6B-XH-A C144397) are unchanged.

Why: the unification bought one connector part number, but forced a 4-pin harness housing on every
2-wire lead and pushed J_BTN_R1 off the top edge for width. Both parts are through-hole Extended
types, so the 2-pin addition carries no feeder-setup fee, and it is cheaper per board.

## Changed

- `design.py`: `XH2` footprint; `J_HBAT1`/`J_BUZ1`/`J_SPK1` -> `Conn_01x02` + XH2; LCSC split
  (C158012 vs C144395); `XH_SPARE` gone. Top edge re-spaced at pad-1 x 10 / 30.5 / 41 / 56.5 / 72 for
  J_PWR1 / J_HBAT1 / J_BTN_R1 / J_LCD1 / J_NFC1 (~2 mm courtyard gaps). J_BTN_R1 is back on the top
  edge and its `REF_AT` workaround is gone.
- `gen_sch.py`: dropped the `XH_SPARE` no-connect test.
- `gen_pcb.py`: dropped the stale "2-wire connectors on 4-pin XH" label comment.
- `pack.py`: `J_KEY1` -> XH2 / C158012; `XH4` and `XH_SPARE` gone. Position unchanged (the freed
  length buys nothing on the right edge).
- `fab/ORDERING.md`, `fab/OFFBOARD_PARTS.md`: THT type counts, silk/preview note, housing list, backups.

## Verified

- `make boards` on KiCad 9.0.8: carrier 522 tracks, pack 1394 tracks, both 0 unrouted; ERC 0 errors /
  0 warnings and DRC 0 violations on both; `fab/` and `fab/pack/` regenerated.
- Carrier BOM gained one line: the 4-pin C144395 (LCD/NFC/BTN_R/BTN_B) and 2-pin C158012
  (HELTEC_BAT/BUZ/SPK) connector lines are now separate.
- C158012 checked live on LCSC: JST B2B-XH-A(LF)(SN), XH 2.5 mm THT, 2P, 3 A / 250 V, 322,420 in
  stock, $0.0409 at 20+.
