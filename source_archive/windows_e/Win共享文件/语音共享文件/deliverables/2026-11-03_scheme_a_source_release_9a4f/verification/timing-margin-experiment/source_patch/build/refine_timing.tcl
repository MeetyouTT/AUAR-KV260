# Refine a freshly generated, routed AUAR checkpoint while retaining its original timing budget.
proc margin_metrics {} {
    set setup [get_timing_paths -delay_type max -max_paths 1]
    set hold [get_timing_paths -delay_type min -max_paths 1]
    if {![llength $setup] || ![llength $hold]} {
        error "Setup or hold paths are missing"
    }
    return [dict create wns [get_property SLACK $setup] whs [get_property SLACK $hold]]
}

proc margin_clocks {} {
    set snapshot [dict create]
    foreach clk [get_clocks *] {
        dict set snapshot [get_property NAME $clk] [list \
            [get_property PERIOD $clk] [get_property WAVEFORM $clk]]
    }
    return $snapshot
}

proc margin_uncertainty {setup hold} {
    set clocks [get_clocks *]
    if {![llength $clocks]} {
        error "No clocks found"
    }
    set_clock_uncertainty -setup -from $clocks -to $clocks $setup
    set_clock_uncertainty -hold -from $clocks -to $clocks $hold
}

proc margin_save_metrics {file metrics} {
    set stream [open "$file.tmp" w]
    puts $stream [format {{"wns_ns":%.6f,"whs_ns":%.6f}} \
        [dict get $metrics wns] [dict get $metrics whs]]
    close $stream
    file rename -force "$file.tmp" $file
}

