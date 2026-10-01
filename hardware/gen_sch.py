"""Generate <BOARD>.kicad_sch and <BOARD>.kicad_pro from the BOARD module (board.py).

Block-structured, wired schematic. The board module's BLOCKS places every part by hand in a block
(power, amp, Heltec headers, level shifter, expander + buttons, drivers). Inside a block each net
is drawn with orthogonal wires, routed by A* on the 1.27 mm grid. A net that spans blocks gets one
global label per block. GND everywhere, and +3V3/+5V/VBAT_SW outside the blocks that draw them as
wires, use power ports. Routing never joins two nets (no T or overlap on a foreign wire, no wire
through a foreign pin), so ERC plus check_netlist.py prove the netlist is design.py's.
Symbol uuids are uid("sym/<ref>"), which gen_pcb.py uses to link footprints.
Run: /usr/bin/python3 gen_sch.py
"""
import collections
import heapq
import json
import math
import re
import uuid
from pathlib import Path

from board import design  # pyright: ignore[reportMissingImports]

HERE = Path(__file__).parent
SYMDIR = Path("/usr/share/kicad/symbols")
NS = uuid.UUID("5b0c7d8e-2f4a-4c1e-9a53-0d6e8f1b2c3a")  # fixed: stable uuids across runs
STEP = 1.27  # connection grid; every pin, wire and label sits on it
CH = 1.05  # approx glyph advance (mm) of the 1.27 mm font, for text boxes

DIRS = {"L": (-1, 0), "R": (1, 0), "U": (0, -1), "D": (0, 1)}
DIRS_OF = {v: k for k, v in DIRS.items()}
BEND, CROSS, NEAR = 2.0, 4.0, 1.0  # router costs on top of 1 per grid step


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
        # "local" is the project library (sym-lib-table) for parts KiCad does not ship
        tree = parse(((HERE if lib == "local" else SYMDIR) / f"{lib}.kicad_sym").read_text())
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
    """{number: (x, y, angle, length)}: connection point in symbol coords (Y up)."""
    pins = {}
    for body in unit_bodies(sym):
        for p in kids(body, "pin"):
            at = child(p, "at")
            pins[unq(child(p, "number")[1])] = (*(float(v) for v in at[1:4]), float(child(p, "length")[1]))
    return pins


def graphic_points(node):
    for x in node:
        if isinstance(x, list):
            if x[0] in ("xy", "start", "end", "center"):
                yield float(x[1]), float(x[2])
            elif x[0] != "pin":
                yield from graphic_points(x)


