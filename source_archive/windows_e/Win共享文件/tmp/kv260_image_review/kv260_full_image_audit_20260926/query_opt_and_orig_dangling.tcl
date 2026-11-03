# 只读：opt_design 后阶段定位 + 旧 routed DCP 悬空输入对照
set outdir /home/ghmd/kv260_full_image_audit_20260926
cd $outdir
set f [open "$outdir/reports/opt_stage_and_orig_dangling.txt" w]

puts $f "=== NEW opt_design DCP (2026-09-26) ==="
open_checkpoint /home/ghmd/kv260_clockfix_rebuild_20260926/kv260_dpu.runs/impl_1/kv260_dpu_bd_wrapper_opt.dcp
puts $f "TOP=[get_property TOP [current_design]]"
foreach p {kv260_dpu_bd_i/dpu_0/dpu_2x_resetn kv260_dpu_bd_i/dpu_0/m_axi_dpu_aresetn kv260_dpu_bd_i/dpu_0/dpu_2x_clk kv260_dpu_bd_i/dpu_0/m_axi_dpu_aclk \
           kv260_dpu_bd_i/dpu_0/inst/dpu_2x_resetn kv260_dpu_bd_i/dpu_0/inst/m_axi_dpu_aresetn} {
  set pin [get_pins -quiet $p]
  if {[llength $pin] == 0} { puts $f "OPT_PIN=$p MISSING" } else {
    puts $f "OPT_PIN=$p IS_CONNECTED=[get_property IS_CONNECTED $pin] NETS=[get_nets -quiet -of_objects $pin]"
  }
}
puts $f "OPT_RST_DPU_DSP_CELL_COUNT=[llength [get_cells -hier -quiet -filter {NAME =~ *rst_dpu_dsp*}]]"
puts $f "OPT_RST_DPU_DSP_NET_COUNT=[llength [get_nets -hier -quiet -filter {NAME =~ *rst_dpu_dsp*}]]"
set dangle 0
foreach pin [get_pins -quiet -of_objects [get_cells -quiet kv260_dpu_bd_i/dpu_0]] {
  if {[get_property DIRECTION $pin] eq "IN" && ![get_property IS_CONNECTED $pin]} { incr dangle }
}
puts $f "OPT_DPU_BOUNDARY_DANGLING_INPUT_COUNT=$dangle"
close_design

puts $f "=== ORIG routed DCP (2026-09-19) 悬空输入对照 ==="
open_checkpoint /home/ghmd/work/kv260_dpu_b2304_uram/kv260_dpu.runs/impl_1/kv260_dpu_bd_wrapper_routed.dcp
set names {}
foreach pin [get_pins -quiet -of_objects [get_cells -quiet kv260_dpu_bd_i/dpu_0]] {
  if {[get_property DIRECTION $pin] eq "IN" && ![get_property IS_CONNECTED $pin]} {
    set n [get_property REF_PIN_NAME $pin]
    lappend names $n
  }
}
puts $f "ORIG_DPU_BOUNDARY_DANGLING_INPUT_COUNT=[llength $names]"
foreach nm [lsort -unique $names] { puts $f "ORIG_DANGLING=$nm" }
close_design
close $f
exit
