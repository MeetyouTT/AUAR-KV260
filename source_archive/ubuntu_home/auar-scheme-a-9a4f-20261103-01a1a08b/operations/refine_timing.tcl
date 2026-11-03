# Additional timing-closure flow, only for a verified cold run that failed its final timing gate.
set here [file dirname [file normalize [info script]]]
proc slack_pair {} {
    set setup [get_timing_paths -delay_type max -max_paths 1]
    set hold [get_timing_paths -delay_type min -max_paths 1]
    if {[llength $setup] != 1 || [llength $hold] != 1} {error "Missing timing path"}
    return [list [get_property SLACK $setup] [get_property SLACK $hold]]
}
proc closed {pair} {
    lassign $pair setup hold
    return [expr {$setup >= 0.0 && $hold >= 0.0}]
}
proc log_pair {label} {
    set pair [slack_pair]
    puts "AUAR_TIMING $label $pair"
    return $pair
}
proc reload_best {file} {
    close_design
    open_checkpoint $file
}
proc try_post_route {out label} {
    set best_file [file join $out $label.best_routed.dcp]
    set best [log_pair $label.initial]
    write_checkpoint -force $best_file
    if {[closed $best]} {return 1}
    foreach {name options} {
        aggressive {-directive AggressiveExplore}
        pin_placement {-critical_pin_opt -placement_opt -routing_opt}
        skew {-clock_opt}
        hold {-hold_fix}
    } {
        if {$name eq "hold" && [lindex $best 1] >= 0.0} {continue}
        if {[catch {phys_opt_design {*}$options} why]} {
            puts "AUAR_OPTION_SKIPPED $name $why"
            reload_best $best_file
            continue
        }
        set current [log_pair $label.$name]
        if {[closed $current]} {
            write_checkpoint -force $best_file
            return 1
        }
        set bestworst [expr {min([lindex $best 0],[lindex $best 1])}]
        set nowworst [expr {min([lindex $current 0],[lindex $current 1])}]
        if {$nowworst > $bestworst || ($nowworst == $bestworst && [lindex $current 0]+[lindex $current 1] > [lindex $best 0]+[lindex $best 1])} {
            set best $current
            write_checkpoint -force $best_file
        } else {
            reload_best $best_file
        }
    }
    return 0
}
proc finish {out} {
    set reports [file join $out reports]
    set pad [get_ports servo_pwm]
    foreach {prop expected} {PACKAGE_PIN E10 IOSTANDARD LVCMOS33 DRIVE 8 SLEW SLOW DIRECTION OUT} {
        if {[get_property $prop $pad] ne $expected} {error "PWM pin changed: $prop"}
    }
    report_timing_summary -delay_type min_max -report_unconstrained -max_paths 10 -file [file join $reports timing.rpt]
    report_utilization -file [file join $reports utilization.rpt]
    report_route_status -file [file join $reports route.rpt]
    report_drc -file [file join $reports drc.rpt]
    report_clocks -file [file join $reports clocks.rpt]
    report_bus_skew -file [file join $reports bus_skew.rpt]
    report_io -file [file join $reports io.rpt]
    report_timing -to $pad -max_paths 3 -file [file join $reports pwm_timing.rpt]
    check_timing -verbose -file [file join $reports check_timing.rpt]
    set fh [open [file join $reports route.rpt] r]
    set route [read $fh]
    close $fh
    foreach {pattern key} {{# of routable nets[^:]*:[ ]*([0-9]+)} nets {# of fully routed nets[^:]*:[ ]*([0-9]+)} done {# of nets with routing errors[^:]*:[ ]*([0-9]+)} err} {
        if {![regexp $pattern $route -> $key]} {error "Missing routing count $key"}
    }
    lassign [slack_pair] wns whs
    set drc [llength [get_drc_violations -quiet -filter {SEVERITY == Error}]]
    set fh [open [file join $reports implementation.json] w]
    puts $fh "{\"wns_ns\":$wns,\"whs_ns\":$whs,\"drc_errors\":$drc,\"old_checkpoint_used\":false,\"board_verified\":false}"
    close $fh
    if {$nets < 1 || $nets != $done || $err != 0 || $wns < 0 || $whs < 0 || $drc != 0} {error "Implementation timing/route/DRC failed"}
    set final [file join $out auar_source_routed.dcp]
    write_checkpoint $final
    reload_best $final
    write_bitstream -bin_file [file join $out auar_source.bit]
    write_hw_platform -fixed -include_bit [file join $out auar_source.xsa]
    validate_hw_platform -verbose [file join $out auar_source.xsa]
    close_design
    puts "AUAR_REFINE_PASS"
}
proc run_refinement {args} {
    lassign $args prior out
    if {[llength $args] != 2 || [file exists $out]} {error "Use the verified Python entry point and a new hardware output"}
    if {![string match "2022.2*" [version -short]]} {error "Vivado 2022.2 required"}
    set_param general.maxThreads 4
    file mkdir [file join $out reports]
    open_checkpoint [file join $prior source_placed.dcp]
    route_design -directive AdvancedSkewModeling
    if {![try_post_route $out alternative]} {
        set current_route [file join $out alternative.best_routed.dcp]
        close_design
        open_checkpoint [file join $prior source_synth.dcp]
        opt_design
        # Use only the checkpoint generated above from this cold source build.
        read_checkpoint -incremental -directive TimingClosure $current_route
        place_design -directive Explore
        phys_opt_design -directive AggressiveExplore
        write_checkpoint [file join $out incremental.placed.dcp]
        route_design -directive NoTimingRelaxation
        try_post_route $out incremental
    }
    finish $out
}
if {[catch {run_refinement {*}$argv} reason opts]} {
    puts stderr "AUAR_REFINE_FAILED $reason"
    if {[dict exists $opts -errorinfo]} {puts stderr [dict get $opts -errorinfo]}
    exit 1
}
exit 0

