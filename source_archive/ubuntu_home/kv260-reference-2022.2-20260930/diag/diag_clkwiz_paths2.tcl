# 只读/可逆诊断：不改文件、不改厂商 Tcl、不改安装。
# 目的：确认时钟 IP 速度文件查询的开关与根因，并判定是否存在官方参数级修复路径。
set diag_dir /home/ghmd/kv260-reference-2022.2-20260930/diag
file mkdir $diag_dir

puts "=== A) 相关 Tcl 命令 ==="
foreach pat {Ip_Clocking* *peed* *lkwiz*} {
    if {[catch {set c [lsort [info commands $pat]]} e]} { set c "(error:$e)" }
    puts "CMDS($pat)=$c"
}

puts "=== B) 工具参数中与 speedfile 有关的项 ==="
if {[llength [info commands list_param]] > 0} {
    if {[catch {set all [list_param -quiet]} e0]} { set all {} ; puts "LIST_PARAM_ERR=$e0" }
    puts "LIST_PARAM_COUNT=[llength $all]"
    foreach pat {*peed* *Speed* *paspd* *device.*} {
        set hits [lsort [lsearch -all -inline $all $pat]]
        puts "PARAM_HITS($pat)=$hits"
    }
    foreach p {device.loadMLSpeedfile device.evalarch.padrFileAsText} {
        if {[catch {set v [list_param -quiet $p]} e1]} { puts "PARAM($p)=ERR:$e1" } else { puts "PARAM($p)=$v" }
    }
} else {
    puts "list_param=NOT_AVAILABLE"
}

puts "=== C) 器件枚举 ==="
puts "K26_PARTS=[lsort [get_parts -quiet xck26*]]"
puts "K24_PARTS=[lsort [get_parts -quiet xck24*]]"
puts "ZU_PARTS=[lsort [get_parts -quiet xczu*]]"

puts "=== D) 复现：默认状态下创建 clk_wiz ==="
create_project -force diag_proj2 $diag_dir/diag_proj2 -part xck26-sfvc784-2LV-c
if {[catch {create_ip -name clk_wiz -vendor xilinx.com -library ip -module_name d_clk_default} e2]} {
    puts "DEFAULT_CLKWIZ_ERR=$e2"
} else {
    puts "DEFAULT_CLKWIZ_OK"
}

puts "=== E) 若存在 device.loadMLSpeedfile：切换取值后重试（运行时参数，不改文件）==="
set hasParam [expr {[llength [info commands list_param]] > 0 ? [llength [list_param -quiet device.loadMLSpeedfile]] > 0 : 0}]
puts "HAS_loadMLSpeedfile=$hasParam"
if {$hasParam} {
    foreach val {false true} {
        if {[catch {set_param device.loadMLSpeedfile $val} e3]} {
            puts "SETPARAM_ERR($val)=$e3"
            continue
        }
        puts "SETPARAM_OK($val)=[list_param -quiet device.loadMLSpeedfile]"
        if {[catch {create_ip -name clk_wiz -vendor xilinx.com -library ip -module_name d_clk_$val} e4]} {
            puts "CLKWIZ_ERR($val)=$e4"
        } else {
            puts "CLKWIZ_OK($val)"
        }
    }
}

puts "=== F) 直调厂商 clocking 计算命令 ==="
foreach c {Ip_Clocking_Calc_M_D Ip_Clocking_Calc_Phase Ip_Clocking_Calc_DC} {
    if {[llength [info commands $c]] == 0} { puts "CMD_MISSING=$c"; continue }
    if {[catch {set r [eval $c [list -part xck26-sfvc784-2LV-c -input_freq 100 -primtive MMCM]]} e5]} {
        puts "CALL_ERR($c)=$e5"
    } else {
        puts "CALL_OK($c)=$r"
    }
}
puts "DIAG2_DONE"
close_project
