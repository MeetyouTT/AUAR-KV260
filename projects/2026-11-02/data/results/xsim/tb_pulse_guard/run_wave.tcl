open_vcd {actual_wave.vcd}
set obs [get_objects -quiet /tb_pulse_guard/pwm]
if {[llength $obs]} {log_vcd $obs; log_wave $obs}
set obs [get_objects -quiet /tb_pulse_guard/resetn]
if {[llength $obs]} {log_vcd $obs; log_wave $obs}
set obs [get_objects -quiet /tb_pulse_guard/dut/width]
if {[llength $obs]} {log_vcd $obs; log_wave $obs}
set obs [get_objects -quiet /tb_pulse_guard/dut/target]
if {[llength $obs]} {log_vcd $obs; log_wave $obs}
set obs [get_objects -quiet /tb_pulse_guard/dut/active]
if {[llength $obs]} {log_vcd $obs; log_wave $obs}
set obs [get_objects -quiet /tb_pulse_guard/dut/armed]
if {[llength $obs]} {log_vcd $obs; log_wave $obs}
set obs [get_objects -quiet /tb_pulse_guard/dut/reason]
if {[llength $obs]} {log_vcd $obs; log_wave $obs}
set obs [get_objects -quiet /tb_pulse_guard/dut/lease_left]
if {[llength $obs]} {log_vcd $obs; log_wave $obs}
run all
close_vcd
quit
