cmd_net/sched/modules.order := {   echo net/sched/cls_cgroup.ko; :; } | awk '!x[$$0]++' - > net/sched/modules.order
