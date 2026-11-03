foreach cmd {open_project write_device_image open_wave_database open_wave_config create_wave_config add_wave zoom_wave save_wave_config} {
 puts "AUAR_HELP_BEGIN $cmd"
 if {[catch {help $cmd} value]} {puts "HELP_ERROR $value"} else {puts $value}
 puts "AUAR_HELP_END $cmd"
}
exit
