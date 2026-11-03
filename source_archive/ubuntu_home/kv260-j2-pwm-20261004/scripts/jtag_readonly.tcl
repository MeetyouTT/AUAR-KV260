# Enumerate targets; optional read of UART1 configuration/status only.
# Never halt/reset/program, write registers, or read the destructive UART FIFO.
if {[llength $argv] != 2 || ![string is integer -strict [lindex $argv 0]]} {
    error "A localhost port number and inventory|uart-registers mode are required"
}
set mode [lindex $argv 1]
if {$mode ni {inventory uart-registers}} {error "Invalid query mode"}
connect -url TCP:127.0.0.1:[lindex $argv 0]
after 1500
puts "AURA_PROCESSOR_TARGETS_BEGIN"
puts [targets]
puts "AURA_PROCESSOR_TARGETS_END"
puts "AURA_JTAG_TARGETS_BEGIN"
set devices [jtag targets]
puts $devices
puts "AURA_JTAG_TARGETS_END"
if {$mode eq "uart-registers"} {
    if {![string match {*XFL1EMEBC1R5A*} $devices] || ![string match {*xck26*} $devices]} {
        error "Expected KV260 cable and device not found"
    }
    targets -set -filter {name == "PSU"}
    puts "AURA_UART1_REGISTERS_BEGIN"
    foreach address {0xff010000 0xff010004 0xff010010 0xff010018 0xff01002c 0xff010034} {
        puts [mrd $address]
    }
    puts "AURA_UART1_REGISTERS_END"
}
disconnect
exit
