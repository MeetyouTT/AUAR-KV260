open_vcd {actual_wave.vcd}
set obs [get_objects -quiet /tb_nominal/pwm]
if {[llength $obs]} {log_vcd $obs; log_wave $obs}
set obs [get_objects -quiet /tb_nominal/resetn]
if {[llength $obs]} {log_vcd $obs; log_wave $obs}
set obs [get_objects -quiet /tb_nominal/dut/width]
if {[llength $obs]} {log_vcd $obs; log_wave $obs}
set obs [get_objects -quiet /tb_nominal/dut/target]
if {[llength $obs]} {log_vcd $obs; log_wave $obs}
set obs [get_objects -quiet /tb_nominal/dut/active]
if {[llength $obs]} {log_vcd $obs; log_wave $obs}
set obs [get_objects -quiet /tb_nominal/dut/armed]
if {[llength $obs]} {log_vcd $obs; log_wave $obs}
set obs [get_objects -quiet /tb_nominal/dut/reason]
if {[llength $obs]} {log_vcd $obs; log_wave $obs}
set obs [get_objects -quiet /tb_nominal/dut/lease_left]
if {[llength $obs]} {log_vcd $obs; log_wave $obs}
run all
close_vcd
quit
