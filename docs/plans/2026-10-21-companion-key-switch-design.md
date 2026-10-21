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
| Barrel | double-D: 11.2 mm round, 10.5 mm across flats |
| Behind panel incl. terminals | 15.9 mm |
| Front collar | 14 mm diameter (vendor page) |
| Thread length, nut size | MEASURE (sets the maximum plate thickness) |

## Design

1. **Lengthen.** Cut both shells at y = +31.5 (past the vent slots at y 23..30, before the end screw
   bosses at y = 36 and past the board at the USB end). Move everything beyond the plane +20 mm in y and
   fill the gap with the extruded cross-section. The plane cuts only the compartment's side walls and
   floor, the flat front plate, and the antenna tunnel. Both shells take the same shift, so the end
   screws still line up. Length becomes 84.4 -> 104.4 mm.
2. **Hole.** A D-shaped hole (11.2 mm round, 10.5 mm across the flats, plus 0.2 mm clearance) through
   FK's front plate at about (x +8, y +41.5), centred in the new strip and right of the antenna arc.
   The flat stops the switch turning under the key. The collar sits on the outside and the nut clamps
   from inside.
3. **Space behind.** About 22 mm of inside height (FK plate underside 9.6 to BK floor -12.3) leaves about
   4 mm below the 15.9 mm body for wires.
4. **Wiring.** Battery + -> switch -> Heltec SH1.25 battery socket, the same as the carrier's J_KEY.

## Checks (in the script, failing on violation)

- The switch envelope (14 mm diameter x 20 mm cylinder below the plate) does not intersect FK or BK.
- At least 1.6 mm of plate around the D-hole, and the plate is no thicker than the switch's thread allows.
- The antenna bay is still clear at 13.5 mm over its full (now longer) length.
- Each shell is one watertight body, and the FK/BK screw holes still line up.

## Assumptions

- The board sits at the USB end (y -40..+12), and nothing that locates it crosses y = +31.5.
- The battery pouch lies in BK's compartment.
- Placement is checked against the mesh, not a real-board assembly. Print a test before the final part.
