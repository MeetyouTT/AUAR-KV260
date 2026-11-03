-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- --------------------------------------------------------------------------------
-- Tool Version: Vivado v.2022.2 (lin64) Build 3671981 Fri Oct 14 04:59:54 MDT 2022
-- Date        : Thu Oct  8 02:17:50 2026
-- Host        : ghmd-MRA-XXX running 64-bit Ubuntu 20.04.4 LTS
-- Command     : write_vhdl -force -mode synth_stub -rename_top kv260_ispMipiRx_vcu_DP_audio_ss_0_0 -prefix
--               kv260_ispMipiRx_vcu_DP_audio_ss_0_0_ kv260_ispMipiRx_vcu_DP_audio_ss_0_0_stub.vhdl
-- Design      : kv260_ispMipiRx_vcu_DP_audio_ss_0_0
-- Purpose     : Stub declaration of top-level module interface
-- Device      : xck26-sfvc784-2LV-c
-- --------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;

entity kv260_ispMipiRx_vcu_DP_audio_ss_0_0 is
  Port ( 
    ACLK : in STD_LOGIC;
    ARESETN : in STD_LOGIC;
    clk_out_audio : out STD_LOGIC;
    irq_i2s_rx : out STD_LOGIC;
    irq_i2s_tx : out STD_LOGIC;
    irq_mm2s_audio : out STD_LOGIC;
    irq_s2mm_audio : out STD_LOGIC;
    lrclk_rx : out STD_LOGIC;
    lrclk_tx : out STD_LOGIC;
    m_axi_aclk : in STD_LOGIC;
    m_axi_aresetn : in STD_LOGIC;
    m_axi_mm2s_audio_araddr : out STD_LOGIC_VECTOR ( 63 downto 0 );
    m_axi_mm2s_audio_arburst : out STD_LOGIC_VECTOR ( 1 downto 0 );
    m_axi_mm2s_audio_arcache : out STD_LOGIC_VECTOR ( 3 downto 0 );
    m_axi_mm2s_audio_arlen : out STD_LOGIC_VECTOR ( 7 downto 0 );
    m_axi_mm2s_audio_arlock : out STD_LOGIC_VECTOR ( 0 to 0 );
    m_axi_mm2s_audio_arprot : out STD_LOGIC_VECTOR ( 2 downto 0 );
    m_axi_mm2s_audio_arqos : out STD_LOGIC_VECTOR ( 3 downto 0 );
    m_axi_mm2s_audio_arready : in STD_LOGIC;
    m_axi_mm2s_audio_arregion : out STD_LOGIC_VECTOR ( 3 downto 0 );
    m_axi_mm2s_audio_arsize : out STD_LOGIC_VECTOR ( 2 downto 0 );
    m_axi_mm2s_audio_aruser : out STD_LOGIC_VECTOR ( 3 downto 0 );
    m_axi_mm2s_audio_arvalid : out STD_LOGIC;
    m_axi_mm2s_audio_rdata : in STD_LOGIC_VECTOR ( 31 downto 0 );
    m_axi_mm2s_audio_rlast : in STD_LOGIC;
    m_axi_mm2s_audio_rready : out STD_LOGIC;
    m_axi_mm2s_audio_rresp : in STD_LOGIC_VECTOR ( 1 downto 0 );
    m_axi_mm2s_audio_rvalid : in STD_LOGIC;
    m_axi_s2mm_audio_awaddr : out STD_LOGIC_VECTOR ( 63 downto 0 );
    m_axi_s2mm_audio_awburst : out STD_LOGIC_VECTOR ( 1 downto 0 );
    m_axi_s2mm_audio_awcache : out STD_LOGIC_VECTOR ( 3 downto 0 );
    m_axi_s2mm_audio_awlen : out STD_LOGIC_VECTOR ( 7 downto 0 );
    m_axi_s2mm_audio_awlock : out STD_LOGIC_VECTOR ( 0 to 0 );
    m_axi_s2mm_audio_awprot : out STD_LOGIC_VECTOR ( 2 downto 0 );
    m_axi_s2mm_audio_awqos : out STD_LOGIC_VECTOR ( 3 downto 0 );
    m_axi_s2mm_audio_awready : in STD_LOGIC;
    m_axi_s2mm_audio_awregion : out STD_LOGIC_VECTOR ( 3 downto 0 );
    m_axi_s2mm_audio_awsize : out STD_LOGIC_VECTOR ( 2 downto 0 );
    m_axi_s2mm_audio_awuser : out STD_LOGIC_VECTOR ( 3 downto 0 );
    m_axi_s2mm_audio_awvalid : out STD_LOGIC;
    m_axi_s2mm_audio_bready : out STD_LOGIC;
    m_axi_s2mm_audio_bresp : in STD_LOGIC_VECTOR ( 1 downto 0 );
    m_axi_s2mm_audio_bvalid : in STD_LOGIC;
    m_axi_s2mm_audio_wdata : out STD_LOGIC_VECTOR ( 31 downto 0 );
    m_axi_s2mm_audio_wlast : out STD_LOGIC;
    m_axi_s2mm_audio_wready : in STD_LOGIC;
    m_axi_s2mm_audio_wstrb : out STD_LOGIC_VECTOR ( 3 downto 0 );
    m_axi_s2mm_audio_wvalid : out STD_LOGIC;
    mclk_out_rx : out STD_LOGIC;
    mclk_out_tx : out STD_LOGIC;
    peripheral_aresetn : out STD_LOGIC_VECTOR ( 0 to 0 );
    pl_clk1 : in STD_LOGIC;
    pl_rstn1 : in STD_LOGIC;
    s_axi_ctrl_i2s_rx_araddr : in STD_LOGIC_VECTOR ( 39 downto 0 );
    s_axi_ctrl_i2s_rx_arready : out STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_ctrl_i2s_rx_arvalid : in STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_ctrl_i2s_rx_awaddr : in STD_LOGIC_VECTOR ( 39 downto 0 );
    s_axi_ctrl_i2s_rx_awready : out STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_ctrl_i2s_rx_awvalid : in STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_ctrl_i2s_rx_bready : in STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_ctrl_i2s_rx_bresp : out STD_LOGIC_VECTOR ( 1 downto 0 );
    s_axi_ctrl_i2s_rx_bvalid : out STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_ctrl_i2s_rx_rdata : out STD_LOGIC_VECTOR ( 31 downto 0 );
    s_axi_ctrl_i2s_rx_rready : in STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_ctrl_i2s_rx_rresp : out STD_LOGIC_VECTOR ( 1 downto 0 );
    s_axi_ctrl_i2s_rx_rvalid : out STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_ctrl_i2s_rx_wdata : in STD_LOGIC_VECTOR ( 31 downto 0 );
    s_axi_ctrl_i2s_rx_wready : out STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_ctrl_i2s_rx_wvalid : in STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_ctrl_i2s_tx_araddr : in STD_LOGIC_VECTOR ( 39 downto 0 );
    s_axi_ctrl_i2s_tx_arready : out STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_ctrl_i2s_tx_arvalid : in STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_ctrl_i2s_tx_awaddr : in STD_LOGIC_VECTOR ( 39 downto 0 );
    s_axi_ctrl_i2s_tx_awready : out STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_ctrl_i2s_tx_awvalid : in STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_ctrl_i2s_tx_bready : in STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_ctrl_i2s_tx_bresp : out STD_LOGIC_VECTOR ( 1 downto 0 );
    s_axi_ctrl_i2s_tx_bvalid : out STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_ctrl_i2s_tx_rdata : out STD_LOGIC_VECTOR ( 31 downto 0 );
    s_axi_ctrl_i2s_tx_rready : in STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_ctrl_i2s_tx_rresp : out STD_LOGIC_VECTOR ( 1 downto 0 );
    s_axi_ctrl_i2s_tx_rvalid : out STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_ctrl_i2s_tx_wdata : in STD_LOGIC_VECTOR ( 31 downto 0 );
    s_axi_ctrl_i2s_tx_wready : out STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_ctrl_i2s_tx_wvalid : in STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_lite_audio_fmt_araddr : in STD_LOGIC_VECTOR ( 39 downto 0 );
    s_axi_lite_audio_fmt_arready : out STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_lite_audio_fmt_arvalid : in STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_lite_audio_fmt_awaddr : in STD_LOGIC_VECTOR ( 39 downto 0 );
    s_axi_lite_audio_fmt_awready : out STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_lite_audio_fmt_awvalid : in STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_lite_audio_fmt_bready : in STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_lite_audio_fmt_bresp : out STD_LOGIC_VECTOR ( 1 downto 0 );
    s_axi_lite_audio_fmt_bvalid : out STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_lite_audio_fmt_rdata : out STD_LOGIC_VECTOR ( 31 downto 0 );
    s_axi_lite_audio_fmt_rready : in STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_lite_audio_fmt_rresp : out STD_LOGIC_VECTOR ( 1 downto 0 );
    s_axi_lite_audio_fmt_rvalid : out STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_lite_audio_fmt_wdata : in STD_LOGIC_VECTOR ( 31 downto 0 );
    s_axi_lite_audio_fmt_wready : out STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_lite_audio_fmt_wvalid : in STD_LOGIC_VECTOR ( 0 to 0 );
    sclk_rx : out STD_LOGIC;
    sclk_tx : out STD_LOGIC;
    sdata_rx : in STD_LOGIC;
    sdata_tx : out STD_LOGIC
  );

