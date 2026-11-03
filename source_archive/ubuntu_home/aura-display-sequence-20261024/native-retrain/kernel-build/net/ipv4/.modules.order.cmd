cmd_net/ipv4/modules.order := {   cat net/ipv4/netfilter/modules.order;   echo net/ipv4/udp_tunnel.ko; :; } | awk '!x[$$0]++' - > net/ipv4/modules.order
