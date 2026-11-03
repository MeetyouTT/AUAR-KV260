set root /home/ghmd/kv260-reference-2022.2-20260930
set out [file join $root evidence deployment_review]
set dcp [file join $root src kv260 overlays examples benchmark binary_container_1 link vivado vpl prj prj.runs impl_1 kv260_ispMipiRx_vcu_DP_wrapper_routed.dcp]

proc safe_property {object property} {
    if {[catch {get_property $property $object} value]} { return "<unavailable>" }
    return $value
}

open_checkpoint $dcp
set summary [open [file join $out routed_dcp_inventory.txt] w]
puts $summary "PART=[safe_property [current_design] PART]"
puts $summary "DESIGN=[current_design]"
set pblocks [get_pblocks -quiet]
puts $summary "PBLOCK_COUNT=[llength $pblocks]"
set index 0
foreach pblock $pblocks {
    incr index
    set name [safe_property $pblock NAME]
    set ranges [safe_property $pblock GRID_RANGES]
    set cells [get_cells -quiet -of_objects $pblock]
    set cellnames {}
    foreach cell $cells { lappend cellnames [safe_property $cell NAME] }
    puts $summary "PBLOCK_${index}_NAME=$name"
    puts $summary "PBLOCK_${index}_GRID_RANGES=$ranges"
    puts $summary "PBLOCK_${index}_CELL_COUNT=[llength $cellnames]"
    puts $summary "PBLOCK_${index}_CELLS=[join $cellnames ,]"
    puts $summary "PBLOCK_${index}_PROPERTIES=[list_property $pblock]"
    set report [file join $out "pblock_${index}_utilization.rpt"]
    if {[catch {report_utilization -pblocks $pblock -file $report} result]} {
        puts $summary "PBLOCK_${index}_UTILIZATION_ERROR=$result"
    }
}
close $summary

report_drc -file [file join $out routed_drc.rpt]
report_timing_summary -delay_type min_max -report_unconstrained -check_timing_verbose -file [file join $out routed_timing_summary.rpt]
check_timing -verbose -file [file join $out routed_check_timing.rpt]
report_utilization -hierarchical -file [file join $out routed_utilization_hierarchical.rpt]
report_utilization -file [file join $out routed_utilization.rpt]

set violation_file [open [file join $out routed_drc_objects.tsv] w]
puts $violation_file "OBJECT\tNAME\tRULE\tCHECK_ID\tSEVERITY\tDESCRIPTION\tAFFECTED_OBJECTS\tVIOLATED_OBJECTS"
if {[catch {set violations [get_drc_violations -quiet]} error]} {
    puts $violation_file "GET_DRC_VIOLATIONS_ERROR\t$error"
} else {
    foreach violation $violations {
        set row [list $violation]
        foreach property {NAME RULE CHECK_ID SEVERITY DESCRIPTION AFFECTED_OBJECTS VIOLATED_OBJECTS} {
            lappend row [safe_property $violation $property]
        }
        puts $violation_file [join $row "\t"]
    }
}
close $violation_file
puts "DEPLOYMENT_DCP_REVIEW_DONE"
