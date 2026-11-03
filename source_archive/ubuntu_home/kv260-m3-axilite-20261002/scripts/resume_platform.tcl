set root [file normalize [file join [file dirname [info script]] ..]]
set name kv260_ispMipiRx_vcu_DP
set project_dir [file join $root src kv260 platforms vivado $name project]
open_project [file join $project_dir ${name}.xpr]

# Only the HLS-backed framebuffer synthesis was blocked by sandbox local sockets.
# Retain completed IP checkpoints; reset the blocked run and the waiting top run.
set framebuffer_run [get_runs ${name}_v_frmbuf_wr_0_0_synth_1]
reset_run $framebuffer_run
reset_run synth_1
launch_runs $framebuffer_run -jobs 4
wait_on_run $framebuffer_run
if {[get_property PROGRESS $framebuffer_run] ne "100%"} {
    error "Framebuffer synthesis did not complete: [get_property STATUS $framebuffer_run]"
}
launch_runs synth_1 -jobs 4
wait_on_run synth_1
if {[get_property PROGRESS [get_runs synth_1]] ne "100%"} {
    error "Top synthesis did not complete: [get_property STATUS [get_runs synth_1]]"
}

set_property platform.board_id $name [current_project]
set_property platform.default_output_type xclbin [current_project]
set_property platform.design_intent.datacenter false [current_project]
set_property platform.design_intent.embedded true [current_project]
set_property platform.design_intent.external_host false [current_project]
set_property platform.design_intent.server_managed false [current_project]
set_property platform.extensible true [current_project]
set_property platform.platform_state pre_synth [current_project]
set_property platform.name $name [current_project]
set_property platform.vendor xilinx [current_project]
set_property platform.version 1.0 [current_project]
set xsa [file join $project_dir ${name}.xsa]
write_hw_platform -force -file $xsa
validate_hw_platform -verbose $xsa
puts "AURA_M3_PLATFORM_RESUME_COMPLETE"
exit
