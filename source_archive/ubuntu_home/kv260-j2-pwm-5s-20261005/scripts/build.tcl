set root $::env(AURA_PWM_ROOT)
set out $::env(AURA_PWM_OUT)
set rtl [file join $root rtl]
set boards [get_board_parts "*:kv260_som:*" -latest_file_version]
if {[llength $boards] != 1} {error "Expected one KV260 SOM board definition"}
set part [get_property PART_NAME $boards]
create_project pwm_package [file join $out package] -part $part
add_files -norecurse [list [file join $rtl aura_pwm_probe.sv] [file join $rtl pwm_burst.sv]]
set_property top aura_pwm_probe [current_fileset]
update_compile_order -fileset sources_1
ipx::package_project -root_dir [file join $out ip_repo aura_pwm_probe] \
    -vendor aura.local -library bench -taxonomy /UserIP -import_files -set_current true
set core [ipx::current_core]
set_property name aura_pwm_probe $core
set_property version 1.0 $core
set_property display_name {AURA bounded J2 PWM bench probe} $core
set_property description {Offline bench candidate, disabled on reset, 250 fixed pulses per explicit command} $core
set bus [ipx::get_bus_interfaces S_AXI -of_objects $core]
if {[llength $bus] != 1} {error "AXI-Lite interface was not inferred"}
set_property slave_memory_map_ref S_AXI $bus
set mmap [ipx::get_memory_maps S_AXI -of_objects $core]
set blocks [ipx::get_address_blocks -of_objects $mmap]
if {[llength $blocks] != 1} {error "Expected exactly one register address block"}
set block [lindex $blocks 0]
set_property base_address 0 $block
set_property range 4096 $block
set_property width 32 $block
set_property usage register $block
ipx::associate_bus_interfaces -busif S_AXI -clock s_axi_aclk $core
set clkif [ipx::get_bus_interfaces s_axi_aclk -of_objects $core]
if {[llength [ipx::get_bus_parameters FREQ_HZ -of_objects $clkif]]} {
    ipx::remove_bus_parameter FREQ_HZ $clkif
}
ipx::create_xgui_files $core
ipx::update_checksums $core
ipx::check_integrity $core
ipx::save_core $core
close_project

create_project pwm_bench [file join $out project] -part $part
set_property board_part $boards [current_project]
set_property ip_repo_paths [file join $out ip_repo] [current_project]
update_ip_catalog
create_bd_design pwm_bench
set ps [create_bd_cell -type ip -vlnv xilinx.com:ip:zynq_ultra_ps_e PS_0]
apply_bd_automation -rule xilinx.com:bd_rule:zynq_ultra_ps_e \
    -config {apply_board_preset "1"} $ps
set_property -dict [list CONFIG.PSU__FPGA_PL0_ENABLE {1} \
    CONFIG.PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ {100} \
    CONFIG.PSU__MAXIGP2__DATA_WIDTH {32} CONFIG.PSU__USE__M_AXI_GP2 {1} \
    CONFIG.PSU__USE__M_AXI_GP0 {0} CONFIG.PSU__USE__M_AXI_GP1 {0} \
    CONFIG.PSU__USE__S_AXI_GP0 {0} CONFIG.PSU__USE__S_AXI_GP1 {0} \
    CONFIG.PSU__USE__S_AXI_GP2 {0} CONFIG.PSU__USE__S_AXI_GP3 {0} \
    CONFIG.PSU__USE__S_AXI_GP4 {0} CONFIG.PSU__USE__S_AXI_GP5 {0} \
    CONFIG.PSU__USE__S_AXI_GP6 {0}] $ps
set actual_mhz [get_property CONFIG.PSU__CRL_APB__PL0_REF_CTRL__ACT_FREQMHZ $ps]
set actual_hz [expr {round(double($actual_mhz) * 1000000.0)}]
if {$actual_hz != 99999001} {error "Clock changed to $actual_hz Hz; re-simulate before build"}
set probe [create_bd_cell -type ip -vlnv aura.local:bench:aura_pwm_probe:1.0 probe]
set_property -dict [list CONFIG.CLK_HZ $actual_hz CONFIG.PWM_HZ 50 \
    CONFIG.PULSE_US 1500 CONFIG.RUN_FRAMES 250] $probe
set ic [create_bd_cell -type ip -vlnv xilinx.com:ip:axi_interconnect axi_ctrl]
set_property -dict [list CONFIG.NUM_SI 1 CONFIG.NUM_MI 1] $ic
set rst [create_bd_cell -type ip -vlnv xilinx.com:ip:proc_sys_reset reset_ctrl]
set one [create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant one]
set zero [create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant zero]
set_property CONFIG.CONST_VAL 0 $zero
connect_bd_intf_net [get_bd_intf_pins PS_0/M_AXI_HPM0_LPD] [get_bd_intf_pins axi_ctrl/S00_AXI]
connect_bd_intf_net [get_bd_intf_pins axi_ctrl/M00_AXI] [get_bd_intf_pins probe/S_AXI]
connect_bd_net [get_bd_pins PS_0/pl_clk0] [get_bd_pins PS_0/maxihpm0_lpd_aclk] \
    [get_bd_pins axi_ctrl/ACLK] [get_bd_pins axi_ctrl/S00_ACLK] \
    [get_bd_pins axi_ctrl/M00_ACLK] [get_bd_pins probe/s_axi_aclk] \
    [get_bd_pins reset_ctrl/slowest_sync_clk]
