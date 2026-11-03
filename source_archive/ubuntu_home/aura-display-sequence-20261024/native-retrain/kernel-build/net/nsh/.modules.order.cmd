cmd_net/nsh/modules.order := {   echo net/nsh/nsh.ko; :; } | awk '!x[$$0]++' - > net/nsh/modules.order
