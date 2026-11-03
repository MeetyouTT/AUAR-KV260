cmd_drivers/iio/test/modules.order := {  :; } | awk '!x[$$0]++' - > drivers/iio/test/modules.order
