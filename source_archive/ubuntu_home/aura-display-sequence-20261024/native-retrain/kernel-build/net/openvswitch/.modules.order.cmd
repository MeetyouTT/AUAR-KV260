cmd_net/openvswitch/modules.order := {   echo net/openvswitch/openvswitch.ko;   echo net/openvswitch/vport-vxlan.ko; :; } | awk '!x[$$0]++' - > net/openvswitch/modules.order
