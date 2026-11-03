# 只读诊断 v5：确认影响范围——所有已安装 Kria 器件（xck26/xck24）在 Clocking Wizard 上的表现。
set diag_dir /home/ghmd/kv260-reference-2022.2-20260930/diag
file mkdir $diag_dir

set parts {xck26-sfvc784-2LV-c xck26-sfvc784-2LVI-i xck24-ubva530-2LV-c xck24-ubva530-2LVI-i}

foreach p $parts {
    set proj "$diag_dir/diag_p5_[string map {. _ - _} $p]"
    if {[catch {create_project -force $proj $proj -part $p} e1]} {
        puts "RESULT($p)=PROJECT_ERR:$e1"
        continue
    }
    if {[catch {create_ip -name clk_wiz -vendor xilinx.com -library ip -module_name p5_clk} e2]} {
        puts "RESULT($p)=CLKWIZ_FAIL"
    } else {
        puts "RESULT($p)=CLKWIZ_OK"
    }
    # 同时验证非时钟 IP 流程是否正常（对照，排除 IP 框架整体损坏）
    if {[catch {create_ip -name axi_gpio -vendor xilinx.com -library ip -module_name p5_gpio} e3]} {
        puts "GPIO($p)=FAIL:$e3"
    } else {
        puts "GPIO($p)=OK"
    }
}
puts "DIAG5_DONE"
