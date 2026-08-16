read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
read_db /OpenROAD-flow-scripts/flow/results/nangate45/gcd/base/4_cts.odb
read_sdc /OpenROAD-flow-scripts/flow/results/nangate45/gcd/base/4_cts.sdc
source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl

set ::env(MIN_ROUTING_LAYER) metal2
set ::env(MIN_CLK_ROUTING_LAYER) metal4
set ::env(MAX_ROUTING_LAYER) metal10

source /OpenROAD-flow-scripts/flow/platforms/nangate45/fastroute.tcl

# Training knob: intentionally reduce routing capacity too aggressively.
set_global_routing_layer_adjustment metal2-metal10 0.95

pin_access
global_route \
  -congestion_report_file /workspace/workspace/07_openroad_grt_closure/p3_low_capacity_congestion_bad.rpt \
  -congestion_iterations 30 \
  -congestion_report_iter_step 5 \
  -verbose

puts "P3 low-capacity global route finished"
