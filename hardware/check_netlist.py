"""Assert the exported KiCad netlist matches the board module.

kicad-cli sch export netlist --format kicadxml -o build/<BOARD>.xml kicad/<BOARD>.kicad_sch
/usr/bin/python3 check_netlist.py [build/<BOARD>.xml]
"""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from board import design  # pyright: ignore[reportMissingImports]

XML = Path(__file__).resolve().parent / "build" / f"{design.NAME}.xml"


def check(xml_path=XML, parts=design.PARTS, nets=design.NETS, dnp=design.DNP,
          offboard=frozenset(getattr(design, "OFFBOARD", {}))):
    """OFFBOARD refs are schematic documentation (not on board, not in a BOM): left out of the comparison."""
    # local, kicad-cli-generated netlist, not untrusted input; ElementTree does not resolve external entities
    root = ET.fromstring(Path(xml_path).read_text())
    got = {(n.attrib["name"].lstrip("/"), f"{node.get('ref')}.{node.get('pin')}")
           for n in root.iter("net") if not n.attrib["name"].startswith("unconnected-")
           for node in n.iter("node") if node.get("ref") not in offboard}
    want = {(net, p) for net, members in nets.items() for p in members}
    errors = [f"missing {x}" for x in sorted(want - got)] + [f"extra {x}" for x in sorted(got - want)]
    comps = {c.attrib["ref"]: (c.findtext("value"), c.findtext("footprint")) for c in root.iter("comp")
             if c.attrib["ref"] not in offboard}
    for ref, (value, _, fp) in parts.items():
        if comps.get(ref) != (value, fp):
            errors.append(f"{ref}: want {(value, fp)}, got {comps.get(ref)}")
    errors += [f"unexpected component {r}" for r in sorted(comps.keys() - parts.keys())]
    got_dnp = {c.attrib["ref"] for c in root.iter("comp") if c.find("property[@name='dnp']") is not None}
    if got_dnp != dnp:
        errors.append(f"DNP: want {sorted(dnp)}, got {sorted(got_dnp)}")
    return errors


def self_test():
    """An OFFBOARD documentation symbol on a board net must not count as a mismatch."""
    import tempfile
    xml = """<export><components>
      <comp ref="J1"><value>LCD</value><footprint>fp</footprint></comp>
      <comp ref="X_LCD"><value>LCD 1602</value><footprint></footprint></comp>
    </components><nets>
      <net name="/SDA_5V"><node ref="J1" pin="3"/><node ref="X_LCD" pin="3"/></net>
    </nets></export>"""
    with tempfile.NamedTemporaryFile("w", suffix=".xml") as f:
        f.write(xml)
        f.flush()
        kw = {"parts": {"J1": ("LCD", "C", "fp")}, "nets": {"SDA_5V": ["J1.3"]}, "dnp": set()}
        assert check(f.name, offboard={"X_LCD"}, **kw) == [], check(f.name, offboard={"X_LCD"}, **kw)
        assert check(f.name, offboard=set(), **kw), "an unknown X_ part must still be reported"
    print("check_netlist self-test ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        self_test()
        sys.exit()
    errors = check(Path(sys.argv[1]) if len(sys.argv) > 1 else XML)
    if errors:
        sys.exit("netlist MISMATCH:\n  " + "\n  ".join(errors))
    print(f"netlist matches {design.NAME}.py")
