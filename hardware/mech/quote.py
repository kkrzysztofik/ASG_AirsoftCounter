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
import sys
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import params as P  # noqa: E402

FAB = HERE / "fab"

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
    f"All dimensions millimetres. Tray and lid are {P.BOX_IN[0]:.0f} x {P.BOX_IN[1]:.0f} mm envelopes; "
    f"they must stay under {P.BOX_IN[0] - 2 * P.FIT:.1f} x {P.BOX_IN[1] - 2 * P.FIT:.1f} mm to drop into the box.",
    f"Critical fit: the 4 corner sleeves are {P.COLUMN_SIZE[0] + P.FIT:.1f} x "
    f"{P.COLUMN_SIZE[1] + P.FIT:.1f} mm bores; a few tenths either way decides whether the part goes in.",
    f"Wall thickness is {P.SLEEVE_WALL:.1f} mm minimum, {P.FLOOR_T:.1f} mm floor; the speaker mesh land "
    f"is {P.MESH_PITCH - P.MESH_HOLE_D:.1f} mm.",
    "No supports modelled. Overhangs are 45 degrees or shallower; please confirm the process does not "
    "need any, or quote support removal if it does.",
    "The quote is for fit and feel, not a production run: it is not yet measured against a physical box.",
]


def file_list(fmt):
    """[(item, zip name, source path)] in quote order. The number prefix keeps the sheet and
    the zip in the same order as the model set."""
    out = []
    for i, (stem, _qty, _note) in enumerate(PARTS, start=1):
        out.append((i, f"{i:02d}_{stem}.{fmt}", HERE / "out" / f"{stem}.{fmt}"))
    return out


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--material", default="MJF PA12 (nylon), black")
    ap.add_argument("--format", default="stl", choices=("stl", "step"))
    args = ap.parse_args(argv)

    files = file_list(args.format)
    absent = [str(path) for _i, _n, path in files if not path.exists()]
    if absent:
        raise SystemExit("missing models, run `make mech` first:\n  " + "\n  ".join(absent))

    FAB.mkdir(exist_ok=True)
    today = datetime.date.today().isoformat()

    zip_path = FAB / f"jlc3dp_{today}_{args.format}.zip"
    raw = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for _item, name, path in files:
            raw += path.stat().st_size
            z.write(path, name)

    csv_path = FAB / f"jlc3dp_quote_{today}_{args.format}.csv"
    with csv_path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Item", "Part", "File", "Qty", "Material", "Colour", "Surface finish",
                    "Tolerance", "Notes"])
        for item, (stem, qty, note), (_i, name, _p) in zip(range(1, len(PARTS) + 1), PARTS, files,
                                                          strict=True):
            w.writerow([item, stem, name, qty, args.material, "black",
                        "as-printed / standard", "standard", note])
        for n in SHOP_NOTES:
            w.writerow(["", "NOTE", "", "", "", "", "", "", n])

    print(f"wrote {zip_path.relative_to(HERE.parent)}  ({len(files)} files, {raw / 1024:.0f} KB)")
    for _i, name, _p in files:
        print(f"  {name}")
    print(f"wrote {csv_path.relative_to(HERE.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
