

#---------------------------
# Constant blocks
#---------------------------

#---------------------------
# Platform Parameters for kv260_ispMipiRx_vcu_DP
#---------------------------
set PS_0 [get_bd_cell /PS_0]
    
set_property -dict [ list \
  CONFIG.PSU__USE__S_AXI_GP1 1 \
  CONFIG.PSU__USE__S_AXI_GP3 1 \
  CONFIG.PSU__USE__S_AXI_GP5 1 \
  ] $PS_0
set axi_ic_accel_ctrl [get_bd_cell /axi_ic_accel_ctrl]
    
set_property -dict [ list \
  CONFIG.NUM_SI 1 \
  CONFIG.NUM_MI 2 \
  CONFIG.M01_HAS_REGSLICE 1 \
  ] $axi_ic_accel_ctrl
set axi_ic_audio_mcu [get_bd_cell /axi_ic_audio_mcu]
    
set_property -dict [ list \
  CONFIG.NUM_SI 3 \
  CONFIG.NUM_MI 1 \
  ] $axi_ic_audio_mcu

#---------------------------
# Instantiating DPUCZDX8G_1
#---------------------------
set DPUCZDX8G_1 [create_bd_cell -type ip -vlnv xilinx.com:RTLKernel:DPUCZDX8G:1.0 DPUCZDX8G_1]
  

#---------------------------
# Instantiating axi_ic_PS_0_S_AXI_HPC1_FPD
#---------------------------
set axi_ic_PS_0_S_AXI_HPC1_FPD [create_bd_cell -type ip -vlnv xilinx.com:ip:axi_interconnect:2.1 axi_ic_PS_0_S_AXI_HPC1_FPD]
  
set_property -dict [ list  \
  CONFIG.NUM_MI {1} \
  CONFIG.NUM_SI {1} \
  CONFIG.M00_HAS_REGSLICE {0} \
  CONFIG.S00_HAS_REGSLICE {0}  ] $axi_ic_PS_0_S_AXI_HPC1_FPD

#---------------------------
# Instantiating axi_ic_PS_0_S_AXI_HP1_FPD
#---------------------------
set axi_ic_PS_0_S_AXI_HP1_FPD [create_bd_cell -type ip -vlnv xilinx.com:ip:axi_interconnect:2.1 axi_ic_PS_0_S_AXI_HP1_FPD]
  
set_property -dict [ list  \
  CONFIG.NUM_MI {1} \
  CONFIG.NUM_SI {1} \
  CONFIG.M00_HAS_REGSLICE {0} \
  CONFIG.S00_HAS_REGSLICE {0}  ] $axi_ic_PS_0_S_AXI_HP1_FPD

#---------------------------
# Instantiating axi_ic_PS_0_S_AXI_HP3_FPD
#---------------------------
set axi_ic_PS_0_S_AXI_HP3_FPD [create_bd_cell -type ip -vlnv xilinx.com:ip:axi_interconnect:2.1 axi_ic_PS_0_S_AXI_HP3_FPD]
  
set_property -dict [ list  \
  CONFIG.NUM_MI {1} \
  CONFIG.NUM_SI {1} \
  CONFIG.M00_HAS_REGSLICE {0} \
  CONFIG.S00_HAS_REGSLICE {0}  ] $axi_ic_PS_0_S_AXI_HP3_FPD

#---------------------------
# Instantiating PS_0_pl_ps_irq0_1_interrupt_concat
#---------------------------
set PS_0_pl_ps_irq0_1_interrupt_concat [create_bd_cell -type ip -vlnv xilinx.com:ip:xlconcat:2.1 PS_0_pl_ps_irq0_1_interrupt_concat]
  
set_property -dict [ list  \
  CONFIG.NUM_PORTS {7}  ] $PS_0_pl_ps_irq0_1_interrupt_concat

#---------------------------
# Instantiating irq_const_tieoff
#---------------------------
set irq_const_tieoff [create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 irq_const_tieoff]
  
set_property -dict [ list  \
  CONFIG.CONST_WIDTH {1} \
  CONFIG.CONST_VAL {0}  ] $irq_const_tieoff

