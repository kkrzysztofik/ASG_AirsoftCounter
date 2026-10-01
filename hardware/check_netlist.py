"""Assert the exported KiCad netlist matches design.py.

kicad-cli sch export netlist --format kicadxml -o build/<BOARD>.xml <BOARD>.kicad_sch
/usr/bin/python3 check_netlist.py [build/<BOARD>.xml]
"""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from board import design  # pyright: ignore[reportMissingImports]

XML = Path(__file__).resolve().parent / "build" / f"{design.NAME}.xml"


def check(xml_path=XML, parts=design.PARTS, nets=design.NETS, dnp=design.DNP):
    # local, kicad-cli-generated netlist, not untrusted input; ElementTree does not resolve external entities
    root = ET.fromstring(Path(xml_path).read_text())
    got = {(n.attrib["name"].lstrip("/"), f"{node.get('ref')}.{node.get('pin')}")
           for n in root.iter("net") if not n.attrib["name"].startswith("unconnected-")
           for node in n.iter("node")}
    want = {(net, p) for net, members in nets.items() for p in members}
    errors = [f"missing {x}" for x in sorted(want - got)] + [f"extra {x}" for x in sorted(got - want)]
    comps = {c.attrib["ref"]: (c.findtext("value"), c.findtext("footprint")) for c in root.iter("comp")}
    for ref, (value, _, fp) in parts.items():
        if comps.get(ref) != (value, fp):
            errors.append(f"{ref}: want {(value, fp)}, got {comps.get(ref)}")
    errors += [f"unexpected component {r}" for r in sorted(comps.keys() - parts.keys())]
    got_dnp = {c.attrib["ref"] for c in root.iter("comp") if c.find("property[@name='dnp']") is not None}
    if got_dnp != dnp:
        errors.append(f"DNP: want {sorted(dnp)}, got {sorted(got_dnp)}")
    return errors


if __name__ == "__main__":
    errors = check(Path(sys.argv[1]) if len(sys.argv) > 1 else XML)
    if errors:
        sys.exit("netlist MISMATCH:\n  " + "\n  ".join(errors))
    print("netlist matches design.py")
