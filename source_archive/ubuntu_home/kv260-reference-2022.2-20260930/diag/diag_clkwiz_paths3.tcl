# 只读/可逆诊断 v3：全部语句用 catch 包裹，避免中断。
set diag_dir /home/ghmd/kv260-reference-2022.2-20260930/diag
file mkdir $diag_dir

puts "=== 1) 官方 speed 相关命令及帮助 ==="
foreach c {get_speed_models set_speed_grade} {
    if {[llength [info commands $c]] == 0} { puts "MISSING=$c"; continue }
    if {[catch {set h [$c -help]} e]} { puts "HELP_ERR($c)=$e" } else { puts "HELP($c)=$h" }
}

puts "=== 2) 参数查询（report_param / get_param）==="
foreach cmd {report_param get_param} {
    if {[llength [info commands $cmd]] == 0} { puts "CMD_MISSING=$cmd"; continue }
    if {[catch {set r [$cmd -quiet device.loadMLSpeedfile]} e]} { puts "Q_ERR($cmd)=$e" } else { puts "Q($cmd)=$r" }
}
if {[llength [info commands report_param]] > 0} {
    if {[catch {set all [report_param -non_default -quiet]} e2]} {
        puts "RP_ALL_ERR=$e2"
    } else {
        set lines [split $all "\n"]
        puts "RP_ALL_LINES=[llength $lines]"
        foreach l $lines { if {[string match -nocase *speed* $l]} { puts "RP_LINE=$l" } }
    }
}

puts "=== 3) get_speed_models 调用 ==="
if {[llength [info commands get_speed_models]]} {
    if {[catch {set r [get_speed_models]} e3]} { puts "GSM_ERR=$e3" } else { puts "GSM=$r" }
    if {[catch {set r2 [get_speed_models -quiet]} e3b]} { puts "GSM_Q_ERR=$e3b" } else { puts "GSM_Q=$r2" }
}

puts "=== 4) 切换 device.loadMLSpeedfile 后创建 clk_wiz（运行时参数，不改文件）==="
if {[catch {create_project -force diag_proj3 $diag_dir/diag_proj3 -part xck26-sfvc784-2LV-c} e4]} {
    puts "PROJ_ERR=$e4"
} else {
    foreach val {true false} {
        if {[catch {set_param device.loadMLSpeedfile $val} e5]} { puts "SP_ERR($val)=$e5"; continue }
        puts "SP_OK($val)"
        if {[catch {set q [report_param -quiet device.loadMLSpeedfile]} e6]} { puts "SP_Q_ERR=$e6" } else { puts "SP_VALUE($val)=$q" }
        if {[catch {create_ip -name clk_wiz -vendor xilinx.com -library ip -module_name d3_$val} e7]} {
            puts "CW_ERR($val)=$e7"
        } else {
            puts "CW_OK($val)"
        }
    }
}
puts "DIAG3_DONE"
