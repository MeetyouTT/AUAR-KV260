cmd_drivers/input/modules.order := {   cat drivers/input/keyboard/modules.order;   cat drivers/input/misc/modules.order; :; } | awk '!x[$$0]++' - > drivers/input/modules.order
