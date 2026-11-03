set_param general.maxThreads 8
open_checkpoint {/home/ghmd/auar-scheme-a-9a4f-20261103-01a1a08b/verification/run01/hardware/auar_source_routed.dcp}
set out {/home/ghmd/auar-scheme-a-9a4f-20261103-01a1a08b/verification/margin-probe}
set f [open [file join $out clocks.tsv] w]
foreach clk [get_clocks *] {
    puts $f "CLOCK\t[get_property NAME $clk]"
    foreach prop [list_property $clk] {
        if {[regexp -nocase {uncertainty|jitter|period|waveform|master_clock|source_pin|is_generated} $prop]} {
            puts $f "$prop\t[get_property $prop $clk]"
        }
    }
}
close $f
write_xdc -type timing [file join $out original_timing.xdc]
report_timing_summary -delay_type min_max -max_paths 5 -file [file join $out baseline_timing.rpt]
puts "AUAR_MARGIN_PROBE_PASS"
close_design
exit 0

