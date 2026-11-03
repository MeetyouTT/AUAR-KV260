# KV260 RevB03 J2.3 / PMOD_HDA12 = FPGA D10 (official pin mapping).
# Physical connector orientation and voltage have not been verified for this pin.
set_property PACKAGE_PIN D10 [get_ports servo_pwm]
set_property IOSTANDARD LVCMOS33 [get_ports servo_pwm]
set_property DRIVE 4 [get_ports servo_pwm]
set_property SLEW SLOW [get_ports servo_pwm]
# This fixed-level diagnostic has no external sampling clock.
# Limit the launch-register-to-pad path to 20 ns; this is an internal budget,
# not a claimed external setup/hold requirement or a measured wire delay.
set_max_delay -datapath_only 20.000 -from [all_registers] -to [get_ports servo_pwm]
set_property BITSTREAM.CONFIG.OVERTEMPSHUTDOWN ENABLE [current_design]
