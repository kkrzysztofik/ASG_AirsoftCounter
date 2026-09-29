"""Generate carrier.kicad_sch and carrier.kicad_pro from design.py.

Label-per-pin schematic: every connected pin gets a 2.54 mm wire stub ending
in a global label named after its net, so no wires need routing.
Run: /usr/bin/python3 gen_sch.py
"""
import json
import math
import re
import uuid
from pathlib import Path

import design

HERE = Path(__file__).parent
SYMDIR = Path("/usr/share/kicad/symbols")
NS = uuid.UUID("5b0c7d8e-2f4a-4c1e-9a53-0d6e8f1b2c3a")  # fixed: stable uuids across runs
GRID = 2.54
STUB = 2.54
PER_ROW = 10
FLAG_NETS = ["GND", "+3V3", "+5V", "VBAT_SW"]
NC_PARTS = {"J2", "J3"}  # every unconnected pin gets a no-connect flag
NC_PINS = {"U1.6",  # MT3608 NC
           "U2.11", "U2.12",  # TCA9534 P6/P7 spare
           "U3.5", "U3.6", "U3.12", "U3.13"}  # MAX98357A NC


# --- S-expressions: atoms stay raw tokens (quoted strings keep their quotes) ---

def parse(text):
    stack = [[]]
    for tok in re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+', text):
        if tok == "(":
            stack.append([])
        elif tok == ")":
            done = stack.pop()
            stack[-1].append(done)
        else:
            stack[-1].append(tok)
    return stack[0][0]


def dump(node, depth=0):
    if not isinstance(node, list):
        return node
    i = next((k for k, x in enumerate(node) if isinstance(x, list)), len(node))
    head = " ".join(node[:i])
    if i == len(node):
        return f"({head})"
    pad = "\t" * (depth + 1)
    return f"({head}" + "".join(f"\n{pad}{dump(x, depth + 1)}" for x in node[i:]) + f"\n{pad[:-1]})"


