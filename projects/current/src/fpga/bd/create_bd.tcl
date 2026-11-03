# Executed once after project creation and custom-IP packaging.
source [file join $::AUAR_ROOT src fpga bd system.tcl]
set auar_bd [get_files -quiet */kv260_ispMipiRx_vcu_DP.bd]
if {[llength $auar_bd] != 1} {error "BD source reconstruction did not create exactly one system"}
if {[llength [get_bd_cells -quiet aura_m3_regs_0]] != 1} {error "Custom motion IP is absent"}
foreach {key expected} {BUILD_ID 0x10282601 MIN_US 500 MAX_US 2500 CENTER_US 1500 STEP_US 4} {
    set got [get_property CONFIG.$key [get_bd_cells aura_m3_regs_0]]
    if {$got != $expected} {error "Motion configuration mismatch $key=$got expected=$expected"}
}
validate_bd_design
save_bd_design
