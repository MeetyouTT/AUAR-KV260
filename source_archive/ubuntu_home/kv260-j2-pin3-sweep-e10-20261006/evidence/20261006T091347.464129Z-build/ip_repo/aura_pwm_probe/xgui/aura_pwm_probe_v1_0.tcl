# Definitional proc to organize widgets for parameters.
proc init_gui { IPINST } {
  ipgui::add_param $IPINST -name "Component_Name"
  #Adding Page
  set Page_0 [ipgui::add_page $IPINST -name "Page 0"]
  ipgui::add_param $IPINST -name "BUILD_ID" -parent ${Page_0}
  ipgui::add_param $IPINST -name "CLK_HZ" -parent ${Page_0}
  ipgui::add_param $IPINST -name "HOLD_FRAMES" -parent ${Page_0}
  ipgui::add_param $IPINST -name "PULSE_HIGH_US" -parent ${Page_0}
  ipgui::add_param $IPINST -name "PULSE_US" -parent ${Page_0}
  ipgui::add_param $IPINST -name "PWM_HZ" -parent ${Page_0}
  ipgui::add_param $IPINST -name "RUN_FRAMES" -parent ${Page_0}


}

proc update_PARAM_VALUE.BUILD_ID { PARAM_VALUE.BUILD_ID } {
	# Procedure called to update BUILD_ID when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.BUILD_ID { PARAM_VALUE.BUILD_ID } {
	# Procedure called to validate BUILD_ID
	return true
}

proc update_PARAM_VALUE.CLK_HZ { PARAM_VALUE.CLK_HZ } {
	# Procedure called to update CLK_HZ when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.CLK_HZ { PARAM_VALUE.CLK_HZ } {
	# Procedure called to validate CLK_HZ
	return true
}

proc update_PARAM_VALUE.HOLD_FRAMES { PARAM_VALUE.HOLD_FRAMES } {
	# Procedure called to update HOLD_FRAMES when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.HOLD_FRAMES { PARAM_VALUE.HOLD_FRAMES } {
	# Procedure called to validate HOLD_FRAMES
	return true
}

proc update_PARAM_VALUE.PULSE_HIGH_US { PARAM_VALUE.PULSE_HIGH_US } {
	# Procedure called to update PULSE_HIGH_US when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.PULSE_HIGH_US { PARAM_VALUE.PULSE_HIGH_US } {
	# Procedure called to validate PULSE_HIGH_US
	return true
}

proc update_PARAM_VALUE.PULSE_US { PARAM_VALUE.PULSE_US } {
	# Procedure called to update PULSE_US when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.PULSE_US { PARAM_VALUE.PULSE_US } {
	# Procedure called to validate PULSE_US
	return true
}

proc update_PARAM_VALUE.PWM_HZ { PARAM_VALUE.PWM_HZ } {
	# Procedure called to update PWM_HZ when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.PWM_HZ { PARAM_VALUE.PWM_HZ } {
	# Procedure called to validate PWM_HZ
	return true
}

proc update_PARAM_VALUE.RUN_FRAMES { PARAM_VALUE.RUN_FRAMES } {
	# Procedure called to update RUN_FRAMES when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.RUN_FRAMES { PARAM_VALUE.RUN_FRAMES } {
	# Procedure called to validate RUN_FRAMES
	return true
}


proc update_MODELPARAM_VALUE.CLK_HZ { MODELPARAM_VALUE.CLK_HZ PARAM_VALUE.CLK_HZ } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.CLK_HZ}] ${MODELPARAM_VALUE.CLK_HZ}
}

proc update_MODELPARAM_VALUE.PWM_HZ { MODELPARAM_VALUE.PWM_HZ PARAM_VALUE.PWM_HZ } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.PWM_HZ}] ${MODELPARAM_VALUE.PWM_HZ}
}

proc update_MODELPARAM_VALUE.PULSE_US { MODELPARAM_VALUE.PULSE_US PARAM_VALUE.PULSE_US } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.PULSE_US}] ${MODELPARAM_VALUE.PULSE_US}
}

proc update_MODELPARAM_VALUE.RUN_FRAMES { MODELPARAM_VALUE.RUN_FRAMES PARAM_VALUE.RUN_FRAMES } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.RUN_FRAMES}] ${MODELPARAM_VALUE.RUN_FRAMES}
}

proc update_MODELPARAM_VALUE.PULSE_HIGH_US { MODELPARAM_VALUE.PULSE_HIGH_US PARAM_VALUE.PULSE_HIGH_US } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.PULSE_HIGH_US}] ${MODELPARAM_VALUE.PULSE_HIGH_US}
}

proc update_MODELPARAM_VALUE.HOLD_FRAMES { MODELPARAM_VALUE.HOLD_FRAMES PARAM_VALUE.HOLD_FRAMES } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.HOLD_FRAMES}] ${MODELPARAM_VALUE.HOLD_FRAMES}
}

proc update_MODELPARAM_VALUE.BUILD_ID { MODELPARAM_VALUE.BUILD_ID PARAM_VALUE.BUILD_ID } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.BUILD_ID}] ${MODELPARAM_VALUE.BUILD_ID}
}

