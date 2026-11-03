# 只读/可逆诊断 v4：打开官方 device debug 参数，观察 Vivado 实际查找的器件数据/速度文件路径。
set diag_dir /home/ghmd/kv260-reference-2022.2-20260930/diag
file mkdir $diag_dir

puts "=== 1) 关键参数当前值（report_param 输出）==="
foreach p {device.loadMLSpeedfile device.evalarch.paspdFile device.evalarch.nonlibPaspdFile} {
    puts "---- $p ----"
    if {[catch {report_param $p} e]} { puts "RP_ERR($p)=$e" }
}

puts "=== 2) 打开 device debug 参数 ==="
foreach p {device.debugGetDeviceLoadPath device.debugPartLoader device.debugPartsParse device.dumpSpeedModelStackTrace device.debugDeviceCaching device.debugLoadDevice} {
    if {[catch {set_param $p true} e]} { puts "DBG_SET_ERR($p)=$e" } else { puts "DBG_SET_OK($p)" }
}

puts "=== 3) 加载器件并复现 clk_wiz 失败 ==="
if {[catch {create_project -force diag_proj4 $diag_dir/diag_proj4 -part xck26-sfvc784-2LV-c} e1]} {
    puts "PROJ_ERR=$e1"
} else {
    puts "PROJ_OK"
}
if {[catch {create_ip -name clk_wiz -vendor xilinx.com -library ip -module_name d4_clk} e2]} {
    puts "CW_ERR=$e2"
} else {
    puts "CW_OK"
}
puts "DIAG4_DONE"
