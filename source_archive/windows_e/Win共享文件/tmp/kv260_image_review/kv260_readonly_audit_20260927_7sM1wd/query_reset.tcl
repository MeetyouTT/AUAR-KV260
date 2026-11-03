set base /home/ghmd/kv260_clockfix_rebuild_20260926
set out [open /home/ghmd/kv260_readonly_audit_20260927_7sM1wd/logs/reset_query.txt w]
set dcps [list \
  "$base/kv260_dpu.runs/kv260_dpu_bd_dpu_0_0_synth_1/kv260_dpu_bd_dpu_0_0.dcp" \
  "$base/kv260_dpu.runs/synth_1/kv260_dpu_bd_wrapper.dcp" \
  "$base/kv260_dpu.runs/impl_1/kv260_dpu_bd_wrapper_opt.dcp" \
  "$base/kv260_dpu.runs/impl_1/kv260_dpu_bd_wrapper_routed.dcp"]
foreach dcp $dcps {
  puts $out "DCP=$dcp"
  if {[catch {open_checkpoint $dcp} err]} {
    puts $out "ERROR=$err"
    continue
  }
  if {[string match *dpu_0_0.dcp $dcp]} {
    foreach n {dpu_2x_resetn m_axi_dpu_aresetn dpu_2x_clk m_axi_dpu_aclk s_axi_aresetn} {
      set obj [get_ports -quiet $n]
      puts $out "PORT=$n COUNT=[llength $obj] NETS=[get_nets -quiet -of_objects $obj]"
    }
  } else {
    foreach n {dpu_2x_resetn m_axi_dpu_aresetn dpu_2x_clk m_axi_dpu_aclk} {
      set obj [get_pins -hier -quiet -filter "NAME == kv260_dpu_bd_i/dpu_0/$n"]
      set con NA
      if {[llength $obj]} {catch {set con [get_property IS_CONNECTED $obj]}}
      puts $out "PIN=$n COUNT=[llength $obj] IS_CONNECTED=$con NETS=[get_nets -quiet -of_objects $obj]"
    }
  }
  close_design
}
close $out
exit
