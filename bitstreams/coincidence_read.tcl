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
refresh_hw_device [lindex [get_hw_devices xc7vx485t_0] 0]
set mask [get_property OUTPUT_VALUE [get_hw_probes tdc_i/coincidence]]
puts $mask

