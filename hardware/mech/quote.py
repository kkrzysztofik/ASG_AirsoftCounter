#!/usr/bin/env python3
"""Pack the printed parts for a JLC3DP (JLCPCB 3D printing) quote.

One model file per part inside a single zip, plus the quote sheet with a row per part.
Runs on a plain /usr/bin/python3: zipping files needs no CAD stack, so this works on a
machine that cannot build the models.

    /usr/bin/python3 hardware/mech/quote.py [--material "..."] [--format stl|step]
"""

import argparse
import csv
import datetime
import pathlib
import struct
import sys
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import params as P  # noqa: E402

FAB = HERE / "fab"
# What the quote is priced against. The material label follows the process, so a quote prepared
# with MECH_PROCESS=fdm cannot claim to be MJF.
MATERIAL_BY_PROCESS = {
    "mjf": "MJF PA12 (nylon), black",
    "fdm": "FDM PETG",
    "sla": "SLA 9000R resin",
}
MATERIAL = MATERIAL_BY_PROCESS.get(P.PROCESS, MATERIAL_BY_PROCESS["mjf"])

# (order, file stem, qty, note). Order is the row order on the sheet and the filename prefix,
# so the quote lines up with the drawing.
PARTS = [
    ("tray", 1, "base tray: corner sleeves, cell saddles, board posts, cable clips, wall backings"),
    ("lid", 1, "lid panel: LCD frame, button bosses, NFC opening, corner ears"),
    ("grille", 1, f"speaker mesh, {P.MESH_OPEN:.0%} open area, {P.SPEAKER_D:.0f} mm"),
    ("guide", 1, f"drill guide ring for the {P.SPEAKER_D:.0f} mm holesaw"),
]
for _dev, _wp in P.WALL_PARTS.items():
    PARTS.append((f"bushing_{_dev}", 1, f"wall bushing, {_wp['hole_d']:.1f} mm hole to {_wp['device_d']:.1f} mm device"))

# These are the things a print shop has to be told and the model cannot carry.
SHOP_NOTES = [
    f"Quoted process: {MATERIAL}, dyed. Thinnest wall {P.SLEEVE_WALL:.1f} mm, thinnest feature "
    f"{P.MESH_PITCH - P.MESH_HOLE_D:.1f} mm (the speaker mesh land): both inside MJF's minimum, "
    "so no feature needs thickening for the process.",
    f"All dimensions millimetres. The box interior is {P.BOX_IN[0]:.0f} x {P.BOX_IN[1]:.0f} mm and the "
    f"tray and lid are {P.BOX_IN[0] - 2 * P.FIT:.1f} x {P.BOX_IN[1] - 2 * P.FIT:.1f} mm, so they drop in "
    "with 0.4 mm all round: please hold that outside envelope and do not grow it.",
    f"Critical fit: the 4 corner sleeves are {P.COLUMN_SIZE[0] + P.FIT:.1f} x "
    f"{P.COLUMN_SIZE[1] + P.FIT:.1f} mm bores; a few tenths either way decides whether the part goes in. "
    "Please keep that bore to the nominal and tell me the as-built figure.",
    f"Wall thickness is {P.SLEEVE_WALL:.1f} mm minimum, {P.FLOOR_T:.1f} mm floor; the speaker mesh land "
    f"is {P.MESH_PITCH - P.MESH_HOLE_D:.1f} mm.",
    "No supports modelled. Overhangs are 45 degrees or shallower, which MJF does not need anyway.",
    "The 4 board posts take M3 self-tapping screws; a standard MJF PA12 pilot is fine.",
    "Checked against the JLC3DP 3D printing design guideline (MJF column) and compliant: build "
    "size, size-dependent wall thickness, 0.2-0.4 mm assembly clearance, hole aperture vs depth, "
    "small-column H/D with a base flare, and no enclosed cavities so no escape holes are needed.",
    "The tray and lid are large hollow shells, which the guideline prices as a special-shaped "
    "model; please say if that carries a surcharge before we commit.",
    "The quote is for fit and feel, not a production run: it is not yet measured against a physical box.",
]