proc margin_route_counts {report_file} {
    set stream [open $report_file r]
    set contents [read $stream]
    close $stream
    set values [dict create]
    foreach {key label} {
        routable {routable nets}
        routed {fully routed nets}
        errors {nets with routing errors}
    } {
        set pattern [format {# of %s[^:]*:[ ]*([0-9,]+)} $label]
        if {![regexp $pattern $contents -> count]} {
            error "Route status field missing: $label"
        }
        dict set values $key [string map {, {}} $count]
    }
    return $values
}

proc auar_refine_margin {} {
    if {[llength $::argv] % 2} {
        error "Arguments must be key/value pairs"
    }
    set options [dict create]
    foreach {key value} $::argv {
        if {$key ni {--root --checkpoint --out --rtl-results --setup-min-ns --hold-min-ns}} {
            error "Unknown argument $key"
        }
        dict set options $key $value
    }
    foreach key {--root --checkpoint --out --rtl-results --setup-min-ns --hold-min-ns} {
        if {![dict exists $options $key]} {
            error "Missing argument $key"
        }
    }
    set root [file normalize [dict get $options --root]]
    set out [file normalize [dict get $options --out]]
    set checkpoint [file normalize [dict get $options --checkpoint]]
    set setup_min [dict get $options --setup-min-ns]
    set hold_min [dict get $options --hold-min-ns]
    foreach value [list $setup_min $hold_min] {
        if {![string is double -strict $value] || $value < 0} {
            error "Margins must be nonnegative numbers in ns"
        }
    }
    if {$out eq $root || [string first "$root/" "$out/"] == 0 || [file exists $out]} {
        error "Choose a fresh output directory outside the package"
    }
    if {![string match "2022.2*" [version -short]]} {
        error "Vivado 2022.2 is required"
    }
    if {[catch {
        exec python3 -B [file join $root build rtl_results.py] verify \
            --root $root --result [dict get $options --rtl-results] 2>@1
    } message]} {
        error "RTL gate refused: $message"
    }
    puts $message
    file mkdir [file join $out reports]

    open_checkpoint $checkpoint
    set_param general.maxThreads 8
    if {[get_property PART [current_design]] ne "xck26-sfvc784-2LV-c"} {
        error "Checkpoint targets a different device"
    }
    set pad [get_ports servo_pwm]
    foreach {property expected} {PACKAGE_PIN E10 IOSTANDARD LVCMOS33 DRIVE 8 SLEW SLOW DIRECTION OUT} {
        if {[get_property $property $pad] ne $expected} {
            error "PWM pad mismatch: $property"
        }
    }

    set original_clocks [margin_clocks]
    set reports [file join $out reports]
    write_xdc -type timing [file join $reports original_timing.xdc]
    set stream [open [file join $reports original_timing.xdc] r]
    set original_constraints [read $stream]
    close $stream
    if {[regexp -line {^[ \t]*set_clock_uncertainty[ \t]} $original_constraints]} {
        error "Existing user clock uncertainty must be preserved explicitly"
    }

    set baseline [margin_metrics]
    margin_save_metrics [file join $reports baseline.json] $baseline
    margin_uncertainty 0.0 0.0
    set zeroed [margin_metrics]
    foreach key {wns whs} {
        if {abs([dict get $baseline $key] - [dict get $zeroed $key]) > 0.0011} {
            error "Zero user uncertainty changed the baseline timing budget"
        }
    }

    # Guard bands guide the optimizer. Final acceptance uses the original timing budget.
    set setup_guard [expr {$setup_min + 0.005}]
    set hold_guard [expr {$hold_min + 0.005}]
    margin_uncertainty $setup_guard $hold_guard
    set guarded [margin_metrics]
    if {abs([dict get $guarded wns] - ([dict get $baseline wns] - $setup_guard)) > 0.0011 ||
        abs([dict get $guarded whs] - ([dict get $baseline whs] - $hold_guard)) > 0.0011} {
        error "Guard bands did not tighten all setup and hold timing as expected"
    }
    margin_save_metrics [file join $reports guarded_start.json] $guarded
    write_xdc -type timing [file join $reports optimization_timing.xdc]

    # Small hold deficits are handled by timing-driven route detours. Inserting
    # many LUT1 buffers here can unnecessarily damage setup-critical paths.
    phys_opt_design -directive Explore
    margin_save_metrics [file join $reports critical_optimized.json] [margin_metrics]
    phys_opt_design -clock_opt
    margin_save_metrics [file join $reports clock_optimized.json] [margin_metrics]
    route_design -directive NoTimingRelaxation
    set first_route [margin_metrics]
    margin_save_metrics [file join $reports first_route.json] $first_route
    if {[dict get $first_route wns] < $setup_min - $setup_guard ||
        [dict get $first_route whs] < $hold_min - $hold_guard} {
        phys_opt_design -directive Explore
        route_design -directive AggressiveExplore
    }
    set guarded_final [margin_metrics]
    margin_save_metrics [file join $reports guarded_final.json] $guarded_final

    margin_uncertainty 0.0 0.0
    set current_clocks [margin_clocks]
    dict for {name definition} $original_clocks {
        if {![dict exists $current_clocks $name] ||
            [dict get $current_clocks $name] ne $definition} {
            error "Clock frequency or waveform changed: $name"
        }
    }
    write_xdc -type timing [file join $reports final_timing.xdc]
    report_timing_summary -delay_type min_max -report_unconstrained -max_paths 10 \
        -file [file join $reports timing.rpt]
    report_utilization -file [file join $reports utilization.rpt]
    report_route_status -file [file join $reports route.rpt]
    report_drc -file [file join $reports drc.rpt]
    report_clocks -file [file join $reports clocks.rpt]
    report_io -file [file join $reports io.rpt]
    report_bus_skew -file [file join $reports bus_skew.rpt]
    report_timing -to $pad -max_paths 3 -file [file join $reports pwm_timing.rpt]
    check_timing -verbose -file [file join $reports check_timing.rpt]
    set final [margin_metrics]
    set route [margin_route_counts [file join $reports route.rpt]]
    set errors [get_drc_violations -quiet -filter {SEVERITY == Error}]
    set stream [open [file join $reports implementation.json] w]
    puts $stream [format \
        {{"wns_ns":%.6f,"whs_ns":%.6f,"setup_min_ns":%.6f,"hold_min_ns":%.6f,"setup_guard_ns":%.6f,"hold_guard_ns":%.6f,"drc_errors":%d,"routable_nets":%d,"routed_nets":%d,"routing_errors":%d,"original_clock_periods_preserved":true,"original_user_uncertainty_restored":true,"historical_checkpoint_used":false,"checkpoint_origin":"same_run_source_implementation","board_verified":false}} \
        [dict get $final wns] [dict get $final whs] $setup_min $hold_min \
        $setup_guard $hold_guard [llength $errors] \
        [dict get $route routable] [dict get $route routed] [dict get $route errors]]
    close $stream
    write_checkpoint [file join $out margin_candidate.dcp]
    if {[dict get $final wns] < $setup_min || [dict get $final whs] < $hold_min ||
        [llength $errors] || [dict get $route errors] != 0 ||
        [dict get $route routable] < 1 ||
        [dict get $route routed] != [dict get $route routable]} {
        error "Refined design has not reached the requested setup/hold margins or DRC/routing conditions"
    }

    close_design
    open_checkpoint [file join $out margin_candidate.dcp]
    set_param general.maxThreads 8
    write_bitstream -bin_file [file join $out auar_source.bit]
    write_hw_platform -fixed -include_bit [file join $out auar_source.xsa]
    validate_hw_platform -verbose [file join $out auar_source.xsa]
    close_design
    puts "AUAR_MARGIN_PASS"
}

if {[catch {auar_refine_margin} message options]} {
    puts stderr "AUAR_MARGIN_FAILED: $message"
    if {[dict exists $options -errorinfo]} {
        puts stderr [dict get $options -errorinfo]
    }
    exit 1
}
exit 0

