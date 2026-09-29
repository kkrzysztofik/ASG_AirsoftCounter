# Full rebuild: design check -> schematic -> netlist parity -> placed board -> autoroute -> ERC/DRC -> fab package.
# Every target regenerates from design.py (route.py needs the unrouted board, so pcb always runs first).
PY = /usr/bin/python3
GERBER_LAYERS = F.Cu,B.Cu,F.Mask,B.Mask,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,Edge.Cuts
ZIP = fab/carrier_gerbers_jlcpcb.zip

.DELETE_ON_ERROR:
.PHONY: all sch pcb route check fab clean

all: check fab

sch:
	$(PY) design.py
	$(PY) gen_sch.py
	kicad-cli sch export netlist --format kicadxml -o /tmp/carrier.xml carrier.kicad_sch
	$(PY) check_netlist.py

pcb: sch
	$(PY) gen_pcb.py

route: pcb
	$(PY) route.py

check: route
	kicad-cli sch erc --severity-error --exit-code-violations -o /tmp/erc.rpt carrier.kicad_sch
	kicad-cli pcb drc --schematic-parity --severity-error --exit-code-violations -o /tmp/drc.rpt carrier.kicad_pcb

fab: check
	rm -rf fab/gerbers $(ZIP)
	mkdir -p fab/gerbers
	kicad-cli pcb export gerbers -l $(GERBER_LAYERS) -o fab/gerbers/ carrier.kicad_pcb
	kicad-cli pcb export drill --format excellon -u mm --excellon-separate-th \
		--generate-map --map-format gerberx2 -o fab/gerbers/ carrier.kicad_pcb
	zip -jqX $(ZIP) fab/gerbers/* -x '*drl_map*' '*.gbrjob'
	$(PY) check_gerbers.py $(ZIP)
	kicad-cli sch export bom --exclude-dnp --fields 'Reference,Value,Footprint,$${QUANTITY}' \
		--labels 'Refs,Value,Footprint,Qty' --group-by Value,Footprint -o fab/bom.csv carrier.kicad_sch
	kicad-cli sch export pdf -o fab/schematic.pdf carrier.kicad_sch
	kicad-cli pcb render --side top -o fab/top.png carrier.kicad_pcb
	kicad-cli pcb render --side bottom -o fab/bottom.png carrier.kicad_pcb
	# no F.Cu: the GND pour would print solid black and hide the labels; pads come from F.Fab sketch
	kicad-cli pcb export pdf --layers F.Fab,F.Silkscreen,Edge.Cuts --sketch-pads-on-fab-layers --mode-single \
		--black-and-white --drill-shape-opt 2 -o fab/print_1to1.pdf carrier.kicad_pcb

clean:
	rm -rf fab/gerbers $(ZIP)
