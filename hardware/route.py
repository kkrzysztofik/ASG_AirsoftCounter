"""Autoroute kicad/<BOARD>.kicad_pcb with Freerouting, add the F.Cu GND pour, fill zones, save in place.

Input must be the unrouted board straight from gen_pcb.py: a board that already has unlocked tracks
or vias is refused (re-run gen_pcb.py first) rather than stripped, so a half-routed board never gets
reused. gen_pcb.py's locked GND vias and ties go to Freerouting as fixed wiring and are kept.
Loads the board in place so KiCad picks up the net classes from <BOARD>.kicad_pro beside it.
Run from anywhere: /usr/bin/python3 route.py
"""
import re
import subprocess
import tempfile
from pathlib import Path

import pcbnew  # pyright: ignore[reportMissingImports]

import gen_pcb
from board import design  # pyright: ignore[reportMissingImports]

JAR = gen_pcb.HERE / "tools" / "freerouting-2.4.1.jar"
PASSES = 100
TIMEOUT_S = 600


def load():
    gen_pcb.verify()  # rules + per-net classes resolve (i.e. <BOARD>.kicad_pro is beside the board)
    return pcbnew.LoadBoard(str(gen_pcb.PCB))


def freeroute(board, tmp, margin_um):
    dsn, ses, log = tmp / "carrier.dsn", tmp / "carrier.ses", tmp / "freerouting.log"
    if not pcbnew.ExportSpecctraDSN(board, str(dsn)):
        raise SystemExit("DSN export failed")
    # KiCad exports the B.Cu GND pour as a Specctra plane, and Freerouting then counts every THT GND
    # pin and via as connected through it without routing them, while cutting that pour with its own
    # B.Cu traces (J3.1 ended up on an island). Without the plane it routes GND like any net, so the
    # pours added afterwards can only add connections.
    text = dsn.read_text()
    planes = re.findall(r"^\s*\(plane GND .*\n", text, re.M)
    if len(planes) != 1:
        raise SystemExit(f"expected one GND plane in the DSN, found {len(planes)}")
    if planes[0].count("(") != planes[0].count(")"):  # the regex only strips a one-line stanza
        raise SystemExit("GND plane spans several lines in the DSN: extend the stripping")
    text = text.replace(planes[0], "")
    # Freerouting checks clearance on octagons, KiCad on true round ends: on a 0.8 mm Power track the
    # octagon undercuts by up to 0.4 * (1/cos 22.5 - 1) = 0.033 mm, and KiCad 10 exports clearances with
    # no margin (KiCad 9 wrote 200.1 um), so Power tracks landed 0.17-0.18 mm apart. Route Power with a margin.
    m = re.search(r"\(class Power[^(]*\(circuit[^)]*\)[^(]*\)\s*\(rule\s*\(width \d+\)\s*\(clearance (\d+)\)", text)
    if text.count("(class Power") > 1 or ("(class Power" in text) != bool(m):
        raise SystemExit("unexpected Power class layout in the DSN: update the clearance margin regex")
    if m:
        text = text[:m.start(1)] + str(int(m.group(1)) + margin_um) + text[m.end(1):]
    dsn.write_text(text)
    cmd = ["java", "-jar", str(JAR), "-de", str(dsn), "-do", str(ses), "-mp", str(PASSES),
           "--gui.enabled=false", "--api_server.enabled=false",
           "--usage_and_diagnostic_data.disable_analytics=true"]
    try:
        with open(log, "w") as f:
            subprocess.run(cmd, check=True, stdout=f, stderr=subprocess.STDOUT, timeout=TIMEOUT_S)
    except (OSError, subprocess.SubprocessError) as e:
        raise SystemExit(f"freerouting failed ({e}):\n{log.read_text()[-3000:]}") from e
    text = log.read_text()
    # Regex tied to Freerouting 2.4.1 log wording; the post-import unconnected check is the real gate
    done = re.findall(r"Auto-routing stage completed: .*?final score: ([\d.]+) \((\d+) unrouted", text)
    if not done or done[-1][1] != "0" or not ses.exists():
        print(f"freerouting (Power margin {margin_um} um) left unrouted connections or no SES:\n{text[-1500:]}")
        return None
    print(f"freerouting: Power margin {margin_um} um, {len(re.findall('Auto-routing pass #', text))} passes, "
          f"score {done[-1][0]}, 0 unrouted")
    return ses


def main():
    board = load()
    if any(not t.IsLocked() for t in board.GetTracks()) or any(z.GetZoneName() == "GND_F" for z in board.Zones()):
        raise SystemExit(f"{gen_pcb.PCB.name} is already routed: run gen_pcb.py first")
    with tempfile.TemporaryDirectory(prefix="route-") as tmp:
        # The margin can cost the last connection on a tight board (carrier); without it, make check's DRC
        # is the gate on the octagon undercut.
        ses = freeroute(board, Path(tmp), 40) or freeroute(board, Path(tmp), 0)
        if not ses:
            raise SystemExit("freerouting left unrouted connections with and without the Power margin")
        board = load()  # fresh copy: DSN export must not leave anything behind
        pcbnew.KIID.SeedGenerator(2)  # deterministic uuids for imported tracks/vias and the new zone
        if not pcbnew.ImportSpecctraSES(board, str(ses)):
            raise SystemExit("SES import failed")

    # Freerouting leaves the odd sub-mm stub with a free end (DRC track_dangling); it carries nothing.
    board.BuildConnectivity()
    while stubs := [t for t in board.GetTracks() if t.Type() == pcbnew.PCB_TRACE_T and not t.IsLocked()
                    and board.GetConnectivity().TestTrackEndpointDangling(t, False)]:
        for t in stubs:
            board.Remove(t)
        board.BuildConnectivity()

    b_gnd = [z for z in board.Zones() if z.GetZoneName() == "GND"]
    if len(b_gnd) != 1:
        raise SystemExit(f"expected one GND pour from gen_pcb.py, found {len(b_gnd)}")
    f_gnd = gen_pcb.zone(board, "GND_F", 0, 0, design.W, design.H, lset=gen_pcb.layers(pcbnew.F_Cu))
    f_gnd.SetNet(board.FindNet("GND"))
    f_gnd.SetAssignedPriority(0)
    f_gnd.SetLocalClearance(b_gnd[0].GetLocalClearance())
    f_gnd.SetPadConnection(gen_pcb.GND_PAD_CONNECTION)
    if not pcbnew.ZONE_FILLER(board).Fill(board.Zones()):
        raise SystemExit("zone fill failed")

    board.BuildConnectivity()
    unconnected = board.GetConnectivity().GetUnconnectedCount(False)
    if unconnected:
        raise SystemExit(f"{unconnected} unconnected items after SES import + fill")
    if not pcbnew.SaveBoard(str(gen_pcb.PCB), board, True):  # True: leave <BOARD>.kicad_pro alone
        raise SystemExit("save failed")
    gen_pcb.verify()
    print(f"wrote {gen_pcb.PCB.name}: {len(board.GetTracks())} tracks/vias, 0 unconnected")


if __name__ == "__main__":
    main()
