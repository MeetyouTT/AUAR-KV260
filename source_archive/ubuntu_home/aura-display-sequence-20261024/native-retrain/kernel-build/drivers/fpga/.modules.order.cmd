cmd_drivers/fpga/modules.order := {  :; } | awk '!x[$$0]++' - > drivers/fpga/modules.order
