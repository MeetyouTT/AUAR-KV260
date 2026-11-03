# Read-only checks supplement report_timing_summary: bus skew, actual pad
# properties and the MMCM primitive parameters from the implemented netlist.
report_bus_skew -delay_type min_max -max_paths 1 -warn_on_violation -file [file join $out joint_bus_skew.rpt]
report_io -file [file join $out joint_io.rpt]
set properties [open [file join $out joint_binding_properties.tsv] w]
set pad [get_ports lrclk_tx]
foreach {property expected} {PACKAGE_PIN E10 IOSTANDARD LVCMOS33 DRIVE 8 SLEW SLOW DIRECTION OUT} {
    set actual [get_property $property $pad]
    puts $properties "PAD\t$property\t$actual\t$expected"
    if {$actual ne $expected} {close $properties;error "PWM pad property mismatch: $property=$actual"}
}
set mmcm [get_cells -quiet kv260_ispMipiRx_vcu_DP_i/clk_wiz_0/inst/mmcme4_adv_inst]
if {[llength $mmcm]!=1} {close $properties;error "Missing reference clock primitive"}
foreach {property expected} {CLKIN1_PERIOD 10.000 CLKFBOUT_MULT_F 12.000 DIVCLK_DIVIDE 1 CLKOUT0_DIVIDE_F 6.000 CLKOUT1_DIVIDE 12 CLKOUT2_DIVIDE 4 CLKOUT3_DIVIDE 24 CLKOUT4_DIVIDE 2} {
    set actual [get_property $property $mmcm]
    puts $properties "MMCM\t$property\t$actual\t$expected"
    if {![string is double -strict $actual] || abs(double($actual)-double($expected))>0.000001} {
        close $properties;error "Reference clock hardware changed: $property=$actual"
    }
}
set pad_driver [get_pins -leaf -of_objects [get_nets -of_objects $pad] -filter {DIRECTION == OUT}]
if {[llength $pad_driver]!=1} {close $properties;error "PWM pad driver is not unique"}
set pad_buffer [get_cells -of_objects $pad_driver]
if {[get_property REF_NAME $pad_buffer] ne "OBUF"} {close $properties;error "PWM output buffer missing"}
set pad_input [get_pins [get_property NAME $pad_buffer]/I]
set source_driver [get_pins -leaf -of_objects [get_nets -segments -of_objects $pad_input] -filter {DIRECTION == OUT}]
puts $properties "PWM_DRIVER\t$source_driver"
if {[llength $source_driver]!=1 || ![string match kv260_ispMipiRx_vcu_DP_i/aura_m3_regs_0/* $source_driver]} {
    close $properties;error "PWM pad is not driven by the motion leaf: $source_driver"
}
close $properties
puts "AURA_SIGNOFF_PROPERTIES_VERIFIED"
