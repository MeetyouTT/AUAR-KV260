cmd_drivers/net/xen-netback/modules.order := {   echo drivers/net/xen-netback/xen-netback.ko; :; } | awk '!x[$$0]++' - > drivers/net/xen-netback/modules.order
