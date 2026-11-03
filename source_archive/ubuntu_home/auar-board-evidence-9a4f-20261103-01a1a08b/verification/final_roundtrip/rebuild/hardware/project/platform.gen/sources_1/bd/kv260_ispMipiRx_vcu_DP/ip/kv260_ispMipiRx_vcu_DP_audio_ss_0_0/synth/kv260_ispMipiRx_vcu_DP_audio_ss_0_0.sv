// (c) Copyright 1995-2026 Xilinx, Inc. All rights reserved.
// 
// This file contains confidential and proprietary information
// of Xilinx, Inc. and is protected under U.S. and
// international copyright and other intellectual property
// laws.
// 
// DISCLAIMER
// This disclaimer is not a license and does not grant any
// rights to the materials distributed herewith. Except as
// otherwise provided in a valid license issued to you by
// Xilinx, and to the maximum extent permitted by applicable
// law: (1) THESE MATERIALS ARE MADE AVAILABLE "AS IS" AND
// WITH ALL FAULTS, AND XILINX HEREBY DISCLAIMS ALL WARRANTIES
// AND CONDITIONS, EXPRESS, IMPLIED, OR STATUTORY, INCLUDING
// BUT NOT LIMITED TO WARRANTIES OF MERCHANTABILITY, NON-
// INFRINGEMENT, OR FITNESS FOR ANY PARTICULAR PURPOSE; and
// (2) Xilinx shall not be liable (whether in contract or tort,
// including negligence, or under any other theory of
// liability) for any loss or damage of any kind or nature
// related to, arising under or in connection with these
// materials, including for any direct, or any indirect,
// special, incidental, or consequential loss or damage
// (including loss of data, profits, goodwill, or any type of
// loss or damage suffered as a result of any action brought
// by a third party) even if such damage or loss was
// reasonably foreseeable or Xilinx had been advised of the
// possibility of the same.
// 
// CRITICAL APPLICATIONS
// Xilinx products are not designed or intended to be fail-
// safe, or for use in any application requiring fail-safe
// performance, such as life-support or safety devices or
// systems, Class III medical devices, nuclear facilities,
// applications related to the deployment of airbags, or any
// other applications that could lead to death, personal
// injury, or severe property or environmental damage
// (individually and collectively, "Critical
// Applications"). Customer assumes the sole risk and
// liability of any use of Xilinx products in Critical
// Applications, subject only to applicable laws and
// regulations governing limitations on product liability.
// 
// THIS COPYRIGHT NOTICE AND DISCLAIMER MUST BE RETAINED AS
// PART OF THIS FILE AT ALL TIMES.
// 
// DO NOT MODIFY THIS FILE.


// IP VLNV: aura.local:user:aura_disabled_audio:1.0
// IP Revision: 1

