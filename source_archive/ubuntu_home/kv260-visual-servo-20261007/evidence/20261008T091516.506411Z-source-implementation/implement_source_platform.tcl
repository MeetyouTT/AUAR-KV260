# Complete source-project implementation; reference DCP is only a placement hint.
set out [file normalize $::env(AURA_SOURCE_IMPL_OUT)]
set platform [file normalize $::env(AURA_PLATFORM_OUT)]
set_param general.maxThreads 4
open_project [file join $platform platform platform.xpr]
set bd [get_files *.bd]
puts "SOURCE_SYNTH_CHECKPOINT_MODE=[get_property synth_checkpoint_mode $bd]"
create_ip_run $bd
launch_runs synth_1 -jobs 4
wait_on_run synth_1
if {[get_property PROGRESS [get_runs synth_1]] ne "100%"} {error "Source synthesis failed: [get_property STATUS [get_runs synth_1]]"}
open_run synth_1
write_checkpoint [file join $out source_synth.dcp]
set pad [get_ports servo_pwm]
foreach {prop expected} {PACKAGE_PIN E10 IOSTANDARD LVCMOS33 DRIVE 8 SLEW SLOW DIRECTION OUT} {
    if {[get_property $prop $pad] ne $expected} {error "Unexpected source PWM pad $prop"}
}
set registers [get_cells -hier -filter {NAME =~ */aura_m3_regs_0/* && IS_SEQUENTIAL}]
if {![llength $registers]} {error "Source PWM registers not found"}
set_max_delay 100.0 -datapath_only -from $registers -to $pad
opt_design
write_checkpoint [file join $out source_optimized.dcp]
read_checkpoint -incremental -directive TimingClosure $::env(AURA_SOURCE_IMPL_REFERENCE)
report_incremental_reuse -file [file join $out incremental_reuse.rpt]
place_design -directive Explore
phys_opt_design -directive AggressiveExplore
write_checkpoint [file join $out source_placed.dcp]
route_design -directive AggressiveExplore
phys_opt_design -directive AggressiveExplore
report_timing_summary -delay_type min_max -report_unconstrained -max_paths 10 -file [file join $out timing.rpt]
report_utilization -file [file join $out utilization.rpt]
report_route_status -file [file join $out route.rpt]
report_drc -file [file join $out drc.rpt]
report_bus_skew -delay_type min_max -max_paths 1 -warn_on_violation -file [file join $out bus_skew.rpt]
report_io -file [file join $out io.rpt]
report_clocks -file [file join $out clocks.rpt]
check_timing -verbose -file [file join $out check_timing.rpt]
report_timing -to $pad -max_paths 3 -file [file join $out pwm_timing.rpt]
write_checkpoint [file join $out source_routed.dcp]
set setup [get_timing_paths -delay_type max -max_paths 1]
set hold [get_timing_paths -delay_type min -max_paths 1]
set wns [get_property SLACK $setup]
set whs [get_property SLACK $hold]
set errors [get_drc_violations -quiet -filter {SEVERITY == Error}]
set f [open [file join $out implementation.json] w]
puts $f "{\"wns_ns\":$wns,\"whs_ns\":$whs,\"drc_errors\":[llength $errors],\"board_verified\":false}"
close $f
if {$wns < 0 || $whs < 0 || [llength $errors]} {error "Source implementation timing/DRC failed"}
write_bitstream [file join $out visual_servo_source.bit]
write_hw_platform -fixed [file join $out visual_servo_source_implemented.xsa]
validate_hw_platform -verbose [file join $out visual_servo_source_implemented.xsa]
puts "AURA_SOURCE_PLATFORM_IMPLEMENTED"
close_project
exit
