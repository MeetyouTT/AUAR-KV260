cmd_drivers/hwmon/modules.order := {   cat drivers/hwmon/pmbus/modules.order; :; } | awk '!x[$$0]++' - > drivers/hwmon/modules.order
