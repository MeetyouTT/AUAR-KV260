cmd_drivers/scsi/modules.order := {   echo drivers/scsi/xen-scsifront.ko; :; } | awk '!x[$$0]++' - > drivers/scsi/modules.order
