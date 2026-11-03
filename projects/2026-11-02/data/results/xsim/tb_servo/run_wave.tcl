open_vcd {actual_wave.vcd}
set obs [get_objects -quiet /tb_servo/pwm]
if {[llength $obs]} {log_vcd $obs; log_wave $obs}
set obs [get_objects -quiet /tb_servo/resetn]
if {[llength $obs]} {log_vcd $obs; log_wave $obs}
set obs [get_objects -quiet /tb_servo/dut/width]
if {[llength $obs]} {log_vcd $obs; log_wave $obs}
set obs [get_objects -quiet /tb_servo/dut/target]
if {[llength $obs]} {log_vcd $obs; log_wave $obs}
set obs [get_objects -quiet /tb_servo/dut/active]
if {[llength $obs]} {log_vcd $obs; log_wave $obs}
set obs [get_objects -quiet /tb_servo/dut/armed]
if {[llength $obs]} {log_vcd $obs; log_wave $obs}
set obs [get_objects -quiet /tb_servo/dut/reason]
if {[llength $obs]} {log_vcd $obs; log_wave $obs}
set obs [get_objects -quiet /tb_servo/dut/lease_left]
if {[llength $obs]} {log_vcd $obs; log_wave $obs}
run all
close_vcd
quit
