set root [file normalize [file join [file dirname [info script]] ..]]
set out [file join $root evidence postroute]
file mkdir $out
set dcp [file join $root src kv260 overlays examples benchmark binary_container_1 link vivado vpl prj prj.runs impl_1 kv260_ispMipiRx_vcu_DP_wrapper_routed.dcp]
if {![file isfile $dcp]} {error "No final routed checkpoint: $dcp"}
open_checkpoint $dcp
set inventory [open [file join $out inventory.txt] w]
puts $inventory "PART=[get_property PART [current_design]]"
puts $inventory "PBLOCK_COUNT=[llength [get_pblocks -quiet]]"
puts $inventory "RECONFIGURABLE_CELLS=[get_cells -quiet -hierarchical -filter {HD.RECONFIGURABLE == 1}]"
set m3_cells [get_cells -quiet -hierarchical -filter {NAME =~ */aura_m3_regs_0}]
puts $inventory "M3_HIERARCHY=$m3_cells"
close $inventory
set clock_detail [open [file join $out endpoint_clocks.tsv] w]
puts $clock_detail "ENDPOINT\tCELL_PIN\tCLOCK\tPERIOD_NS\tWAVEFORM"
foreach {endpoint cell_pattern port_name} {
    DPU_ACLK */DPUCZDX8G_1 aclk
    DPU_2X */DPUCZDX8G_1 ap_clk_2
    M3_ACLK */aura_m3_regs_0 s_axi_aclk
} {
    set cells [get_cells -quiet -hierarchical -filter "NAME =~ $cell_pattern"]
    if {[llength $cells] != 1} {error "Expected one cell for $endpoint: $cells"}
    set pin [get_pins -quiet "[lindex $cells 0]/$port_name"]
    if {[llength $pin] != 1} {error "Missing clock pin for $endpoint"}
    set clocks [get_clocks -quiet -of_objects $pin]
    if {[llength $clocks] != 1} {error "Expected one clock for $endpoint: $clocks"}
    set clock [lindex $clocks 0]
    puts $clock_detail [join [list $endpoint $pin $clock [get_property PERIOD $clock] \
        [get_property WAVEFORM $clock]] "\t"]
}
close $clock_detail
report_drc -file [file join $out drc.rpt]
set detail [open [file join $out drc_objects.tsv] w]
puts $detail "OBJECT\tNAME\tRULE\tCHECK_ID\tSEVERITY\tDESCRIPTION\tAFFECTED_OBJECTS\tVIOLATED_OBJECTS\tRELATED_CELLS\tRELATED_NETS\tRELATED_PORTS\tRELATED_PINS"
foreach violation [get_drc_violations -quiet] {
    set row [list $violation]
    foreach property {NAME RULE CHECK_ID SEVERITY DESCRIPTION AFFECTED_OBJECTS VIOLATED_OBJECTS} {
        if {[lsearch -exact [list_property $violation] $property] < 0} {
            lappend row "<unavailable>"
        } else {
            lappend row [string map [list "\t" " " "\n" " "] [get_property $property $violation]]
        }
    }
    foreach query {get_cells get_nets get_ports get_pins} {
        set related [$query -quiet -of_objects $violation]
        lappend row [string map [list "\t" " " "\n" " "] $related]
    }
    puts $detail [join $row "\t"]
}
close $detail
check_timing -verbose -file [file join $out check_timing.rpt]
report_timing_summary -delay_type min_max -report_unconstrained -check_timing_verbose -file [file join $out timing_summary.rpt]
report_utilization -file [file join $out utilization.rpt]
report_utilization -hierarchical -file [file join $out utilization_hierarchical.rpt]
if {[llength $m3_cells] == 1} {
    report_utilization -cells $m3_cells -file [file join $out m3_utilization.rpt]
    set placements [open [file join $out m3_placement.tsv] w]
    puts $placements "CELL\tREF_NAME\tLOC\tBEL"
    set m3_primitives [get_cells -quiet -hierarchical -filter {IS_PRIMITIVE && NAME =~ *aura_m3_regs_0/*}]
    foreach cell $m3_primitives {
        puts $placements [join [list $cell [get_property REF_NAME $cell] \
            [get_property LOC $cell] [get_property BEL $cell]] "\t"]
    }
    close $placements
}
report_route_status -file [file join $out route_status.rpt]
report_clocks -file [file join $out clocks.rpt]
report_clock_interaction -file [file join $out clock_interaction.rpt]
report_exceptions -coverage -file [file join $out exceptions_coverage.rpt]
write_xdc -force [file join $out routed_constraints.xdc]
puts "AURA_M3_ROUTED_REVIEW_COMPLETE"
exit
