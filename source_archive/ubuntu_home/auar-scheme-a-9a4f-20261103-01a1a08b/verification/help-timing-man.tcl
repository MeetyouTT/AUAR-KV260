if {[catch {help -verbose phys_opt_design} v]} {puts $v} else {puts $v}
if {[catch {help -help} v]} {puts $v} else {puts $v}
if {[catch {help -long phys_opt_design} v]} {puts $v} else {puts $v}
if {[catch {help -long route_design} v]} {puts $v} else {puts $v}
exit 0
