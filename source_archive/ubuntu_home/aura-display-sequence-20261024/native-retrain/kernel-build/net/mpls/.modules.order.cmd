cmd_net/mpls/modules.order := {   echo net/mpls/mpls_gso.ko; :; } | awk '!x[$$0]++' - > net/mpls/modules.order