def q(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def unq(tok):
    return tok[1:-1] if tok.startswith('"') else tok


def num(v):
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return "0" if s == "-0" else s


def kids(node, head):
    return [x for x in node if isinstance(x, list) and x and x[0] == head]


def child(node, head):
    found = kids(node, head)
    if not found:
        raise SystemExit(f"no ({head} ...) in ({' '.join(x for x in node[:2] if isinstance(x, str))} ...)")
    return found[0]


# --- Library symbols ---

_libs = {}


def lib_symbols(lib):
    if lib not in _libs:
        tree = parse((SYMDIR / f"{lib}.kicad_sym").read_text())
        _libs[lib] = {unq(s[1]): s for s in kids(tree, "symbol")}
    return _libs[lib]


def lib_symbol(lib, name):
    try:
        return lib_symbols(lib)[name]
    except KeyError:
        raise SystemExit(f"{name} not in {lib}.kicad_sym") from None


def rename_units(sym, old, new):
    """Sub-symbols are named <symbol>_<unit>_<style>."""
    return [["symbol", q(new + unq(s[1])[len(old):]), *s[2:]] for s in kids(sym, "symbol")]


def flat_symbol(lib, name):
    """Symbol `name` with (extends ...) resolved: base graphics/pins, derived properties."""
    sym = lib_symbol(lib, name)
    ext = kids(sym, "extends")
    if not ext:
        return sym
    base = flat_symbol(lib, unq(ext[0][1]))
    # properties: derived wins, base-only ones (e.g. ki_fp_filters) are kept
    own = {unq(p[1]): p for p in kids(sym, "property")}
    props = [own.pop(unq(p[1]), p) for p in kids(base, "property")] + list(own.values())
    # attrs (power, pin_names, in_bom, ...) and all graphics/pins come from base
    # ponytail: derived-only top-level attrs are dropped; fine for stock KiCad 9 derived symbols
    overrides = {x[0]: x for x in sym[2:] if isinstance(x, list) and x[0] not in ("extends", "property", "symbol")}
    attrs = [overrides.get(x[0], x) for x in base[2:]
             if isinstance(x, list) and x[0] not in ("property", "symbol", "embedded_fonts")]
    return ["symbol", q(name), *attrs, *props, *rename_units(base, unq(base[1]), name), ["embedded_fonts", "no"]]


def embedded(lib_id):
    lib, name = lib_id.split(":")
    sym = flat_symbol(lib, name)
    return ["symbol", q(lib_id), *sym[2:]]


def unit_bodies(sym):
    """Sub-symbols of unit 1 / common, body style 1 (skip De Morgan alternates)."""
    return [s for s in kids(sym, "symbol") if all(k in ("0", "1") for k in unq(s[1]).rsplit("_", 2)[1:])]


def pins_of(sym):
    """{number: (x, y, angle)}: connection point in symbol coords (Y up)."""
    pins = {}
    for body in unit_bodies(sym):
        for p in kids(body, "pin"):
            at = child(p, "at")
            pins[unq(child(p, "number")[1])] = tuple(float(v) for v in at[1:4])
    return pins


def graphic_points(node):
    for x in node:
        if isinstance(x, list):
            if x[0] in ("xy", "start", "end", "center"):
                yield float(x[1]), float(x[2])
            elif x[0] != "pin":
                yield from graphic_points(x)


# --- Placement geometry (schematic coords, Y down) ---

def stub_dir(angle):
    """Pin angle points from the connection point into the body; stubs go the other way."""
    a = math.radians(angle)
    return -round(math.cos(a)), round(math.sin(a))


# Layout estimates only (approx glyph width at 1.27 mm font, 1.5 mm half label height); safe to tweak.
def label_width(net):
    return 0.85 * 1.27 * len(net) + 3


def bbox(sym, pin_net, fields):
    """Rough extent of a placed symbol (origin at 0,0) incl. stubs, labels and fields."""
    pts = [(-GRID, -GRID), (GRID, GRID)]
    pts += [(x, -y) for body in unit_bodies(sym) for x, y in graphic_points(body)]
    for n, (px, py, a) in pins_of(sym).items():
        dx, dy = stub_dir(a)
        reach = STUB + label_width(pin_net[n]) if n in pin_net else 0
        pts.append((px + dx * reach + dy * 1.5, -py + dy * reach + dx * 1.5))
        pts.append((px + dx * reach - dy * 1.5, -py + dy * reach - dx * 1.5))
    for text, (fx, fy, rot) in fields:
        half = 0.6 * len(text)
        pts += [(fx - half, -fy), (fx + half, -fy)] if rot == 0 else [(fx, -fy - half), (fx, -fy + half)]
    xs, ys = zip(*pts)
    return min(xs) - GRID, min(ys) - GRID, max(xs) + GRID, max(ys) + GRID


def snap(v):
    return math.ceil(v / GRID) * GRID


def layout(items):
    """Rows of PER_ROW, top-aligned; origins on the 2.54 grid so pins land on grid."""
    x0, y0 = 25.4, 25.4
    top, placed = y0, []
    for i in range(0, len(items), PER_ROW):
        row = items[i:i + PER_ROW]
        x, bottom = x0, top
        for it in row:
            xmin, ymin, xmax, ymax = it["bbox"]
            ox, oy = snap(x - xmin), snap(top - ymin)
            placed.append((it, ox, oy))
            x = ox + xmax
            bottom = max(bottom, oy + ymax)
        top = snap(bottom)
    return placed


# --- Schematic items ---

def uid(key):
    return q(str(uuid.uuid5(NS, key)))


def font(*extra):
    return ["effects", ["font", ["size", "1.27", "1.27"]], *extra]


def at(x, y, a=0.0):
    return ["at", num(x), num(y), num(a)]


def placed_symbol(it, ox, oy, root):
    sym, ref = it["sym"], it["ref"]
    values = {"Reference": ref, "Value": it["value"], "Footprint": it["fp"]}
    props = []
    for p in kids(sym, "property"):
        name = unq(p[1])
        if name.startswith("ki_"):
            continue
        pa = child(p, "at")
        props.append(["property", q(name), q(values[name]) if name in values else p[2],
                      at(ox + float(pa[1]), oy - float(pa[2]), float(pa[3])), child(p, "effects")])
    dnp = ref in design.DNP
    virtual = ref.startswith("#")
    lib_bom = kids(sym, "in_bom")[0][1] if kids(sym, "in_bom") else "yes"  # "no" for MountingHole
    return ["symbol", ["lib_id", q(it["lib_id"])], at(ox, oy), ["unit", "1"],
            ["exclude_from_sim", "no"], ["in_bom", "no" if dnp or virtual or lib_bom == "no" else "yes"],
            ["on_board", "no" if virtual else "yes"], ["dnp", "yes" if dnp else "no"],
            ["uuid", uid(f"sym/{ref}")], *props,
            *[["pin", q(n), ["uuid", uid(f"pin/{ref}/{n}")]] for n in pins_of(sym)],
            ["instances", ["project", q("carrier"),
                           ["path", q(f"/{root}"), ["reference", q(ref)], ["unit", "1"]]]]]


def pin_items(it, ox, oy):
    ref, out = it["ref"], []
    for n, (px, py, a) in pins_of(it["sym"]).items():
        x, y = ox + px, oy - py
        if n in it["pin_net"]:
            dx, dy = stub_dir(a)
            ex, ey = x + dx * STUB, y + dy * STUB
            la = (a + 180) % 360
            out.append(["wire", ["pts", ["xy", num(x), num(y)], ["xy", num(ex), num(ey)]],
                        ["stroke", ["width", "0"], ["type", "default"]], ["uuid", uid(f"wire/{ref}/{n}")]])
            out.append(["global_label", q(it["pin_net"][n]), ["shape", "passive"], at(ex, ey, la),
                        ["fields_autoplaced", "yes"], font(["justify", "left" if la in (0, 90) else "right"]),
                        ["uuid", uid(f"label/{ref}/{n}")]])
        elif ref in NC_PARTS or f"{ref}.{n}" in NC_PINS:
            out.append(["no_connect", at(x, y)[:3], ["uuid", uid(f"nc/{ref}/{n}")]])
        else:
            raise SystemExit(f"{ref}.{n} is neither on a net nor marked no-connect")
    return out


def make_item(ref, value, lib_id, fp, pin_net):
    lib, name = lib_id.split(":")
    sym = flat_symbol(lib, name)
    bad = set(pin_net) - set(pins_of(sym))
    if bad:
        raise SystemExit(f"{ref}: pins {sorted(bad)} not in symbol {lib_id} (has {sorted(pins_of(sym))})")
    shown = {"Reference": ref, "Value": value}
    fields = [(shown[unq(p[1])], tuple(float(v) for v in child(p, "at")[1:4]))
              for p in kids(sym, "property") if unq(p[1]) in shown]
    return {"ref": ref, "value": value, "lib_id": lib_id, "fp": fp, "sym": sym,
            "pin_net": pin_net, "bbox": bbox(sym, pin_net, fields)}


def items():
    net_of = {p: net for net, members in design.NETS.items() for p in members}
    out = []
    for ref, (value, lib_id, fp) in design.PARTS.items():
        pin_net = {p.split(".")[1]: net for p, net in net_of.items() if p.split(".")[0] == ref}
        out.append(make_item(ref, value, lib_id, fp, pin_net))
    for i, net in enumerate(FLAG_NETS, 1):
        out.append(make_item(f"#FLG{i:02d}", "PWR_FLAG", "power:PWR_FLAG", "", {"1": net}))
    return out


def schematic():
    root = str(uuid.uuid5(NS, "root"))
    parts = items()
    placed = layout(parts)
    lib_ids = sorted({it["lib_id"] for it in parts})
    body = [["lib_symbols", *[embedded(i) for i in lib_ids]]]
    for it, ox, oy in placed:
        body += pin_items(it, ox, oy)
    body += [placed_symbol(it, ox, oy, root) for it, ox, oy in placed]
    body += [["sheet_instances", ["path", q("/"), ["page", q("1")]]], ["embedded_fonts", "no"]]
    return ["kicad_sch", ["version", "20250114"], ["generator", q("gen_sch")],
            ["generator_version", q("9.0")], ["uuid", q(root)], ["paper", q("A3")], *body], root


# KiCad 9 default ERC pin conflict matrix (0 ok, 1 warning, 2 error), rows/columns: input, output,
# bidirectional, tri-state, passive, free, unspecified, power in, power out, open collector,
# open emitter, no connect.
PIN_MAP = [[0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 2], [0, 2, 0, 1, 0, 0, 1, 0, 2, 2, 2, 2],
           [0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 2], [0, 1, 0, 0, 0, 0, 1, 1, 2, 1, 1, 2],
           [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 2], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2],
           [1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 2], [0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 2],
           [0, 2, 1, 2, 0, 0, 1, 0, 2, 2, 2, 2], [0, 2, 0, 1, 0, 0, 1, 0, 2, 0, 0, 2],
           [0, 2, 1, 1, 0, 0, 1, 0, 2, 0, 0, 2], [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2]]
