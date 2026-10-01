"""Sanity-check the JLCPCB zip by parsing the Gerber/Excellon text, independent of KiCad's DRC.

Checks: exact file set; layers that must draw contain draw/flash commands; Edge.Cuts is mm and its
extent matches design.SIZE_MM; drills are metric; PTH has 0.3 mm vias and no component drill under
design.PTH_COMPONENT_MIN (0.8 mm default); NPTH is the 4 x 3.2 mm mounting holes, or exactly
design.NPTH_EXPECT when the board's footprints add their own NPTH drills (holders, USB-C shell).
Not checked: that the outline is closed (DRC upstream covers it).

/usr/bin/python3 check_gerbers.py [fab/<BOARD>_gerbers_jlcpcb.zip]
"""
import re
import sys
import zipfile

from board import design  # pyright: ignore[reportMissingImports]

LAYERS = ["F_Cu.gtl", "B_Cu.gbl", "F_Mask.gts", "B_Mask.gbs", "F_Paste.gtp", "B_Paste.gbp",
          "F_Silkscreen.gto", "B_Silkscreen.gbo", "Edge_Cuts.gm1"]
MUST_DRAW = set(LAYERS) - {"B_Paste.gbp", "B_Silkscreen.gbo"}  # no bottom parts or bottom silk
EXPECTED = {f"{design.NAME}-{x}" for x in LAYERS} | {f"{design.NAME}-PTH.drl", f"{design.NAME}-NPTH.drl"}


def tools(text):
    return {t: float(d) for t, d in re.findall(r"^(T\d+)C([\d.]+)", text, re.M)}


def npth_hits(text):
    """[(x, y, drill)] per Excellon hit (tools are declared T<n>C<d> in the header, selected as T<n>)."""
    diam = {t: float(d) for t, d in re.findall(r"^(T\d+)C([\d.]+)", text, re.M)}
    out, cur = [], None
    for line in text.splitlines():
        m = re.match(r"^(T\d+)$", line.strip())
        if m:
            cur = diam.get(m.group(1))
            continue
        m = re.match(r"^X([-\d.]+)Y([-\d.]+)", line)
        if m and cur is not None:
            out.append((abs(float(m.group(1))), abs(float(m.group(2))), cur))
    return out


def check(path=f"fab/{design.NAME}_gerbers_jlcpcb.zip"):
    """Return (errors, summary)."""
    errors = []
    with zipfile.ZipFile(path) as z:
        files = {n: z.read(n).decode() for n in z.namelist()}
    names = set(files)
    if names != EXPECTED:
        errors.append(f"zip contents: missing {sorted(EXPECTED - names)}, extra {sorted(names - EXPECTED)}")
    errors += [f"{x} has no draw/flash commands" for x in sorted(MUST_DRAW)
               if not re.search(r"D0[13]\*", files.get(f"{design.NAME}-{x}", ""))]

    edge = files.get(f"{design.NAME}-Edge_Cuts.gm1", "")
    if "%FSLAX46Y46*%" not in edge or "%MOMM*%" not in edge:
        errors.append("Edge.Cuts: expected mm, 4.6 format")
    xy = [(int(x) / 1e6, int(y) / 1e6) for x, y in re.findall(r"^X(-?\d+)Y(-?\d+)", edge, re.M)]
    size = None
    if xy:
        xs, ys = zip(*xy, strict=True)
        size = (round(max(xs) - min(xs), 3), round(max(ys) - min(ys), 3))
    if size != design.SIZE_MM:
        errors.append(f"Edge.Cuts extent {size}, want {design.SIZE_MM}")

    pth, npth = files.get(f"{design.NAME}-PTH.drl", ""), files.get(f"{design.NAME}-NPTH.drl", "")
    errors += [f"{n} drill not metric" for n, t in (("PTH", pth), ("NPTH", npth)) if "METRIC" not in t]
    pt = sorted(set(tools(pth).values()))
    if 0.3 not in pt:
        errors.append(f"PTH: no 0.3 mm via drill in {pt}")
    if min((d for d in pt if d != 0.3), default=0) < getattr(design, "PTH_COMPONENT_MIN", 0.8):
        errors.append(f"PTH: component drill below {getattr(design, 'PTH_COMPONENT_MIN', 0.8)} mm in {pt}")
    if 3.2 in pt:
        errors.append("PTH: 3.2 mm mounting hole in the plated file")
    hits = [(round(x, 3), round(y, 3), d) for x, y, d in npth_hits(npth)]
    want = getattr(design, "NPTH_EXPECT", None)  # board may add the footprints' own NPTH drills
    if want is not None:
        want = sorted((round(x, 3), round(y, 3), d) for x, y, d in want)
        if sorted(hits) != want:
            errors.append(f"NPTH hits {sorted(hits)} != expected {want}")
    else:
        # single tool, so every coordinate line is a 3.2 mm hit; Excellon Y is negative (board is y-down)
        holes = sorted((x, y) for x, y, _ in hits)
        nt = sorted({d for _, _, d in hits})
        if nt != [3.2] or holes != design.NPTH_XY:
            errors.append(f"NPTH: want 3.2 mm at {design.NPTH_XY}, got tools {nt} at {holes}")
    nt = sorted({d for _, _, d in hits})
    return errors, f"{len(names)} files, outline {size} mm, PTH drills {pt} mm, NPTH {len(hits)} x {nt} mm"


if __name__ == "__main__":
    errors, summary = check(*sys.argv[1:2])
    if errors:
        sys.exit("gerber check FAILED:\n  " + "\n  ".join(errors))
    print(f"gerbers ok: {summary}")
