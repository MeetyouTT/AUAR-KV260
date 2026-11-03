set root /home/ghmd/kv260-dpu41-control-20261001
set out [file join $root evidence postroute]
file mkdir $out
set dcp [file join $root src kv260 overlays examples benchmark binary_container_1 link vivado vpl prj prj.runs impl_1 kv260_ispMipiRx_vcu_DP_wrapper_routed.dcp]
open_checkpoint $dcp
set inventory [open [file join $out inventory.txt] w]
puts $inventory "PART=[get_property PART [current_design]]"
puts $inventory "PBLOCK_COUNT=[llength [get_pblocks -quiet]]"
puts $inventory "RECONFIGURABLE_CELLS=[get_cells -quiet -hierarchical -filter {HD.RECONFIGURABLE == 1}]"
close $inventory
report_drc -file [file join $out drc.rpt]
set detail [open [file join $out drc_objects.tsv] w]
puts $detail "OBJECT\tNAME\tRULE\tCHECK_ID\tSEVERITY\tDESCRIPTION\tAFFECTED_OBJECTS\tVIOLATED_OBJECTS"
foreach violation [get_drc_violations -quiet] {
    set row [list $violation]
    foreach property {NAME RULE CHECK_ID SEVERITY DESCRIPTION AFFECTED_OBJECTS VIOLATED_OBJECTS} {
        if {[lsearch -exact [list_property $violation] $property] < 0} {
            lappend row "<unavailable>"
        } else {
            set value [get_property $property $violation]
            lappend row [string map [list "\t" " " "\n" " "] $value]
        }
    }
    puts $detail [join $row "\t"]
}
close $detail
check_timing -verbose -file [file join $out check_timing.rpt]
report_timing_summary -delay_type min_max -report_unconstrained -check_timing_verbose -file [file join $out timing_summary.rpt]
report_utilization -file [file join $out utilization.rpt]
report_utilization -hierarchical -file [file join $out utilization_hierarchical.rpt]
report_route_status -file [file join $out route_status.rpt]
report_clocks -file [file join $out clocks.rpt]
report_clock_interaction -file [file join $out clock_interaction.rpt]
report_exceptions -coverage -file [file join $out exceptions_coverage.rpt]
write_xdc [file join $out routed_constraints.xdc]
puts "DPU41_ROUTED_REVIEW_COMPLETE"
