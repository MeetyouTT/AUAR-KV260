# 只读查询：IP OOC checkpoint（新/旧）与新建 routed checkpoint 的 DPU reset 拓扑
# 不修改任何工程文件；所有输出写入诊断目录。
set outdir /home/ghmd/kv260_full_image_audit_20260926
cd $outdir
set f [open "$outdir/reports/ip_ooc_and_new_routed_reset_topology.txt" w]

proc dump_trunk {tag} {
  global f
  puts $f "=== $tag ==="
  puts $f "TOP=[get_property TOP [current_design]] PART=[get_property PART [current_design]]"
  foreach p {dpu_2x_clk dpu_2x_resetn m_axi_dpu_aclk m_axi_dpu_aresetn s_axi_aclk s_axi_aresetn dpu_2x_clk_ce} {
    set port [get_ports -quiet $p]
    if {[llength $port] == 0} {
      puts $f "PORT=$p MISSING"
    } else {
      set nets [get_nets -quiet -of_objects $port]
      puts $f "PORT=$p IS_CONNECTED=[get_property IS_CONNECTED $port] NETS=$nets FANOUT=[llength [get_pins -quiet -of_objects $nets]]"
    }
  }
  foreach p {inst/dpu_2x_clk inst/dpu_2x_resetn inst/m_axi_dpu_aclk inst/m_axi_dpu_aresetn inst/s_axi_aresetn} {
    set pin [get_pins -quiet $p]
    if {[llength $pin] == 0} {
      puts $f "IPINST_PIN=$p MISSING"
    } else {
      set nets [get_nets -quiet -of_objects $pin]
      puts $f "IPINST_PIN=$p IS_CONNECTED=[get_property IS_CONNECTED $pin] NETS=$nets FANOUT=[llength [get_pins -quiet -of_objects $nets]]"
    }
  }
  set cells [get_cells -quiet -hier -filter {IS_PRIMITIVE == 0}]
  puts $f "NONPRIMITIVE_CELL_COUNT=[llength $cells]"
  # reset 相关 pin 的连通性统计（限制输出量）
  set tot 0; set conn 0; set tied 0
  foreach pin [get_pins -quiet -hier -filter {REF_PIN_NAME =~ *resetn* || REF_PIN_NAME =~ *aresetn*}] {
    incr tot
    if {[get_property IS_CONNECTED $pin]} {
      incr conn
      set n [get_nets -quiet -of_objects $pin]
      if {[string match "*<const*" $n]} { incr tied; if {$tied <= 10} { puts $f "TIED_RESET_PIN=$pin NET=$n" } }
    }
  }
  puts $f "RESET_PIN_TOTAL=$tot CONNECTED=$conn CONST_TIED=$tied"
  # IP 内部层次名清单（前 20）
  set lvl [lsort [get_cells -quiet -hier -filter {IS_PRIMITIVE == 0}]]
  set i 0
  foreach c $lvl { puts $f "HIER_CELL=$c REF_NAME=[get_property REF_NAME $c]"; incr i; if {$i >= 25} break }
}

open_checkpoint /home/ghmd/kv260_clockfix_rebuild_20260926/kv260_dpu.gen/sources_1/bd/kv260_dpu_bd/ip/kv260_dpu_bd_dpu_0_0/kv260_dpu_bd_dpu_0_0.dcp
dump_trunk "NEW_IP_OOC_DCP(2026-09-26)"
close_design

open_checkpoint /home/ghmd/work/kv260_dpu_b2304_uram/kv260_dpu.gen/sources_1/bd/kv260_dpu_bd/ip/kv260_dpu_bd_dpu_0_0/kv260_dpu_bd_dpu_0_0.dcp
dump_trunk "ORIG_IP_OOC_DCP(2026-09-19)"
close_design

open_checkpoint /home/ghmd/kv260_clockfix_rebuild_20260926/kv260_dpu.runs/impl_1/kv260_dpu_bd_wrapper_routed.dcp
puts $f "=== NEW_ROUTED_DCP(2026-09-26) ==="
puts $f "TOP=[get_property TOP [current_design]]"
# DPU 边界全部输入 pin 的连通性
foreach cell {kv260_dpu_bd_i/dpu_0 kv260_dpu_bd_i/dpu_0/inst} {
  set c [get_cells -quiet $cell]
  if {[llength $c] == 0} { puts $f "CELL=$cell MISSING"; continue }
  puts $f "CELL=$cell REF_NAME=[get_property REF_NAME $c] IS_BLACKBOX=[get_property IS_BLACKBOX $c]"
  set n_in 0; set n_dangle 0
  foreach pin [get_pins -quiet -of_objects $c] {
    set dir [get_property DIRECTION $pin]
    if {$dir eq "IN" || $dir eq "INOUT"} {
      incr n_in
      if {![get_property IS_CONNECTED $pin]} {
        incr n_dangle
        puts $f "  DANGLING_INPUT=$pin"
      }
    }
  }
  puts $f "  INPUT_COUNT=$n_in DANGLING_COUNT=$n_dangle"
}
# reset 相关 net 的完整拓扑
foreach n [get_nets -hier -quiet -filter {NAME =~ *rst_dpu* || NAME =~ *aresetn*}] {
  set pins [get_pins -quiet -of_objects $n]
  puts $f "NET=$n FANOUT=[llength $pins]"
  foreach p $pins { puts $f "  PIN=$p CELL=[get_cells -quiet -of_objects $p]" }
}
# 是否存在 const 驱动的 DPU reset
foreach p {kv260_dpu_bd_i/dpu_0/dpu_2x_resetn kv260_dpu_bd_i/dpu_0/m_axi_dpu_aresetn \
           kv260_dpu_bd_i/dpu_0/inst/dpu_2x_resetn kv260_dpu_bd_i/dpu_0/inst/m_axi_dpu_aresetn} {
  set pin [get_pins -quiet $p]
  if {[llength $pin] == 0} { puts $f "FINAL_PIN=$p MISSING" } else {
    puts $f "FINAL_PIN=$p IS_CONNECTED=[get_property IS_CONNECTED $pin] NETS=[get_nets -quiet -of_objects $pin]"
  }
}
close_design
close $f
exit
