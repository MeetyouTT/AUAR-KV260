set root $::env(AURA_ADAPT_ROOT)
set out $::env(AURA_ADAPT_OUT)
set_param general.maxThreads 4
if {[catch {
    open_checkpoint $::env(AURA_ADAPT_CHECKPOINT)
    source [file join $out report_signoff.tcl]
    puts "AURA_CHECKPOINT_AUDIT_COMPLETE"
} result options]} {
    puts stderr "AURA_CHECKPOINT_AUDIT_ERROR=$result"
    puts stderr [dict get $options -errorinfo]
    exit 1
}
exit 0
