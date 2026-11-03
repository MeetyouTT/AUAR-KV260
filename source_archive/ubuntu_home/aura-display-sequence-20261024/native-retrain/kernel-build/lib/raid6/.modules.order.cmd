cmd_lib/raid6/modules.order := {  :; } | awk '!x[$$0]++' - > lib/raid6/modules.order
