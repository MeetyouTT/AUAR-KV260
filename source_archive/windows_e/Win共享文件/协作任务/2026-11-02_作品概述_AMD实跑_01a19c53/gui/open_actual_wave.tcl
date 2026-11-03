set_param general.maxThreads 2
set out [file dirname [info script]]
set log [open [file join $out wave_setup_status.txt] w]
proc wave_step {label cmd} {
 global log
 if {[catch {uplevel #0 $cmd} value]} {puts $log "$label FAILED $value"} else {puts $log "$label OK $value"}
 flush $log
}
wave_step load_simulator {load_features simulator}
wave_step open_actual_wdb {open_wave_database {/home/ghmd/Win共享文件/协作任务/2026-11-02_作品概述_AMD实跑_01a19c53/simulations/tb_nominal/actual_wave.wdb}}
wave_step create_config {create_wave_config AUAR_NOMINAL_RTL_SIMULATION}
foreach signal {/tb_nominal/pwm /tb_nominal/resetn /tb_nominal/dut/width /tb_nominal/dut/target /tb_nominal/dut/active /tb_nominal/dut/armed /tb_nominal/dut/reason} {
 wave_step "add_$signal" [list add_wave $signal]
}
wave_step config_properties {
 set obj [current_wave_config]
 set props [list_property $obj]
 foreach prop $props {puts $log "PROPERTY $prop [get_property $prop $obj]"}
 if {[lsearch -exact $props DISPLAY_SCALE]>=0} {set_property DISPLAY_SCALE ms $obj}
}
wave_step save_config [list save_wave_config [file join $out nominal_wave.wcfg]]
puts $log "GUI_WAVE_READY"
close $log
