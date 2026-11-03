open_vcd {actual_wave.vcd}
set obs [get_objects -quiet /tb_wide/pwm]
if {[llength $obs]} {log_vcd $obs; log_wave $obs}
set obs [get_objects -quiet /tb_wide/resetn]
if {[llength $obs]} {log_vcd $obs; log_wave $obs}
set obs [get_objects -quiet /tb_wide/dut/width]
if {[llength $obs]} {log_vcd $obs; log_wave $obs}
set obs [get_objects -quiet /tb_wide/dut/target]
if {[llength $obs]} {log_vcd $obs; log_wave $obs}
set obs [get_objects -quiet /tb_wide/dut/active]
if {[llength $obs]} {log_vcd $obs; log_wave $obs}
set obs [get_objects -quiet /tb_wide/dut/armed]
if {[llength $obs]} {log_vcd $obs; log_wave $obs}
set obs [get_objects -quiet /tb_wide/dut/reason]
if {[llength $obs]} {log_vcd $obs; log_wave $obs}
set obs [get_objects -quiet /tb_wide/dut/lease_left]
if {[llength $obs]} {log_vcd $obs; log_wave $obs}
run all
close_vcd
quit
