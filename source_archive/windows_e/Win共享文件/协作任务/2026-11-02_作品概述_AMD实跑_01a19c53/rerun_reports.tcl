set_param general.maxThreads 2
set out [file dirname [info script]]
set reports [file join $out vivado_reports]
set status [open [file join $reports command_status.tsv] w]
puts $status "command\tstatus\tdetail"
proc capture_report {name command} {
 global status
 puts "AUAR_REPORT_BEGIN $name"
 if {[catch {uplevel #0 $command} message]} {
  puts $status "$name\tFAILED\t[string map {\n { } \t { }} $message]"
  puts "AUAR_REPORT_FAILED $name $message"
 } else {
  puts $status "$name\tOK\t"
  puts "AUAR_REPORT_DONE $name"
 }
 flush $status
}
open_checkpoint {/home/ghmd/aura-pan-wide-20261028/implementation/source_routed.dcp}
capture_report utilization [list report_utilization -file [file join $reports utilization.rpt]]
capture_report utilization_hierarchical [list report_utilization -hierarchical -hierarchical_depth 3 -file [file join $reports utilization_hierarchical.rpt]]
capture_report timing_summary [list report_timing_summary -delay_type min_max -max_paths 10 -report_unconstrained -file [file join $reports timing_summary.rpt]]
capture_report check_timing [list check_timing -verbose -file [file join $reports check_timing.rpt]]
capture_report route_status [list report_route_status -file [file join $reports route_status.rpt]]
capture_report drc [list report_drc -file [file join $reports drc.rpt]]
capture_report clocks [list report_clocks -file [file join $reports clocks.rpt]]
capture_report io [list report_io -file [file join $reports io.rpt]]
capture_report cdc [list report_cdc -details -file [file join $reports cdc.rpt]]
set meta [open [file join $reports design_metrics.tsv] w]
puts $meta "key\tvalue"
puts $meta "tool_version\t[version -short]"
puts $meta "design\t[get_property NAME [current_design]]"
puts $meta "part\t[get_property PART [current_design]]"
foreach {key dtype} {setup_worst_slack_ns max hold_worst_slack_ns min} {
 set paths [get_timing_paths -delay_type $dtype -max_paths 1]
 if {[llength $paths]} {puts $meta "$key\t[get_property SLACK [lindex $paths 0]]"}
}
puts $meta "cell_count\t[llength [get_cells -hierarchical]]"
puts $meta "net_count\t[llength [get_nets -hierarchical]]"
puts $meta "servo_pwm_package_pin\t[get_property PACKAGE_PIN [get_ports servo_pwm]]"
puts $meta "servo_pwm_iostandard\t[get_property IOSTANDARD [get_ports servo_pwm]]"
close $meta
close $status
puts "AUAR_FRESH_REPORTS_COMPLETE"
exit
