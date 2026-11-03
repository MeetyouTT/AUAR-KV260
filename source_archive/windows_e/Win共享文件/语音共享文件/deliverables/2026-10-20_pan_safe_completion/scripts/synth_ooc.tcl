# Offline synthesis only. No hardware manager, device programming or board I/O.
set candidate [file normalize $::env(AURA_PAN_SAFE_CANDIDATE)]
set out [file normalize $::env(AURA_PAN_SAFE_SYNTH_OUT)]
set_param general.maxThreads 4
if {[catch {
    create_project -in_memory -part xck26-sfvc784-2LV-c
    read_verilog -sv [file join $candidate rtl visual_servo.sv]
    synth_design -top aura_m3_regs -mode out_of_context -part xck26-sfvc784-2LV-c
    create_clock -name axi_clock -period 10.0 [get_ports s_axi_aclk]
    report_utilization -file [file join $out utilization.rpt]
    report_timing_summary -delay_type min_max -file [file join $out timing_estimate.rpt]
    report_drc -file [file join $out drc.rpt]
    write_checkpoint [file join $out vsrv2_ooc.dcp]
    puts "AURA_VSRV2_OOC_SYNTH_PASS_NOT_JOINT_IMPLEMENTATION"
} result opts]} {
    puts stderr $result
    puts stderr [dict get $opts -errorinfo]
    exit 1
}
exit 0
