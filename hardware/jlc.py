"""Write the JLCPCB assembly (PCBA) files from design.py and the routed board, and validate them.

fab/jlc_bom.csv  Comment,Designator,Footprint,LCSC Part #   one row per LCSC number
fab/jlc_cpl.csv  Designator,Mid X,Mid Y,Layer,Rotation      one row per placed part (SMD and THT)
Placed parts are design.assembled(): no DNP parts, no mounting holes.

Coordinates come from `kicad-cli pcb export pos` (raw file in build/pos.csv). Like the Gerbers it
uses the page origin with Y negated, so the board spans X 0..90, Y -60..0 mm in both and JLC lines
them up. Mid X/Y is the centre of the pads, not the footprint anchor: THT footprints (pin sockets,
JST-XH, radial caps) are anchored on pin 1, which would put J2/J3 21.6 mm off in JLC's preview.
Rotation is KiCad's, with no JLC correction (ORDERING.md lists the parts to check in the preview).

/usr/bin/python3 jlc.py   (after `make fab` has built the Gerber zip)
"""
import csv
import re
import subprocess
import sys
import zipfile
from pathlib import Path

import pcbnew

import design

HERE = Path(__file__).parent
PCB = HERE / "carrier.kicad_pcb"
POS = HERE / "build/pos.csv"
ZIP = HERE / "fab/carrier_gerbers_jlcpcb.zip"
BOM = HERE / "fab/jlc_bom.csv"
CPL = HERE / "fab/jlc_cpl.csv"


def natural(ref):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", ref)]


def bom_rows():
    groups = {}
    for r in sorted(design.assembled(), key=natural):
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
        edge = z.read("carrier-Edge_Cuts.gm1").decode()
    xs, ys = zip(*((int(x) / 1e6, int(y) / 1e6) for x, y in re.findall(r"^X(-?\d+)Y(-?\d+)", edge, re.M)))
    return min(xs), max(xs), min(ys), max(ys)


def cpl_rows():
    subprocess.run(["kicad-cli", "pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "both",
                    "-o", str(POS), str(PCB)], check=True, capture_output=True)
    with open(POS, newline="") as f:
        pos = list(csv.DictReader(f))
    placed = set(design.assembled())
    pos = [p for p in pos if p["Ref"] in placed]
    refs = [p["Ref"] for p in pos]
    dupes = {r for r in refs if refs.count(r) > 1}
    assert not dupes and set(refs) == placed, \
        f"pos file: duplicates {dupes}, missing {placed - set(refs)}"

    fps = {fp.GetReference(): fp for fp in pcbnew.LoadBoard(str(PCB)).GetFootprints()}
    xmin, xmax, ymin, ymax = board_outline()
    rows = []
    for p in sorted(pos, key=lambda p: natural(p["Ref"])):
        fp = fps[p["Ref"]]
        # pos export = board coordinates with Y negated; confirm before mixing in pcbnew data
        anchor = (fp.GetPosition().x / 1e6, -fp.GetPosition().y / 1e6)
        assert abs(anchor[0] - float(p["PosX"])) < 1e-3 and abs(anchor[1] - float(p["PosY"])) < 1e-3, \
            f"{p['Ref']}: pos {p['PosX']},{p['PosY']} is not board {anchor} with Y negated"
        px = [pad.GetPosition().x / 1e6 for pad in fp.Pads()]
        py = [-pad.GetPosition().y / 1e6 for pad in fp.Pads()]
        x, y = (min(px) + max(px)) / 2, (min(py) + max(py)) / 2
        assert xmin < x < xmax and ymin < y < ymax, \
            f"{p['Ref']} at ({x}, {y}) is outside the Gerber outline {xmin}..{xmax} x {ymin}..{ymax}"
        layer = {"top": "Top", "bottom": "Bottom"}[p["Side"]]
        rows.append([p["Ref"], f"{x:.4f}mm", f"{y:.4f}mm", layer, f"{float(p['Rot']) % 360:g}"])
    return rows


def write(path, header, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def main():
    bom, cpl = bom_rows(), cpl_rows()
    assert all(re.fullmatch(r"C\d+", row[3]) for row in bom), "BOM row without an LCSC number"
    bom_refs = [r for row in bom for r in row[1].split(",")]
    cpl_refs = [row[0] for row in cpl]
    assert sorted(bom_refs) == sorted(cpl_refs) and len(set(bom_refs)) == len(bom_refs), \
        f"BOM/CPL designators differ: {set(bom_refs) ^ set(cpl_refs)}"
    write(BOM, ["Comment", "Designator", "Footprint", "LCSC Part #"], bom)
    write(CPL, ["Designator", "Mid X", "Mid Y", "Layer", "Rotation"], cpl)
    print(f"jlc ok: {len(bom)} BOM lines, {len(cpl)} placements inside the Gerber outline")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        sys.exit(f"jlc check FAILED: {e}")
