cmd_drivers/remoteproc/modules.order := {   echo drivers/remoteproc/zynqmp_r5_remoteproc.ko; :; } | awk '!x[$$0]++' - > drivers/remoteproc/modules.order
