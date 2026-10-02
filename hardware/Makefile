# shellcheck disable=SC1009,SC1050,SC1064,SC1065,SC1072,SC1073  # GNU make, not shell: shellcheck misparses conditional directives
# Full rebuild of one board: design check -> schematic -> netlist parity -> placed board ->
# autoroute -> ERC/DRC -> fab package. BOARD=carrier (default), pack, pack_b or lipo selects the
# board
# module (board.py) and every output name; all of it regenerates from that module. route.py needs
# the unrouted board, so pcb always runs first. Intermediates and ERC/DRC reports go to build/.
BOARD ?= carrier
export BOARD
PY = /usr/bin/python3
GERBER_LAYERS = F.Cu,B.Cu,F.Mask,B.Mask,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,Edge.Cuts
# Carrier keeps its committed fab/ paths; the pack writes under fab/pack/ (FAB is exported so
# jlc.py and check_gerbers.py agree on where the zip and CSVs live). BOARD_PY is the board module
# file: carrier's data module is design.py, the pack's is pack.py.
ifeq ($(BOARD),carrier)
FAB = fab
BOARD_PY = design.py
else
FAB = fab/$(BOARD)
BOARD_PY = $(BOARD).py
endif
export FAB
ZIP = $(FAB)/$(BOARD)_gerbers_jlcpcb.zip

.PHONY: all sch pcb route check fab boards

all: check fab

sch:
	mkdir -p build
	$(PY) $(BOARD_PY)
	$(PY) gen_sch.py
	kicad-cli sch export netlist --format kicadxml -o build/$(BOARD).xml $(BOARD).kicad_sch
	$(PY) check_netlist.py build/$(BOARD).xml

pcb: sch
	$(PY) gen_pcb.py

route: pcb
	$(PY) route.py

check: route
	kicad-cli sch erc --severity-all --exit-code-violations -o build/$(BOARD)_erc.rpt $(BOARD).kicad_sch \
		|| { echo "ERC failed: see build/$(BOARD)_erc.rpt"; exit 1; }
	kicad-cli pcb drc --schematic-parity --severity-all --exit-code-violations -o build/$(BOARD)_drc.rpt $(BOARD).kicad_pcb \
		|| { echo "DRC failed: see build/$(BOARD)_drc.rpt"; exit 1; }

# $(FAB)/gerbers/ is gitignored scratch; the zip built from it is the upload. A zip that fails
# check_gerbers.py is deleted so it can't be uploaded by mistake.
# print_1to1.pdf leaves out F.Cu: the GND pour would print solid black and hide the labels;
# pads come from the F.Fab sketch instead.
# jlc.py writes the JLCPCB assembly BOM + CPL ($(FAB)/jlc_*.csv) and checks them against the zip;
# a *_tme board is hand-built, so it has no JLC files and tme.py writes its list straight from the
# module instead ($(FAB)/tme_bom.csv).
fab: check
	rm -rf $(FAB)/gerbers $(ZIP) $(FAB)/jlc_*.csv
	mkdir -p $(FAB)/gerbers
	kicad-cli pcb export gerbers -l $(GERBER_LAYERS) -o $(FAB)/gerbers/ $(BOARD).kicad_pcb
	kicad-cli pcb export drill --format excellon -u mm --excellon-separate-th \
		--generate-map --map-format gerberx2 -o $(FAB)/gerbers/ $(BOARD).kicad_pcb
	zip -jqX $(ZIP) $(FAB)/gerbers/* -x '*drl_map*' '*.gbrjob'
	$(PY) check_gerbers.py $(ZIP) || { rm -f $(ZIP); exit 1; }
ifeq ($(filter %_tme,$(BOARD)),)
	$(PY) jlc.py
endif
	$(PY) tme.py
	kicad-cli sch export bom --exclude-dnp --fields 'Reference,Value,Footprint,$${QUANTITY}' \
		--labels 'Refs,Value,Footprint,Qty' --group-by Value,Footprint -o $(FAB)/bom.csv $(BOARD).kicad_sch
	kicad-cli sch export pdf -o $(FAB)/schematic.pdf $(BOARD).kicad_sch
	kicad-cli pcb render --side top -o $(FAB)/top.png $(BOARD).kicad_pcb
	kicad-cli pcb render --side bottom -o $(FAB)/bottom.png $(BOARD).kicad_pcb
	kicad-cli pcb export pdf --layers F.Fab,F.Silkscreen,Edge.Cuts --sketch-pads-on-fab-layers --mode-single \
		--black-and-white --drill-shape-opt 2 -o $(FAB)/print_1to1.pdf $(BOARD).kicad_pcb

# Every board in one command (run before ordering).
boards:
	$(MAKE) BOARD=carrier all
	$(MAKE) BOARD=pack all
	$(MAKE) BOARD=pack_b all
	$(MAKE) BOARD=lipo all
	$(MAKE) BOARD=carrier_tme all
	$(MAKE) BOARD=pack_tme all
	$(MAKE) BOARD=lipo_tme all

# Printed insert for the Pawbol S-BOX 416-P. check.py is deliberately run on the system
# python3: it is the half of the checking that has to work with no CAD stack installed.
# insert.py is a PEP-723 script, so uv resolves build123d from the file's own metadata.
# PROC picks the print process everything is validated and priced against: mjf, fdm or sla.
# PARTS limits a run to the parts that process will actually make, so an FDM run is not judged
# against features belonging to the small flat parts it rejects.
PROC ?= mjf
PARTS ?= all
export MECH_PROCESS = $(PROC)
export MECH_PARTS = $(PARTS)
.PHONY: mech
mech:
	/usr/bin/python3 mech/check.py
	uv run mech/insert.py --part $(PARTS) --check

# Quote package for JLCPCB 3D printing: one model per part in a zip, plus the quote sheet.
# MAT follows PROC unless overridden. Regenerate per process; the filenames carry the process
# so an FDM quote cannot be mistaken for the MJF one.
MAT ?= $(shell /usr/bin/python3 -c "import sys; sys.path.insert(0,'mech'); import quote; print(quote.MATERIAL)")
.PHONY: mech-fab
mech-fab: mech
	/usr/bin/python3 mech/quote.py --parts "$(PARTS)" --format stl --material "$(MAT)"
	/usr/bin/python3 mech/quote.py --parts "$(PARTS)" --format step --material "$(MAT)"
