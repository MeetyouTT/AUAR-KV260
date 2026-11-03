# Offline netlist implementation; no board programming.
set root $::env(AURA_VISUAL_SERVO_ROOT)
set out $::env(AURA_VISUAL_SERVO_OUT)
set part xck26-sfvc784-2LV-c
set cell kv260_ispMipiRx_vcu_DP_i/aura_m3_regs_0
set_param general.maxThreads 4
if {[catch {
    create_project -in_memory -part $part
    read_verilog -sv [file join $out visual_servo.sv]
    synth_design -top aura_m3_regs -mode out_of_context -part $part \
        -generic BUILD_ID=$::env(AURA_VISUAL_SERVO_BUILD_ID)
    report_utilization -file [file join $out motion_ooc_utilization.rpt]
    write_checkpoint [file join $out motion_ooc.dcp]
    close_project
    open_checkpoint $::env(AURA_VISUAL_SERVO_INPUT)
    # Verified USB-audio profile already has retired I2S/DMA logic removed;
    # all unrelated DPU, VCU/display, clock and reset structure is retained.
    route_design -unroute
    update_design -cell $cell -black_box
    foreach pin [get_pins -of_objects [get_cells $cell]] {
        set leaf [string range [get_property NAME $pin] [expr {[string length $cell]+1}] end]
        if {![string match s_axi_* $leaf] && $leaf ne "servo_pwm"} {
            set net [get_nets -quiet -of_objects $pin]
            if {[llength $net]} {disconnect_net -net $net -objects $pin}
            remove_pin $pin
        }
    }
    read_checkpoint -cell $cell [file join $out motion_ooc.dcp]
    rename_port -to servo_pwm [get_ports lrclk_tx]
    set pad [get_ports servo_pwm]
    foreach {prop expected} {PACKAGE_PIN E10 IOSTANDARD LVCMOS33 DRIVE 8 SLEW SLOW DIRECTION OUT} {
        if {[get_property $prop $pad] ne $expected} {error "Unexpected PWM pad $prop"}
    }
    set registers [get_cells -hier -filter "NAME =~ $cell/* && IS_SEQUENTIAL"]
    set_max_delay 100.0 -datapath_only -from $registers -to $pad
    set buffer [get_cells -of_objects [get_pins -leaf -of_objects [get_nets -of_objects $pad] -filter {DIRECTION == OUT}]]
    set pwm_driver [get_pins -leaf -of_objects [get_nets -segments -of_objects [get_pins $buffer/I]] -filter {DIRECTION == OUT}]
    if {[llength $pwm_driver]!=1 || ![get_property IS_SEQUENTIAL [get_cells -of_objects $pwm_driver]]} {
        error "PWM pad must have a unique registered driver: $pwm_driver"
    }
    set dpu [get_cells -quiet kv260_ispMipiRx_vcu_DP_i/DPUCZDX8G_1]
    if {[llength $dpu]!=1} {error "DPU hierarchy missing"}
    set identity [open [file join $out binding.txt] w]
    puts $identity "PIN=J2.3/E10 PORT=servo_pwm DRIVER=$pwm_driver DPU=$dpu"
    puts $identity "AXI_BASE=0x80080000 RANGE=0x1000 ABI=VSRV/1"
    close $identity
    opt_design
    write_checkpoint [file join $out joint_optimized.dcp]
    read_checkpoint -incremental -directive TimingClosure $::env(AURA_VISUAL_SERVO_REFERENCE)
    report_incremental_reuse -file [file join $out incremental_reuse.rpt]
    place_design -directive Explore
    phys_opt_design -directive AggressiveExplore
    write_checkpoint [file join $out joint_placed.dcp]
    route_design -directive AggressiveExplore
    write_checkpoint [file join $out joint_preroute_physopt.dcp]
    phys_opt_design -directive AggressiveExplore
    report_timing_summary -delay_type min_max -report_unconstrained -max_paths 10 -file [file join $out timing.rpt]
    report_utilization -file [file join $out utilization.rpt]
    report_drc -file [file join $out drc.rpt]
    report_route_status -file [file join $out route.rpt]
    report_bus_skew -delay_type min_max -max_paths 1 -warn_on_violation -file [file join $out bus_skew.rpt]
    report_io -file [file join $out io.rpt]
    report_clocks -file [file join $out clocks.rpt]
    check_timing -verbose -file [file join $out check_timing.rpt]
    report_timing -to $pad -max_paths 3 -file [file join $out pwm_timing.rpt]
    write_checkpoint [file join $out joint_routed.dcp]
    set setup [get_timing_paths -delay_type max -max_paths 1]
    set hold [get_timing_paths -delay_type min -max_paths 1]
    if {[llength $setup]!=1 || [llength $hold]!=1} {error "Timing paths unavailable"}
    set wns [get_property SLACK $setup]
    set whs [get_property SLACK $hold]
    set violations [get_drc_violations -quiet -filter {SEVERITY == Error}]
    set verdict [open [file join $out implementation.json] w]
    puts $verdict "{\"wns_ns\":$wns,\"whs_ns\":$whs,\"drc_errors\":[llength $violations],\"board_verified\":false,\"metadata_verified\":false}"
    close $verdict
    if {$wns<0 || $whs<0 || [llength $violations]} {error "Joint timing/DRC failed"}
    # Retain offline binary, but never mark deployable without matching
    # hardware description, DT/XCLBIN review and independent report audit.
    write_bitstream -bin_file [file join $out visual_servo_joint.bit]
    puts "AURA_VISUAL_SERVO_JOINT_IMPLEMENTED"
} result opts]} {
    puts stderr "AURA_VISUAL_SERVO_ERROR=$result"
    puts stderr [dict get $opts -errorinfo]
    exit 1
}
exit 0
