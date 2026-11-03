# Recover only proven buffer/inverter aliases. Unknown mappings are errors.
proc audio_signature {pin} {
    set parity 0
    for {set depth 0} {$depth<32} {incr depth} {
        set nets [get_nets -segments -quiet -of_objects $pin]
        set drivers [get_pins -quiet -leaf -of_objects $nets -filter {DIRECTION == OUT}]
        if {![llength $drivers]} {return {}}
        if {[llength $drivers]!=1} {error "Ambiguous audio driver for $pin: $drivers"}
        set driver [lindex $drivers 0]
        set cell [get_cells -of_objects $driver]
        set ref [get_property REF_NAME $cell]
        if {$ref eq "LUT1"} {
            set init [get_property INIT $cell]
            if {[regexp {^[0-9]+'h([0-9a-fA-F]+)$} $init unused value]} {
                scan $value %x number
                if {$number==1 || $number==2} {
                    if {$number==1} {set parity [expr {1-$parity}]}
                    set pin [get_pins [get_property NAME $cell]/I0]
                    continue
                }
            }
        }
        return [list [get_property NAME $driver] $parity]
    }
    error "Audio alias buffer chain exceeded bound"
}
set canonical [dict create]
set alias_outputs {}
foreach pin [get_pins -of_objects [get_cells $audio_cell] -filter {DIRECTION == OUT}] {
    set leaf [string range [get_property NAME $pin] [expr {[string length $audio_cell]+1}] end]
    regsub {\[[0-9]+\]$} $leaf {} base
    if {[lsearch -exact $audio_port_names $base]>=0} {
        set signature [audio_signature $pin]
        if {![llength $signature]} {
            puts "AURA_SKIP_UNUSED_CANONICAL=$leaf"
            continue
        }
        lassign $signature driver parity
        dict lappend canonical $driver [list $leaf $parity]
    } else {lappend alias_outputs [list $pin $leaf]}
}
set mapping [open [file join $out audio_alias_map.tsv] w]
set unmapped {}
foreach pair $alias_outputs {
    lassign $pair pin leaf
    set signature [audio_signature $pin]
    if {![llength $signature]} {
        lappend unmapped [list $leaf no_driver]
        continue
    }
    lassign $signature driver parity
    if {![dict exists $canonical $driver]} {
        lappend unmapped [list $leaf $driver $parity]
        continue
    }
    lassign [lindex [dict get $canonical $driver] 0] expression canonical_parity
    set delta [expr {$parity ^ $canonical_parity}]
    puts $mapping "$leaf\t$expression\t$delta"
}
close $mapping
if {[llength $unmapped]} {error "Unmapped audio physical aliases: $unmapped"}
puts "AURA_AUDIO_OUTPUT_ALIASES_MAPPED=[llength $alias_outputs]"
