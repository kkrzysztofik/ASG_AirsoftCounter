"""Compare two placed boards: footprint identity, position, rotation, side and pad nets.

    /usr/bin/python3 tools/pcb_diff.py <old.kicad_pcb> <new.kicad_pcb>
    /usr/bin/python3 tools/pcb_diff.py HEAD:kicad/carrier.kicad_pcb kicad/carrier.kicad_pcb

Used by the hierarchical-schematic migration: regenerating a schematic must not move the board.
`HEAD:<path>` reads the committed revision from git (`git show HEAD:<path>`), which is what the
handover's gate compares against.

Footprint *paths* are expected to differ (gen_pcb now links them through the sheet uuid), so they are
not compared. Unconnected-pin net names may also differ where a symbol's pin names changed; those show
up as `pad nets` diffs and are called out separately.

Exit code 0 when the boards agree on everything but paths (and, with --allow-unnamed, on pads whose
net is a KiCad-generated `unconnected-(...)` name).
"""
import subprocess
import sys
import tempfile
from pathlib import Path

import pcbnew  # pyright: ignore[reportMissingImports]

HERE = Path(__file__).resolve().parent.parent


def load(spec):
    """A board path, resolving `HEAD:<rel>` / `<rev>:<rel>` through git into a temp file."""
    if ":" not in spec or Path(spec).exists():
        return pcbnew.LoadBoard(str(Path(spec))), spec
    rev, rel = spec.split(":", 1)
    text = subprocess.run(["git", "show", f"{rev}:hardware/{rel}"], cwd=HERE, check=True,
                          capture_output=True, text=True).stdout
    tmp = Path(tempfile.mkdtemp(prefix="pcbdiff-")) / Path(rel).name
    tmp.write_text(text)
    return pcbnew.LoadBoard(str(tmp)), spec


def survey(board):
    """{ref: (x_um, y_um, rotation, flipped, {pad number: net name})} plus footprint paths."""
    out, paths = {}, {}
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        pos = fp.GetPosition()
        pads = {pad.GetNumber(): pad.GetNetname() for pad in fp.Pads()}
        out[ref] = (pos.x, pos.y, round(fp.GetOrientationDegrees(), 4), bool(fp.IsFlipped()), pads)
        paths[ref] = fp.GetPath().AsString()
    return out, paths


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__.strip().splitlines()[2].strip())
    allow_unnamed = "--allow-unnamed" in sys.argv
    argv = [a for a in sys.argv[1:] if not a.startswith("--")]
    (old, old_name), (new, new_name) = load(argv[0]), load(argv[1])
    a, _pa = survey(old)
    b, _pb = survey(new)

    problems = []
    only_old, only_new = sorted(set(a) - set(b)), sorted(set(b) - set(a))
    if only_old:
        problems.append(f"only in {old_name}: {only_old}")
    if only_new:
        problems.append(f"only in {new_name}: {only_new}")
    for ref in sorted(set(a) & set(b)):
        pa, pb = a[ref], b[ref]
        if pa[:4] != pb[:4]:
            problems.append(f"{ref}: moved/rotated/flipped {pa[:4]} -> {pb[:4]}")
        if pa[4] != pb[4]:
            for pad in sorted(set(pa[4]) | set(pb[4])):
                na, nb = pa[4].get(pad), pb[4].get(pad)
                if na == nb:
                    continue
                if allow_unnamed and {na, nb} <= {"", None} | {n for n in (na, nb) if n and n.startswith("unconnected-")}:
                    continue
                problems.append(f"{ref}.{pad}: net {na!r} -> {nb!r}")
    npaths = sum(1 for r in set(a) & set(b) if _pa[r] != _pb.get(r))
    print(f"{old_name} vs {new_name}: {len(a)} footprints, {npaths} with a changed footprint path")
    if problems:
        for p in problems:
            print("  DIFF " + p)
        raise SystemExit(f"{len(problems)} difference(s): the board must only change in footprint paths")
    print("  identical apart from footprint paths")


if __name__ == "__main__":
    main()
