# Full rebuild: design check -> schematic -> netlist parity -> placed board -> autoroute -> ERC/DRC -> fab package.
# Every target regenerates from design.py (route.py needs the unrouted board, so pcb always runs first).
# Intermediate netlist and ERC/DRC reports go to build/ (gitignored).
PY = /usr/bin/python3
GERBER_LAYERS = F.Cu,B.Cu,F.Mask,B.Mask,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,Edge.Cuts
ZIP = fab/carrier_gerbers_jlcpcb.zip

.PHONY: all sch pcb route check fab

all: check fab

sch:
	mkdir -p build
	$(PY) design.py
	$(PY) gen_sch.py
	kicad-cli sch export netlist --format kicadxml -o build/carrier.xml carrier.kicad_sch
	$(PY) check_netlist.py build/carrier.xml

pcb: sch
	$(PY) gen_pcb.py

route: pcb
	$(PY) route.py

check: route
	kicad-cli sch erc --severity-all --exit-code-violations -o build/erc.rpt carrier.kicad_sch \
		|| { echo "ERC failed: see build/erc.rpt"; exit 1; }
	kicad-cli pcb drc --schematic-parity --severity-all --exit-code-violations -o build/drc.rpt carrier.kicad_pcb \
		|| { echo "DRC failed: see build/drc.rpt"; exit 1; }

# fab/gerbers/ is gitignored scratch; the zip built from it is the upload. A zip that fails
# check_gerbers.py is deleted so it can't be uploaded by mistake.
# print_1to1.pdf leaves out F.Cu: the GND pour would print solid black and hide the labels;
# pads come from the F.Fab sketch instead.
# jlc.py writes the JLCPCB assembly BOM + CPL (fab/jlc_*.csv) and checks them against the zip.
fab: check
	rm -rf fab/gerbers $(ZIP) fab/jlc_*.csv
	mkdir -p fab/gerbers
	kicad-cli pcb export gerbers -l $(GERBER_LAYERS) -o fab/gerbers/ carrier.kicad_pcb
	kicad-cli pcb export drill --format excellon -u mm --excellon-separate-th \
		--generate-map --map-format gerberx2 -o fab/gerbers/ carrier.kicad_pcb
	zip -jqX $(ZIP) fab/gerbers/* -x '*drl_map*' '*.gbrjob'
	$(PY) check_gerbers.py $(ZIP) || { rm -f $(ZIP); exit 1; }
	$(PY) jlc.py
	kicad-cli sch export bom --exclude-dnp --fields 'Reference,Value,Footprint,$${QUANTITY}' \
		--labels 'Refs,Value,Footprint,Qty' --group-by Value,Footprint -o fab/bom.csv carrier.kicad_sch
	kicad-cli sch export pdf -o fab/schematic.pdf carrier.kicad_sch
	kicad-cli pcb render --side top -o fab/top.png carrier.kicad_pcb
	kicad-cli pcb render --side bottom -o fab/bottom.png carrier.kicad_pcb
	kicad-cli pcb export pdf --layers F.Fab,F.Silkscreen,Edge.Cuts --sketch-pads-on-fab-layers --mode-single \
		--black-and-white --drill-shape-opt 2 -o fab/print_1to1.pdf carrier.kicad_pcb
