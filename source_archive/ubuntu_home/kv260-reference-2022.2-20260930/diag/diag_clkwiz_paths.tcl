# 只读诊断：不修改厂商 Tcl、不改速度参数、不改安装。
# 目的：定位 clk_wiz create_gui 报错时 Vivado 查询“速度文件”的具体路径与可用命令/参数。
set diag_dir /home/ghmd/kv260-reference-2022.2-20260930/diag
file mkdir $diag_dir

puts "=== 1) 可用的 clocking / speed 相关 Tcl 命令 ==="
foreach pat {Ip_Clocking* *peed* *lkwiz* *locking*} {
    if {[catch {set c [lsort [info commands $pat]]} e]} { set c "(error:$e)" }
    puts "CMDS($pat)=$c"
}

puts "=== 2) 与 speed 相关的工具参数 ==="
foreach cmd {list_param get_param report_param} {
    if {[llength [info commands $cmd]] > 0} {
        if {[catch {set v [lsort [$cmd -quiet *peed*]]} e]} { set v "(error/$e)" }
        puts "$cmd(*peed*)=$v"
        if {[catch {set v2 [lsort [$cmd -quiet *peedfile*]]} e2]} { set v2 "(error/$e2)" }
        puts "$cmd(*peedfile*)=$v2"
    } else {
        puts "$cmd=NOT_AVAILABLE"
    }
}

puts "=== 3) 器件枚举与属性 ==="
puts "K26_PARTS=[lsort [get_parts -quiet xck26*]]"
puts "K24_PARTS=[lsort [get_parts -quiet xck24*]]"
puts "ZU_PARTS=[lsort [get_parts -quiet xczu*]]"
if {[catch {
    create_project -force diag_proj $diag_dir/diag_proj -part xck26-sfvc784-2LV-c
} e]} { puts "CREATE_PROJECT_ERR=$e" }
set p [get_parts -quiet xck26-sfvc784-2LV-c]
if {[llength $p]} {
    foreach prop {DEVICE PACKAGE SPEED TEMPERATURE_GRADE FAMILY ARCHITECTURE IS_SOFT_SILICON} {
        if {[catch {set val [get_property -quiet $prop $p]} e3]} { set val "(err)" }
        puts "PART_PROP($prop)=$val"
    }
}

puts "=== 4) 直调厂商 clocking 计算命令（观察 speedfile 行为）==="
foreach c {Ip_Clocking_Calc_M_D Ip_Clocking_Calc_Phase Ip_Clocking_Calc_DC} {
    if {[llength [info commands $c]] == 0} { puts "CMD_MISSING=$c"; continue }
    if {[catch {set r [eval $c [list -part xck26-sfvc784-2LV-c -input_freq 100 -primtive MMCM]]} e4]} {
        puts "CALL_DEFAULT_ERR($c)=$e4"
    } else {
        puts "CALL_DEFAULT_OK($c)=$r"
    }
}

puts "=== 5) 复现原始失败（最小 clk_wiz 创建）==="
if {[catch {create_ip -name clk_wiz -vendor xilinx.com -library ip -module_name diag_clk_wiz} e5]} {
    puts "CLKWIZ_ERR=$e5"
} else {
    puts "CLKWIZ_OK=create_ip succeeded"
}
puts "DIAG_DONE"
