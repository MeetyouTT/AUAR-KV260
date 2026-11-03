# Called after the unchanged reference config_bd.tcl, in the isolated M3 project.
set m3_root [file normalize [file join [file dirname [info script]] ..]]
current_bd_instance /
set control_ic [get_bd_cells axi_ic_ctrl_100]
if {[llength $control_ic] != 1} {error "Expected reference axi_ic_ctrl_100"}
if {[get_property CONFIG.NUM_MI $control_ic] != 6} {error "Unexpected existing AXI control port count"}
if {[llength [get_bd_cells -quiet aura_m3_regs_0]] != 0} {error "M3 module already exists"}
set_property CONFIG.NUM_MI 7 $control_ic
set m3_cell [create_bd_cell -type ip -vlnv aura.local:user:aura_m3_regs:1.0 aura_m3_regs_0]
connect_bd_intf_net [get_bd_intf_pins axi_ic_ctrl_100/M06_AXI] [get_bd_intf_pins aura_m3_regs_0/S_AXI]
connect_bd_net [get_bd_pins clk_wiz_0/clk_100M] \
    [get_bd_pins axi_ic_ctrl_100/M06_ACLK] [get_bd_pins aura_m3_regs_0/s_axi_aclk]
connect_bd_net [get_bd_pins proc_sys_reset_100MHz/peripheral_aresetn] \
    [get_bd_pins axi_ic_ctrl_100/M06_ARESETN] [get_bd_pins aura_m3_regs_0/s_axi_aresetn]

set m3_segment [get_bd_addr_segs aura_m3_regs_0/S_AXI/reg0]
if {[llength $m3_segment] != 1} {error "M3 register segment not found"}
assign_bd_address -offset 0x80080000 -range 0x1000 \
    -target_address_space [get_bd_addr_spaces PS_0/Data] $m3_segment
validate_bd_design
save_bd_design

set fd [open [file join $m3_root evidence m3_platform_addresses.txt] w]
foreach segment [get_bd_addr_segs -of_objects [get_bd_addr_spaces PS_0/Data]] {
    puts $fd "[get_property NAME $segment] OFFSET=[get_property OFFSET $segment] RANGE=[get_property RANGE $segment]"
}
close $fd
set fd [open [file join $m3_root evidence m3_platform_connections.txt] w]
puts $fd "M3_IP=[get_property VLNV $m3_cell]"
foreach pin {aura_m3_regs_0/s_axi_aclk aura_m3_regs_0/s_axi_aresetn axi_ic_ctrl_100/M06_ACLK axi_ic_ctrl_100/M06_ARESETN} {
    puts $fd "$pin NET=[get_bd_nets -of_objects [get_bd_pins $pin]]"
}
puts $fd "M3_CONTROL_NET=[get_bd_intf_nets -of_objects [get_bd_intf_pins aura_m3_regs_0/S_AXI]]"
close $fd
puts "AURA_M3_BD_INTEGRATION_COMPLETE BASE=0x80080000 RANGE=0x1000 CLOCK=100MHz"
