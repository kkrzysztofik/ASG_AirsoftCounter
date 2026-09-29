"""Sanity-check the JLCPCB zip by parsing the Gerber/Excellon text, independent of KiCad's DRC.

/usr/bin/python3 check_gerbers.py [fab/carrier_gerbers_jlcpcb.zip]
"""
import re
import sys
import zipfile

LAYERS = ["F_Cu.gtl", "B_Cu.gbl", "F_Mask.gts", "B_Mask.gbs", "F_Paste.gtp", "B_Paste.gbp",
          "F_Silkscreen.gto", "B_Silkscreen.gbo", "Edge_Cuts.gm1"]
EXPECTED = {f"carrier-{x}" for x in LAYERS} | {"carrier-PTH.drl", "carrier-NPTH.drl"}
SIZE_MM = (90.0, 60.0)


def tools(text):
    return {t: float(d) for t, d in re.findall(r"^(T\d+)C([\d.]+)", text, re.M)}


def hits(text, tool):
    body = text.split("%", 1)[1]  # after the header
    return len(re.findall(r"^X", body.split(f"\n{tool}\n", 1)[1].split("\nT", 1)[0], re.M))


def check(path="fab/carrier_gerbers_jlcpcb.zip"):
    errors = []
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        files = {n: z.read(n).decode() for n in names}
    if names != EXPECTED:
        errors.append(f"zip contents: missing {sorted(EXPECTED - names)}, extra {sorted(names - EXPECTED)}")
    errors += [f"{n} is empty" for n, t in files.items() if not t.strip()]

    edge = files.get("carrier-Edge_Cuts.gm1", "")
    if "%FSLAX46Y46*%" not in edge or "%MOMM*%" not in edge:
        errors.append("Edge.Cuts: expected mm, 4.6 format")
    xs = [int(x) / 1e6 for x in re.findall(r"X(-?\d+)", edge)]
    ys = [int(y) / 1e6 for y in re.findall(r"Y(-?\d+)", edge)]
    if not xs or not ys:
        raise SystemExit("gerber check FAILED: Edge.Cuts has no coordinates")
    size = (round(max(xs) - min(xs), 3), round(max(ys) - min(ys), 3))
    if size != SIZE_MM:
        errors.append(f"Edge.Cuts extent {size}, want {SIZE_MM}")

    pth, npth = files.get("carrier-PTH.drl", ""), files.get("carrier-NPTH.drl", "")
    for n, t in (("PTH", pth), ("NPTH", npth)):
        if "METRIC" not in t:
            errors.append(f"{n} drill not metric")
    pt = tools(pth)
    if 0.3 not in pt.values():
        errors.append(f"PTH: no 0.3 mm via drill in {sorted(pt.values())}")
    if min((d for d in pt.values() if d != 0.3), default=0) < 0.8:
        errors.append(f"PTH: component drill below 0.8 mm in {sorted(pt.values())}")
    nt = tools(npth)
    if sorted(nt.values()) != [3.2] or hits(npth, next(iter(nt))) != 4:
        errors.append(f"NPTH: want 4 x 3.2 mm, got {nt}")
    if 3.2 in pt.values():
        errors.append("PTH: 3.2 mm mounting hole in the plated file")
    return errors, size, pt, nt, names


if __name__ == "__main__":
    errors, size, pt, nt, names = check(*sys.argv[1:2])
    if errors:
        sys.exit("gerber check FAILED:\n  " + "\n  ".join(errors))
    print(f"gerbers ok: {len(names)} files, outline {size[0]} x {size[1]} mm, "
          f"PTH drills {sorted(set(pt.values()))} mm, NPTH 4 x {nt[next(iter(nt))]} mm")
