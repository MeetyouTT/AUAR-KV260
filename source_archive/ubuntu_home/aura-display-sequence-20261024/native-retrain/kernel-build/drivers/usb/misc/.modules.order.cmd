cmd_drivers/usb/misc/modules.order := {   echo drivers/usb/misc/usb2244.ko;   echo drivers/usb/misc/usb5744.ko; :; } | awk '!x[$$0]++' - > drivers/usb/misc/modules.order
