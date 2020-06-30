set fpga [lindex $argv 0]
set argument1 "\{localhost:3121/xilinx_tcf/Digilent/"
if {$fpga==1} {
    set argument2 "210203A5FC8DA"
} else {
    set argument2 "210203A63118A"
}        
set argument3 "\}"
set argument $argument1$argument2$argument3
open_hw
connect_hw_server
eval open_hw_target $argument
current_hw_device [get_hw_devices xc7vx485t_0]
refresh_hw_device -update_hw_probes false [lindex [get_hw_devices xc7vx485t_0] 0]
set_property PROBES.FILE {/home/xdaq/bitstreams/tdc_gbt.ltx} [get_hw_devices xc7vx485t_0]
set_property FULL_PROBES.FILE {/home/xdaq/bitstreams/tdc_gbt.ltx} [get_hw_devices xc7vx485t_0]
set_property PROGRAM.FILE {/home/xdaq/bitstreams/tdc_gbt.bit} [get_hw_devices xc7vx485t_0]
program_hw_devices [get_hw_devices xc7vx485t_0]
refresh_hw_device [lindex [get_hw_devices xc7vx485t_0] 0]
set_property OUTPUT_VALUE 8 [get_hw_probes tdc_i/coincidence -of_objects [get_hw_vios -of_objects [get_hw_devices xc7vx485t_0] -filter {CELL_NAME=~"tdc_i/vio_i"}]]
commit_hw_vio [get_hw_probes {tdc_i/coincidence} -of_objects [get_hw_vios -of_objects [get_hw_devices xc7vx485t_0] -filter {CELL_NAME=~"tdc_i/vio_i"}]]
set_property OUTPUT_VALUE FF [get_hw_probes tdc_i/event_mask -of_objects [get_hw_vios -of_objects [get_hw_devices xc7vx485t_0] -filter {CELL_NAME=~"tdc_i/vio_i"}]]
commit_hw_vio [get_hw_probes {tdc_i/event_mask} -of_objects [get_hw_vios -of_objects [get_hw_devices xc7vx485t_0] -filter {CELL_NAME=~"tdc_i/vio_i"}]]
set_property OUTPUT_VALUE 300000000000000000000000000000000 [get_hw_probes tdc_i/mask -of_objects [get_hw_vios -of_objects [get_hw_devices xc7vx485t_0] -filter {CELL_NAME=~"tdc_i/vio_i"}]]
commit_hw_vio [get_hw_probes {tdc_i/mask} -of_objects [get_hw_vios -of_objects [get_hw_devices xc7vx485t_0] -filter {CELL_NAME=~"tdc_i/vio_i"}]]
set_property OUTPUT_VALUE 3 [get_hw_probes testPatterSel_from_user -of_objects [get_hw_vios -of_objects [get_hw_devices xc7vx485t_0] -filter {CELL_NAME=~"vio"}]]
commit_hw_vio [get_hw_probes {testPatterSel_from_user} -of_objects [get_hw_vios -of_objects [get_hw_devices xc7vx485t_0] -filter {CELL_NAME=~"vio"}]]
set_property OUTPUT_VALUE $fpga [get_hw_probes rst_sel -of_objects [get_hw_vios -of_objects [get_hw_devices xc7vx485t_0] -filter {CELL_NAME=~"vio"}]]
commit_hw_vio [get_hw_probes {rst_sel} -of_objects [get_hw_vios -of_objects [get_hw_devices xc7vx485t_0] -filter {CELL_NAME=~"vio"}]]
startgroup
set_property OUTPUT_VALUE 1 [get_hw_probes generalReset_from_user -of_objects [get_hw_vios -of_objects [get_hw_devices xc7vx485t_0] -filter {CELL_NAME=~"vio"}]]
commit_hw_vio [get_hw_probes {generalReset_from_user} -of_objects [get_hw_vios -of_objects [get_hw_devices xc7vx485t_0] -filter {CELL_NAME=~"vio"}]]
endgroup
startgroup
set_property OUTPUT_VALUE 0 [get_hw_probes generalReset_from_user -of_objects [get_hw_vios -of_objects [get_hw_devices xc7vx485t_0] -filter {CELL_NAME=~"vio"}]]
commit_hw_vio [get_hw_probes {generalReset_from_user} -of_objects [get_hw_vios -of_objects [get_hw_devices xc7vx485t_0] -filter {CELL_NAME=~"vio"}]]
endgroup

