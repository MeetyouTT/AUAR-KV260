# Independently reopen the final routed candidate; never program hardware.
set out $::env(AURA_AUDIT_OUT)
set cell kv260_ispMipiRx_vcu_DP_i/aura_m3_regs_0
set_param general.maxThreads 4
if {[catch {
    open_checkpoint $::env(AURA_AUDIT_DCP)
    set f [open [file join $out properties.tsv] w]
    set pad [get_ports -quiet servo_pwm]
    if {[llength $pad]!=1 || [llength [get_ports -quiet lrclk_tx]]} {error "PWM external port mismatch"}
    foreach {prop expected} {PACKAGE_PIN E10 IOSTANDARD LVCMOS33 DRIVE 8 SLEW SLOW DIRECTION OUT} {
        set value [get_property $prop $pad]
        puts $f "PAD\t$prop\t$value\t$expected"
        if {$value ne $expected} {error "PWM pad mismatch $prop=$value"}
    }
    set driver [get_pins -leaf -of_objects [get_nets -of_objects $pad] -filter {DIRECTION == OUT}]
    if {[llength $driver]!=1} {error "Pad driver not unique"}
    set buffer [get_cells -of_objects $driver]
    if {[get_property REF_NAME $buffer] ne "OBUF"} {error "Pad buffer mismatch"}
    set source [get_pins -leaf -of_objects [get_nets -segments -of_objects [get_pins $buffer/I]] -filter {DIRECTION == OUT}]
    if {[llength $source]!=1 || $source ne "$cell/servo_pwm_reg/Q"} {error "PWM source mismatch $source"}
    set reg [get_cells -of_objects $source]
    if {[get_property REF_NAME $reg] ne "FDRE" || [get_property INIT $reg] ne "1'b0"} {error "Registered PWM init mismatch"}
    puts $f "PWM_DRIVER\t$source\t[get_property REF_NAME $reg]\t[get_property INIT $reg]"
    set clocks [get_clocks -of_objects [get_pins $reg/C]]
    set expected_clock clk_100M_kv260_ispMipiRx_vcu_DP_clk_wiz_0_0
    if {[llength $clocks]!=1 || $clocks ne $expected_clock || [get_property PERIOD $clocks]!=10.0} {error "PWM clock mismatch $clocks"}
    puts $f "PWM_CLOCK\t$clocks\t[get_property PERIOD $clocks]"
    set mmcm [get_cells -quiet kv260_ispMipiRx_vcu_DP_i/clk_wiz_0/inst/mmcme4_adv_inst]
    if {[llength $mmcm]!=1} {error "Missing MMCM"}
    foreach {prop expected} {CLKIN1_PERIOD 10.000 CLKFBOUT_MULT_F 12.000 DIVCLK_DIVIDE 1 CLKOUT0_DIVIDE_F 6.000 CLKOUT1_DIVIDE 12 CLKOUT2_DIVIDE 4 CLKOUT3_DIVIDE 24 CLKOUT4_DIVIDE 2} {
        set value [get_property $prop $mmcm]
        puts $f "MMCM\t$prop\t$value\t$expected"
        if {![string is double -strict $value] || abs(double($value)-double($expected))>0.000001} {error "MMCM mismatch $prop=$value"}
    }
    foreach hierarchy {DPUCZDX8G_1 vcu_0} {
        set h [get_cells -quiet kv260_ispMipiRx_vcu_DP_i/$hierarchy]
        if {[llength $h]!=1} {error "Platform hierarchy missing $hierarchy"}
        puts $f "PLATFORM\t$h"
    }
    close $f
    report_timing_summary -delay_type min_max -report_unconstrained -max_paths 1 -file [file join $out timing.rpt]
    report_bus_skew -delay_type min_max -max_paths 1 -warn_on_violation -file [file join $out bus_skew.rpt]
    report_route_status -file [file join $out route.rpt]
    report_drc -file [file join $out drc.rpt]
    check_timing -verbose -file [file join $out check_timing.rpt]
    report_timing -to $pad -max_paths 1 -file [file join $out pwm_timing.rpt]
    puts "AURA_VISUAL_SERVO_FINAL_PROPERTIES_VERIFIED"
} message options]} {
    puts stderr "AURA_VISUAL_SERVO_AUDIT_ERROR=$message"
    puts stderr [dict get $options -errorinfo]
    exit 1
}
exit 0
