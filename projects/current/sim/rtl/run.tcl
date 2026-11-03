# Run all four original benches using the XSim installation belonging to this Vivado.
set root [file dirname [file dirname [file dirname [file normalize [info script]]]]]
proc write_lines {path values} {
    set f [open $path w]
    fconfigure $f -encoding utf-8 -translation lf
    foreach v $values {puts $f $v}
    close $f
}
proc verify_rtl {root argv} {
    if {[llength $argv] != 2 || [lindex $argv 0] ne "--out"} {error "usage: --out NEW_RTL_DIRECTORY"}
    set out [file normalize [lindex $argv 1]]
    if {$out eq $root || [string first "$root/" "$out/"] == 0 || [file exists $out]} {error "select a fresh directory outside the source tree"}
    if {![string match "2022.2*" [version -short]]} {error "Vivado 2022.2 required"}
    set bin [file join $::env(XILINX_VIVADO) bin]
    set helper [file join $root build rtl_results.py]
    file mkdir $out
    write_lines [file join $out tool_version.txt] [list [version] [info patchlevel]]
    exec python3 -B $helper snapshot --root $root --out $out
    foreach tb {tb_nominal tb_wide tb_pulse_guard tb_servo} {
        set work [file join $out $tb]
        file mkdir $work
        cd $work
        foreach {stage cmd} [list xvlog [list [file join $bin xvlog] -sv [file join $root src fpga rtl visual_servo.sv] [file join $root sim rtl $tb.sv]] \
                                    xelab [list [file join $bin xelab] $tb -s $tb -debug typical] \
                                    xsim [list [file join $bin xsim] $tb -runall]] {
            write_lines [file join $work $stage.argv] $cmd
            set log [file join $work $stage.console.log]
            set rc 0
            if {[catch {exec {*}$cmd > $log 2>@1} why opts]} {
                set ec [dict get $opts -errorcode]
                if {[lindex $ec 0] eq "CHILDSTATUS"} {set rc [lindex $ec 2]} else {set rc 127}
                puts stderr "$tb/$stage: $why"
            }
            write_lines [file join $work $stage.exitcode] [list $rc]
            puts "$tb/$stage exit=$rc"
            flush stdout
            if {$rc != 0} {break}
        }
    }
    cd $out
    if {[catch {exec python3 -B $helper finalize --root $root --out $out 2>@1} msg]} {error "RTL validation failed: $msg"}
    puts $msg
    puts "AUAR_RTL_PASS"
}
if {[catch {verify_rtl $root $::argv} message options]} {
    puts stderr $message
    if {[dict exists $options -errorinfo]} {puts stderr [dict get $options -errorinfo]}
    exit 1
}
exit 0

