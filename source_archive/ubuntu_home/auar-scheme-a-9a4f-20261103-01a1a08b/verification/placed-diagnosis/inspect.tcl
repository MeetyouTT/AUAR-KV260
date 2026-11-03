set_param general.maxThreads 8
open_checkpoint {/home/ghmd/auar-scheme-a-9a4f-20261103-01a1a08b/verification/run01/hardware/source_placed.dcp}
report_timing_summary -delay_type min_max -max_paths 20 -report_unconstrained -file {/home/ghmd/auar-scheme-a-9a4f-20261103-01a1a08b/verification/placed-diagnosis/timing.rpt}
report_timing -delay_type max -max_paths 20 -path_type full_clock_expanded -input_pins -file {/home/ghmd/auar-scheme-a-9a4f-20261103-01a1a08b/verification/placed-diagnosis/setup_paths.rpt}
report_qor_suggestions -file {/home/ghmd/auar-scheme-a-9a4f-20261103-01a1a08b/verification/placed-diagnosis/qor.rpt}
close_design
exit 0
