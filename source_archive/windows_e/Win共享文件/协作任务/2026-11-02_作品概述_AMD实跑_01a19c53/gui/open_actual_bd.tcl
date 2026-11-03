set_param general.maxThreads 2
set out [file dirname [info script]]
set log [open [file join $out bd_setup_status.txt] w]
proc bd_step {label cmd} {
 global log
 if {[catch {uplevel #0 $cmd} value]} {puts $log "$label FAILED $value"} else {puts $log "$label OK $value"}
 flush $log
}
bd_step open_read_only_project {open_project -read_only {/home/ghmd/aura-pan-wide-20261028/platform/platform/platform.xpr}}
bd_step open_actual_bd {open_bd_design {/home/ghmd/aura-pan-wide-20261028/platform/platform/platform.srcs/sources_1/bd/bd/kv260_ispMipiRx_vcu_DP.bd}}
bd_step export_bd_tcl [list write_bd_tcl -force [file join $out actual_block_design.tcl]]
bd_step export_native_svg [list write_bd_layout -force -format svg [file join $out actual_block_design.svg]]
bd_step ip_status [list report_ip_status -file [file join $out ip_status.rpt]]
bd_step topology {
 set f [open [file join $out bd_cells.tsv] w]
 puts $f "cell\tvlnv\ttype"
 foreach cell [get_bd_cells -hierarchical] {
  puts $f "$cell\t[get_property VLNV $cell]\t[get_property TYPE $cell]"
 }
 close $f
 set f [open [file join $out bd_ports.tsv] w]
 puts $f "port\tdirection\ttype"
 foreach port [get_bd_ports] {puts $f "$port\t[get_property DIR $port]\t[get_property TYPE $port]"}
 close $f
}
puts $log "GUI_BD_READY"
close $log
