# Read-only query of the existing DPU OOC checkpoint; does not open a project.
set dcp /home/ghmd/kv260_clockfix_rebuild_20260926/kv260_dpu.gen/sources_1/bd/kv260_dpu_bd/ip/kv260_dpu_bd_dpu_0_0/kv260_dpu_bd_dpu_0_0.dcp
set out_path /home/ghmd/kv260_full_image_audit_20260926_codex/reports/dpu_ooc_port_query.txt
if {[catch {open_checkpoint $dcp} err]} {
  set out [open $out_path w]
  puts $out "OPEN_ERROR=$err"
  close $out
  exit 1
}
set out [open $out_path w]
puts $out "DCP=$dcp"
puts $out "PORT_COUNT=[llength [get_ports -quiet *]]"
foreach port [get_ports -quiet *] {
  if {[regexp -nocase {clk|reset|areset|resetn} $port]} {
    puts $out "PORT=$port DIR=[get_property DIRECTION $port] WIDTH=[get_property PORT_WIDTH $port]"
  }
}
close $out
close_design
exit