connect_bd_net [get_bd_pins PS_0/pl_resetn0] [get_bd_pins reset_ctrl/ext_reset_in]
connect_bd_net [get_bd_pins one/dout] [get_bd_pins reset_ctrl/dcm_locked]
# Both external and auxiliary reset polarities are propagated active-low.
# Keep the unused auxiliary reset deasserted; debug reset is active-high.
connect_bd_net [get_bd_pins one/dout] [get_bd_pins reset_ctrl/aux_reset_in]
connect_bd_net [get_bd_pins zero/dout] [get_bd_pins reset_ctrl/mb_debug_sys_rst]
connect_bd_net [get_bd_pins reset_ctrl/interconnect_aresetn] [get_bd_pins axi_ctrl/ARESETN]
connect_bd_net [get_bd_pins reset_ctrl/peripheral_aresetn] \
    [get_bd_pins axi_ctrl/S00_ARESETN] [get_bd_pins axi_ctrl/M00_ARESETN] [get_bd_pins probe/s_axi_aresetn]
create_bd_port -dir O servo_pwm
connect_bd_net [get_bd_ports servo_pwm] [get_bd_pins probe/servo_pwm]
assign_bd_address -offset 0x80080000 -range 0x1000 \
    -target_address_space [get_bd_addr_spaces PS_0/Data] [get_bd_addr_segs probe/S_AXI/reg0]
validate_bd_design
set ext_reset_high [get_property CONFIG.C_EXT_RESET_HIGH $rst]
set aux_reset_high [get_property CONFIG.C_AUX_RESET_HIGH $rst]
if {$ext_reset_high != 0 || $aux_reset_high != 0} {
    error "Reset polarity changed: external=$ext_reset_high auxiliary=$aux_reset_high"
}
save_bd_design
set fd [open [file join $out platform.txt] w]
puts $fd "PART=$part BOARD=$boards CLOCK_HZ=$actual_hz BASE=0x80080000 RANGE=0x1000"
puts $fd "EXT_RESET_ACTIVE_HIGH=$ext_reset_high AUX_RESET_ACTIVE_HIGH=$aux_reset_high AUX_RESET_LEVEL=1 DEBUG_RESET_LEVEL=0"
foreach p {probe/s_axi_aclk probe/s_axi_aresetn probe/servo_pwm} {
    puts $fd "$p NET=[get_bd_nets -of_objects [get_bd_pins $p]]"
}
close $fd
set bd [get_files */pwm_bench.bd]
generate_target all $bd
make_wrapper -files $bd -top
add_files -norecurse [file join $out project pwm_bench.gen sources_1 bd pwm_bench hdl pwm_bench_wrapper.v]
set_property top pwm_bench_wrapper [current_fileset]
add_files -fileset constrs_1 -norecurse [file join $root constraints j2.xdc]
update_compile_order -fileset sources_1
set_property STEPS.WRITE_BITSTREAM.ARGS.BIN_FILE true [get_runs impl_1]
launch_runs synth_1 -jobs 4
wait_on_run synth_1
if {[get_property PROGRESS [get_runs synth_1]] ne "100%"} {error "Synthesis did not complete"}
launch_runs impl_1 -to_step write_bitstream -jobs 4
wait_on_run impl_1
if {[get_property PROGRESS [get_runs impl_1]] ne "100%"} {error "Implementation did not complete"}
open_run impl_1
report_timing_summary -file [file join $out timing.rpt] -report_unconstrained
report_utilization -file [file join $out utilization.rpt]
report_drc -file [file join $out drc.rpt]
report_io -file [file join $out io.rpt]
report_timing -delay_type max -to [get_ports servo_pwm] -max_paths 1 \
    -file [file join $out output_timing.rpt]
set output_path [get_timing_paths -delay_type max -to [get_ports servo_pwm] -max_paths 1]
if {[llength $output_path] != 1} {error "Missing PWM output timing path"}
set output_requirement [get_property REQUIREMENT $output_path]
set output_slack [get_property SLACK $output_path]
if {abs($output_requirement - 20.000) > 0.001 || $output_slack < 0 || $output_slack > 20.000} {
    error "PWM output path is not constrained to 20 ns: requirement=$output_requirement slack=$output_slack"
}
if {[get_property PACKAGE_PIN [get_ports servo_pwm]] ne "H12" ||
    [get_property IOSTANDARD [get_ports servo_pwm]] ne "LVCMOS33"} {
    error "PWM output pin or voltage standard changed"
}
set setup [get_timing_paths -delay_type max -max_paths 1]
set hold [get_timing_paths -delay_type min -max_paths 1]
if {[llength $setup] != 1 || [llength $hold] != 1} {error "Missing timing paths"}
set wns [get_property SLACK $setup]
set whs [get_property SLACK $hold]
if {$wns < 0 || $whs < 0} {error "Timing failed WNS=$wns WHS=$whs"}
set errors [get_drc_violations -quiet -filter {SEVERITY == Error}]
if {[llength $errors]} {error "DRC errors: $errors"}
set artifacts [file join $out artifacts]
file mkdir $artifacts
foreach ext {bit bin} {
    file copy [file join $out project pwm_bench.runs impl_1 pwm_bench_wrapper.$ext] \
        [file join $artifacts aura_pwm_probe.$ext]
}
write_hw_platform -fixed -include_bit -force -file [file join $artifacts aura_pwm_probe.xsa]
set fd [open [file join $out build_result.json] w]
puts $fd "{\"configured_clock_hz\":$actual_hz,\"wns_ns\":$wns,\"whs_ns\":$whs,\"output_budget_ns\":$output_requirement,\"output_slack_ns\":$output_slack,\"drc_errors\":[llength $errors],\"external_reset_active_high\":$ext_reset_high,\"auxiliary_reset_active_high\":$aux_reset_high,\"board_verified\":false,\"includes_dpu\":false}"
close $fd
puts "AURA_PWM_OFFLINE_BUILD_PASS"
exit
