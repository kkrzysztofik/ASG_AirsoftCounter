"""Autoroute carrier.kicad_pcb with Freerouting, add the F.Cu GND pour, fill zones, save in place.

Input must be the unrouted board straight from gen_pcb.py: a board that already has unlocked tracks
or vias is refused (re-run gen_pcb.py first) rather than stripped, so a half-routed board never gets
reused. gen_pcb.py's locked GND vias and ties go to Freerouting as fixed wiring and are kept.
Loads the board in place so KiCad picks up the net classes from carrier.kicad_pro beside it.
Run from anywhere: /usr/bin/python3 route.py
"""
import re
import subprocess
import tempfile
from pathlib import Path

import pcbnew

import gen_pcb

JAR = gen_pcb.HERE / "tools" / "freerouting-2.4.1.jar"
PASSES = 100
TIMEOUT_S = 600


def load():
    gen_pcb.verify()  # rules + per-net classes resolve (i.e. carrier.kicad_pro is beside the board)
    return pcbnew.LoadBoard(str(gen_pcb.PCB))


def freeroute(board, tmp):
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
    dsn.write_text(text.replace(planes[0], ""))
    cmd = ["java", "-jar", str(JAR), "-de", str(dsn), "-do", str(ses), "-mp", str(PASSES),
           "--gui.enabled=false", "--api_server.enabled=false",
           "--usage_and_diagnostic_data.disable_analytics=true"]
    with open(log, "w") as f:
        try:
            subprocess.run(cmd, check=True, stdout=f, stderr=subprocess.STDOUT, timeout=TIMEOUT_S)
        except (OSError, subprocess.SubprocessError) as e:
            raise SystemExit(f"freerouting failed ({e}):\n{log.read_text()[-3000:]}")
    text = log.read_text()
    # Regex tied to Freerouting 2.4.1 log wording; the post-import unconnected check is the real gate
    done = re.findall(r"Auto-routing stage completed: .*?final score: ([\d.]+) \((\d+) unrouted", text)
    if not done or done[-1][1] != "0" or not ses.exists():
        raise SystemExit(f"freerouting left unrouted connections or no SES:\n{text[-3000:]}")
    print(f"freerouting: {len(re.findall('Auto-routing pass #', text))} passes, score {done[-1][0]}, 0 unrouted")
    return ses


def main():
    board = load()
    if any(not t.IsLocked() for t in board.GetTracks()) or any(z.GetZoneName() == "GND_F" for z in board.Zones()):
        raise SystemExit(f"{gen_pcb.PCB.name} is already routed: run gen_pcb.py first")
    with tempfile.TemporaryDirectory(prefix="route-") as tmp:
        ses = freeroute(board, Path(tmp))
        board = load()  # fresh copy: DSN export must not leave anything behind
        pcbnew.KIID.SeedGenerator(2)  # deterministic uuids for imported tracks/vias and the new zone
        if not pcbnew.ImportSpecctraSES(board, str(ses)):
            raise SystemExit("SES import failed")

    b_gnd = [z for z in board.Zones() if z.GetZoneName() == "GND"]
    if len(b_gnd) != 1:
        raise SystemExit(f"expected one GND pour from gen_pcb.py, found {len(b_gnd)}")
    f_gnd = gen_pcb.zone(board, "GND_F", 0, 0, gen_pcb.W, gen_pcb.H, lset=gen_pcb.layers(pcbnew.F_Cu))
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
    if not pcbnew.SaveBoard(str(gen_pcb.PCB), board, True):  # True: leave carrier.kicad_pro alone
        raise SystemExit("save failed")
    gen_pcb.verify()
    print(f"wrote {gen_pcb.PCB.name}: {len(board.GetTracks())} tracks/vias, 0 unconnected")


if __name__ == "__main__":
    main()
