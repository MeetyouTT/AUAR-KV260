set out /home/ghmd/aura-pan-joint-20261023/implementation
set_param general.maxThreads 1
open_checkpoint /home/ghmd/aura-pan-joint-20261023/implementation/source_placed.dcp
set pad [get_ports servo_pwm]
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
write_bitstream -bin_file [file join $out visual_servo_source.bit]
write_hw_platform -fixed -include_bit [file join $out visual_servo_source_implemented.xsa]
validate_hw_platform -verbose [file join $out visual_servo_source_implemented.xsa]
puts "AURA_SOURCE_PLATFORM_IMPLEMENTED"
close_project
exit
