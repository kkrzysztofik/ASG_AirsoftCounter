#!/bin/sh
# Regenerate the unrouted carrier and compare with the P1 baseline, then restore the routed files.
set -e
cd "$(dirname "$0")/.."
make pcb >/dev/null
for f in carrier.kicad_sch carrier.kicad_pro carrier.kicad_pcb; do cmp "$f" "/tmp/carrier_base/$f"; done
git checkout -- carrier.kicad_pcb carrier.kicad_sch carrier.kicad_pro
echo "carrier unchanged"
