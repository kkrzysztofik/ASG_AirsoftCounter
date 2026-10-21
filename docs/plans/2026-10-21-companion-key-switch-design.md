# Companion case: key switch on the front plate

## Goal

Add a key switch (Blow SWT-06357, ON-OFF SPST, two keys) in series with the LiPo pouch of the
Heltec WiFi LoRa32 V4 companion, mounted on the front plate. Lengthen the case so the switch costs
no battery or board space.

## Source

`hardware/companion/heltec-wifi-lora32-v4-wk-gps.3mf` is a mesh-only Bambu Studio project
(no parametric source). `widen_antenna_bay.py` already rewrites its two shells:

- FK (`3D/Objects/object_1.model`): front shell, z -11.58..11.58, parting plane at z = -2.14.
- BK (`3D/Objects/object_7.model`): back shell, z -6..6; its rim (z = 6) meets FK's parting plane,
  so BK sits at dz = -8.14 in FK's frame.
- The antenna side was stretched 1.6 mm in -x and bored to 13.5 mm (antenna base 12.5 mm).

## Switch (measured)

| Feature | Value |
|---|---|
| Barrel | double-D: 11.2 mm round, 10.5 mm across flats (flats left/right) |
| Behind panel incl. terminals | 15.9 mm |
| Front collar | 14 mm diameter (vendor page) |
| Mounting | push-in, locking tab, no thread or nut; the tab grips a 2 mm panel (measured) |

## Design

1. **Lengthen.** Cut both shells at y = +20.5 and move everything beyond the plane +20 mm in y,
   filling the gap with the extruded cross-section. A scan of the switch column (x 1..15,
   z -6.6..9.5) at 1 mm steps found it clear for y 19..22.5. At y = 20.5 the section is only the 2 mm
   front plate (underside 9.58, top 11.58), the compartment's side walls and floor, and the antenna
   tunnel. The display pocket ends by y 18.5 and the vent slots start at about 23. y = +31.5 was
   rejected: an internal pocket hangs from the plate there (x -7..14, down to z -6.3), and extruding
   it would put walls through the switch. Both shells take the same shift, so the end screws still line
   up. Length becomes 84.4 -> 104.4 mm.
2. **Hole.** A double-D hole (round top and bottom, flat left and right, i.e. flats facing ±x;
   11.2 mm round, 10.5 mm across the flats, plus 0.2 mm clearance) through the
   front plate at (x +8, y +30.5), centred in the new strip. The section at y = 20.5 carries 1 mm-deep
   decorative grooves on the plate top (x about -4..20). Extruded, they would become 20 mm ribs under
   the 14 mm collar, so the new strip is filled flat over x -5..21. The flats stop the switch turning
   under the key. The switch pushes in from the front and its tab snaps behind the plate. The plate
   must stay 2.0 mm thick at the hole, which it already is, so there is no thinning pocket.
3. **Space behind.** The body reaches z -6.3, and BK's floor is at -12.3, so about 6 mm is left below
   for wires. A pouch can still run under the switch if it is 5 mm thick or less.
4. **Wiring.** Battery + -> switch -> Heltec SH1.25 battery socket, the same as the carrier's J_KEY.

## Checks (in the script, failing on violation)

- The switch envelope (14 mm diameter x 16.2 mm cylinder below the plate) does not intersect FK or BK.
- At least 1.6 mm of plate around the hole, and the plate there is 2.0 ±0.1 mm (the tab's grip).
- The antenna bay is still clear at 13.5 mm over its full (now longer) length.
- The hole is open, and the plate is flat at full height on a ring just outside the collar.
- Each shell is one watertight body. Both shells get the identical transform, so the screw holes need
  no separate check.

## Electrical rating (open)

The SWT-06357 has no published electrical rating. The LoRa companion design (Part 5) requires a
documented ≥ 1 A DC rating at 3.7 V (2 A preferred), or a hot-switch bench test at 1 A, before the
switch is used in the cell lead. The real load is ~0.14 A RMS; TX peaks are well under 1 A at the
≤ 25.5 dBm conducted setpoint.

## Assumptions

- The board sits at the USB end (y -40..+12), and nothing that locates it crosses y = +20.5.
- The battery pouch lies in BK's compartment.
- Placement is checked against the mesh, not a real-board assembly. Print a test before the final part.
