cmd_net/8021q/modules.order := {  :; } | awk '!x[$$0]++' - > net/8021q/modules.order
