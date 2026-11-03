# Run only after probe_clk_wiz.tcl succeeds with the repaired 2022.2 install.
set out_dir /home/ghmd/kv260-reference-2022.2-20260930/evidence/clk_wiz_postrepair
create_project -force clk_wiz_postrepair $out_dir -part xck26-sfvc784-2LV-c
set_property board_part xilinx.com:kv260_som:part0:1.4 [current_project]
create_ip -name clk_wiz -vendor xilinx.com -library ip -module_name clk_wiz_postrepair_0
set ip [get_ips clk_wiz_postrepair_0]
generate_target all $ip
create_ip_run $ip
launch_runs clk_wiz_postrepair_0_synth_1 -jobs 2
wait_on_run clk_wiz_postrepair_0_synth_1
set run [get_runs clk_wiz_postrepair_0_synth_1]
puts "CLOCK_IP_RUN_STATUS=[get_property STATUS $run]"
puts "CLOCK_IP_RUN_PROGRESS=[get_property PROGRESS $run]"
if {[get_property PROGRESS $run] ne "100%"} {
    error "Clocking Wizard output products generated, but synthesis did not complete"
}
open_run clk_wiz_postrepair_0_synth_1
report_utilization -file $out_dir/clk_wiz_synth_utilization.rpt
report_timing_summary -file $out_dir/clk_wiz_synth_timing_summary.rpt
close_project
