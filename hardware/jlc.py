"""Write the JLCPCB assembly (PCBA) files from design.py and the routed board, and validate them.

fab/jlc_bom.csv  (deluxe; other variants: jlc_bom_<variant>.csv) Comment,Designator,Footprint,LCSC Part #   one row per LCSC number
fab/jlc_cpl.csv  Designator,Mid X,Mid Y,Layer,Rotation      one row per placed part (SMD and THT)
Placed parts are design.assembled(): no DNP parts, no mounting holes.

Placements come from the board via pcbnew. Coordinates are in the Gerber convention: board X, board
Y negated (the board is Y-down with its origin at the top-left corner, the Gerbers are Y-up), so the
board spans X 0..90, Y -60..0 mm in both and JLC lines them up. Mid X/Y is the centre of the F.CrtYd
courtyard, not the footprint anchor: THT footprints (pin sockets, JST-XH, radial caps) are anchored
on pin 1, which would put J2/J3 21.6 mm off in JLC's preview. Rotation is KiCad's, with no JLC
correction (ORDERING.md lists the parts to check in the preview).

/usr/bin/python3 jlc.py   (after `make fab` has built the Gerber zip)
"""
import csv
import re
import sys
import zipfile
from pathlib import Path

import pcbnew  # pyright: ignore[reportMissingImports]

from board import design  # pyright: ignore[reportMissingImports]

HERE = Path(__file__).parent
PCB = HERE / f"{design.NAME}.kicad_pcb"
ZIP = HERE / f"fab/{design.NAME}_gerbers_jlcpcb.zip"
DEFAULT_VARIANT = next(iter(design.VARIANTS))  # carrier: deluxe; pack: standard


def out(kind, variant):
    """The default (first) variant is the unsuffixed fab/jlc_<kind>.csv; other variants get a suffix."""
    return HERE / f"fab/jlc_{kind}{'' if variant == DEFAULT_VARIANT else '_' + variant}.csv"


def natural(ref):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", ref)]


def bom_rows(variant):
    groups = {}
    for r in sorted(design.assembled(variant), key=natural):
        value, _, fp = design.PARTS[r]
        groups.setdefault(design.LCSC[(value, fp)], []).append(r)
    rows = []
    for lcsc, refs in groups.items():
        fps = {design.PARTS[r][2].split(":")[1] for r in refs}
        assert len(fps) == 1, f"{lcsc} used on several footprints: {fps}"
        values = dict.fromkeys(design.PARTS[r][0] for r in refs)  # connectors: one name each
        rows.append(["/".join(values), ",".join(refs), fps.pop(), lcsc])
    return sorted(rows, key=lambda row: natural(row[1]))


def board_outline():
    """Edge.Cuts extent from the Gerber itself: (xmin, xmax, ymin, ymax) in mm."""
    with zipfile.ZipFile(ZIP) as z:
        edge = z.read(f"{design.NAME}-Edge_Cuts.gm1").decode()
    xs, ys = zip(*((int(x) / 1e6, int(y) / 1e6) for x, y in re.findall(r"^X(-?\d+)Y(-?\d+)", edge, re.M)),
                strict=True)
    return min(xs), max(xs), min(ys), max(ys)


def cpl_rows(variant):
    placed = set(design.assembled(variant))
    fps = [fp for fp in pcbnew.LoadBoard(str(PCB)).GetFootprints() if fp.GetReference() in placed]
    refs = [fp.GetReference() for fp in fps]
    dupes = {r for r in refs if refs.count(r) > 1}
    assert not dupes and set(refs) == placed, f"board: duplicates {dupes}, missing {placed - set(refs)}"
    xmin, xmax, ymin, ymax = board_outline()
    rows = []
    for fp in sorted(fps, key=lambda fp: natural(fp.GetReference())):
        ref = fp.GetReference()
        crtyd = fp.GetCourtyard(pcbnew.F_CrtYd)
        assert crtyd.OutlineCount(), f"{ref} has no F.CrtYd courtyard"
        c = crtyd.BBox().Centre()
        x, y = c.x / 1e6, -c.y / 1e6
        assert xmin < x < xmax and ymin < y < ymax, \
            f"{ref} at ({x}, {y}) is outside the Gerber outline {xmin}..{xmax} x {ymin}..{ymax}"
        layer = "Bottom" if fp.IsFlipped() else "Top"
        rows.append([ref, f"{x:.4f}mm", f"{y:.4f}mm", layer, f"{fp.GetOrientationDegrees() % 360:g}"])
    return rows


def write(path, header, rows):
    try:
        with open(path, "w", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(header)
            w.writerows(rows)
    except OSError as e:
        raise SystemExit(f"cannot write {path}: {e}") from e


def main():
    design.check()
    for variant in design.VARIANTS:
        bom, cpl = bom_rows(variant), cpl_rows(variant)
        assert all(re.fullmatch(r"C\d+", row[3]) for row in bom), "BOM row without an LCSC number"
        bom_refs = [r for row in bom for r in row[1].split(",")]
        cpl_refs = [row[0] for row in cpl]
        assert sorted(bom_refs) == sorted(cpl_refs) and len(set(bom_refs)) == len(bom_refs), \
            f"{variant}: BOM/CPL designators differ: {set(bom_refs) ^ set(cpl_refs)}"
        write(out("bom", variant), ["Comment", "Designator", "Footprint", "LCSC Part #"], bom)
        write(out("cpl", variant), ["Designator", "Mid X", "Mid Y", "Layer", "Rotation"], cpl)
        print(f"jlc ok ({variant}): {len(bom)} BOM lines, {len(cpl)} placements inside the Gerber outline")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        sys.exit(f"jlc check FAILED: {e}")
