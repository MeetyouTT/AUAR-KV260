# 只读查询：原工程（旧 100 MHz 拓扑）routed checkpoint 的 DPU clock/reset 连通性
# 不修改任何工程文件；输出仅写入本诊断目录。
set outdir /home/ghmd/kv260_full_image_audit_20260926
cd $outdir
set dcp /home/ghmd/work/kv260_dpu_b2304_uram/kv260_dpu.runs/impl_1/kv260_dpu_bd_wrapper_routed.dcp
open_checkpoint $dcp
set f [open "$outdir/reports/orig_routed_reset_query.txt" w]
puts $f "CHECKPOINT=$dcp"
puts $f "PART=[get_property PART [current_design]]"
puts $f "VIVADO=[version -short]"

# 1) 固定路径 pin 的存在性与连通性
foreach p {kv260_dpu_bd_i/dpu_0/dpu_2x_resetn kv260_dpu_bd_i/dpu_0/m_axi_dpu_aresetn \
           kv260_dpu_bd_i/dpu_0/dpu_2x_clk kv260_dpu_bd_i/dpu_0/m_axi_dpu_aclk \
           kv260_dpu_bd_i/dpu_0/s_axi_aresetn kv260_dpu_bd_i/dpu_0/s_axi_aclk \
           kv260_dpu_bd_i/dpu_0/inst/dpu_2x_resetn kv260_dpu_bd_i/dpu_0/inst/m_axi_dpu_aresetn} {
  set objs [get_pins -quiet $p]
  if {[llength $objs] == 0} {
    puts $f "PIN=$p EXISTS=0"
  } else {
    set nets [get_nets -quiet -of_objects $objs]
    puts $f "PIN=$p EXISTS=1 IS_CONNECTED=[get_property IS_CONNECTED $objs] NETS=$nets"
  }
}

# 2) reset 控制器实例与 reset net
foreach c [get_cells -hier -quiet -filter {NAME =~ *rst_dpu*}] {
  puts $f "RESET_CELL=$c REF_NAME=[get_property REF_NAME $c]"
}
foreach n [get_nets -hier -quiet -filter {NAME =~ *rst_dpu*}] {
  puts $f "RESET_NET=$n FANOUT=[llength [get_pins -quiet -of_objects $n]]"
}

# 3) DPU 所有层次 pin 中 reset/clock 名称的连通性统计
set total_reset 0; set conn_reset 0
foreach pin [get_pins -hier -quiet -filter {REF_PIN_NAME =~ *resetn* || REF_PIN_NAME =~ *aresetn*}] {
  incr total_reset
  if {[get_property IS_CONNECTED $pin]} { incr conn_reset }
}
puts $f "HIER_RESET_PINS_TOTAL=$total_reset CONNECTED=$conn_reset"
close $f
close_design
exit
