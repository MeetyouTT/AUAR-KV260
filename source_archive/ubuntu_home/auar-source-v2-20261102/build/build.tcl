# Invoke with Vivado, not directly as a shell executable.
# vivado -mode batch -source build/build.tcl -tclargs --out NEW_DIR --stage all --vitis-root VITIS_DIR
set ::AUAR_ROOT [file dirname [file dirname [file normalize [info script]]]]
proc auar_main {} {
    set args [dict create --stage all]
    if {[llength $::argv] % 2} {error "Arguments must be key/value pairs"}
    foreach {key value} $::argv {
        if {$key ni {--out --stage --vitis-root}} {error "Unknown argument $key"}
        dict set args $key $value
    }
    foreach key {--out --vitis-root} {
        if {![dict exists $args $key]} {error "Missing required argument $key"}
    }
    set out [file normalize [dict get $args --out]]
    set vitis [file normalize [dict get $args --vitis-root]]
    set stage [dict get $args --stage]
    if {$stage ni {prepare implement all}} {error "Unknown stage $stage"}
    set root $::AUAR_ROOT
    if {$out eq $root || [string first "$root/" "$out/"] == 0} {
        error "Build output must be outside the source directory"
    }
    if {![string match "2022.2*" [version -short]]} {error "This release requires Vivado 2022.2"}
    set_param general.maxThreads 1
    file mkdir [file join $out reports]
    if {$stage in {prepare all}} {
        if {[file exists [file join $out project platform.xpr]]} {error "Refusing to overwrite an existing project"}
        source [file join $root src fpga ip ip_config.tcl]
        auar_configure_ips $root $out $vitis
        source [file join $root src fpga bd create_bd.tcl]
        set bd [get_files */kv260_ispMipiRx_vcu_DP.bd]
        add_files -fileset constrs_1 -norecurse [file join $root src fpga constraints pins.xdc]
        generate_target all $bd
        add_files -norecurse [make_wrapper -files $bd -top]
        set_property top kv260_ispMipiRx_vcu_DP_wrapper [current_fileset]
        update_compile_order -fileset sources_1
        write_bd_tcl -force [file join $out reports reconstructed_bd.tcl]
        report_ip_status -file [file join $out reports ip_status.rpt]
        close_project
        puts "AUAR_PREPARE_PASS"
    }
    if {$stage in {implement all}} {
        open_project [file join $out project platform.xpr]
        set bd [get_files */kv260_ispMipiRx_vcu_DP.bd]
        create_ip_run $bd
        launch_runs synth_1 -jobs 1
        wait_on_run synth_1
        if {[get_property PROGRESS [get_runs synth_1]] ne "100%"} {
            error "Synthesis failed: [get_property STATUS [get_runs synth_1]]"
        }
        open_run synth_1
        set pad [get_ports servo_pwm]
        foreach {prop expected} {PACKAGE_PIN E10 IOSTANDARD LVCMOS33 DRIVE 8 SLEW SLOW DIRECTION OUT} {
            if {[get_property $prop $pad] ne $expected} {error "PWM pad mismatch $prop"}
        }
        set regs [get_cells -hier -filter {NAME =~ */aura_m3_regs_0/* && IS_SEQUENTIAL}]
        if {![llength $regs]} {error "Motion registers absent from synthesis"}
        set_max_delay 100.0 -datapath_only -from $regs -to $pad
        opt_design
        # Deliberately no old/incremental read_checkpoint input.
        place_design -directive Explore
        phys_opt_design -directive AggressiveExplore
        route_design -directive AggressiveExplore
        phys_opt_design -directive AggressiveExplore
        set reports [file join $out reports]
        report_timing_summary -delay_type min_max -report_unconstrained -max_paths 10 -file [file join $reports timing.rpt]
        report_utilization -file [file join $reports utilization.rpt]
        report_route_status -file [file join $reports route.rpt]
        report_drc -file [file join $reports drc.rpt]
        report_clocks -file [file join $reports clocks.rpt]
        check_timing -verbose -file [file join $reports check_timing.rpt]
        set setup [get_timing_paths -delay_type max -max_paths 1]
        set hold [get_timing_paths -delay_type min -max_paths 1]
        if {![llength $setup] || ![llength $hold]} {error "Setup/hold paths missing"}
        set wns [get_property SLACK $setup]
        set whs [get_property SLACK $hold]
        set errors [get_drc_violations -quiet -filter {SEVERITY == Error}]
        set f [open [file join $reports implementation.json] w]
        puts $f "{\"wns_ns\":$wns,\"whs_ns\":$whs,\"drc_errors\":[llength $errors],\"old_checkpoint_used\":false,\"board_verified\":false}"
        close $f
        if {$wns < 0 || $whs < 0 || [llength $errors]} {error "Implementation timing/DRC failed"}
        set checkpoint [file join $out auar_source_routed.dcp]
        write_checkpoint $checkpoint
        close_project
        # Export from THIS run's checkpoint in non-project mode.
        open_checkpoint $checkpoint
        write_bitstream -bin_file [file join $out auar_source.bit]
        write_hw_platform -fixed -include_bit [file join $out auar_source.xsa]
        validate_hw_platform -verbose [file join $out auar_source.xsa]
        close_project
        puts "AUAR_IMPLEMENT_PASS"
    }
}
if {[catch {auar_main} why options]} {
    puts stderr "AUAR_BUILD_FAILED: $why"
    if {[dict exists $options -errorinfo]} {puts stderr [dict get $options -errorinfo]}
    exit 1
}
exit 0
