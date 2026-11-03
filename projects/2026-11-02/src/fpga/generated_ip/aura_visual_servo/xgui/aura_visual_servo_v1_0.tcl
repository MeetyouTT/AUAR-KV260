# Definitional proc to organize widgets for parameters.
proc init_gui { IPINST } {
  ipgui::add_param $IPINST -name "Component_Name"
  #Adding Page
  set Page_0 [ipgui::add_page $IPINST -name "Page 0"]
  ipgui::add_param $IPINST -name "BUILD_ID" -parent ${Page_0}
  ipgui::add_param $IPINST -name "CENTER_US" -parent ${Page_0}
  ipgui::add_param $IPINST -name "DIVIDER" -parent ${Page_0}
  ipgui::add_param $IPINST -name "FRAME_US" -parent ${Page_0}
  ipgui::add_param $IPINST -name "MAX_US" -parent ${Page_0}
  ipgui::add_param $IPINST -name "MILLIS_US" -parent ${Page_0}
  ipgui::add_param $IPINST -name "MIN_US" -parent ${Page_0}
  ipgui::add_param $IPINST -name "STEP_US" -parent ${Page_0}


}

proc update_PARAM_VALUE.BUILD_ID { PARAM_VALUE.BUILD_ID } {
	# Procedure called to update BUILD_ID when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.BUILD_ID { PARAM_VALUE.BUILD_ID } {
	# Procedure called to validate BUILD_ID
	return true
}

proc update_PARAM_VALUE.CENTER_US { PARAM_VALUE.CENTER_US } {
	# Procedure called to update CENTER_US when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.CENTER_US { PARAM_VALUE.CENTER_US } {
	# Procedure called to validate CENTER_US
	return true
}

proc update_PARAM_VALUE.DIVIDER { PARAM_VALUE.DIVIDER } {
	# Procedure called to update DIVIDER when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.DIVIDER { PARAM_VALUE.DIVIDER } {
	# Procedure called to validate DIVIDER
	return true
}

proc update_PARAM_VALUE.FRAME_US { PARAM_VALUE.FRAME_US } {
	# Procedure called to update FRAME_US when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.FRAME_US { PARAM_VALUE.FRAME_US } {
	# Procedure called to validate FRAME_US
	return true
}

proc update_PARAM_VALUE.MAX_US { PARAM_VALUE.MAX_US } {
	# Procedure called to update MAX_US when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.MAX_US { PARAM_VALUE.MAX_US } {
	# Procedure called to validate MAX_US
	return true
}

proc update_PARAM_VALUE.MILLIS_US { PARAM_VALUE.MILLIS_US } {
	# Procedure called to update MILLIS_US when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.MILLIS_US { PARAM_VALUE.MILLIS_US } {
	# Procedure called to validate MILLIS_US
	return true
}

proc update_PARAM_VALUE.MIN_US { PARAM_VALUE.MIN_US } {
	# Procedure called to update MIN_US when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.MIN_US { PARAM_VALUE.MIN_US } {
	# Procedure called to validate MIN_US
	return true
}

proc update_PARAM_VALUE.STEP_US { PARAM_VALUE.STEP_US } {
	# Procedure called to update STEP_US when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.STEP_US { PARAM_VALUE.STEP_US } {
	# Procedure called to validate STEP_US
	return true
}


proc update_MODELPARAM_VALUE.DIVIDER { MODELPARAM_VALUE.DIVIDER PARAM_VALUE.DIVIDER } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.DIVIDER}] ${MODELPARAM_VALUE.DIVIDER}
}

proc update_MODELPARAM_VALUE.FRAME_US { MODELPARAM_VALUE.FRAME_US PARAM_VALUE.FRAME_US } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.FRAME_US}] ${MODELPARAM_VALUE.FRAME_US}
}

proc update_MODELPARAM_VALUE.MILLIS_US { MODELPARAM_VALUE.MILLIS_US PARAM_VALUE.MILLIS_US } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.MILLIS_US}] ${MODELPARAM_VALUE.MILLIS_US}
}

proc update_MODELPARAM_VALUE.MIN_US { MODELPARAM_VALUE.MIN_US PARAM_VALUE.MIN_US } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.MIN_US}] ${MODELPARAM_VALUE.MIN_US}
}

proc update_MODELPARAM_VALUE.MAX_US { MODELPARAM_VALUE.MAX_US PARAM_VALUE.MAX_US } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.MAX_US}] ${MODELPARAM_VALUE.MAX_US}
}

proc update_MODELPARAM_VALUE.CENTER_US { MODELPARAM_VALUE.CENTER_US PARAM_VALUE.CENTER_US } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.CENTER_US}] ${MODELPARAM_VALUE.CENTER_US}
}

proc update_MODELPARAM_VALUE.STEP_US { MODELPARAM_VALUE.STEP_US PARAM_VALUE.STEP_US } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.STEP_US}] ${MODELPARAM_VALUE.STEP_US}
}

proc update_MODELPARAM_VALUE.BUILD_ID { MODELPARAM_VALUE.BUILD_ID PARAM_VALUE.BUILD_ID } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.BUILD_ID}] ${MODELPARAM_VALUE.BUILD_ID}
}

