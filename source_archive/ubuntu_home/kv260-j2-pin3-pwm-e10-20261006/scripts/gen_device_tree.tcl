# Generate the 2022.2 overlay from the accepted XSA; no hardware access.
if {$argc != 3} { error "usage: xsct gen_device_tree.tcl XSA REPOSITORY OUTPUT" }
lassign $argv xsa repo out
file mkdir $out
hsi::open_hw_design $xsa
hsi::set_repo_path $repo
hsi::create_sw_design aura_pwm_dt -os device_tree -proc psu_cortexa53_0
hsi::set_property CONFIG.dt_overlay true [hsi::get_os]
hsi::generate_target -dir $out
hsi::close_hw_design [hsi::current_hw_design]
puts "AURA_PWM_DT_GENERATED"
exit