PASSIVE, UNSPEC = 4, 6
# The MAX98357A exposed pad (U3.17) is typed Unspecified in the library and goes to GND: treat
# Unspecified like Passive so it doesn't warn against the GND pins. project() asserts it stays the
# only Unspecified pin, so a new one can't be silently treated as Passive.
UNSPEC_OK = {"U3.17"}
PIN_MAP[UNSPEC] = PIN_MAP[PASSIVE][:]
for row in PIN_MAP:
    row[UNSPEC] = row[PASSIVE]
VIA = {"via_diameter": 0.6, "via_drill": 0.3}  # JLCPCB standard; gen_pcb.py reuses it


def unspecified_pins():
    return {f"{ref}.{unq(child(p, 'number')[1])}" for ref, (_, lib_id, _) in design.PARTS.items()
            for body in unit_bodies(flat_symbol(*lib_id.split(":"))) for p in kids(body, "pin")
            if p[1] == "unspecified"}


def project(root):
    assert unspecified_pins() == UNSPEC_OK, f"Unspecified pins {unspecified_pins()}: review PIN_MAP"
    return {
        "meta": {"filename": "carrier.kicad_pro", "version": 3},
        "board": {"design_settings": {"rules": {
            # 0.15 mm (JLCPCB 2-layer minimum is 0.127 mm): headroom for Freerouting neck-downs into
            # the U1/U2/U3 fine-pitch pads (earlier routes necked to ~0.19 mm; the current narrowest
            # track is 0.25 mm). Net-class widths (0.25 / 0.8 mm) are unchanged.
            "min_track_width": 0.15, "min_clearance": 0.2,
            "min_via_diameter": 0.6, "min_through_hole_diameter": 0.3},
            # gen_pcb.py loads every footprint fresh from the library, so the only possible mismatch
            # is its deliberate one: U3's thermal vias widened from 0.2 to 0.3 mm drill for JLCPCB.
            "rule_severities": {"lib_footprint_mismatch": "ignore"}}},
        "net_settings": {
            "meta": {"version": 4},
            "classes": [
                # KiCad 9 silently drops every class if "priority" is missing
                {"name": "Default", "priority": 2147483647, "track_width": 0.25, "clearance": 0.2, **VIA},
                # 0.2 mm, not 0.25: the U3 (TQFN) pad gaps are 0.25 mm, so Freerouting can only neck
                # a VBAT_SW track down into its VDD pads at the default clearance
                {"name": "Power", "priority": 0, "track_width": 0.8, "clearance": 0.2, **VIA},
            ],
            # GND is not Power: both layers carry GND pours (route.py routes GND as a normal net, so
            # pours only add connectivity), and a 0.8 mm GND track can't reach
            # U3's GND pins (0.5 mm pitch, one of them between OUTN and a NC pin) or U2's A0-A2.
            "netclass_patterns": [{"netclass": "Power", "pattern": p} for p in ("VBAT*", "+5V", "SW")],
        },
        "erc": {"pin_map": PIN_MAP},
        "sheets": [[root, "Root"]],
    }


def main():
    design.check()
    sch, root = schematic()
    (HERE / "carrier.kicad_sch").write_text(dump(sch) + "\n")
    (HERE / "carrier.kicad_pro").write_text(json.dumps(project(root), indent=2) + "\n")
    print("wrote carrier.kicad_sch, carrier.kicad_pro")


if __name__ == "__main__":
    main()
