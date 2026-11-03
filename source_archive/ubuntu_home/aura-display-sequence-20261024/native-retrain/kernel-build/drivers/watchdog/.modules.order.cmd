cmd_drivers/watchdog/modules.order := {   echo drivers/watchdog/xen_wdt.ko; :; } | awk '!x[$$0]++' - > drivers/watchdog/modules.order
