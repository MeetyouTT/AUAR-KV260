# Read-only audit of an existing final routed checkpoint. No implementation,
# bitstream generation, hardware access, or production-file changes.
set out [file normalize /home/ghmd/aura-system-review-20261026/fpga]
file mkdir $out
set_param general.maxThreads 1
set status [open [file join $out audit_status.tsv] w]
proc audit_report {label command} {
    global status
    puts "AURA_SYSTEM_AUDIT_BEGIN $label"
    flush stdout
    if {[catch {uplevel #0 $command} message options]} {
        puts $status "$label\tFAIL\t[string map {\n { } \t { }} $message]"
        puts "AURA_SYSTEM_AUDIT_FAIL $label $message"
    } else {
        puts $status "$label\tPASS"
        puts "AURA_SYSTEM_AUDIT_DONE $label"
    }
    flush $status
}
if {[catch {
    open_checkpoint /home/ghmd/aura-pan-joint-20261023/implementation/source_routed.dcp
    puts $status "open_checkpoint\tPASS\t[get_property PART [current_design]]"
    flush $status
    audit_report timing [list report_timing_summary -delay_type min_max -report_unconstrained -max_paths 3 -file [file join $out timing.rpt]]
    audit_report route [list report_route_status -file [file join $out route.rpt]]
    audit_report hierarchy [list report_utilization -hierarchical -hierarchical_depth 3 -file [file join $out hierarchy.rpt]]
    audit_report clock_interaction [list report_clock_interaction -file [file join $out clock_interaction.rpt]]
    audit_report cdc [list report_cdc -details -file [file join $out cdc.rpt]]
    audit_report methodology [list report_methodology -file [file join $out methodology.rpt]]
    audit_report exceptions [list report_exceptions -coverage -file [file join $out exceptions.rpt]]
    audit_report control_sets [list report_control_sets -file [file join $out control_sets.rpt]]
    audit_report congestion [list report_design_analysis -congestion -file [file join $out congestion.rpt]]
    audit_report constraints [list write_xdc -force [file join $out exported_constraints.xdc]]
} message options]} {
    puts $status "fatal\tFAIL\t$message"
    puts stderr [dict get $options -errorinfo]
    close $status
    exit 1
}
close $status
exit 0
