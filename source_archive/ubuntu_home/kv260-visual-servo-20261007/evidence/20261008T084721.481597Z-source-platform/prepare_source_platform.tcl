# Build fresh IP/BD collateral in AURA_PLATFORM_OUT, not the original Vitis project.
set out [file normalize $::env(AURA_PLATFORM_OUT)]
set part xck26-sfvc784-2LV-c
set bid $::env(AURA_PLATFORM_BUILD_ID)
set repos [split [string trim [read [set f [open [file join $out repos.txt] r]]]] "\n"]
close $f
foreach {name top rtl} {aura_visual_servo aura_m3_regs visual_servo.sv aura_disabled_audio aura_disabled_audio disabled_audio.sv} {
    create_project $name [file join $out package_$name] -part $part
    add_files -norecurse [file join $out $rtl]
    set_property top $top [current_fileset]
    update_compile_order -fileset sources_1
    ipx::package_project -root_dir [file join $out ip_repo $name] -vendor aura.local -library user -taxonomy /UserIP -import_files -set_current true
    set core [ipx::current_core]
    set_property name $name $core
    set_property version 1.0 $core
    set_property display_name $name $core
    if {$name eq "aura_visual_servo"} {
        set buses {S_AXI}
        set clocks {s_axi_aclk}
        set param [ipx::get_user_parameters BUILD_ID -of_objects $core]
        set_property value $bid $param
        set_property value $bid [ipx::get_hdl_parameters BUILD_ID -of_objects $core]
    } else {
        set buses {s_axi_ctrl_i2s_rx s_axi_ctrl_i2s_tx s_axi_lite_audio_fmt}
        set clocks {ACLK m_axi_aclk}
    }
    foreach busname $buses {
        set bus [ipx::get_bus_interfaces $busname -of_objects $core]
        if {[llength $bus] != 1} {error "Missing interface $name/$busname"}
        set_property slave_memory_map_ref $busname $bus
        set mm [ipx::get_memory_maps $busname -of_objects $core]
        if {$mm eq ""} {set mm [ipx::add_memory_map $busname $core]}
        set blocks [ipx::get_address_blocks -of_objects $mm]
        if {[llength $blocks] == 0} {set block [ipx::add_address_block reg0 $mm]} else {set block [lindex $blocks 0]}
        set_property base_address 0 $block
        set_property range [expr {$name eq "aura_visual_servo" ? 4096 : 65536}] $block
        set_property width 32 $block
        set_property usage register $block
    }
    foreach clock $clocks {
        set c [ipx::get_bus_interfaces $clock -of_objects $core]
        if {[llength [ipx::get_bus_parameters FREQ_HZ -of_objects $c]]} {ipx::remove_bus_parameter FREQ_HZ $c}
    }
    ipx::create_xgui_files $core
    ipx::update_checksums $core
    ipx::check_integrity $core
    ipx::save_core $core
    close_project
}

create_project platform [file join $out platform] -part $part
set_property board_part xilinx.com:kv260_som:part0:1.4 [current_project]
set_property ip_repo_paths [concat [list [file join $out ip_repo]] $repos] [current_project]
set_property ip_output_repo [file join $out ip_cache] [current_project]
update_ip_catalog
# import_files makes the BD/project outputs independent of the historic project.
import_files -norecurse [file join $out platform.bd]
set bd [get_files *.bd]
open_bd_design $bd
set motion [get_bd_cells aura_m3_regs_0]
set audio [get_bd_cells audio_ss_0]
if {[llength $motion] != 1 || [llength $audio] != 1} {error "Unexpected source platform"}
set saved_pins [dict create]
set saved_intfs [dict create]
foreach cell [list $motion $audio] {
    foreach pin [get_bd_pins -of_objects $cell] {
        set nets [get_bd_nets -quiet -of_objects $pin]
        if {[llength $nets] == 1} {dict set saved_pins [string trimleft $pin /] $nets}
    }
    foreach pin [get_bd_intf_pins -of_objects $cell] {
        set nets [get_bd_intf_nets -quiet -of_objects $pin]
        if {[llength $nets] == 1} {dict set saved_intfs [string trimleft $pin /] $nets}
    }
}
delete_bd_objs $motion $audio
create_bd_cell -type ip -vlnv aura.local:user:aura_visual_servo:1.0 aura_m3_regs_0
set_property CONFIG.BUILD_ID $bid [get_bd_cells aura_m3_regs_0]
create_bd_cell -type ip -vlnv aura.local:user:aura_disabled_audio:1.0 audio_ss_0
dict for {pin net} $saved_pins {
    if {$pin eq "audio_ss_0/lrclk_tx"} {continue}
    connect_bd_net -net $net [get_bd_pins $pin]
}
dict for {pin net} $saved_intfs {connect_bd_intf_net -intf_net $net [get_bd_intf_pins $pin]}
set_property name servo_pwm [get_bd_ports lrclk_tx]
connect_bd_net [get_bd_pins aura_m3_regs_0/servo_pwm] [get_bd_ports servo_pwm]

foreach {interface offset range} {
    aura_m3_regs_0/S_AXI 0x80080000 0x1000
    audio_ss_0/s_axi_lite_audio_fmt 0x80040000 0x10000
    audio_ss_0/s_axi_ctrl_i2s_rx 0x80060000 0x10000
    audio_ss_0/s_axi_ctrl_i2s_tx 0x80070000 0x10000
} {
    assign_bd_address -offset $offset -range $range -target_address_space [get_bd_addr_spaces PS_0/Data] [get_bd_addr_segs $interface/reg0]
}
assign_bd_address [get_bd_addr_spaces audio_ss_0/m_axi_mm2s_audio]
assign_bd_address [get_bd_addr_spaces audio_ss_0/m_axi_s2mm_audio]
validate_bd_design
save_bd_design
write_bd_tcl [file join $out platform_generated.tcl]
add_files -fileset constrs_1 -norecurse [file join $out pin.xdc]
generate_target all $bd
set wrappers [make_wrapper -files $bd -top]
add_files -norecurse $wrappers
set_property top kv260_ispMipiRx_vcu_DP_wrapper [current_fileset]
update_compile_order -fileset sources_1
set fd [open [file join $out platform_connections.txt] w]
foreach p {aura_m3_regs_0/s_axi_aclk aura_m3_regs_0/s_axi_aresetn aura_m3_regs_0/servo_pwm} {
    puts $fd "$p [get_bd_nets -of_objects [get_bd_pins $p]]"
}
puts $fd "BUILD_ID [get_property CONFIG.BUILD_ID [get_bd_cells aura_m3_regs_0]]"
foreach seg [get_bd_addr_segs -of_objects [get_bd_addr_spaces PS_0/Data]] {puts $fd "$seg [get_property OFFSET $seg] [get_property RANGE $seg]"}
close $fd
puts "AURA_SOURCE_PLATFORM_GENERATED"
close_project
exit
