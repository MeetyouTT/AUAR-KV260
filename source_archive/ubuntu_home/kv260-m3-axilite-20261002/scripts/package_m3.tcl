set task_root [file normalize [file join [file dirname [info script]] ..]]
set rtl_dir [file join $task_root rtl]
set board_parts [get_board_parts "*:kv260_som:*" -latest_file_version]
if {[llength $board_parts] != 1} {error "Expected one installed KV260 SOM board part: $board_parts"}
set part [get_property PART_NAME $board_parts]

create_project -force m3_package [file join $task_root build m3_package] -part $part
add_files -norecurse [list [file join $rtl_dir aura_m3_regs.v] [file join $rtl_dir m3_build_id.vh]]
set_property file_type {Verilog Header} [get_files m3_build_id.vh]
set_property include_dirs $rtl_dir [current_fileset]
set_property top aura_m3_regs [current_fileset]
update_compile_order -fileset sources_1
ipx::package_project -root_dir [file join $task_root ip_repo aura_m3_regs] \
    -vendor aura.local -library user -taxonomy /UserIP -import_files -set_current true
set core [ipx::current_core]
set_property name aura_m3_regs $core
set_property display_name {AURA M3 AXI-Lite registers} $core
set_property description {Identification and scratch registers; no PWM or actuator outputs} $core
set_property version 1.0 $core

set bus [ipx::get_bus_interfaces S_AXI -of_objects $core]
if {[llength $bus] != 1} {error "S_AXI was not inferred from RTL interface attributes"}
set_property interface_mode slave $bus
set_property slave_memory_map_ref S_AXI $bus
set memory_map [ipx::get_memory_maps S_AXI -of_objects $core]
if {$memory_map eq ""} {set memory_map [ipx::add_memory_map S_AXI $core]}
set blocks [ipx::get_address_blocks -of_objects $memory_map]
if {[llength $blocks] != 1} {error "Expected one automatically inferred AXI address block"}
set address_block [lindex $blocks 0]
if {[get_property NAME $address_block] ne "reg0"} {error "Unexpected inferred address block name"}
set_property base_address 0 $address_block
set_property range 4096 $address_block
set_property width 32 $address_block
set_property usage register $address_block
foreach {name offset access} {IP_ID 0 read-only ABI_VERSION 4 read-only BUILD_ID 8 read-only SCRATCH 12 read-write} {
    set register [ipx::add_register $name $address_block]
    set_property address_offset $offset $register
    set_property size 32 $register
    set_property access $access $register
}
ipx::associate_bus_interfaces -busif S_AXI -clock s_axi_aclk $core
set clock_interface [ipx::get_bus_interfaces s_axi_aclk -of_objects $core]
# This core consumes the platform clock; it does not generate a fixed-frequency clock.
# Reference clk_100M is 99.999 MHz. Let BD propagate its real frequency.
if {[llength [ipx::get_bus_parameters FREQ_HZ -of_objects $clock_interface]] != 0} {
    ipx::remove_bus_parameter FREQ_HZ $clock_interface
}
ipx::create_xgui_files $core
ipx::update_checksums $core
ipx::check_integrity $core
ipx::save_core $core

set fd [open [file join $task_root evidence m3_package_properties.txt] w]
puts $fd "PART=$part"
puts $fd "VLNV=[get_property VLNV $core]"
puts $fd "BUS=[get_property NAME $bus]"
puts $fd "MEMORY_MAP=[get_property SLAVE_MEMORY_MAP_REF $bus]"
puts $fd "RANGE=[get_property RANGE $address_block]"
close $fd
close_project

# Compile the new RTL separately before spending time on the complete platform.
# This OOC result does not prove full-system placement, routing or I/O coverage.
create_project -in_memory -part $part
set_property include_dirs $rtl_dir [current_fileset]
read_verilog [file join $rtl_dir aura_m3_regs.v]
set_property top aura_m3_regs [current_fileset]
synth_design -top aura_m3_regs -part $part -mode out_of_context
create_clock -period 10.000 -name m3_aclk [get_ports s_axi_aclk]
file mkdir [file join $task_root evidence m3_ooc]
report_utilization -file [file join $task_root evidence m3_ooc utilization.rpt]
report_timing_summary -file [file join $task_root evidence m3_ooc timing_summary.rpt]
write_checkpoint -force [file join $task_root evidence m3_ooc aura_m3_regs_synth.dcp]
puts "AURA_M3_PACKAGE_AND_SYNTHESIS_COMPLETE"
exit
