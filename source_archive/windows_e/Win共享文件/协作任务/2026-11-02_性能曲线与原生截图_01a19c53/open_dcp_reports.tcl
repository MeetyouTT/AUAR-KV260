set_param general.maxThreads 2
set out {/home/ghmd/auar-report-captures-01a19c53}
set f [open [file join $out report_gui_status.txt] w]
proc record_step {name command} {
 global f
 puts $f "START $name";flush $f
 if {[catch {uplevel #0 $command} result]} {puts $f "FAILED $name $result"} else {puts $f "OK $name"}
 flush $f
}
record_step open_existing_final_checkpoint {open_checkpoint {/home/ghmd/aura-pan-wide-20261028/implementation/source_routed.dcp}}
record_step utilization_native_view {report_utilization -name AUAR_RESOURCE_SCREENSHOT}
record_step timing_native_view {report_timing_summary -name AUAR_TIMING_SCREENSHOT}
puts $f "GUI_REPORTS_READY";close $f
