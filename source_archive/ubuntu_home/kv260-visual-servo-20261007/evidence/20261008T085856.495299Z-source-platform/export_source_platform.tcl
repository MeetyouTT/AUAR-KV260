# Export the generated source-platform description without embedding a bitstream.
# This does not assert that an implementation was built from this project.
set out [file normalize $::env(AURA_PLATFORM_OUT)]
open_project [file join $out platform platform.xpr]
set_property platform.board_id aura_visual_servo [current_project]
set_property platform.name aura_visual_servo [current_project]
set_property platform.vendor aura.local [current_project]
set_property platform.version 1.0 [current_project]
write_hw_platform -fixed [file join $out visual_servo_source.xsa]
validate_hw_platform -verbose [file join $out visual_servo_source.xsa]
puts "AURA_SOURCE_XSA_EXPORTED"
close_project
exit
