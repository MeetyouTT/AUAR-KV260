set control_root /home/ghmd/kv260-dpu41-control-20261001
set packaged [file join $control_root src kv260 overlays examples benchmark packaged_kernel_DPUCZDX8G_hw_mpsoc]
create_project dpu41_probe [file join $control_root evidence dpu41_probe_project] -part xck26-sfvc784-2LV-c
set_property ip_repo_paths [list $packaged] [current_project]
update_ip_catalog
create_ip -vlnv xilinx.com:RTLKernel:DPUCZDX8G:1.0 -module_name dpu41_probe_ip
set ip [get_ips dpu41_probe_ip]
report_property $ip -file [file join $control_root evidence dpu41_probe_properties.txt]
generate_target all $ip
set generated [glob -nocomplain [file join $control_root evidence dpu41_probe_project dpu41_probe.gen sources_1 ip dpu41_probe_ip arch.json]]
if {[llength $generated] != 1} {
    error "Expected one generated arch.json, found: $generated"
}
set handle [open [lindex $generated 0] r]
set arch_text [read $handle]
close $handle
puts "DPU41_PROBE_ARCH=$arch_text"
if {![regexp {0x101000056010407} $arch_text]} {
    error "DPU41 probe fingerprint does not match baseline model"
}
file copy [lindex $generated 0] [file join $control_root evidence dpu41_probe_arch.json]
puts "DPU41_PROBE_PASS"
