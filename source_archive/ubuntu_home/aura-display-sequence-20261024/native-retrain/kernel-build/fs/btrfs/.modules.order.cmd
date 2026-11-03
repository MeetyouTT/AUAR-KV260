cmd_fs/btrfs/modules.order := {  :; } | awk '!x[$$0]++' - > fs/btrfs/modules.order