#---------------------------
# Connectivity Phase 1
#---------------------------
connect_bd_intf_net \
  [get_bd_intf_pins -auto_enable /axi_ic_PS_0_S_AXI_HPC1_FPD/M00_AXI] \
  [get_bd_intf_pins -auto_enable /PS_0/S_AXI_HPC1_FPD] \

connect_bd_intf_net \
  [get_bd_intf_pins -auto_enable /axi_ic_PS_0_S_AXI_HP1_FPD/M00_AXI] \
  [get_bd_intf_pins -auto_enable /PS_0/S_AXI_HP1_FPD] \

connect_bd_intf_net \
  [get_bd_intf_pins -auto_enable /axi_ic_PS_0_S_AXI_HP3_FPD/M00_AXI] \
  [get_bd_intf_pins -auto_enable /PS_0/S_AXI_HP3_FPD] \

connect_bd_intf_net \
  [get_bd_intf_pins -auto_enable /axi_ic_accel_ctrl/M01_AXI] \
  [get_bd_intf_pins -auto_enable /DPUCZDX8G_1/S_AXI_CONTROL] \

connect_bd_intf_net \
  [get_bd_intf_pins -auto_enable /DPUCZDX8G_1/M_AXI_GP0] \
  [get_bd_intf_pins -auto_enable /axi_ic_PS_0_S_AXI_HPC1_FPD/S00_AXI] \

connect_bd_intf_net \
  [get_bd_intf_pins -auto_enable /DPUCZDX8G_1/M_AXI_HP0] \
  [get_bd_intf_pins -auto_enable /axi_ic_PS_0_S_AXI_HP1_FPD/S00_AXI] \

connect_bd_intf_net \
  [get_bd_intf_pins -auto_enable /DPUCZDX8G_1/M_AXI_HP2] \
  [get_bd_intf_pins -auto_enable /axi_ic_PS_0_S_AXI_HP3_FPD/S00_AXI] \

connect_bd_net  \
  [get_bd_pins -auto_enable /PS_0_pl_ps_irq0_1_interrupt_concat/dout] \
  [get_bd_pins -auto_enable /PS_0/pl_ps_irq0] \

connect_bd_net  \
  [get_bd_pins -auto_enable /DPUCZDX8G_1/interrupt] \
  [get_bd_pins -auto_enable /PS_0_pl_ps_irq0_1_interrupt_concat/In1] \

connect_bd_net  \
  [get_bd_pins -auto_enable /irq_const_tieoff/dout] \
  [get_bd_pins -auto_enable /PS_0_pl_ps_irq0_1_interrupt_concat/In0] \
  [get_bd_pins -auto_enable /PS_0_pl_ps_irq0_1_interrupt_concat/In2] \
  [get_bd_pins -auto_enable /PS_0_pl_ps_irq0_1_interrupt_concat/In3] \
  [get_bd_pins -auto_enable /PS_0_pl_ps_irq0_1_interrupt_concat/In4] \
  [get_bd_pins -auto_enable /PS_0_pl_ps_irq0_1_interrupt_concat/In5] \
  [get_bd_pins -auto_enable /PS_0_pl_ps_irq0_1_interrupt_concat/In6] \


#---------------------------
# Clock/Reset Annotation
#---------------------------

set_property HDL_ATTRIBUTE.saxihpc1_fpd_aclk.FREQ_HZ {300000000} [get_bd_cells PS_0]
set_property HDL_ATTRIBUTE.saxihpc1_fpd_aclk.FREQ_HZ_TOLERANCE {15000000} [get_bd_cells PS_0]
set_property HDL_ATTRIBUTE.saxihp1_fpd_aclk.FREQ_HZ {300000000} [get_bd_cells PS_0]
set_property HDL_ATTRIBUTE.saxihp1_fpd_aclk.FREQ_HZ_TOLERANCE {15000000} [get_bd_cells PS_0]
set_property HDL_ATTRIBUTE.saxihp3_fpd_aclk.FREQ_HZ {300000000} [get_bd_cells PS_0]
set_property HDL_ATTRIBUTE.saxihp3_fpd_aclk.FREQ_HZ_TOLERANCE {15000000} [get_bd_cells PS_0]

