set argument "\{localhost:3121/xilinx_tcf/Xilinx/00001165d12a01\}"
open_hw
connect_hw_server
eval open_hw_target $argument
current_hw_device [get_hw_devices xcku115_0]
refresh_hw_device -update_hw_probes false [lindex [get_hw_devices xcku115_0] 0]
set_property PROBES.FILE {/home/xdaq/bitstreams/pcie_gbt_2.ltx} [get_hw_devices xcku115_0]
set_property FULL_PROBES.FILE {/home/xdaq/bitstreams/pcie_gbt_2.ltx} [get_hw_devices xcku115_0]
set_property PROGRAM.FILE {/home/xdaq/bitstreams/pcie_gbt_2.bit} [get_hw_devices xcku115_0]
program_hw_devices [get_hw_devices xcku115_0]

refresh_hw_device [lindex [get_hw_devices xcku115_0] 0]
set_property OUTPUT_VALUE 0020 [get_hw_probes packet_lenght -of_objects [get_hw_vios -of_objects [get_hw_devices xcku115_0] -filter {CELL_NAME=~"vio_i"}]]
commit_hw_vio [get_hw_probes {packet_lenght} -of_objects [get_hw_vios -of_objects [get_hw_devices xcku115_0] -filter {CELL_NAME=~"vio_i"}]]
set_property OUTPUT_VALUE 3 [get_hw_probes gbt_i/testPatterSel_from_user -of_objects [get_hw_vios -of_objects [get_hw_devices xcku115_0] -filter {CELL_NAME=~"gbt_i/vio"}]]
commit_hw_vio [get_hw_probes {gbt_i/testPatterSel_from_user} -of_objects [get_hw_vios -of_objects [get_hw_devices xcku115_0] -filter {CELL_NAME=~"gbt_i/vio"}]]
startgroup
set_property OUTPUT_VALUE 1 [get_hw_probes gbt_i/generalReset_from_user -of_objects [get_hw_vios -of_objects [get_hw_devices xcku115_0] -filter {CELL_NAME=~"gbt_i/vio"}]]
commit_hw_vio [get_hw_probes {gbt_i/generalReset_from_user} -of_objects [get_hw_vios -of_objects [get_hw_devices xcku115_0] -filter {CELL_NAME=~"gbt_i/vio"}]]
endgroup
startgroup
set_property OUTPUT_VALUE 0 [get_hw_probes gbt_i/generalReset_from_user -of_objects [get_hw_vios -of_objects [get_hw_devices xcku115_0] -filter {CELL_NAME=~"gbt_i/vio"}]]
commit_hw_vio [get_hw_probes {gbt_i/generalReset_from_user} -of_objects [get_hw_vios -of_objects [get_hw_devices xcku115_0] -filter {CELL_NAME=~"gbt_i/vio"}]]
endgroup
