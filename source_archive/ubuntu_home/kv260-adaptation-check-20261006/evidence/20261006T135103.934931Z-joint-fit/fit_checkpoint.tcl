# Capacity experiment only. Preserves source DCP, no application deployment.
set root $::env(AURA_ADAPT_ROOT)
set out $::env(AURA_ADAPT_OUT)
set part xck26-sfvc784-2LV-c
set_param general.maxThreads 4
if {[catch {
    create_project -in_memory -part $part
    read_verilog -sv [file join $root fpga rtl motion_fit.sv]
    synth_design -top aura_m3_regs -mode out_of_context -part $part
    report_utilization -file [file join $out motion_ooc_utilization.rpt]
    write_checkpoint -force [file join $out motion_ooc.dcp]
    close_project
    open_checkpoint /home/ghmd/kv260-m3-axilite-20261002/src/kv260/overlays/examples/benchmark/binary_container_1/link/vivado/vpl/prj/prj.runs/impl_1/kv260_ispMipiRx_vcu_DP_wrapper_routed.dcp
    set cell kv260_ispMipiRx_vcu_DP_i/aura_m3_regs_0
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
    create_port -direction OUT servo_pwm
    create_net aura_servo_net
    create_net aura_servo_pad
    create_cell -reference OBUF aura_servo_obuf
    connect_net -net aura_servo_net -objects [list [get_pins $cell/servo_pwm] [get_pins aura_servo_obuf/I]]
    connect_net -net aura_servo_pad -objects [list [get_pins aura_servo_obuf/O] [get_ports servo_pwm]]
    set_property PACKAGE_PIN E10 [get_ports servo_pwm]
    set_property IOSTANDARD LVCMOS33 [get_ports servo_pwm]
    set_property DRIVE 8 [get_ports servo_pwm]
    set_property SLEW SLOW [get_ports servo_pwm]
    # Servo receiver is asynchronous; this is an engineering max-delay budget,
    # not a invented synchronous capture clock or a blanket false-path.
    set_max_delay 100.0 -datapath_only -to [get_ports servo_pwm]
    write_checkpoint -force [file join $out joint_unplaced.dcp]
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
    write_checkpoint -force [file join $out joint_routed.dcp]
    puts "AURA_ADAPT_JOINT_ROUTED"
} result opts]} {
    puts stderr "AURA_ADAPT_ERROR=$result"
    puts stderr [dict get $opts -errorinfo]
    exit 1
}
exit 0
