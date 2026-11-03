# Capacity experiment only. Preserves source DCP, no application deployment.
set root $::env(AURA_ADAPT_ROOT)
set out $::env(AURA_ADAPT_OUT)
set part xck26-sfvc784-2LV-c
set_param general.maxThreads 4
if {[catch {
    set cell kv260_ispMipiRx_vcu_DP_i/aura_m3_regs_0
    if {[info exists ::env(AURA_ADAPT_RESUME)]} {
        open_checkpoint $::env(AURA_ADAPT_RESUME)
    } else {
    create_project -in_memory -part $part
    read_verilog -sv [file join $root fpga rtl motion_fit.sv]
    synth_design -top aura_m3_regs -mode out_of_context -part $part
    report_utilization -file [file join $out motion_ooc_utilization.rpt]
    write_checkpoint -force [file join $out motion_ooc.dcp]
    close_project
    open_checkpoint /home/ghmd/kv260-m3-axilite-20261002/src/kv260/overlays/examples/benchmark/binary_container_1/link/vivado/vpl/prj/prj.runs/impl_1/kv260_ispMipiRx_vcu_DP_wrapper_routed.dcp
    # Replace the AXI register leaf, leaving the proven DPU datapath intact.
    update_design -cell $cell -black_box
    # Routed physical optimization adds reset-replica alias input pins. Their
    # original consumers were removed with the leaf; they are not RTL ports.
    foreach pin [get_pins -of_objects [get_cells $cell]] {
        set leaf [string range [get_property NAME $pin] [expr {[string length $cell]+1}] end]
        if {![string match s_axi_* $leaf]} {
            puts "AURA_REMOVE_PHYSOPT_ALIAS=$leaf"
            set net [get_nets -quiet -of_objects $pin]
            if {[llength $net]} {disconnect_net -net $net -objects $pin}
            remove_pin $pin
        }
    }
    create_pin -direction OUT $cell/servo_pwm
    read_checkpoint -cell $cell [file join $out motion_ooc.dcp]
    write_checkpoint -force [file join $out joint_spliced.dcp]
    }
    # J2.3/E10 is an I2S TX clock pad in the legacy reference. The AURA plan
    # uses USB audio. Reuse its existing OBUF/pad, disconnecting the I2S driver.
    # The legacy top-level label remains lrclk_tx in this capacity experiment;
    # the regenerated release BD must export it explicitly as servo_pwm.
    if {![info exists ::env(AURA_ADAPT_BOUND)]} {
    set pad [get_ports lrclk_tx]
    if {[get_property PACKAGE_PIN $pad] ne "E10"} {error "Unexpected legacy audio pad mapping"}
    set pad_net [get_nets -of_objects $pad]
    set pad_driver [get_pins -leaf -of_objects $pad_net -filter {DIRECTION == OUT}]
    if {[llength $pad_driver] != 1} {error "Expected one pad driver"}
    set obuf [get_cells -of_objects $pad_driver]
    if {[get_property REF_NAME $obuf] ne "OBUF"} {error "Unexpected pad buffer"}
    set obuf_input [get_pins [get_property NAME $obuf]/I]
    set old_audio_net [get_nets -of_objects $obuf_input]
    set binding [open [file join $out io_binding.txt] w]
    puts $binding "PHYSICAL=J2.3/E10 LEGACY_PORT=lrclk_tx NEW_ROLE=servo_pwm"
    puts $binding "RETIRED_DRIVER_NET=$old_audio_net"
    puts $binding "OBUF=$obuf"
    close $binding
    disconnect_net -net $old_audio_net -objects $obuf_input
    create_net aura_servo_net
    connect_net -hier -net aura_servo_net -objects [list [get_pins $cell/servo_pwm] $obuf_input]
    set_property IOSTANDARD LVCMOS33 $pad
    set_property DRIVE 8 $pad
    set_property SLEW SLOW $pad
    # Servo receiver is asynchronous; this is an engineering max-delay budget,
    # not a invented synchronous capture clock or a blanket false-path.
    set pwm_registers [get_cells -hier -filter "NAME =~ $cell/* && IS_SEQUENTIAL"]
    if {![llength $pwm_registers]} {error "No motion launch registers"}
    set_max_delay 100.0 -datapath_only -from $pwm_registers -to $pad
    write_checkpoint -force [file join $out joint_unplaced.dcp]
    }
    # The old routed cache contains removed leaf-net routing. Vivado 2022.2
    # crashes in opt_design Sweep when it cleans those stale special nodes.
    # Clear physical routing before netlist optimization; then implement anew.
    if {![info exists ::env(AURA_ADAPT_UNROUTED)]} {
        route_design -unroute
        write_checkpoint -force [file join $out joint_unrouted.dcp]
    }
    if {[info exists ::env(AURA_ADAPT_USB_AUDIO)] && ![info exists ::env(AURA_ADAPT_STAGE)]} {
        set audio_cell kv260_ispMipiRx_vcu_DP_i/audio_ss_0
        source [file join $root fpga audio_ports.tcl]
        # Trace the previously failing crossbar input before replacement.
        set debug_pins [get_pins -hier -regexp {.*m_ready_d\[1\]_i_5/I1}]
        foreach debug_pin $debug_pins {
            puts "AURA_CTRL_ORIGINAL_PIN=$debug_pin NET=[get_nets -of_objects $debug_pin] DRIVERS=[get_pins -leaf -of_objects [get_nets -segments -of_objects $debug_pin] -filter {DIRECTION == OUT}]"
        }
        if {[info exists ::env(AURA_ADAPT_AUDIO_STUB)]} {
            set audio_stub $::env(AURA_ADAPT_AUDIO_STUB)
        } else {
        source [file join $root scripts map_audio_aliases.tcl]
        exec python3 [file join $root scripts prepare_audio_stub.py] --alias-map [file join $out audio_alias_map.tsv] --output [file join $out disabled_audio.sv]
        write_checkpoint -force [file join $out audio_prior.dcp]
        close_project
        create_project -in_memory -part $part
        read_verilog -sv [file join $out disabled_audio.sv]
        synth_design -top aura_disabled_audio -mode out_of_context -part $part
        report_utilization -file [file join $out audio_stub_utilization.rpt]
        write_checkpoint -force [file join $out audio_stub.dcp]
        close_project
        open_checkpoint [file join $out audio_prior.dcp]
        set audio_stub [file join $out audio_stub.dcp]
        }
        update_design -cell $audio_cell -black_box
        foreach pin [get_pins -of_objects [get_cells $audio_cell]] {
            set leaf [string range [get_property NAME $pin] [expr {[string length $audio_cell]+1}] end]
            regsub {\[[0-9]+\]$} $leaf {} base
            if {[lsearch -exact $audio_port_names $base]<0 && [get_property DIRECTION $pin] eq "IN"} {
                puts "AURA_REMOVE_AUDIO_ALIAS=$leaf"
                set net [get_nets -quiet -of_objects $pin]
                if {[llength $net]} {disconnect_net -net $net -objects $pin}
                remove_pin $pin
            }
        }
        read_checkpoint -cell $audio_cell $audio_stub
        write_checkpoint -force [file join $out joint_imported.dcp]
    }
    if {[info exists ::env(AURA_ADAPT_USB_AUDIO)] && (![info exists ::env(AURA_ADAPT_STAGE)] || $::env(AURA_ADAPT_STAGE) eq "imported")} {
        set audio_cell kv260_ispMipiRx_vcu_DP_i/audio_ss_0
        # Routed phys_opt uses reset-replica inputs instead of the original
        # ARESETN port. Rebind the replacement to the proven 100 MHz control
        # domain. Generated source BD connects audio ACLK/ARESETN and M3
        # s_axi_aclk/s_axi_aresetn to these same two nets.
        foreach {audio_port motion_port} {ACLK s_axi_aclk ARESETN s_axi_aresetn} {
            set pin [get_pins $audio_cell/$audio_port]
            set old_net [get_nets -quiet -of_objects $pin]
            if {[llength $old_net]} {disconnect_net -net $old_net -objects $pin}
            set control_net [get_nets -of_objects [get_pins $cell/$motion_port]]
            if {[llength $control_net]!=1} {error "Missing control-domain $motion_port"}
            set source_drivers [get_pins -leaf -of_objects [get_nets -segments -of_objects [get_pins $cell/$motion_port]] -filter {DIRECTION == OUT}]
            if {[llength $source_drivers]!=1} {error "Unproven control-domain driver: $motion_port $source_drivers"}
            connect_net -hier -net $control_net -objects $pin
            puts "AURA_AUDIO_REBIND=$audio_port SOURCE=$motion_port NET=$control_net DRIVER=$source_drivers"
        }
        set motion_clocks [get_clocks -of_objects [get_pins $cell/s_axi_aclk]]
        set audio_clocks [get_clocks -of_objects [get_pins $audio_cell/ACLK]]
        if {![llength $audio_clocks] || $audio_clocks ne $motion_clocks} {error "Audio stub clock domain mismatch"}
        puts "AURA_AUDIO_CONTROL_CLOCK=$audio_clocks"
        set debug_pins [get_pins -hier -regexp {.*m_ready_d\[1\]_i_5/I1}]
        foreach debug_pin $debug_pins {
            set drivers [get_pins -leaf -of_objects [get_nets -segments -of_objects $debug_pin] -filter {DIRECTION == OUT}]
            puts "AURA_CTRL_REPLACED_PIN=$debug_pin NET=[get_nets -of_objects $debug_pin] DRIVERS=$drivers"
            if {![llength $drivers]} {error "Crossbar input lost its driver before optimization"}
        }
        puts "AURA_USB_AUDIO_PROFILE_ENABLED_VCU_BUS_PRESERVED"
        write_checkpoint -force [file join $out joint_trimmed.dcp]
    }
    set stage trimmed
    if {[info exists ::env(AURA_ADAPT_STAGE)]} {set stage $::env(AURA_ADAPT_STAGE)}
    if {$stage eq "imported"} {set stage trimmed}
    if {$stage eq "trimmed"} {opt_design}
    report_utilization -file [file join $out preplace_utilization.rpt]
    if {$stage eq "trimmed"} {write_checkpoint -force [file join $out joint_optimized.dcp]}
    if {$stage eq "trimmed" || $stage eq "optimized"} {
    if {[info exists ::env(AURA_ADAPT_INCREMENTAL)]} {
        read_checkpoint -incremental /home/ghmd/kv260-m3-axilite-20261002/src/kv260/overlays/examples/benchmark/binary_container_1/link/vivado/vpl/prj/prj.runs/impl_1/kv260_ispMipiRx_vcu_DP_wrapper_routed.dcp
        report_incremental_reuse -file [file join $out incremental_reuse.rpt]
        write_checkpoint -force [file join $out joint_incremental.dcp]
    }
    place_design -directive Explore
    phys_opt_design -directive AggressiveExplore
    write_checkpoint -force [file join $out joint_placed.dcp]
    }
    if {$stage ne "routed"} {
    route_design -directive AggressiveExplore
    write_checkpoint -force [file join $out joint_preroute_physopt.dcp]
    }
    phys_opt_design -directive AggressiveExplore
    report_utilization -file [file join $out joint_utilization.rpt]
    report_utilization -cells [get_cells $cell] -file [file join $out motion_joint_utilization.rpt]
    report_timing_summary -delay_type min_max -report_unconstrained -max_paths 10 -file [file join $out joint_timing.rpt]
    report_route_status -file [file join $out joint_route.rpt]
    report_drc -file [file join $out joint_drc.rpt]
    check_timing -verbose -file [file join $out joint_check_timing.rpt]
    report_clocks -file [file join $out joint_clocks.rpt]
    report_timing -to [get_ports lrclk_tx] -max_paths 3 -file [file join $out pwm_pad_timing.rpt]
    write_checkpoint -force [file join $out joint_routed.dcp]
    puts "AURA_ADAPT_JOINT_ROUTED"
} result opts]} {
    puts stderr "AURA_ADAPT_ERROR=$result"
    puts stderr [dict get $opts -errorinfo]
    exit 1
}
exit 0
