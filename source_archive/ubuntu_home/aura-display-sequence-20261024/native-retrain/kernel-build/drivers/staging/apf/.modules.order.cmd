cmd_drivers/staging/apf/modules.order := {  :; } | awk '!x[$$0]++' - > drivers/staging/apf/modules.order
