cmd_drivers/block/xen-blkback/modules.order := {   echo drivers/block/xen-blkback/xen-blkback.ko; :; } | awk '!x[$$0]++' - > drivers/block/xen-blkback/modules.order
