cmd_drivers/block/modules.order := {   cat drivers/block/xen-blkback/modules.order; :; } | awk '!x[$$0]++' - > drivers/block/modules.order