end kv260_ispMipiRx_vcu_DP_audio_ss_0_0;

architecture stub of kv260_ispMipiRx_vcu_DP_audio_ss_0_0 is
attribute syn_black_box : boolean;
attribute black_box_pad_pin : string;
attribute syn_black_box of stub : architecture is true;
attribute black_box_pad_pin of stub : architecture is "ACLK,ARESETN,clk_out_audio,irq_i2s_rx,irq_i2s_tx,irq_mm2s_audio,irq_s2mm_audio,lrclk_rx,lrclk_tx,m_axi_aclk,m_axi_aresetn,m_axi_mm2s_audio_araddr[63:0],m_axi_mm2s_audio_arburst[1:0],m_axi_mm2s_audio_arcache[3:0],m_axi_mm2s_audio_arlen[7:0],m_axi_mm2s_audio_arlock[0:0],m_axi_mm2s_audio_arprot[2:0],m_axi_mm2s_audio_arqos[3:0],m_axi_mm2s_audio_arready,m_axi_mm2s_audio_arregion[3:0],m_axi_mm2s_audio_arsize[2:0],m_axi_mm2s_audio_aruser[3:0],m_axi_mm2s_audio_arvalid,m_axi_mm2s_audio_rdata[31:0],m_axi_mm2s_audio_rlast,m_axi_mm2s_audio_rready,m_axi_mm2s_audio_rresp[1:0],m_axi_mm2s_audio_rvalid,m_axi_s2mm_audio_awaddr[63:0],m_axi_s2mm_audio_awburst[1:0],m_axi_s2mm_audio_awcache[3:0],m_axi_s2mm_audio_awlen[7:0],m_axi_s2mm_audio_awlock[0:0],m_axi_s2mm_audio_awprot[2:0],m_axi_s2mm_audio_awqos[3:0],m_axi_s2mm_audio_awready,m_axi_s2mm_audio_awregion[3:0],m_axi_s2mm_audio_awsize[2:0],m_axi_s2mm_audio_awuser[3:0],m_axi_s2mm_audio_awvalid,m_axi_s2mm_audio_bready,m_axi_s2mm_audio_bresp[1:0],m_axi_s2mm_audio_bvalid,m_axi_s2mm_audio_wdata[31:0],m_axi_s2mm_audio_wlast,m_axi_s2mm_audio_wready,m_axi_s2mm_audio_wstrb[3:0],m_axi_s2mm_audio_wvalid,mclk_out_rx,mclk_out_tx,peripheral_aresetn[0:0],pl_clk1,pl_rstn1,s_axi_ctrl_i2s_rx_araddr[39:0],s_axi_ctrl_i2s_rx_arready[0:0],s_axi_ctrl_i2s_rx_arvalid[0:0],s_axi_ctrl_i2s_rx_awaddr[39:0],s_axi_ctrl_i2s_rx_awready[0:0],s_axi_ctrl_i2s_rx_awvalid[0:0],s_axi_ctrl_i2s_rx_bready[0:0],s_axi_ctrl_i2s_rx_bresp[1:0],s_axi_ctrl_i2s_rx_bvalid[0:0],s_axi_ctrl_i2s_rx_rdata[31:0],s_axi_ctrl_i2s_rx_rready[0:0],s_axi_ctrl_i2s_rx_rresp[1:0],s_axi_ctrl_i2s_rx_rvalid[0:0],s_axi_ctrl_i2s_rx_wdata[31:0],s_axi_ctrl_i2s_rx_wready[0:0],s_axi_ctrl_i2s_rx_wvalid[0:0],s_axi_ctrl_i2s_tx_araddr[39:0],s_axi_ctrl_i2s_tx_arready[0:0],s_axi_ctrl_i2s_tx_arvalid[0:0],s_axi_ctrl_i2s_tx_awaddr[39:0],s_axi_ctrl_i2s_tx_awready[0:0],s_axi_ctrl_i2s_tx_awvalid[0:0],s_axi_ctrl_i2s_tx_bready[0:0],s_axi_ctrl_i2s_tx_bresp[1:0],s_axi_ctrl_i2s_tx_bvalid[0:0],s_axi_ctrl_i2s_tx_rdata[31:0],s_axi_ctrl_i2s_tx_rready[0:0],s_axi_ctrl_i2s_tx_rresp[1:0],s_axi_ctrl_i2s_tx_rvalid[0:0],s_axi_ctrl_i2s_tx_wdata[31:0],s_axi_ctrl_i2s_tx_wready[0:0],s_axi_ctrl_i2s_tx_wvalid[0:0],s_axi_lite_audio_fmt_araddr[39:0],s_axi_lite_audio_fmt_arready[0:0],s_axi_lite_audio_fmt_arvalid[0:0],s_axi_lite_audio_fmt_awaddr[39:0],s_axi_lite_audio_fmt_awready[0:0],s_axi_lite_audio_fmt_awvalid[0:0],s_axi_lite_audio_fmt_bready[0:0],s_axi_lite_audio_fmt_bresp[1:0],s_axi_lite_audio_fmt_bvalid[0:0],s_axi_lite_audio_fmt_rdata[31:0],s_axi_lite_audio_fmt_rready[0:0],s_axi_lite_audio_fmt_rresp[1:0],s_axi_lite_audio_fmt_rvalid[0:0],s_axi_lite_audio_fmt_wdata[31:0],s_axi_lite_audio_fmt_wready[0:0],s_axi_lite_audio_fmt_wvalid[0:0],sclk_rx,sclk_tx,sdata_rx,sdata_tx";
attribute X_CORE_INFO : string;
attribute X_CORE_INFO of stub : architecture is "aura_disabled_audio,Vivado 2022.2";
begin
end;
