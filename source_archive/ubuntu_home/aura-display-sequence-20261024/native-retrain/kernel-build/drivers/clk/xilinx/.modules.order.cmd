cmd_drivers/clk/xilinx/modules.order := {   echo drivers/clk/xilinx/xlnx_vcu.ko; :; } | awk '!x[$$0]++' - > drivers/clk/xilinx/modules.order
