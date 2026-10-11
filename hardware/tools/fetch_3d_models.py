#!/usr/bin/env python3
"""Fetch just the KiCad 3D models our boards reference, into hardware/kicad/3dmodels/.

The full kicad-packages3D library is gigabytes; the boards use a few dozen models. With these
in place the mech assembly gate sees real components instead of bare plates (insert.py points
kicad-cli at this folder). Plain Python, no dependencies:

    /usr/bin/python3 hardware/tools/fetch_3d_models.py
"""

import pathlib
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

HW = pathlib.Path(__file__).resolve().parent.parent
DEST = HW / "kicad" / "3dmodels"
API = "https://gitlab.com/api/v4/projects/kicad%2Flibraries%2Fkicad-packages3D/repository/files/{}/raw?ref={}"
REFS = ("9.0.8", "master")  # the tag matching kicad-cli 9.0.8 first, then newer models


def referenced():
    paths = set()
    for pcb in (HW / "kicad").glob("*.kicad_pcb"):
        paths.update(re.findall(r'\(model "\$\{KICAD9_3DMODEL_DIR\}/([^"]+)"', pcb.read_text()))
    return sorted(paths)


def fetch(rel):
    for ref in REFS:
        url = API.format(urllib.parse.quote(rel, safe=""), ref)
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                raise
    return None


def main():
    got, missing = 0, []
    for rel in referenced():
        dest = DEST / rel
        if dest.exists():
            continue
        data = fetch(rel)
        if data is None:
            missing.append(rel)
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(".tmp")
        tmp.write_bytes(data)
        tmp.replace(dest)
        got += 1
    have = len(list(DEST.rglob("*.step"))) if DEST.exists() else 0
    print(f"ok    3D models: fetched {got}, {have} in {DEST.relative_to(HW)}")
    for rel in missing:
        print(f"note  no upstream model for {rel} (the gate will not see that part)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
