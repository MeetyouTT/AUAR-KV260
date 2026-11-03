cmd_drivers/net/phy/modules.order := {   cat drivers/net/phy/mscc/modules.order; :; } | awk '!x[$$0]++' - > drivers/net/phy/modules.order