def stl_volume_cm3(path):
    """Solid volume of a binary STL, by the signed-tetrahedron sum.

    Independent of the CAD: it reports what the mesh the shop receives actually encloses, so a
    bad export shows up as a wrong number here rather than as a wrong price on the invoice.
    """
    data = path.read_bytes()
    if len(data) < 84:
        raise ValueError(f"{path.name}: too short to be an STL")
    count = struct.unpack_from("<I", data, 80)[0]
    if len(data) != 84 + count * 50:
        raise ValueError(f"{path.name}: not a binary STL ({count} facets, {len(data)} bytes)")
    total = 0.0
    for i in range(count):
        # facet record: 12-byte normal, then 3 vertices as 9 floats (36 bytes), then 2 bytes
        v = struct.unpack_from("<9f", data, 84 + i * 50 + 12)
        (ax, ay, az, bx, by, bz, cx, cy, cz) = v[0:9]
        total += (ax * (by * cz - bz * cy)
                  - ay * (bx * cz - bz * cx)
                  + az * (bx * cy - by * cx)) / 6.0
    return abs(total) / 1000.0


def file_list(fmt, wanted=None):
    """[(item, zip name, source path)] in quote order. The number prefix keeps the sheet and
    the zip in the same order as the model set. `wanted` filters to the parts a process can
    actually make, so an FDM quote never carries the small flat parts it rejects."""
    out = []
    for i, (stem, _qty, _note) in enumerate(PARTS, start=1):
        if wanted and stem not in wanted:
            continue
        out.append((i, f"{i:02d}_{stem}.{fmt}", HERE / "out" / f"{stem}.{fmt}"))
    return out


def want_list(raw):
    if not raw or raw == "all":
        return None
    want = [p.strip() for p in raw.split(",") if p.strip()]
    known = {stem for stem, _q, _n in PARTS}
    unknown = [p for p in want if p not in known]
    if unknown:
        raise SystemExit(f"unknown part(s) {unknown}; known: {', '.join(sorted(known))}")
    return set(want)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--material", default=MATERIAL)
    ap.add_argument("--rate", type=float, default=0.55,
                    help="estimated price per cm3, for the estimate column only")
    ap.add_argument("--format", default="stl", choices=("stl", "step"))
    ap.add_argument("--parts", default="all",
                    help="comma-separated part names, or all")
    args = ap.parse_args(argv)

    wanted = want_list(args.parts)
    files = file_list(args.format, wanted)
    absent = [str(path) for _i, _n, path in files if not path.exists()]
    if absent:
        raise SystemExit("missing models, run `make mech` first:\n  " + "\n  ".join(absent))

    FAB.mkdir(exist_ok=True)
    today = datetime.date.today().isoformat()

    zip_path = FAB / f"jlc3dp_{today}_{P.PROCESS}_{args.format}.zip"
    raw = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for _item, name, path in files:
            raw += path.stat().st_size
            z.write(path, name)

    csv_path = FAB / f"jlc3dp_quote_{today}_{P.PROCESS}_{args.format}.csv"
    total_cm3 = 0.0
    with csv_path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Item", "Part", "File", "Qty", "Volume cm3", f"Est cost @{args.rate}/cm3",
                    "Material", "Colour", "Surface finish", "Tolerance", "Notes"])
        for item, (stem, qty, note), (_i, name, path) in zip(range(1, len(PARTS) + 1), PARTS, files,
                                                            strict=False):
            if wanted and stem not in wanted:
                continue
            vol = stl_volume_cm3(path) if args.format == "stl" else float("nan")
            known = vol == vol  # NaN-safe: a STEP zip has no mesh to measure
            total_cm3 += vol if known else 0.0
            w.writerow([item, stem, name, qty, f"{vol:.1f}" if known else "",
                        f"{vol * args.rate * qty:.2f}" if known else "",
                        args.material, "black", "as-printed / standard", "standard", note])
        w.writerow(["", "TOTAL", "", sum(q for s, q, _n in PARTS if not wanted or s in wanted),
                    f"{total_cm3:.1f}", f"{total_cm3 * args.rate:.2f}", args.material, "", "", "",
                    "Estimate from solid volume only; the shop prices its own build."])
        for n in SHOP_NOTES:
            w.writerow(["", "NOTE", "", "", "", "", "", "", "", "", n])

    print(f"wrote {zip_path.relative_to(HERE.parent)}  ({len(files)} files, {raw / 1024:.0f} KB)")
    for _i, name, _p in files:
        print(f"  {name}")
    print(f"wrote {csv_path.relative_to(HERE.parent)}")
    if total_cm3:
        print(f"solid volume {total_cm3:.1f} cm3, roughly {total_cm3 * args.rate:.0f}"
              f" at {args.rate}/cm3")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
