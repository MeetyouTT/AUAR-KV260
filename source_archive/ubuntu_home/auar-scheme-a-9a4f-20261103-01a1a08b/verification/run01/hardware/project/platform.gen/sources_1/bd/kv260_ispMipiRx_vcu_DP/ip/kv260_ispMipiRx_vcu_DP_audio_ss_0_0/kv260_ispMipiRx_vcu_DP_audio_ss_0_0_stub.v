// Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
// --------------------------------------------------------------------------------
// Tool Version: Vivado v.2022.2 (lin64) Build 3671981 Fri Oct 14 04:59:54 MDT 2022
// Date        : Tue Nov  3 02:15:47 2026
// Host        : ghmd-MRA-XXX running 64-bit Ubuntu 20.04.4 LTS
// Command     : write_verilog -force -mode synth_stub
//               /home/ghmd/auar-scheme-a-9a4f-20261103-01a1a08b/verification/run01/hardware/project/platform.gen/sources_1/bd/kv260_ispMipiRx_vcu_DP/ip/kv260_ispMipiRx_vcu_DP_audio_ss_0_0/kv260_ispMipiRx_vcu_DP_audio_ss_0_0_stub.v
// Design      : kv260_ispMipiRx_vcu_DP_audio_ss_0_0
// Purpose     : Stub declaration of top-level module interface
// Device      : xck26-sfvc784-2LV-c
// --------------------------------------------------------------------------------

// This empty module with port declaration file causes synthesis tools to infer a black box for IP.
// The synthesis directives are for Synopsys Synplify support to prevent IO buffer insertion.
// Please paste the declaration into a Verilog source file or add the file as an additional source.
(* X_CORE_INFO = "aura_disabled_audio,Vivado 2022.2" *)
module kv260_ispMipiRx_vcu_DP_audio_ss_0_0(ACLK, ARESETN, clk_out_audio, irq_i2s_rx, 
  irq_i2s_tx, irq_mm2s_audio, irq_s2mm_audio, lrclk_rx, lrclk_tx, m_axi_aclk, m_axi_aresetn, 
  m_axi_mm2s_audio_araddr, m_axi_mm2s_audio_arburst, m_axi_mm2s_audio_arcache, 
  m_axi_mm2s_audio_arlen, m_axi_mm2s_audio_arlock, m_axi_mm2s_audio_arprot, 
  m_axi_mm2s_audio_arqos, m_axi_mm2s_audio_arready, m_axi_mm2s_audio_arregion, 
  m_axi_mm2s_audio_arsize, m_axi_mm2s_audio_aruser, m_axi_mm2s_audio_arvalid, 
  m_axi_mm2s_audio_rdata, m_axi_mm2s_audio_rlast, m_axi_mm2s_audio_rready, 
  m_axi_mm2s_audio_rresp, m_axi_mm2s_audio_rvalid, m_axi_s2mm_audio_awaddr, 
  m_axi_s2mm_audio_awburst, m_axi_s2mm_audio_awcache, m_axi_s2mm_audio_awlen, 
  m_axi_s2mm_audio_awlock, m_axi_s2mm_audio_awprot, m_axi_s2mm_audio_awqos, 
  m_axi_s2mm_audio_awready, m_axi_s2mm_audio_awregion, m_axi_s2mm_audio_awsize, 
  m_axi_s2mm_audio_awuser, m_axi_s2mm_audio_awvalid, m_axi_s2mm_audio_bready, 
  m_axi_s2mm_audio_bresp, m_axi_s2mm_audio_bvalid, m_axi_s2mm_audio_wdata, 
  m_axi_s2mm_audio_wlast, m_axi_s2mm_audio_wready, m_axi_s2mm_audio_wstrb, 
  m_axi_s2mm_audio_wvalid, mclk_out_rx, mclk_out_tx, peripheral_aresetn, pl_clk1, pl_rstn1, 
  s_axi_ctrl_i2s_rx_araddr, s_axi_ctrl_i2s_rx_arready, s_axi_ctrl_i2s_rx_arvalid, 
  s_axi_ctrl_i2s_rx_awaddr, s_axi_ctrl_i2s_rx_awready, s_axi_ctrl_i2s_rx_awvalid, 
  s_axi_ctrl_i2s_rx_bready, s_axi_ctrl_i2s_rx_bresp, s_axi_ctrl_i2s_rx_bvalid, 
  s_axi_ctrl_i2s_rx_rdata, s_axi_ctrl_i2s_rx_rready, s_axi_ctrl_i2s_rx_rresp, 
  s_axi_ctrl_i2s_rx_rvalid, s_axi_ctrl_i2s_rx_wdata, s_axi_ctrl_i2s_rx_wready, 
  s_axi_ctrl_i2s_rx_wvalid, s_axi_ctrl_i2s_tx_araddr, s_axi_ctrl_i2s_tx_arready, 
  s_axi_ctrl_i2s_tx_arvalid, s_axi_ctrl_i2s_tx_awaddr, s_axi_ctrl_i2s_tx_awready, 
  s_axi_ctrl_i2s_tx_awvalid, s_axi_ctrl_i2s_tx_bready, s_axi_ctrl_i2s_tx_bresp, 
  s_axi_ctrl_i2s_tx_bvalid, s_axi_ctrl_i2s_tx_rdata, s_axi_ctrl_i2s_tx_rready, 
  s_axi_ctrl_i2s_tx_rresp, s_axi_ctrl_i2s_tx_rvalid, s_axi_ctrl_i2s_tx_wdata, 
  s_axi_ctrl_i2s_tx_wready, s_axi_ctrl_i2s_tx_wvalid, s_axi_lite_audio_fmt_araddr, 
  s_axi_lite_audio_fmt_arready, s_axi_lite_audio_fmt_arvalid, 
  s_axi_lite_audio_fmt_awaddr, s_axi_lite_audio_fmt_awready, 
  s_axi_lite_audio_fmt_awvalid, s_axi_lite_audio_fmt_bready, 
  s_axi_lite_audio_fmt_bresp, s_axi_lite_audio_fmt_bvalid, s_axi_lite_audio_fmt_rdata, 
  s_axi_lite_audio_fmt_rready, s_axi_lite_audio_fmt_rresp, s_axi_lite_audio_fmt_rvalid, 
  s_axi_lite_audio_fmt_wdata, s_axi_lite_audio_fmt_wready, s_axi_lite_audio_fmt_wvalid, 
  sclk_rx, sclk_tx, sdata_rx, sdata_tx)
