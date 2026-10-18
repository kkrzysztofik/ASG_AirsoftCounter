"""Import Seeed's XIAO ESP32-S3 (SMD) symbol and footprint into the local libraries:
kicad/local.kicad_sym symbol XIAO_ESP32S3 and kicad/local.pretty/XIAO_ESP32S3_SMD.kicad_mod.

Source: github.com/Seeed-Studio/OPL_Kicad_Library, folder "Seeed Studio XIAO Series Library"
(symbol XIAO-ESP32-S3-SMD, footprint XIAO-ESP32-S3-SMD.kicad_mod). Copied, not redrawn; the
footprint's User.2 artwork (~2500 shapes, ~500 KB) is dropped. Re-running replaces both.

Run: /usr/bin/python3 tools/import_xiao.py <path to "Seeed Studio XIAO Series Library">
"""
import re
import sys
from pathlib import Path

import pcbnew  # pyright: ignore[reportMissingImports]

KICAD = Path(__file__).resolve().parent.parent / "kicad"
SRC_NAME, SYM, FP = "XIAO-ESP32-S3-SMD", "XIAO_ESP32S3", "XIAO_ESP32S3_SMD"
# Pin number -> name, as the design doc's "Module facts" fixes them.
PINS = {**{str(i + 1): f"D{i}" for i in range(11)}, "12": "3V3_OUT", "13": "GND", "14": "VBUS",
        "15": "MTDI", "16": "MTDO", "17": "EN", "18": "GND", "19": "MTMS", "20": "MTCK",
        "21": "USB_DN", "22": "USB_DP", "23": "VBAT", "24": "GND", "25": "PAD"}


def block(text, head):
    """The balanced s-expression starting at `head` in text."""
    i, depth = text.index(head), 0
    for j in range(i, len(text)):
        depth += {"(": 1, ")": -1}.get(text[j], 0)
        if depth == 0:
            return text[i:j + 1]
    raise ValueError(head)


def import_symbol(src):
    sym = block(src.read_text(), f'(symbol "{SRC_NAME}"').replace(f'"{SRC_NAME}', f'"{SYM}')
    sym = re.sub(r'\(property "Footprint" "[^"]*"', f'(property "Footprint" "local:{FP}"', sym)
    got = {num: name for name, num in re.findall(r'\(name "([^"]*)"[\s\S]*?\(number "([^"]*)"', sym)}
    assert got == PINS, f"symbol pins differ: {set(got.items()) ^ set(PINS.items())}"
    lib = KICAD / "local.kicad_sym"
    text = lib.read_text()
    if f'(symbol "{SYM}"' in text:
        text = text.replace(block(text, f'(symbol "{SYM}"'), sym)
    else:
        text = text[:text.rindex(")")] + sym + "\n)\n"
    lib.write_text(text)


def children(text):
    """Top-level child s-expressions of the one block in text."""
    out, depth, start = [], 0, None
    for i, ch in enumerate(text):
        if ch == "(":
            depth += 1
            if depth == 2:
                start = i
        elif ch == ")":
            if depth == 2:
                out.append(text[start:i + 1])
            depth -= 1
    return out


def import_footprint(src):
    """Text copy (pcbnew Remove() on ~2500 shapes crashes KiCad 10's Python): drop User.2 children."""
    kept = [c for c in children(src.read_text()) if '(layer "User.2")' not in c]
    body = "\n\t".join(kept)
    (KICAD / "local.pretty" / f"{FP}.kicad_mod").write_text(f'(footprint "{FP}"\n\t{body}\n)\n')


def check():
    fp = pcbnew.FootprintLoad(str(KICAD / "local.pretty"), FP)
    pads = sorted(p.GetNumber() for p in fp.Pads())
    assert pads == sorted(PINS), f"footprint pads: {pads}"
    text = (KICAD / "local.kicad_sym").read_text()
    assert text.count(f'(symbol "{SYM}"') == 1
    print(f"import_xiao ok: local:{SYM} ({len(PINS)} pins), local:{FP} ({len(pads)} pads)")


if __name__ == "__main__":
    lib_dir = Path(sys.argv[1])
    import_symbol(lib_dir / "Seeed_Studio_XIAO_Series.kicad_sym")
    import_footprint(lib_dir / f"{SRC_NAME}.kicad_mod")
    check()
