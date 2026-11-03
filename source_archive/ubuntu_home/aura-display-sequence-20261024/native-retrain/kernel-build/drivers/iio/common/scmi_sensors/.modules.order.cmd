cmd_drivers/iio/common/scmi_sensors/modules.order := {  :; } | awk '!x[$$0]++' - > drivers/iio/common/scmi_sensors/modules.order