(* X_CORE_INFO = "aura_disabled_audio,Vivado 2022.2" *)
(* CHECK_LICENSE_TYPE = "kv260_ispMipiRx_vcu_DP_audio_ss_0_0,aura_disabled_audio,{}" *)
(* IP_DEFINITION_SOURCE = "package_project" *)
(* DowngradeIPIdentifiedWarnings = "yes" *)
module kv260_ispMipiRx_vcu_DP_audio_ss_0_0 (
  ACLK,
  ARESETN,
  clk_out_audio,
  irq_i2s_rx,
  irq_i2s_tx,
  irq_mm2s_audio,
  irq_s2mm_audio,
  lrclk_rx,
  lrclk_tx,
  m_axi_aclk,
  m_axi_aresetn,
  m_axi_mm2s_audio_araddr,
  m_axi_mm2s_audio_arburst,
  m_axi_mm2s_audio_arcache,
  m_axi_mm2s_audio_arlen,
  m_axi_mm2s_audio_arlock,
  m_axi_mm2s_audio_arprot,
  m_axi_mm2s_audio_arqos,
  m_axi_mm2s_audio_arready,
  m_axi_mm2s_audio_arregion,
  m_axi_mm2s_audio_arsize,
  m_axi_mm2s_audio_aruser,
  m_axi_mm2s_audio_arvalid,
  m_axi_mm2s_audio_rdata,
  m_axi_mm2s_audio_rlast,
  m_axi_mm2s_audio_rready,
  m_axi_mm2s_audio_rresp,
  m_axi_mm2s_audio_rvalid,
  m_axi_s2mm_audio_awaddr,
  m_axi_s2mm_audio_awburst,
  m_axi_s2mm_audio_awcache,
  m_axi_s2mm_audio_awlen,
  m_axi_s2mm_audio_awlock,
  m_axi_s2mm_audio_awprot,
  m_axi_s2mm_audio_awqos,
  m_axi_s2mm_audio_awready,
  m_axi_s2mm_audio_awregion,
  m_axi_s2mm_audio_awsize,
  m_axi_s2mm_audio_awuser,
  m_axi_s2mm_audio_awvalid,
  m_axi_s2mm_audio_bready,
  m_axi_s2mm_audio_bresp,
  m_axi_s2mm_audio_bvalid,
  m_axi_s2mm_audio_wdata,
  m_axi_s2mm_audio_wlast,
  m_axi_s2mm_audio_wready,
  m_axi_s2mm_audio_wstrb,
  m_axi_s2mm_audio_wvalid,
  mclk_out_rx,
  mclk_out_tx,
  peripheral_aresetn,
  pl_clk1,
  pl_rstn1,
  s_axi_ctrl_i2s_rx_araddr,
  s_axi_ctrl_i2s_rx_arready,
  s_axi_ctrl_i2s_rx_arvalid,
  s_axi_ctrl_i2s_rx_awaddr,
  s_axi_ctrl_i2s_rx_awready,
  s_axi_ctrl_i2s_rx_awvalid,
  s_axi_ctrl_i2s_rx_bready,
  s_axi_ctrl_i2s_rx_bresp,
  s_axi_ctrl_i2s_rx_bvalid,
  s_axi_ctrl_i2s_rx_rdata,
  s_axi_ctrl_i2s_rx_rready,
  s_axi_ctrl_i2s_rx_rresp,
  s_axi_ctrl_i2s_rx_rvalid,
  s_axi_ctrl_i2s_rx_wdata,
  s_axi_ctrl_i2s_rx_wready,
  s_axi_ctrl_i2s_rx_wvalid,
  s_axi_ctrl_i2s_tx_araddr,
  s_axi_ctrl_i2s_tx_arready,
  s_axi_ctrl_i2s_tx_arvalid,
  s_axi_ctrl_i2s_tx_awaddr,
  s_axi_ctrl_i2s_tx_awready,
  s_axi_ctrl_i2s_tx_awvalid,
  s_axi_ctrl_i2s_tx_bready,
  s_axi_ctrl_i2s_tx_bresp,
  s_axi_ctrl_i2s_tx_bvalid,
  s_axi_ctrl_i2s_tx_rdata,
  s_axi_ctrl_i2s_tx_rready,
  s_axi_ctrl_i2s_tx_rresp,
  s_axi_ctrl_i2s_tx_rvalid,
  s_axi_ctrl_i2s_tx_wdata,
  s_axi_ctrl_i2s_tx_wready,
  s_axi_ctrl_i2s_tx_wvalid,
  s_axi_lite_audio_fmt_araddr,
  s_axi_lite_audio_fmt_arready,
  s_axi_lite_audio_fmt_arvalid,
  s_axi_lite_audio_fmt_awaddr,
  s_axi_lite_audio_fmt_awready,
  s_axi_lite_audio_fmt_awvalid,
  s_axi_lite_audio_fmt_bready,
  s_axi_lite_audio_fmt_bresp,
  s_axi_lite_audio_fmt_bvalid,
  s_axi_lite_audio_fmt_rdata,
  s_axi_lite_audio_fmt_rready,
  s_axi_lite_audio_fmt_rresp,
  s_axi_lite_audio_fmt_rvalid,
  s_axi_lite_audio_fmt_wdata,
  s_axi_lite_audio_fmt_wready,
  s_axi_lite_audio_fmt_wvalid,
  sclk_rx,
  sclk_tx,
  sdata_rx,
  sdata_tx
);

(* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ACLK, ASSOCIATED_BUSIF s_axi_ctrl_i2s_rx:s_axi_ctrl_i2s_tx:s_axi_lite_audio_fmt, ASSOCIATED_RESET ARESETN, FREQ_HZ 99999000, FREQ_TOLERANCE_HZ 0, PHASE 0.0, CLK_DOMAIN kv260_ispMipiRx_vcu_DP_clk_wiz_0_0_clk_200M, INSERT_VIP 0" *)
(* X_INTERFACE_INFO = "xilinx.com:signal:clock:1.0 ACLK CLK" *)
input wire ACLK;
(* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ARESETN, POLARITY ACTIVE_LOW, INSERT_VIP 0" *)
(* X_INTERFACE_INFO = "xilinx.com:signal:reset:1.0 ARESETN RST" *)
input wire ARESETN;
output wire clk_out_audio;
output wire irq_i2s_rx;
output wire irq_i2s_tx;
output wire irq_mm2s_audio;
output wire irq_s2mm_audio;
output wire lrclk_rx;
output wire lrclk_tx;
(* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME m_axi_aclk, ASSOCIATED_RESET m_axi_aresetn, ASSOCIATED_BUSIF m_axi_mm2s_audio:m_axi_s2mm_audio, FREQ_HZ 299997000, FREQ_TOLERANCE_HZ 0, PHASE 0.0, CLK_DOMAIN kv260_ispMipiRx_vcu_DP_clk_wiz_0_0_clk_200M, INSERT_VIP 0" *)
(* X_INTERFACE_INFO = "xilinx.com:signal:clock:1.0 m_axi_aclk CLK" *)
input wire m_axi_aclk;
(* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME m_axi_aresetn, POLARITY ACTIVE_LOW, INSERT_VIP 0" *)
(* X_INTERFACE_INFO = "xilinx.com:signal:reset:1.0 m_axi_aresetn RST" *)
input wire m_axi_aresetn;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio ARADDR" *)
output wire [63 : 0] m_axi_mm2s_audio_araddr;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio ARBURST" *)
output wire [1 : 0] m_axi_mm2s_audio_arburst;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio ARCACHE" *)
output wire [3 : 0] m_axi_mm2s_audio_arcache;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio ARLEN" *)
output wire [7 : 0] m_axi_mm2s_audio_arlen;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio ARLOCK" *)
output wire [0 : 0] m_axi_mm2s_audio_arlock;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio ARPROT" *)
output wire [2 : 0] m_axi_mm2s_audio_arprot;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio ARQOS" *)
output wire [3 : 0] m_axi_mm2s_audio_arqos;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio ARREADY" *)
input wire m_axi_mm2s_audio_arready;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio ARREGION" *)
output wire [3 : 0] m_axi_mm2s_audio_arregion;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio ARSIZE" *)
output wire [2 : 0] m_axi_mm2s_audio_arsize;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio ARUSER" *)
output wire [3 : 0] m_axi_mm2s_audio_aruser;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio ARVALID" *)
output wire m_axi_mm2s_audio_arvalid;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio RDATA" *)
input wire [31 : 0] m_axi_mm2s_audio_rdata;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio RLAST" *)
input wire m_axi_mm2s_audio_rlast;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio RREADY" *)
output wire m_axi_mm2s_audio_rready;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio RRESP" *)
input wire [1 : 0] m_axi_mm2s_audio_rresp;
(* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME m_axi_mm2s_audio, PROTOCOL AXI4, READ_WRITE_MODE READ_ONLY, DATA_WIDTH 32, FREQ_HZ 299997000, ID_WIDTH 0, ADDR_WIDTH 64, AWUSER_WIDTH 0, ARUSER_WIDTH 4, WUSER_WIDTH 0, RUSER_WIDTH 0, BUSER_WIDTH 0, HAS_BURST 1, HAS_LOCK 1, HAS_PROT 1, HAS_CACHE 1, HAS_QOS 1, HAS_REGION 1, HAS_WSTRB 0, HAS_BRESP 0, HAS_RRESP 1, SUPPORTS_NARROW_BURST 1, NUM_READ_OUTSTANDING 2, NUM_WRITE_OUTSTANDING 2, MAX_BURST_LENGTH 256, PHASE 0.0, CLK_DOMAIN kv260_ispMipiRx_vcu_DP_clk_wiz_0_0_clk_200M, NUM_REA\
D_THREADS 1, NUM_WRITE_THREADS 1, RUSER_BITS_PER_BYTE 0, WUSER_BITS_PER_BYTE 0, INSERT_VIP 0" *)
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio RVALID" *)
input wire m_axi_mm2s_audio_rvalid;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio AWADDR" *)
output wire [63 : 0] m_axi_s2mm_audio_awaddr;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio AWBURST" *)
output wire [1 : 0] m_axi_s2mm_audio_awburst;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio AWCACHE" *)
output wire [3 : 0] m_axi_s2mm_audio_awcache;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio AWLEN" *)
output wire [7 : 0] m_axi_s2mm_audio_awlen;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio AWLOCK" *)
output wire [0 : 0] m_axi_s2mm_audio_awlock;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio AWPROT" *)
output wire [2 : 0] m_axi_s2mm_audio_awprot;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio AWQOS" *)
output wire [3 : 0] m_axi_s2mm_audio_awqos;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio AWREADY" *)
input wire m_axi_s2mm_audio_awready;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio AWREGION" *)
output wire [3 : 0] m_axi_s2mm_audio_awregion;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio AWSIZE" *)
output wire [2 : 0] m_axi_s2mm_audio_awsize;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio AWUSER" *)
output wire [3 : 0] m_axi_s2mm_audio_awuser;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio AWVALID" *)
output wire m_axi_s2mm_audio_awvalid;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio BREADY" *)
output wire m_axi_s2mm_audio_bready;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio BRESP" *)
input wire [1 : 0] m_axi_s2mm_audio_bresp;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio BVALID" *)
input wire m_axi_s2mm_audio_bvalid;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio WDATA" *)
output wire [31 : 0] m_axi_s2mm_audio_wdata;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio WLAST" *)
output wire m_axi_s2mm_audio_wlast;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio WREADY" *)
input wire m_axi_s2mm_audio_wready;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio WSTRB" *)
output wire [3 : 0] m_axi_s2mm_audio_wstrb;
(* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME m_axi_s2mm_audio, PROTOCOL AXI4, READ_WRITE_MODE WRITE_ONLY, DATA_WIDTH 32, FREQ_HZ 299997000, ID_WIDTH 0, ADDR_WIDTH 64, AWUSER_WIDTH 4, ARUSER_WIDTH 0, WUSER_WIDTH 0, RUSER_WIDTH 0, BUSER_WIDTH 0, HAS_BURST 1, HAS_LOCK 1, HAS_PROT 1, HAS_CACHE 1, HAS_QOS 1, HAS_REGION 1, HAS_WSTRB 1, HAS_BRESP 1, HAS_RRESP 0, SUPPORTS_NARROW_BURST 1, NUM_READ_OUTSTANDING 2, NUM_WRITE_OUTSTANDING 2, MAX_BURST_LENGTH 256, PHASE 0.0, CLK_DOMAIN kv260_ispMipiRx_vcu_DP_clk_wiz_0_0_clk_200M, NUM_RE\
AD_THREADS 1, NUM_WRITE_THREADS 1, RUSER_BITS_PER_BYTE 0, WUSER_BITS_PER_BYTE 0, INSERT_VIP 0" *)
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio WVALID" *)
output wire m_axi_s2mm_audio_wvalid;
output wire mclk_out_rx;
output wire mclk_out_tx;
(* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME peripheral_aresetn, POLARITY ACTIVE_LOW, INSERT_VIP 0" *)
(* X_INTERFACE_INFO = "xilinx.com:signal:reset:1.0 peripheral_aresetn RST" *)
output wire [0 : 0] peripheral_aresetn;
input wire pl_clk1;
input wire pl_rstn1;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx ARADDR" *)
input wire [39 : 0] s_axi_ctrl_i2s_rx_araddr;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx ARREADY" *)
output wire [0 : 0] s_axi_ctrl_i2s_rx_arready;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx ARVALID" *)
input wire [0 : 0] s_axi_ctrl_i2s_rx_arvalid;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx AWADDR" *)
input wire [39 : 0] s_axi_ctrl_i2s_rx_awaddr;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx AWREADY" *)
output wire [0 : 0] s_axi_ctrl_i2s_rx_awready;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx AWVALID" *)
input wire [0 : 0] s_axi_ctrl_i2s_rx_awvalid;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx BREADY" *)
input wire [0 : 0] s_axi_ctrl_i2s_rx_bready;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx BRESP" *)
output wire [1 : 0] s_axi_ctrl_i2s_rx_bresp;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx BVALID" *)
output wire [0 : 0] s_axi_ctrl_i2s_rx_bvalid;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx RDATA" *)
output wire [31 : 0] s_axi_ctrl_i2s_rx_rdata;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx RREADY" *)
input wire [0 : 0] s_axi_ctrl_i2s_rx_rready;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx RRESP" *)
output wire [1 : 0] s_axi_ctrl_i2s_rx_rresp;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx RVALID" *)
output wire [0 : 0] s_axi_ctrl_i2s_rx_rvalid;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx WDATA" *)
input wire [31 : 0] s_axi_ctrl_i2s_rx_wdata;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx WREADY" *)
output wire [0 : 0] s_axi_ctrl_i2s_rx_wready;
(* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME s_axi_ctrl_i2s_rx, PROTOCOL AXI4LITE, READ_WRITE_MODE READ_WRITE, DATA_WIDTH 32, FREQ_HZ 99999000, ID_WIDTH 0, ADDR_WIDTH 40, AWUSER_WIDTH 0, ARUSER_WIDTH 0, WUSER_WIDTH 0, RUSER_WIDTH 0, BUSER_WIDTH 0, HAS_BURST 0, HAS_LOCK 0, HAS_PROT 0, HAS_CACHE 0, HAS_QOS 0, HAS_REGION 0, HAS_WSTRB 0, HAS_BRESP 1, HAS_RRESP 1, SUPPORTS_NARROW_BURST 0, NUM_READ_OUTSTANDING 1, NUM_WRITE_OUTSTANDING 1, MAX_BURST_LENGTH 1, PHASE 0.0, CLK_DOMAIN kv260_ispMipiRx_vcu_DP_clk_wiz_0_0_clk_200M, NUM_\
READ_THREADS 1, NUM_WRITE_THREADS 1, RUSER_BITS_PER_BYTE 0, WUSER_BITS_PER_BYTE 0, INSERT_VIP 0" *)
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx WVALID" *)
input wire [0 : 0] s_axi_ctrl_i2s_rx_wvalid;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx ARADDR" *)
input wire [39 : 0] s_axi_ctrl_i2s_tx_araddr;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx ARREADY" *)
output wire [0 : 0] s_axi_ctrl_i2s_tx_arready;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx ARVALID" *)
input wire [0 : 0] s_axi_ctrl_i2s_tx_arvalid;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx AWADDR" *)
input wire [39 : 0] s_axi_ctrl_i2s_tx_awaddr;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx AWREADY" *)
output wire [0 : 0] s_axi_ctrl_i2s_tx_awready;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx AWVALID" *)
input wire [0 : 0] s_axi_ctrl_i2s_tx_awvalid;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx BREADY" *)
input wire [0 : 0] s_axi_ctrl_i2s_tx_bready;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx BRESP" *)
output wire [1 : 0] s_axi_ctrl_i2s_tx_bresp;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx BVALID" *)
output wire [0 : 0] s_axi_ctrl_i2s_tx_bvalid;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx RDATA" *)
output wire [31 : 0] s_axi_ctrl_i2s_tx_rdata;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx RREADY" *)
input wire [0 : 0] s_axi_ctrl_i2s_tx_rready;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx RRESP" *)
output wire [1 : 0] s_axi_ctrl_i2s_tx_rresp;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx RVALID" *)
output wire [0 : 0] s_axi_ctrl_i2s_tx_rvalid;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx WDATA" *)
input wire [31 : 0] s_axi_ctrl_i2s_tx_wdata;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx WREADY" *)
output wire [0 : 0] s_axi_ctrl_i2s_tx_wready;
(* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME s_axi_ctrl_i2s_tx, PROTOCOL AXI4LITE, READ_WRITE_MODE READ_WRITE, DATA_WIDTH 32, FREQ_HZ 99999000, ID_WIDTH 0, ADDR_WIDTH 40, AWUSER_WIDTH 0, ARUSER_WIDTH 0, WUSER_WIDTH 0, RUSER_WIDTH 0, BUSER_WIDTH 0, HAS_BURST 0, HAS_LOCK 0, HAS_PROT 0, HAS_CACHE 0, HAS_QOS 0, HAS_REGION 0, HAS_WSTRB 0, HAS_BRESP 1, HAS_RRESP 1, SUPPORTS_NARROW_BURST 0, NUM_READ_OUTSTANDING 1, NUM_WRITE_OUTSTANDING 1, MAX_BURST_LENGTH 1, PHASE 0.0, CLK_DOMAIN kv260_ispMipiRx_vcu_DP_clk_wiz_0_0_clk_200M, NUM_\
READ_THREADS 1, NUM_WRITE_THREADS 1, RUSER_BITS_PER_BYTE 0, WUSER_BITS_PER_BYTE 0, INSERT_VIP 0" *)
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx WVALID" *)
input wire [0 : 0] s_axi_ctrl_i2s_tx_wvalid;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt ARADDR" *)
input wire [39 : 0] s_axi_lite_audio_fmt_araddr;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt ARREADY" *)
output wire [0 : 0] s_axi_lite_audio_fmt_arready;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt ARVALID" *)
input wire [0 : 0] s_axi_lite_audio_fmt_arvalid;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt AWADDR" *)
input wire [39 : 0] s_axi_lite_audio_fmt_awaddr;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt AWREADY" *)
output wire [0 : 0] s_axi_lite_audio_fmt_awready;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt AWVALID" *)
input wire [0 : 0] s_axi_lite_audio_fmt_awvalid;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt BREADY" *)
input wire [0 : 0] s_axi_lite_audio_fmt_bready;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt BRESP" *)
output wire [1 : 0] s_axi_lite_audio_fmt_bresp;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt BVALID" *)
output wire [0 : 0] s_axi_lite_audio_fmt_bvalid;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt RDATA" *)
output wire [31 : 0] s_axi_lite_audio_fmt_rdata;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt RREADY" *)
input wire [0 : 0] s_axi_lite_audio_fmt_rready;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt RRESP" *)
output wire [1 : 0] s_axi_lite_audio_fmt_rresp;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt RVALID" *)
output wire [0 : 0] s_axi_lite_audio_fmt_rvalid;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt WDATA" *)
input wire [31 : 0] s_axi_lite_audio_fmt_wdata;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt WREADY" *)
output wire [0 : 0] s_axi_lite_audio_fmt_wready;
(* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME s_axi_lite_audio_fmt, PROTOCOL AXI4LITE, READ_WRITE_MODE READ_WRITE, DATA_WIDTH 32, FREQ_HZ 99999000, ID_WIDTH 0, ADDR_WIDTH 40, AWUSER_WIDTH 0, ARUSER_WIDTH 0, WUSER_WIDTH 0, RUSER_WIDTH 0, BUSER_WIDTH 0, HAS_BURST 0, HAS_LOCK 0, HAS_PROT 0, HAS_CACHE 0, HAS_QOS 0, HAS_REGION 0, HAS_WSTRB 0, HAS_BRESP 1, HAS_RRESP 1, SUPPORTS_NARROW_BURST 0, NUM_READ_OUTSTANDING 1, NUM_WRITE_OUTSTANDING 1, MAX_BURST_LENGTH 1, PHASE 0.0, CLK_DOMAIN kv260_ispMipiRx_vcu_DP_clk_wiz_0_0_clk_200M, N\
UM_READ_THREADS 1, NUM_WRITE_THREADS 1, RUSER_BITS_PER_BYTE 0, WUSER_BITS_PER_BYTE 0, INSERT_VIP 0" *)
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt WVALID" *)
input wire [0 : 0] s_axi_lite_audio_fmt_wvalid;
output wire sclk_rx;
output wire sclk_tx;
input wire sdata_rx;
output wire sdata_tx;

  aura_disabled_audio inst (
    .ACLK(ACLK),
    .ARESETN(ARESETN),
    .clk_out_audio(clk_out_audio),
    .irq_i2s_rx(irq_i2s_rx),
    .irq_i2s_tx(irq_i2s_tx),
    .irq_mm2s_audio(irq_mm2s_audio),
    .irq_s2mm_audio(irq_s2mm_audio),
    .lrclk_rx(lrclk_rx),
    .lrclk_tx(lrclk_tx),
    .m_axi_aclk(m_axi_aclk),
    .m_axi_aresetn(m_axi_aresetn),
    .m_axi_mm2s_audio_araddr(m_axi_mm2s_audio_araddr),
    .m_axi_mm2s_audio_arburst(m_axi_mm2s_audio_arburst),
    .m_axi_mm2s_audio_arcache(m_axi_mm2s_audio_arcache),
    .m_axi_mm2s_audio_arlen(m_axi_mm2s_audio_arlen),
    .m_axi_mm2s_audio_arlock(m_axi_mm2s_audio_arlock),
    .m_axi_mm2s_audio_arprot(m_axi_mm2s_audio_arprot),
    .m_axi_mm2s_audio_arqos(m_axi_mm2s_audio_arqos),
    .m_axi_mm2s_audio_arready(m_axi_mm2s_audio_arready),
    .m_axi_mm2s_audio_arregion(m_axi_mm2s_audio_arregion),
    .m_axi_mm2s_audio_arsize(m_axi_mm2s_audio_arsize),
    .m_axi_mm2s_audio_aruser(m_axi_mm2s_audio_aruser),
    .m_axi_mm2s_audio_arvalid(m_axi_mm2s_audio_arvalid),
    .m_axi_mm2s_audio_rdata(m_axi_mm2s_audio_rdata),
    .m_axi_mm2s_audio_rlast(m_axi_mm2s_audio_rlast),
    .m_axi_mm2s_audio_rready(m_axi_mm2s_audio_rready),
    .m_axi_mm2s_audio_rresp(m_axi_mm2s_audio_rresp),
    .m_axi_mm2s_audio_rvalid(m_axi_mm2s_audio_rvalid),
    .m_axi_s2mm_audio_awaddr(m_axi_s2mm_audio_awaddr),
    .m_axi_s2mm_audio_awburst(m_axi_s2mm_audio_awburst),
    .m_axi_s2mm_audio_awcache(m_axi_s2mm_audio_awcache),
    .m_axi_s2mm_audio_awlen(m_axi_s2mm_audio_awlen),
    .m_axi_s2mm_audio_awlock(m_axi_s2mm_audio_awlock),
    .m_axi_s2mm_audio_awprot(m_axi_s2mm_audio_awprot),
    .m_axi_s2mm_audio_awqos(m_axi_s2mm_audio_awqos),
    .m_axi_s2mm_audio_awready(m_axi_s2mm_audio_awready),
    .m_axi_s2mm_audio_awregion(m_axi_s2mm_audio_awregion),
    .m_axi_s2mm_audio_awsize(m_axi_s2mm_audio_awsize),
    .m_axi_s2mm_audio_awuser(m_axi_s2mm_audio_awuser),
    .m_axi_s2mm_audio_awvalid(m_axi_s2mm_audio_awvalid),
    .m_axi_s2mm_audio_bready(m_axi_s2mm_audio_bready),
    .m_axi_s2mm_audio_bresp(m_axi_s2mm_audio_bresp),
    .m_axi_s2mm_audio_bvalid(m_axi_s2mm_audio_bvalid),
    .m_axi_s2mm_audio_wdata(m_axi_s2mm_audio_wdata),
    .m_axi_s2mm_audio_wlast(m_axi_s2mm_audio_wlast),
    .m_axi_s2mm_audio_wready(m_axi_s2mm_audio_wready),
    .m_axi_s2mm_audio_wstrb(m_axi_s2mm_audio_wstrb),
    .m_axi_s2mm_audio_wvalid(m_axi_s2mm_audio_wvalid),
    .mclk_out_rx(mclk_out_rx),
    .mclk_out_tx(mclk_out_tx),
    .peripheral_aresetn(peripheral_aresetn),
    .pl_clk1(pl_clk1),
    .pl_rstn1(pl_rstn1),
    .s_axi_ctrl_i2s_rx_araddr(s_axi_ctrl_i2s_rx_araddr),
    .s_axi_ctrl_i2s_rx_arready(s_axi_ctrl_i2s_rx_arready),
    .s_axi_ctrl_i2s_rx_arvalid(s_axi_ctrl_i2s_rx_arvalid),
    .s_axi_ctrl_i2s_rx_awaddr(s_axi_ctrl_i2s_rx_awaddr),
    .s_axi_ctrl_i2s_rx_awready(s_axi_ctrl_i2s_rx_awready),
    .s_axi_ctrl_i2s_rx_awvalid(s_axi_ctrl_i2s_rx_awvalid),
    .s_axi_ctrl_i2s_rx_bready(s_axi_ctrl_i2s_rx_bready),
    .s_axi_ctrl_i2s_rx_bresp(s_axi_ctrl_i2s_rx_bresp),
    .s_axi_ctrl_i2s_rx_bvalid(s_axi_ctrl_i2s_rx_bvalid),
    .s_axi_ctrl_i2s_rx_rdata(s_axi_ctrl_i2s_rx_rdata),
    .s_axi_ctrl_i2s_rx_rready(s_axi_ctrl_i2s_rx_rready),
    .s_axi_ctrl_i2s_rx_rresp(s_axi_ctrl_i2s_rx_rresp),
    .s_axi_ctrl_i2s_rx_rvalid(s_axi_ctrl_i2s_rx_rvalid),
    .s_axi_ctrl_i2s_rx_wdata(s_axi_ctrl_i2s_rx_wdata),
    .s_axi_ctrl_i2s_rx_wready(s_axi_ctrl_i2s_rx_wready),
    .s_axi_ctrl_i2s_rx_wvalid(s_axi_ctrl_i2s_rx_wvalid),
    .s_axi_ctrl_i2s_tx_araddr(s_axi_ctrl_i2s_tx_araddr),
    .s_axi_ctrl_i2s_tx_arready(s_axi_ctrl_i2s_tx_arready),
    .s_axi_ctrl_i2s_tx_arvalid(s_axi_ctrl_i2s_tx_arvalid),
    .s_axi_ctrl_i2s_tx_awaddr(s_axi_ctrl_i2s_tx_awaddr),
    .s_axi_ctrl_i2s_tx_awready(s_axi_ctrl_i2s_tx_awready),
    .s_axi_ctrl_i2s_tx_awvalid(s_axi_ctrl_i2s_tx_awvalid),
    .s_axi_ctrl_i2s_tx_bready(s_axi_ctrl_i2s_tx_bready),
    .s_axi_ctrl_i2s_tx_bresp(s_axi_ctrl_i2s_tx_bresp),
    .s_axi_ctrl_i2s_tx_bvalid(s_axi_ctrl_i2s_tx_bvalid),
    .s_axi_ctrl_i2s_tx_rdata(s_axi_ctrl_i2s_tx_rdata),
    .s_axi_ctrl_i2s_tx_rready(s_axi_ctrl_i2s_tx_rready),
    .s_axi_ctrl_i2s_tx_rresp(s_axi_ctrl_i2s_tx_rresp),
    .s_axi_ctrl_i2s_tx_rvalid(s_axi_ctrl_i2s_tx_rvalid),
    .s_axi_ctrl_i2s_tx_wdata(s_axi_ctrl_i2s_tx_wdata),
    .s_axi_ctrl_i2s_tx_wready(s_axi_ctrl_i2s_tx_wready),
    .s_axi_ctrl_i2s_tx_wvalid(s_axi_ctrl_i2s_tx_wvalid),
    .s_axi_lite_audio_fmt_araddr(s_axi_lite_audio_fmt_araddr),
    .s_axi_lite_audio_fmt_arready(s_axi_lite_audio_fmt_arready),
    .s_axi_lite_audio_fmt_arvalid(s_axi_lite_audio_fmt_arvalid),
    .s_axi_lite_audio_fmt_awaddr(s_axi_lite_audio_fmt_awaddr),
    .s_axi_lite_audio_fmt_awready(s_axi_lite_audio_fmt_awready),
    .s_axi_lite_audio_fmt_awvalid(s_axi_lite_audio_fmt_awvalid),
    .s_axi_lite_audio_fmt_bready(s_axi_lite_audio_fmt_bready),
    .s_axi_lite_audio_fmt_bresp(s_axi_lite_audio_fmt_bresp),
    .s_axi_lite_audio_fmt_bvalid(s_axi_lite_audio_fmt_bvalid),
    .s_axi_lite_audio_fmt_rdata(s_axi_lite_audio_fmt_rdata),
    .s_axi_lite_audio_fmt_rready(s_axi_lite_audio_fmt_rready),
    .s_axi_lite_audio_fmt_rresp(s_axi_lite_audio_fmt_rresp),
    .s_axi_lite_audio_fmt_rvalid(s_axi_lite_audio_fmt_rvalid),
    .s_axi_lite_audio_fmt_wdata(s_axi_lite_audio_fmt_wdata),
    .s_axi_lite_audio_fmt_wready(s_axi_lite_audio_fmt_wready),
    .s_axi_lite_audio_fmt_wvalid(s_axi_lite_audio_fmt_wvalid),
    .sclk_rx(sclk_rx),
    .sclk_tx(sclk_tx),
    .sdata_rx(sdata_rx),
    .sdata_tx(sdata_tx)
  );
endmodule
