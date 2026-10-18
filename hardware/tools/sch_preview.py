"""Preview a hierarchical board's schematic while laying it out, clashes or not.

    BOARD=carrier_tme /usr/bin/python3 tools/sch_preview.py            # whole hierarchy
    BOARD=carrier_tme /usr/bin/python3 tools/sch_preview.py audio      # one function sheet

Writes build/preview/ (the sheets, .kicad_pro, local libs) and prints each distinct clash once. gen_sch.py
refuses to write a sheet with clashes; this does not, so you can export and look at it:
    kicad-cli sch export pdf -o build/preview/p.pdf build/preview/<BOARD>.kicad_sch
(KiCad's PDF shows every wire; the Konnect PNG renderer drops thin ones.)
"""
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import gen_sch  # noqa: E402
from board import design  # noqa: E402  # pyright: ignore[reportMissingImports]

OUT = HERE / "build" / "preview"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for lib in ("local.kicad_sym", "sym-lib-table"):
        shutil.copy(gen_sch.KICAD / lib, OUT / lib)
    if len(sys.argv) > 1:  # one function sheet, standalone
        tree, labels, clashes = gen_sch.child_sheet(sys.argv[1], [0, 0])
        files = [(f"one-{sys.argv[1]}.kicad_sch", tree)]
        print(f"hierarchical labels: {sorted({n for n, _c, _d in labels})}")
    else:
        files, root, clashes = gen_sch.hierarchy()
        (OUT / f"{design.NAME}.kicad_pro").write_text(json.dumps(gen_sch.project(root), indent=2) + "\n")
    for fname, tree in files:
        (OUT / fname).write_text(gen_sch.dump(tree) + "\n")
    print(f"wrote {len(files)} file(s) to {OUT.relative_to(HERE)}; {len(clashes)} clashes")
    seen = set()
    for c in clashes:
        kind = c.split(" at ")[0]
        if kind not in seen:
            seen.add(kind)
            print("  " + c)


if __name__ == "__main__":
    main()
