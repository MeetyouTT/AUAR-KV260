# Reopen the routed checkpoint in non-project mode; no synthesis or routing.
set_param general.maxThreads 1
set root /home/ghmd/aura-pan-wide-20261028
set out [file join $root implementation export-resume]
file mkdir $out
open_checkpoint [file join $root implementation source_routed.dcp]
write_bitstream -bin_file [file join $out visual_servo_source.bit]
write_hw_platform -fixed -include_bit [file join $root implementation visual_servo_source_implemented.xsa]
validate_hw_platform -verbose [file join $root implementation visual_servo_source_implemented.xsa]
puts "AURA_WIDE_EXPORT_RESUMED_FROM_ROUTED_CHECKPOINT"
close_project
exit
