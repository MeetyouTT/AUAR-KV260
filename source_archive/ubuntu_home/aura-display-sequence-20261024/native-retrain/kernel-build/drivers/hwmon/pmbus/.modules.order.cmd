cmd_drivers/hwmon/pmbus/modules.order := {  :; } | awk '!x[$$0]++' - > drivers/hwmon/pmbus/modules.order
