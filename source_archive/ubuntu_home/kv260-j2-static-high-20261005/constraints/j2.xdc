# B03 J2.1 = FPGA H12; user reports 0 ohm continuity to pin-1 pad.
set_property PACKAGE_PIN H12 [get_ports servo_pwm]
set_property IOSTANDARD LVCMOS33 [get_ports servo_pwm]
set_property DRIVE 4 [get_ports servo_pwm]
set_property SLEW SLOW [get_ports servo_pwm]
# ADuM1201 consumes an asynchronous pulse, without an external sampling clock.
# Limit the launch-register-to-pad path to 20 ns; this is an internal budget,
# not a claimed external setup/hold requirement or a measured wire delay.
set_max_delay -datapath_only 20.000 -from [all_registers] -to [get_ports servo_pwm]
set_property BITSTREAM.CONFIG.OVERTEMPSHUTDOWN ENABLE [current_design]