/* synthesis syn_black_box black_box_pad_pin="ACLK,ARESETN,clk_out_audio,irq_i2s_rx,irq_i2s_tx,irq_mm2s_audio,irq_s2mm_audio,lrclk_rx,lrclk_tx,m_axi_aclk,m_axi_aresetn,m_axi_mm2s_audio_araddr[63:0],m_axi_mm2s_audio_arburst[1:0],m_axi_mm2s_audio_arcache[3:0],m_axi_mm2s_audio_arlen[7:0],m_axi_mm2s_audio_arlock[0:0],m_axi_mm2s_audio_arprot[2:0],m_axi_mm2s_audio_arqos[3:0],m_axi_mm2s_audio_arready,m_axi_mm2s_audio_arregion[3:0],m_axi_mm2s_audio_arsize[2:0],m_axi_mm2s_audio_aruser[3:0],m_axi_mm2s_audio_arvalid,m_axi_mm2s_audio_rdata[31:0],m_axi_mm2s_audio_rlast,m_axi_mm2s_audio_rready,m_axi_mm2s_audio_rresp[1:0],m_axi_mm2s_audio_rvalid,m_axi_s2mm_audio_awaddr[63:0],m_axi_s2mm_audio_awburst[1:0],m_axi_s2mm_audio_awcache[3:0],m_axi_s2mm_audio_awlen[7:0],m_axi_s2mm_audio_awlock[0:0],m_axi_s2mm_audio_awprot[2:0],m_axi_s2mm_audio_awqos[3:0],m_axi_s2mm_audio_awready,m_axi_s2mm_audio_awregion[3:0],m_axi_s2mm_audio_awsize[2:0],m_axi_s2mm_audio_awuser[3:0],m_axi_s2mm_audio_awvalid,m_axi_s2mm_audio_bready,m_axi_s2mm_audio_bresp[1:0],m_axi_s2mm_audio_bvalid,m_axi_s2mm_audio_wdata[31:0],m_axi_s2mm_audio_wlast,m_axi_s2mm_audio_wready,m_axi_s2mm_audio_wstrb[3:0],m_axi_s2mm_audio_wvalid,mclk_out_rx,mclk_out_tx,peripheral_aresetn[0:0],pl_clk1,pl_rstn1,s_axi_ctrl_i2s_rx_araddr[39:0],s_axi_ctrl_i2s_rx_arready[0:0],s_axi_ctrl_i2s_rx_arvalid[0:0],s_axi_ctrl_i2s_rx_awaddr[39:0],s_axi_ctrl_i2s_rx_awready[0:0],s_axi_ctrl_i2s_rx_awvalid[0:0],s_axi_ctrl_i2s_rx_bready[0:0],s_axi_ctrl_i2s_rx_bresp[1:0],s_axi_ctrl_i2s_rx_bvalid[0:0],s_axi_ctrl_i2s_rx_rdata[31:0],s_axi_ctrl_i2s_rx_rready[0:0],s_axi_ctrl_i2s_rx_rresp[1:0],s_axi_ctrl_i2s_rx_rvalid[0:0],s_axi_ctrl_i2s_rx_wdata[31:0],s_axi_ctrl_i2s_rx_wready[0:0],s_axi_ctrl_i2s_rx_wvalid[0:0],s_axi_ctrl_i2s_tx_araddr[39:0],s_axi_ctrl_i2s_tx_arready[0:0],s_axi_ctrl_i2s_tx_arvalid[0:0],s_axi_ctrl_i2s_tx_awaddr[39:0],s_axi_ctrl_i2s_tx_awready[0:0],s_axi_ctrl_i2s_tx_awvalid[0:0],s_axi_ctrl_i2s_tx_bready[0:0],s_axi_ctrl_i2s_tx_bresp[1:0],s_axi_ctrl_i2s_tx_bvalid[0:0],s_axi_ctrl_i2s_tx_rdata[31:0],s_axi_ctrl_i2s_tx_rready[0:0],s_axi_ctrl_i2s_tx_rresp[1:0],s_axi_ctrl_i2s_tx_rvalid[0:0],s_axi_ctrl_i2s_tx_wdata[31:0],s_axi_ctrl_i2s_tx_wready[0:0],s_axi_ctrl_i2s_tx_wvalid[0:0],s_axi_lite_audio_fmt_araddr[39:0],s_axi_lite_audio_fmt_arready[0:0],s_axi_lite_audio_fmt_arvalid[0:0],s_axi_lite_audio_fmt_awaddr[39:0],s_axi_lite_audio_fmt_awready[0:0],s_axi_lite_audio_fmt_awvalid[0:0],s_axi_lite_audio_fmt_bready[0:0],s_axi_lite_audio_fmt_bresp[1:0],s_axi_lite_audio_fmt_bvalid[0:0],s_axi_lite_audio_fmt_rdata[31:0],s_axi_lite_audio_fmt_rready[0:0],s_axi_lite_audio_fmt_rresp[1:0],s_axi_lite_audio_fmt_rvalid[0:0],s_axi_lite_audio_fmt_wdata[31:0],s_axi_lite_audio_fmt_wready[0:0],s_axi_lite_audio_fmt_wvalid[0:0],sclk_rx,sclk_tx,sdata_rx,sdata_tx" */;
  input ACLK;
  input ARESETN;
  output clk_out_audio;
  output irq_i2s_rx;
  output irq_i2s_tx;
  output irq_mm2s_audio;
  output irq_s2mm_audio;
  output lrclk_rx;
  output lrclk_tx;
  input m_axi_aclk;
  input m_axi_aresetn;
  output [63:0]m_axi_mm2s_audio_araddr;
  output [1:0]m_axi_mm2s_audio_arburst;
  output [3:0]m_axi_mm2s_audio_arcache;
  output [7:0]m_axi_mm2s_audio_arlen;
  output [0:0]m_axi_mm2s_audio_arlock;
  output [2:0]m_axi_mm2s_audio_arprot;
  output [3:0]m_axi_mm2s_audio_arqos;
  input m_axi_mm2s_audio_arready;
  output [3:0]m_axi_mm2s_audio_arregion;
  output [2:0]m_axi_mm2s_audio_arsize;
  output [3:0]m_axi_mm2s_audio_aruser;
  output m_axi_mm2s_audio_arvalid;
  input [31:0]m_axi_mm2s_audio_rdata;
  input m_axi_mm2s_audio_rlast;
  output m_axi_mm2s_audio_rready;
  input [1:0]m_axi_mm2s_audio_rresp;
  input m_axi_mm2s_audio_rvalid;
  output [63:0]m_axi_s2mm_audio_awaddr;
  output [1:0]m_axi_s2mm_audio_awburst;
  output [3:0]m_axi_s2mm_audio_awcache;
  output [7:0]m_axi_s2mm_audio_awlen;
  output [0:0]m_axi_s2mm_audio_awlock;
  output [2:0]m_axi_s2mm_audio_awprot;
  output [3:0]m_axi_s2mm_audio_awqos;
  input m_axi_s2mm_audio_awready;
  output [3:0]m_axi_s2mm_audio_awregion;
  output [2:0]m_axi_s2mm_audio_awsize;
  output [3:0]m_axi_s2mm_audio_awuser;
  output m_axi_s2mm_audio_awvalid;
  output m_axi_s2mm_audio_bready;
  input [1:0]m_axi_s2mm_audio_bresp;
  input m_axi_s2mm_audio_bvalid;
  output [31:0]m_axi_s2mm_audio_wdata;
  output m_axi_s2mm_audio_wlast;
  input m_axi_s2mm_audio_wready;
  output [3:0]m_axi_s2mm_audio_wstrb;
  output m_axi_s2mm_audio_wvalid;
  output mclk_out_rx;
  output mclk_out_tx;
  output [0:0]peripheral_aresetn;
  input pl_clk1;
  input pl_rstn1;
  input [39:0]s_axi_ctrl_i2s_rx_araddr;
  output [0:0]s_axi_ctrl_i2s_rx_arready;
  input [0:0]s_axi_ctrl_i2s_rx_arvalid;
  input [39:0]s_axi_ctrl_i2s_rx_awaddr;
  output [0:0]s_axi_ctrl_i2s_rx_awready;
  input [0:0]s_axi_ctrl_i2s_rx_awvalid;
  input [0:0]s_axi_ctrl_i2s_rx_bready;
  output [1:0]s_axi_ctrl_i2s_rx_bresp;
  output [0:0]s_axi_ctrl_i2s_rx_bvalid;
  output [31:0]s_axi_ctrl_i2s_rx_rdata;
  input [0:0]s_axi_ctrl_i2s_rx_rready;
  output [1:0]s_axi_ctrl_i2s_rx_rresp;
  output [0:0]s_axi_ctrl_i2s_rx_rvalid;
  input [31:0]s_axi_ctrl_i2s_rx_wdata;
  output [0:0]s_axi_ctrl_i2s_rx_wready;
  input [0:0]s_axi_ctrl_i2s_rx_wvalid;
  input [39:0]s_axi_ctrl_i2s_tx_araddr;
  output [0:0]s_axi_ctrl_i2s_tx_arready;
  input [0:0]s_axi_ctrl_i2s_tx_arvalid;
  input [39:0]s_axi_ctrl_i2s_tx_awaddr;
  output [0:0]s_axi_ctrl_i2s_tx_awready;
  input [0:0]s_axi_ctrl_i2s_tx_awvalid;
  input [0:0]s_axi_ctrl_i2s_tx_bready;
  output [1:0]s_axi_ctrl_i2s_tx_bresp;
  output [0:0]s_axi_ctrl_i2s_tx_bvalid;
  output [31:0]s_axi_ctrl_i2s_tx_rdata;
  input [0:0]s_axi_ctrl_i2s_tx_rready;
  output [1:0]s_axi_ctrl_i2s_tx_rresp;
  output [0:0]s_axi_ctrl_i2s_tx_rvalid;
  input [31:0]s_axi_ctrl_i2s_tx_wdata;
  output [0:0]s_axi_ctrl_i2s_tx_wready;
  input [0:0]s_axi_ctrl_i2s_tx_wvalid;
  input [39:0]s_axi_lite_audio_fmt_araddr;
  output [0:0]s_axi_lite_audio_fmt_arready;
  input [0:0]s_axi_lite_audio_fmt_arvalid;
  input [39:0]s_axi_lite_audio_fmt_awaddr;
  output [0:0]s_axi_lite_audio_fmt_awready;
  input [0:0]s_axi_lite_audio_fmt_awvalid;
  input [0:0]s_axi_lite_audio_fmt_bready;
  output [1:0]s_axi_lite_audio_fmt_bresp;
  output [0:0]s_axi_lite_audio_fmt_bvalid;
  output [31:0]s_axi_lite_audio_fmt_rdata;
  input [0:0]s_axi_lite_audio_fmt_rready;
  output [1:0]s_axi_lite_audio_fmt_rresp;
  output [0:0]s_axi_lite_audio_fmt_rvalid;
  input [31:0]s_axi_lite_audio_fmt_wdata;
  output [0:0]s_axi_lite_audio_fmt_wready;
  input [0:0]s_axi_lite_audio_fmt_wvalid;
  output sclk_rx;
  output sclk_tx;
  input sdata_rx;
  output sdata_tx;
endmodule
