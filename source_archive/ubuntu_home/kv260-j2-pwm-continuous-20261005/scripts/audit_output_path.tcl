# Offline audit of the existing routed checkpoint; never connects to hardware.
set root [file normalize [file join [file dirname [info script]] ..]]
set build [file join $root evidence 20261005T084116.883020Z-build]
set out [file normalize [lindex $argv 0]]
open_checkpoint [file join $build project pwm_bench.runs impl_1 pwm_bench_wrapper_routed.dcp]
set port [get_ports servo_pwm]
foreach {property expected} {PACKAGE_PIN H12 DIRECTION OUT IOSTANDARD LVCMOS33 DRIVE 4 SLEW SLOW} {
    set actual [get_property $property $port]
    if {$actual ne $expected} {error "$property expected $expected, got $actual"}
}
set buffer [get_cells servo_pwm_OBUF_inst]
if {[get_property REF_NAME $buffer] ne "OBUF"} {error "Output is not a plain OBUF"}
set input_net [get_nets -of_objects [get_pins servo_pwm_OBUF_inst/I]]
set drivers [get_pins -leaf -of_objects [get_nets -segments $input_net] -filter {DIRECTION == OUT}]
set expected_driver pwm_bench_i/probe/inst/burst/pwm_reg/Q
if {[llength $drivers] != 1 || [lindex $drivers 0] ne $expected_driver} {error "Unexpected output drivers: $drivers"}
set reg [get_cells pwm_bench_i/probe/inst/burst/pwm_reg]
if {[get_property REF_NAME $reg] ne "FDRE"} {error "Unexpected PWM register primitive"}
set fd [open [file join $out path.txt] w]
puts $fd "PORT=$port PIN=H12 BANK=45 IOSTANDARD=LVCMOS33 DRIVE=4mA SLEW=SLOW"
puts $fd "OUTPUT_BUFFER=[get_property REF_NAME $buffer] CELL=$buffer"
puts $fd "OUTPUT_DRIVERS=$drivers DRIVER_PRIMITIVE=[get_property REF_NAME $reg]"
puts $fd "USER_PORTS=[get_ports]"
puts $fd "TRISTATE_BUFFERS=[get_cells -quiet -hier -filter {REF_NAME =~ OBUFT* || REF_NAME =~ IOBUF*}]"
puts $fd "STARTUP_PRIMITIVES=[get_cells -quiet -hier -filter {REF_NAME =~ STARTUP*}]"
puts $fd "UNUSED_PIN_POLICY=[get_property BITSTREAM.CONFIG.UNUSEDPIN [current_design]]"
puts $fd "CHECKPOINT_ONLY=1 PHYSICAL_VOLTAGE_VERIFIED=0"
close $fd
report_property -all $port -file [file join $out port-properties.rpt]
report_property -all $buffer -file [file join $out buffer-properties.rpt]
report_property -all $reg -file [file join $out register-properties.rpt]
report_route_status -file [file join $out route-status.rpt]
report_timing -delay_type max -to $port -max_paths 1 -file [file join $out output-timing.rpt]
puts "AURA_OUTPUT_PATH_AUDIT_PASS"
close_design
exit
