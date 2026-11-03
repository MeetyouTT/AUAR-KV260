set output_dir /home/ghmd/kv260-reference-2022.2-20260930/evidence/clk_wiz_probe
create_project -force clk_wiz_probe $output_dir -part xck26-sfvc784-2LV-c
set_property board_part xilinx.com:kv260_som:part0:1.4 [current_project]
puts "PROBE_PART=[get_property PART [current_project]]"
puts "PROBE_BOARD=[get_property BOARD_PART [current_project]]"
create_ip -name clk_wiz -vendor xilinx.com -library ip -module_name clk_wiz_probe_0
puts "PROBE_CLK_WIZ_CREATED"
close_project