set_property HDL_ATTRIBUTE.aclk.FREQ_HZ {300000000} $DPUCZDX8G_1
set_property HDL_ATTRIBUTE.aclk.FREQ_HZ_TOLERANCE {15000000} $DPUCZDX8G_1
set_property HDL_ATTRIBUTE.ap_clk_2.FREQ_HZ {600000000} $DPUCZDX8G_1
set_property HDL_ATTRIBUTE.ap_clk_2.FREQ_HZ_TOLERANCE {30000000} $DPUCZDX8G_1



#---------------------------
# Invoke clock automation
#---------------------------

set_param bd.clkrstautomationv2 1
::bd::clkrst::apply_clk_rst_automation



#---------------------------
# Connectivity Phase 2
#---------------------------

#---------------------------
# Create Stream Map file
#---------------------------
set stream_subsystems [get_bd_cells * -hierarchical -quiet -filter {VLNV =~ "*:*:sdx_stream_subsystem:*"}]
if {[string length $stream_subsystems] > 0} {    
  set xmlFile $vpl_output_dir/qdma_stream_map.xml
  set fp [open ${xmlFile} w]
  puts $fp "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
  puts $fp "<xd:streamMap xmlns:xd=\"http://www.xilinx.com/xd\">"
  foreach streamSS [get_bd_cells * -hierarchical -quiet -filter {VLNV =~ "*:*:sdx_stream_subsystem:*"}] {
    set ssInstance [string trimleft $streamSS /]
    set ssRegion [get_property CONFIG.SLR_ASSIGNMENTS $streamSS]
    foreach ssIntf [get_bd_intf_pins $streamSS/* -quiet -filter {NAME=~"S??_AXIS"}] {
      set pinName [get_property NAME $ssIntf]
      set routeId [sdx_stream_subsystem::get_routeid $ssIntf]
      set flowId [sdx_stream_subsystem::get_flowid $ssIntf]
      puts $fp "  <xd:streamRoute xd:instanceRef=\"$ssInstance\" xd:portRef=\"$pinName\" xd:route=\"$routeId\" xd:flow=\"$flowId\" xd:region=\"$ssRegion\">"
      foreach connection [find_bd_objs -relation connected_to $ssIntf -thru_hier] {
        set connectedRegion [get_property CONFIG.SLR_ASSIGNMENTS [bd::utils::get_parent $connection]]
        set connectedPort [bd::utils::get_short_name $connection]
        set connectedInst [string trimleft [bd::utils::get_parent $connection] /]
        puts $fp "    <xd:connection xd:instanceRef=\"$connectedInst\" xd:portRef=\"$connectedPort\" xd:region=\"$connectedRegion\"/>"
      }
      puts $fp "  </xd:streamRoute>"
    }
    foreach ssIntf [get_bd_intf_pins $streamSS/* -quiet -filter {NAME=~"M??_AXIS"}] {
      set pinName [get_property NAME $ssIntf]
      set routeId [sdx_stream_subsystem::get_routeid $ssIntf]
      set flowId [sdx_stream_subsystem::get_flowid $ssIntf]
      puts $fp "  <xd:streamRoute xd:instanceRef=\"$ssInstance\" xd:portRef=\"$pinName\" xd:route=\"$routeId\" xd:flow=\"$flowId\" xd:region=\"$ssRegion\">"
      foreach connection [find_bd_objs -relation connected_to $ssIntf -thru_hier] {
        set connectedRegion [get_property CONFIG.SLR_ASSIGNMENTS [bd::utils::get_parent $connection]]
        set connectedPort [bd::utils::get_short_name $connection]
        set connectedInst [string trimleft [bd::utils::get_parent $connection] /]
        puts $fp "    <xd:connection xd:instanceRef=\"$connectedInst\" xd:portRef=\"$connectedPort\" xd:region=\"$connectedRegion\"/>"
      }
      puts $fp "  </xd:streamRoute>"
    }
  }
  puts $fp "</xd:streamMap>"
  close $fp
}


