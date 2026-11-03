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
    route_design -unroute
    opt_design
    place_design -directive Explore
    phys_opt_design -directive AggressiveExplore
    route_design -directive AggressiveExplore
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