def xf(px, py, rot=0, mirror=None):
    """Symbol coords (Y up) -> schematic offset (Y down), rotated rot degrees CCW, then mirrored."""
    x, y = px, -py
    for _ in range(rot // 90 % 4):
        x, y = y, -x
    return (-x, y) if mirror == "y" else (x, -y) if mirror == "x" else (x, y)


def gk(x, y):
    return round(x / STEP), round(y / STEP)


def add(c, d, n=1):
    return c[0] + d[0] * n, c[1] + d[1] * n


def neg(d):
    return -d[0], -d[1]


def axis(d):
    return "H" if d[1] == 0 else "V"


def text_box(x, y, text, horizontal=True, justify="center"):
    """Rough extent of a 1.27 mm text (KiCad centres it vertically on the anchor)."""
    w, h = CH * len(text), 0.8
    lo = {"left": 0, "right": -w}.get(justify, -w / 2)
    if horizontal:
        return x + lo, y - h, x + lo + w, y + h
    return x - h, y - lo - w, x + h, y - lo


def box_cells(box, margin=0.3):
    x0, y0, x1, y1 = box
    return {(i, j) for i in range(math.ceil((x0 - margin) / STEP), math.floor((x1 + margin) / STEP) + 1)
            for j in range(math.ceil((y0 - margin) / STEP), math.floor((y1 + margin) / STEP) + 1)}


def bounds_box(pts):
    xs, ys = zip(*pts)
    return min(xs), min(ys), max(xs), max(ys)


# --- Schematic items ---

def uid(key):
    return q(str(uuid.uuid5(NS, key)))


def font(*extra):
    return ["effects", ["font", ["size", "1.27", "1.27"]], *extra]


def hfield(x, y, text, rot, just):  # text: (field name, shown text)
    """Field shown as horizontal text justified `just` on a symbol rotated `rot` (KiCad 9 renders
    a field angle relative to the symbol and flips justification at 180; measured, not documented)."""
    angle = {0: 0, 90: 270, 180: 0, 270: 90}[rot]
    if rot == 180:
        just = {"left": "right", "right": "left"}.get(just, just)
    return ["property", q(text[0]), q(text[1]), at(x, y, angle),
            font(*([["justify", just]] if just != "center" else []))]


def at(x, y, a=0.0):
    return ["at", num(x), num(y), num(a)]


def wire(a, b, key):
    return ["wire", ["pts", ["xy", num(a[0] * STEP), num(a[1] * STEP)], ["xy", num(b[0] * STEP), num(b[1] * STEP)]],
            ["stroke", ["width", "0"], ["type", "default"]], ["uuid", uid(key)]]


def instances(root, ref):
    return ["instances", ["project", q(design.NAME), ["path", q(f"/{root}"), ["reference", q(ref)], ["unit", "1"]]]]


class Sheet:
    """Placement state: obstacles, pins, wires, and the items to emit."""

    def __init__(self):
        self.root = str(uuid.uuid5(NS, "root"))
        self.hard = {}  # cell -> owner: bodies, pin lines, texts, ports, labels (no wire may enter)
        self.term = {}  # cell -> (net, stub dir): pin ends and label/port anchors
        self.zone = {}  # cell -> net: first two cells in front of each connected pin
        self.wires = collections.defaultdict(dict)  # cell -> {net: "H" | "V" | "X"}
        self.edges = collections.defaultdict(set)  # net -> {(cell, cell)}
        self.clashes = []
        self.items, self.symbols, self.lib_ids = [], [], set()
        self.nports = 0

    def mark(self, cells, owner, check=True):
        for c in cells:
            o = self.hard.get(c)
            if o is None:
                self.hard[c] = owner
            elif check and o != owner:
                self.clashes.append(f"{owner} overlaps {o} at {c[0] * STEP:.2f},{c[1] * STEP:.2f}")

    def free(self, cells, net, bound):
        return all(bound[0] <= c[0] <= bound[2] and bound[1] <= c[1] <= bound[3] and c not in self.hard
                   and self.term.get(c, (net,))[0] == net and self.zone.get(c, net) == net
                   and not self.wires.get(c) for c in cells)

    def stub(self, net, a, b):
        """Wire a..b (cells) owned by `net` that nothing may cross or join."""
        d = ((b[0] > a[0]) - (b[0] < a[0]), (b[1] > a[1]) - (b[1] < a[1]))
        c = a
        while c != b:
            n = add(c, d)
            self.edges[net].add(tuple(sorted((c, n))))
            c = n
            self.wires[c][net] = "X"
        self.wires[a][net] = "X"


# --- Parts ---

def place_part(sh, ref, x, y, rot, mirror, fields):
    value, lib_id, fp = design.PARTS[ref]
    sym = flat_symbol(*lib_id.split(":"))
    pin_net = {p.split(".")[1]: n for n, m in design.NETS.items() for p in m if p.split(".")[0] == ref}
    bad = set(pin_net) - set(pins_of(sym))
    if bad:
        raise SystemExit(f"{ref}: pins {sorted(bad)} not in symbol {lib_id} (has {sorted(pins_of(sym))})")
    body = [(x + dx, y + dy) for b in unit_bodies(sym) for px, py in graphic_points(b)
            for dx, dy in [xf(px, py, rot, mirror)]] or [(x, y)]
    bx = bounds_box(body)
    sh.mark(box_cells(bx, 0.4), ref)
    shown = {"Reference": ref, "Value": value, "Footprint": fp}
    props = []
    for p in kids(sym, "property"):
        name = unq(p[1])
        if name.startswith("ki_"):
            continue
        pa = child(p, "at")
        eff = child(p, "effects")
        hidden = any(k[0] == "hide" and k[1:] == ["yes"] for k in kids(eff, "hide"))
        text = shown.get(name, unq(p[2]))
        if name in ("Reference", "Value") and (ref in fields or rot % 180 and bx[2] - bx[0] > bx[3] - bx[1]):
            # parts turned horizontal: text above (Reference) / below (Value) the body unless given
            fx, fy, just = fields.get(ref, {}).get(name) or (
                (0, bx[1] - y - 1.5, "center") if name == "Reference" else (0, bx[3] - y + 1.5, "center"))
            fx, fy = x + fx, y + fy
            props.append(hfield(fx, fy, (name, text), rot, just))
            sh.mark(box_cells(text_box(fx, fy, text, True, just)), ref)
            continue
        dx, dy = xf(float(pa[1]), float(pa[2]), rot, mirror)
        props.append(["property", q(name), q(text), at(x + dx, y + dy, float(pa[3])), eff])
        if not hidden:
            js = [j for k in kids(eff, "justify") for j in k[1:] if j in ("left", "right")]
            horizontal = (float(pa[3]) + rot) % 180 == 0
            sh.mark(box_cells(text_box(x + dx, y + dy, text, horizontal, (js or ["center"])[0])), ref)
    pins = {}
    for n, (px, py, a, length) in pins_of(sym).items():
        dx, dy = xf(px, py, rot, mirror)
        s = xf(-round(math.cos(math.radians(a))), -round(math.sin(math.radians(a))), rot, mirror)
        s = (round(s[0]), round(s[1]))
        c = gk(x + dx, y + dy)
        pins[n] = (c, s)
        line = [add(c, s, -k) for k in range(1, round(length / STEP) + 1)]
        perp = (s[1], s[0])
        sh.mark(line, ref)
        sh.mark({add(p, perp, k) for p in line for k in (-1, 1)} - sh.term.keys(), ref, check=False)
        pin = f"{ref}.{n}"
        net = pin_net.get(n)
        if net is None:
            if ref not in design.NC_PARTS and pin not in design.NC_PINS and pin not in design.XH_SPARE:
                raise SystemExit(f"{pin} is neither on a net nor marked no-connect")
            sh.items.append(["no_connect", at(c[0] * STEP, c[1] * STEP)[:3], ["uuid", uid(f"nc/{ref}/{n}")]])
            sh.mark([c], ref)
            sh.mark(box_cells((c[0] * STEP - 1.27, c[1] * STEP - 1.27, c[0] * STEP + 1.27, c[1] * STEP + 1.27), 0),
                    ref, check=False)  # the X is wider than its cell
            continue
        old = sh.term.get(c)
        if old and old[0] != net:
            raise SystemExit(f"{pin} ({net}) sits on a {old[0]} pin")
        sh.term[c] = (net, s)
        for k in (1, 2):
            z = add(c, s, k)
            if sh.zone.get(z, net) != net:
                sh.clashes.append(f"{pin} stub zone clashes with {sh.zone[z]}")
            sh.zone[z] = net
    dnp = ref in design.DNP
    lib_bom = kids(sym, "in_bom")[0][1] if kids(sym, "in_bom") else "yes"  # "no" for MountingHole
    sh.lib_ids.add(lib_id)
    sh.symbols.append(["symbol", ["lib_id", q(lib_id)], at(x, y, rot), *([["mirror", mirror]] if mirror else []),
                       ["unit", "1"], ["exclude_from_sim", "no"], ["in_bom", "no" if dnp or lib_bom == "no" else "yes"],
                       ["on_board", "yes"], ["dnp", "yes" if dnp else "no"],
                       ["uuid", uid(f"sym/{ref}")], *props,
                       *[["pin", q(n), ["uuid", uid(f"pin/{ref}/{n}")]] for n in pins_of(sym)],
                       instances(sh.root, ref)])
    return {f"{ref}.{n}": v for n, v in pins.items()}


# --- Power ports, flags and labels ---

def port_shape(lib_id, value, c, d):
    """(rotation, value field (x, y, justify), cells) of a power symbol at cell c pointing d."""
    lib, name = lib_id.split(":")
    sym = flat_symbol(lib, name)
    base = "D" if name == "GND" else "U"  # direction the symbol points at rotation 0
    order = ["U", "L", "D", "R"]  # 90 degree CCW steps
    rot = (order.index(d) - order.index(base)) % 4 * 90
    x, y = c[0] * STEP, c[1] * STEP
    pts = [(x + dx, y + dy) for b in unit_bodies(sym) for px, py in graphic_points(b)
           for dx, dy in [xf(px, py, rot)]]
    v = DIRS[d]
    if d in "UD":
        vx, vy, just = x, y + v[1] * 3.6, "center"
    else:
        vx, vy, just = x + v[0] * 3.3, y, "left" if d == "R" else "right"
    cells = box_cells(bounds_box(pts), 0.2) | box_cells(text_box(vx, vy, value, True, just))
    return rot, (vx, vy, just), cells - {c}


def add_power(sh, lib_id, value, c, d, ref):
    rot, (vx, vy, just), cells = port_shape(lib_id, value, c, d)
    sh.mark(cells, ref)
    x, y = c[0] * STEP, c[1] * STEP
    hide = font(["hide", "yes"])
    props = [["property", q("Reference"), q(ref), at(x, y), hide],
             hfield(vx, vy, ("Value", value), rot, just),
             ["property", q("Footprint"), q(""), at(x, y), hide],
             ["property", q("Datasheet"), q(""), at(x, y), hide],
             ["property", q("Description"), q(""), at(x, y), hide]]
    sh.lib_ids.add(lib_id)
    sh.symbols.append(["symbol", ["lib_id", q(lib_id)], at(x, y, rot), ["unit", "1"], ["exclude_from_sim", "no"],
                       ["in_bom", "no"], ["on_board", "no"], ["dnp", "no"], ["uuid", uid(f"sym/{ref}")], *props,
                       ["pin", q("1"), ["uuid", uid(f"pin/{ref}/1")]], instances(sh.root, ref)])


def port(sh, net, c, d):
    sh.nports += 1
    add_power(sh, design.PORT_LIB[net], net, c, d, f"#PWR{sh.nports:02d}")


def natural(net):
    return "D" if net == "GND" else "U"


def port_on_pin(sh, net, c, s, bound):
    """Power port for one pin: on the pin if it faces the right way, else after a stub."""
    nat = natural(net)
    cands = [(0, nat)] if s == DIRS[nat] else []
    for n in (2, 4, 6, 8):
        cands += [(n, nat)] if axis(s) != axis(DIRS[nat]) else []
        cands += [(n, DIRS_OF[s])]
    for n, d in cands:
        e = add(c, s, n)
        stub = {add(c, s, k) for k in range(1, n + 1)}
        if sh.free(stub | port_shape(design.PORT_LIB[net], net, e, d)[2], net, bound):
            sh.stub(net, c, e)
            port(sh, net, e, d)
            return
    sh.clashes.append(f"no room for a {net} port at {c[0] * STEP:.2f},{c[1] * STEP:.2f}")
    port(sh, net, c, DIRS_OF[s])


def port_comb(sh, net, cells, s, bound):
    """Adjacent same-rail pins facing sideways: stubs to one vertical wire, one port at its end."""
    nat = DIRS[natural(net)]
    cells = sorted(cells, key=lambda c: c[1] * nat[1])
    for n in (2, 4):
        ends = [add(c, s, n) for c in cells]
        need = {add(c, s, k) for c in cells for k in range(1, n + 1)}
        need |= {(ends[0][0], j) for j in range(min(e[1] for e in ends), max(e[1] for e in ends) + 1)}
        if sh.free(need | port_shape(design.PORT_LIB[net], net, ends[-1], natural(net))[2], net, bound):
            for c, e in zip(cells, ends):
                sh.stub(net, c, e)
            sh.stub(net, ends[0], ends[-1])
            port(sh, net, ends[-1], natural(net))
            return True
    return False


def rail_ports(sh, net, pins, bound):
    """Ports for the pins of one rail in one block (stacked pins share one port)."""
    by_loc = {}
    for p in pins:
        by_loc.setdefault(sh.pins[p][0], (p, sh.pins[p][1]))
    runs, singles = [], []
    groups = collections.defaultdict(list)
    for c, (p, s) in by_loc.items():
        groups[(p.split(".")[0], s)].append(c)
    for (ref, s), cs in sorted(groups.items()):
        if axis(s) == "H":
            cs.sort(key=lambda c: c[1])
            run = [cs[0]]
            for c in cs[1:]:
                if c[1] - run[-1][1] == 2 and c[0] == run[-1][0]:
                    run.append(c)
                else:
                    runs.append((run, s))
                    run = [c]
            runs.append((run, s))
        else:
            singles += [(c, s) for c in cs]
    for run, s in runs:
        if len(run) > 1 and port_comb(sh, net, run, s, bound):
            continue
        singles += [(c, s) for c in run]
    for c, s in sorted(singles, key=lambda t: (t[0][1], t[0][0])):
        port_on_pin(sh, net, c, s, bound)


def glabel_len(net):
    return CH * len(net) + 1.8  # passive global label: text plus end margins (measured)


def glabel_cells(net, c, d, half=1.0):
    """Cells under a global label; half=1.0 is its own row, 2.3 adds the rows beside it."""
    x, y = c[0] * STEP, c[1] * STEP
    length = glabel_len(net)
    v = DIRS[d]
    ex, ey = x + v[0] * length, y + v[1] * length
    return box_cells((min(x, ex), min(y, ey) - half, max(x, ex), max(y, ey) + half) if d in "LR" else
                     (x - half, min(y, ey), x + half, max(y, ey)), 0.2) - {c}


def glabel(sh, net, c, d):
    angle = {"R": 0, "U": 90, "L": 180, "D": 270}[d]
    sh.mark(glabel_cells(net, c, d), f"label {net}")
    sh.mark(glabel_cells(net, c, d, 2.3), f"label {net}", check=False)  # keep wires off its outline
    sh.items.append(["global_label", q(net), ["shape", "passive"], at(c[0] * STEP, c[1] * STEP, angle),
                     ["fields_autoplaced", "yes"], font(["justify", "left" if d in "RU" else "right"]),
                     ["uuid", uid(f"glabel/{net}/{c[0]}/{c[1]}")]])


def label_on_pin(sh, net, c, s, bound):
    d = DIRS_OF[s]
    for n in (2, 4, 6):
        e = add(c, s, n)
        if sh.free({add(c, s, k) for k in range(1, n + 1)} | glabel_cells(net, e, d), net, bound):
            sh.stub(net, c, e)
            sh.term[e] = (net, neg(s))
            glabel(sh, net, e, d)
            return e
    sh.clashes.append(f"no room for a {net} label at {c[0] * STEP:.2f},{c[1] * STEP:.2f}")
    glabel(sh, net, c, d)
    return c


def flag(sh, net, c, i):
    """PWR_FLAG wired to a port of `net`: ERC needs a driver on each rail (all sources are passive)."""
    e = add(c, (1, 0), 6)
    nat = natural(net)
    sh.stub(net, c, e)
    add_power(sh, "power:PWR_FLAG", "PWR_FLAG", c, "D" if nat == "U" else "U", f"#FLG{i:02d}")
    port(sh, net, e, nat)


def name_label(sh, net, segs):
    """Name a one-block net with a global label laid on one of its straight wires.

    A local label would name the net "/NET" and break PCB parity (gen_pcb.py uses design.py names),
    so every net label is global; a single global label is fine for ERC."""
    n = round(glabel_len(net) / STEP)  # label length in cells
    for a, b in sorted(segs, key=lambda s: (s[0][1] != s[1][1], -abs(s[1][0] - s[0][0]) - abs(s[1][1] - s[0][1]), s)):
        d = (1, 0) if a[1] == b[1] else (0, -1)
        lo = min(a, b) if d == (1, 0) else max(a, b)
        inner = [add(lo, d, k) for k in range(1, abs(b[0] - a[0]) + abs(b[1] - a[1]))]
        side = (d[1], d[0])
        for k in range(len(inner) - n):
            run = inner[k:k + n + 1]
            beside = {add(r, side, m) for r in run for m in (-1, 1)}
            if all(sh.wires.get(r) == {net: axis(d)} and r not in sh.term for r in run) and \
                    all(x not in sh.hard and not sh.wires.get(x) and x not in sh.term for x in beside):
                glabel(sh, net, run[0], DIRS_OF[d])
                return
    sh.clashes.append(f"no room to label net {net}")
    glabel(sh, net, segs[0][0], "R")


# --- Router ---

def astar(sh, net, start, goals, bound):
    """Cheapest orthogonal path from `start` to a cell in `goals` (the net's tree so far).

    Foreign wires may only be crossed straight at right angles; foreign pins and pin zones,
    obstacles, and the net's own cells that aren't goals (tees, crossings) are never entered."""
    def h(c):
        return min(abs(c[0] - g[0]) + abs(c[1] - g[1]) for g in goals)

    def near(c):
        for d in DIRS.values():
            n = add(c, d)
            if n in sh.hard or any(o != net for o in sh.wires.get(n, ())) or sh.zone.get(n, net) != net:
                return NEAR
        return 0

    openq = [(h(start), 0, start, None)]
    best = {(start, None): 0}
    came = {}
    while openq:
        _, g, cur, din = heapq.heappop(openq)
        if g > best.get((cur, din), math.inf):
            continue
        if cur != start and cur in goals:
            path = [cur]
            key = (cur, din)
            while key in came:
                key = came[key]
                path.append(key[0])
            return path[::-1]
        foreign = {o: a for o, a in sh.wires.get(cur, {}).items() if o != net}
        for dout in DIRS.values():
            if din is not None and dout == neg(din):
                continue
            if foreign and (dout != din or any(a in ("X", axis(dout)) for a in foreign.values())):
                continue
            nb = add(cur, dout)
            if not (bound[0] <= nb[0] <= bound[2] and bound[1] <= nb[1] <= bound[3]) or nb in sh.hard:
                continue
            t = sh.term.get(nb)
            if t and (t[0] != net or nb not in goals):
                continue
            if sh.zone.get(nb, net) != net or (net in sh.wires.get(nb, {}) and nb not in goals):
                continue
            fw = {o: a for o, a in sh.wires.get(nb, {}).items() if o != net}
            if any(a in ("X", axis(dout)) for a in fw.values()):
                continue
            ng = g + 1 + (BEND if din is not None and dout != din else 0) + (CROSS if fw else 0) + near(nb)
            if ng < best.get((nb, dout), math.inf):
                best[(nb, dout)] = ng
                came[(nb, dout)] = (cur, din)
                heapq.heappush(openq, (ng + h(nb), ng, nb, dout))
    return None


def degree(edges):
    deg = collections.Counter()
    for a, b in edges:
        deg[a] += 1
        deg[b] += 1
    return deg


def route(sh, net, terms, bound):
    """Connect terminal cells of `net` (pins, label anchors) into one tree, nearest first."""
    tree = {terms[0]} | {c for e in sh.edges[net] for c in e
                         if bound[0] <= c[0] <= bound[2] and bound[1] <= c[1] <= bound[3]}
    left = [t for t in terms[1:] if t not in tree]
    while left:
        start = min(left, key=lambda t: (min(abs(t[0] - c[0]) + abs(t[1] - c[1]) for c in tree), t))
        left.remove(start)
        deg = degree(sh.edges[net])
        goals = {c for c in tree if deg[c] < 3 and not any(o != net for o in sh.wires.get(c, ()))}
        path = astar(sh, net, start, goals, bound)
        if path is None:
            sh.clashes.append(f"router failed on net {net} from {start[0] * STEP:.2f},{start[1] * STEP:.2f}")
            continue
        for a, b in zip(path, path[1:]):
            sh.edges[net].add(tuple(sorted((a, b))))
        for c in path:
            sh.wires[c].setdefault(net, "X")
        tree |= set(path)
    # straight runs may be crossed; corners, tees and ends may not
    nd = collections.defaultdict(set)
    for a, b in sh.edges[net]:
        d = (b[0] - a[0], b[1] - a[1])
        nd[a].add(d)
        nd[b].add(neg(d))
    for c, ds in nd.items():
        straight = len(ds) == 2 and len({axis(d) for d in ds}) == 1 and c not in terms
        sh.wires[c][net] = axis(next(iter(ds))) if straight else "X"


def segments(edges, stops):
    """Merge unit edges into maximal straight wires, split at `stops` (pins, labels, tees)."""
    out = []
    for horiz in (True, False):
        runs = collections.defaultdict(list)
        for a, b in edges:
            if (a[1] == b[1]) == horiz:
                runs[a[1] if horiz else a[0]].append(tuple(sorted((a[0], b[0]) if horiz else (a[1], b[1]))))
        for fixed, ivs in sorted(runs.items()):
            merged = []
            for lo, hi in sorted(ivs):
                if merged and lo <= merged[-1][1]:
                    merged[-1] = (merged[-1][0], max(hi, merged[-1][1]))
                else:
                    merged.append((lo, hi))
            for lo, hi in merged:
                cuts = sorted((c[0] if horiz else c[1]) for c in stops
                              if (c[1] if horiz else c[0]) == fixed and lo < (c[0] if horiz else c[1]) < hi)
                pts = [lo, *cuts, hi]
                for a, b in zip(pts, pts[1:]):
                    out.append(((a, fixed), (b, fixed)) if horiz else ((fixed, a), (fixed, b)))
    return out


# --- Build ---

# (name, width, height) in mm, landscape; the drawing frame and title block need margins
PAPERS = [("A3", 420, 297), ("A2", 594, 420), ("A1", 841, 594)]


def paper_for(w, h):
    """Smallest sheet whose frame holds every block, clear of the bottom title block."""
    for name, pw, ph in PAPERS:
        if w <= pw - 15 and h <= ph - 45:
            return name
    raise SystemExit(f"schematic content {w:.0f}x{h:.0f} mm does not fit on A1")


def schematic():
    sh = Sheet()
    sh.pins = {}
    placed = [r for b in design.BLOCKS for r in b["parts"]]
    missing = set(design.PARTS) - set(placed)
    dupes = {r for r in placed if placed.count(r) > 1}
    if missing or dupes or set(placed) - set(design.PARTS):
        raise SystemExit(f"design.BLOCKS: missing {sorted(missing)}, twice {sorted(dupes)}, "
                         f"unknown {sorted(set(placed) - set(design.PARTS))}")
    block_of, bounds = {}, []
    for i, b in enumerate(design.BLOCKS):
        (bx, by), (bw, bh) = b["at"], b["size"]
        bounds.append((round(bx / STEP) + 1, round(by / STEP) + 1, round((bx + bw) / STEP) - 1,
                       round((by + bh) / STEP) - 1))
        tx, ty = bx + 2.54, by + 5.08
        sh.mark(box_cells((tx, ty - 1.3, tx + len(b["title"]) * 1.7, ty + 0.3)), f"title {i}")
        sh.items.append(["rectangle", ["start", num(bx), num(by)], ["end", num(bx + bw), num(by + bh)],
                         ["stroke", ["width", "0"], ["type", "dash"]], ["fill", ["type", "none"]],
                         ["uuid", uid(f"block/{i}")]])
        sh.items.append(["text", q(b["title"]), ["exclude_from_sim", "no"], at(tx, ty),
                         ["effects", ["font", ["size", "2", "2"], ["bold", "yes"]], ["justify", "left", "bottom"]],
                         ["uuid", uid(f"title/{i}")]])
        for ref, (dx, dy, rot, mirror) in b["parts"].items():
            sh.pins |= place_part(sh, ref, bx + dx, by + dy, rot, mirror, b.get("fields", {}))
            block_of[ref] = i
    nflags = 0
    for i, b in enumerate(design.BLOCKS):
        for net, dx, dy in b.get("flags", []):
            nflags += 1
            flag(sh, net, gk(b["at"][0] + dx, b["at"][1] + dy), nflags)

    # per net: pins grouped by block
    groups = collections.defaultdict(lambda: collections.defaultdict(list))
    for net, members in design.NETS.items():
        for p in members:
            groups[net][block_of[p.split(".")[0]]].append(p)
    terms = collections.defaultdict(list)  # (net, block) -> [(cell, stub dir)]
    # explicit tags first (their boxes must be free before anything else claims the space)
    for i, b in enumerate(design.BLOCKS):
        for net, tags in b.get("tags", {}).items():
            if i not in groups[net]:
                raise SystemExit(f"tag {net} in block {b['title']!r}, which has none of its pins")
            for dx, dy, d in tags:
                c = gk(b["at"][0] + dx, b["at"][1] + dy)
                if c in sh.hard or c in sh.term or sh.zone.get(c, net) != net:
                    sh.clashes.append(f"tag {net} at {c[0] * STEP:.2f},{c[1] * STEP:.2f} is not free")
                sh.term[c] = (net, neg(DIRS[d]))
                terms[(net, i)].append((c, neg(DIRS[d])))
                if net in design.RAILS:
                    port(sh, net, c, d)
                else:
                    glabel(sh, net, c, d)
    for net in design.RAILS:
        for i, pins in sorted(groups[net].items()):
            if net not in design.BLOCKS[i].get("wired", ()):
                rail_ports(sh, net, pins, bounds[i])
    # a lone pin of a multi-block net gets its label on a stub
    for net, by_block in groups.items():
        if net in design.RAILS or len(by_block) == 1:
            continue
        for i, pins in sorted(by_block.items()):
            if not terms[(net, i)] and len(pins) == 1:
                c, s = sh.pins[pins[0]]
                terms[(net, i)].append((label_on_pin(sh, net, c, s, bounds[i]), s))
    for net, by_block in groups.items():
        for i in by_block:
            if net not in design.RAILS and len(by_block) > 1 and not terms[(net, i)]:
                raise SystemExit(f"{net} needs a tag in block {design.BLOCKS[i]['title']!r}")

    def spread(net, i):
        cs = [sh.pins[p][0] for p in groups[net][i]]
        return max(c[0] for c in cs) - min(c[0] for c in cs) + max(c[1] for c in cs) - min(c[1] for c in cs)

    todo = [(net, i) for net, by_block in groups.items() for i in by_block
            if net not in design.RAILS or net in design.BLOCKS[i].get("wired", ())]
    for net, i in sorted(todo, key=lambda t: (spread(*t), t[0], t[1])):
        ts = [sh.pins[p][0] for p in groups[net][i]] + [c for c, _ in terms[(net, i)]]
        route(sh, net, list(dict.fromkeys(ts)), bounds[i])
    # name one-block nets
    for net, by_block in groups.items():
        if net not in design.RAILS and len(by_block) == 1 and not terms[(net, next(iter(by_block)))]:
            deg = degree(sh.edges[net])
            stops = {c for c, (n, _) in sh.term.items() if n == net} | {c for c in deg if deg[c] > 2}
            name_label(sh, net, segments(sh.edges[net], stops))
    inside = set().union(*(box_cells((b["at"][0], b["at"][1], b["at"][0] + b["size"][0], b["at"][1] + b["size"][1]),
                                     -0.1) for b in design.BLOCKS))
    sh.clashes += [f"{o} outside its block at {c[0] * STEP:.2f},{c[1] * STEP:.2f}"
                   for c, o in sh.hard.items() if c not in inside]

    body = []
    for net in sorted(sh.edges):
        ed = sh.edges[net]
        deg = degree(ed)
        ends = {c for c, (n, _) in sh.term.items() if n == net}
        dots = sorted(c for c in deg if deg[c] + (c in ends) >= 3)
        for k, (a, b) in enumerate(segments(ed, set(dots) | ends)):
            body.append(wire(a, b, f"wire/{net}/{k}"))
        body += [["junction", at(c[0] * STEP, c[1] * STEP)[:3], ["diameter", "0"], ["color", "0", "0", "0", "0"],
                  ["uuid", uid(f"junction/{net}/{c[0]}/{c[1]}")]] for c in dots]
    w = max(b["at"][0] + b["size"][0] for b in design.BLOCKS)
    h = max(b["at"][1] + b["size"][1] for b in design.BLOCKS)
    head = [["lib_symbols", *[embedded(i) for i in sorted(sh.lib_ids)]]]
    return ["kicad_sch", ["version", "20250114"], ["generator", q("gen_sch")], ["generator_version", q("9.0")],
            ["uuid", q(sh.root)], ["paper", q(paper_for(w, h))], *head, *body, *sh.items, *sh.symbols,
            ["sheet_instances", ["path", q("/"), ["page", q("1")]]], ["embedded_fonts", "no"]], sh.root, sh.clashes


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
# Unspecified pins are treated like Passive; project() asserts there are none (UNSPEC_OK), so a new one
# can't be silently treated as Passive. (The MAX98357A's exposed pad was the last one.)
UNSPEC_OK = set()
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
        "meta": {"filename": f"{design.NAME}.kicad_pro", "version": 3},
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
                # 0.2 mm, not 0.25: kept from the MAX98357A (TQFN, 0.25 mm pad gaps), where Freerouting could only neck
                # a VBAT_SW track down into its VDD pads at the default clearance
                {"name": "Power", "priority": 0, "track_width": 0.8, "clearance": 0.2, **VIA},
            ],
            # GND is not Power: both layers carry GND pours (route.py routes GND as a normal net, so
            # pours only add connectivity), and a 0.8 mm GND track can't reach
            # U2's A0-A2 (0.65 mm pitch TSSOP).
            "netclass_patterns": [{"netclass": "Power", "pattern": p} for p in ("VBAT*", "BAT_N", "+5V", "SW")],
        },
        "erc": {"pin_map": PIN_MAP},
        "sheets": [[root, "Root"]],
    }


def main():
    design.check()
    sch, root, clashes = schematic()
    if clashes:  # keep the broken sheet for inspection, out of the tree
        (HERE / "build").mkdir(exist_ok=True)
        (HERE / "build" / f"{design.NAME}_bad.kicad_sch").write_text(dump(sch) + "\n")
        first = {}
        for m in clashes:  # one line per kind of problem, at its first spot
            first.setdefault(m.split(" at ")[0], m)
        raise SystemExit(f"layout problems (sheet in build/{design.NAME}_bad.kicad_sch):\n  "
                         + "\n  ".join(sorted(first.values())))
    (HERE / f"{design.NAME}.kicad_sch").write_text(dump(sch) + "\n")
    (HERE / f"{design.NAME}.kicad_pro").write_text(json.dumps(project(root), indent=2) + "\n")
    print(f"wrote {design.NAME}.kicad_sch, {design.NAME}.kicad_pro")


if __name__ == "__main__":
    main()
