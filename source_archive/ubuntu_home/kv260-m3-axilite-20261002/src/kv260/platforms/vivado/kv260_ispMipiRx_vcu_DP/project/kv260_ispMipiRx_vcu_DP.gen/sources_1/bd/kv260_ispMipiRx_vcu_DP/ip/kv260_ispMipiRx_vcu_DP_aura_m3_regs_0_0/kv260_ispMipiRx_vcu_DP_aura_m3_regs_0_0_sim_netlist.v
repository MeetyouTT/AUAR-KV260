// Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
// --------------------------------------------------------------------------------
// Tool Version: Vivado v.2022.2 (lin64) Build 3671981 Fri Oct 14 04:59:54 MDT 2022
// Date        : Fri Oct  2 04:33:13 2026
// Host        : ghmd-MRA-XXX running 64-bit Ubuntu 20.04.4 LTS
// Command     : write_verilog -force -mode funcsim
//               /home/ghmd/kv260-m3-axilite-20261002/src/kv260/platforms/vivado/kv260_ispMipiRx_vcu_DP/project/kv260_ispMipiRx_vcu_DP.gen/sources_1/bd/kv260_ispMipiRx_vcu_DP/ip/kv260_ispMipiRx_vcu_DP_aura_m3_regs_0_0/kv260_ispMipiRx_vcu_DP_aura_m3_regs_0_0_sim_netlist.v
// Design      : kv260_ispMipiRx_vcu_DP_aura_m3_regs_0_0
// Purpose     : This verilog netlist is a functional simulation representation of the design and should not be modified
//               or synthesized. This netlist cannot be used for SDF annotated simulation.
// Device      : xck26-sfvc784-2LV-c
// --------------------------------------------------------------------------------
`timescale 1 ps / 1 ps

(* CHECK_LICENSE_TYPE = "kv260_ispMipiRx_vcu_DP_aura_m3_regs_0_0,aura_m3_regs,{}" *) (* DowngradeIPIdentifiedWarnings = "yes" *) (* IP_DEFINITION_SOURCE = "package_project" *) 
(* X_CORE_INFO = "aura_m3_regs,Vivado 2022.2" *) 
(* NotValidForBitStream *)
module kv260_ispMipiRx_vcu_DP_aura_m3_regs_0_0
   (s_axi_aclk,
    s_axi_aresetn,
    s_axi_awaddr,
    s_axi_awprot,
    s_axi_awvalid,
    s_axi_awready,
    s_axi_wdata,
    s_axi_wstrb,
    s_axi_wvalid,
    s_axi_wready,
    s_axi_bresp,
    s_axi_bvalid,
    s_axi_bready,
    s_axi_araddr,
    s_axi_arprot,
    s_axi_arvalid,
    s_axi_arready,
    s_axi_rdata,
    s_axi_rresp,
    s_axi_rvalid,
    s_axi_rready);
  (* X_INTERFACE_INFO = "xilinx.com:signal:clock:1.0 s_axi_aclk CLK" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME s_axi_aclk, ASSOCIATED_BUSIF S_AXI, ASSOCIATED_RESET s_axi_aresetn, FREQ_HZ 99999000, FREQ_TOLERANCE_HZ 0, PHASE 0.0, CLK_DOMAIN kv260_ispMipiRx_vcu_DP_clk_wiz_0_0_clk_200M, INSERT_VIP 0" *) input s_axi_aclk;
  (* X_INTERFACE_INFO = "xilinx.com:signal:reset:1.0 s_axi_aresetn RST" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME s_axi_aresetn, POLARITY ACTIVE_LOW, INSERT_VIP 0" *) input s_axi_aresetn;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI AWADDR" *) (* X_INTERFACE_PARAMETER = "PROTOCOL AXI4LITE, DATA_WIDTH 32, ADDR_WIDTH 12, READ_WRITE_MODE READ_WRITE" *) input [11:0]s_axi_awaddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI AWPROT" *) input [2:0]s_axi_awprot;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI AWVALID" *) input s_axi_awvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI AWREADY" *) output s_axi_awready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI WDATA" *) input [31:0]s_axi_wdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI WSTRB" *) input [3:0]s_axi_wstrb;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI WVALID" *) input s_axi_wvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI WREADY" *) output s_axi_wready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI BRESP" *) output [1:0]s_axi_bresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI BVALID" *) output s_axi_bvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI BREADY" *) input s_axi_bready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI ARADDR" *) input [11:0]s_axi_araddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI ARPROT" *) input [2:0]s_axi_arprot;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI ARVALID" *) input s_axi_arvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI ARREADY" *) output s_axi_arready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) output [31:0]s_axi_rdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RRESP" *) output [1:0]s_axi_rresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RVALID" *) output s_axi_rvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RREADY" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME S_AXI, PROTOCOL AXI4LITE, DATA_WIDTH 32, ADDR_WIDTH 12, READ_WRITE_MODE READ_WRITE, FREQ_HZ 99999000, ID_WIDTH 0, AWUSER_WIDTH 0, ARUSER_WIDTH 0, WUSER_WIDTH 0, RUSER_WIDTH 0, BUSER_WIDTH 0, HAS_BURST 0, HAS_LOCK 0, HAS_PROT 1, HAS_CACHE 0, HAS_QOS 0, HAS_REGION 0, HAS_WSTRB 1, HAS_BRESP 1, HAS_RRESP 1, SUPPORTS_NARROW_BURST 0, NUM_READ_OUTSTANDING 1, NUM_WRITE_OUTSTANDING 1, MAX_BURST_LENGTH 1, PHASE 0.0, CLK_DOMAIN kv260_ispMipiRx_vcu_DP_clk_wiz_0_0_clk_200M, NUM_READ_THREADS 1, NUM_WRITE_THREADS 1, RUSER_BITS_PER_BYTE 0, WUSER_BITS_PER_BYTE 0, INSERT_VIP 0" *) input s_axi_rready;

  wire \<const0> ;
  wire s_axi_aclk;
  wire [11:0]s_axi_araddr;
  wire s_axi_aresetn;
  wire s_axi_arready;
  wire s_axi_arvalid;
  wire [11:0]s_axi_awaddr;
  wire s_axi_awready;
  wire s_axi_awvalid;
  wire s_axi_bready;
  wire [1:1]\^s_axi_bresp ;
  wire s_axi_bvalid;
  wire [31:0]s_axi_rdata;
  wire s_axi_rready;
  wire [1:1]\^s_axi_rresp ;
  wire s_axi_rvalid;
  wire [31:0]s_axi_wdata;
  wire s_axi_wready;
  wire [3:0]s_axi_wstrb;
  wire s_axi_wvalid;

  assign s_axi_bresp[1] = \^s_axi_bresp [1];
  assign s_axi_bresp[0] = \<const0> ;
  assign s_axi_rresp[1] = \^s_axi_rresp [1];
  assign s_axi_rresp[0] = \<const0> ;
  GND GND
       (.G(\<const0> ));
  kv260_ispMipiRx_vcu_DP_aura_m3_regs_0_0_aura_m3_regs inst
       (.s_axi_aclk(s_axi_aclk),
        .s_axi_araddr(s_axi_araddr),
        .s_axi_aresetn(s_axi_aresetn),
        .s_axi_arready(s_axi_arready),
        .s_axi_arvalid(s_axi_arvalid),
        .s_axi_awaddr(s_axi_awaddr),
        .s_axi_awready(s_axi_awready),
        .s_axi_awvalid(s_axi_awvalid),
        .s_axi_bready(s_axi_bready),
        .s_axi_bresp(\^s_axi_bresp ),
        .s_axi_bvalid_reg_0(s_axi_bvalid),
        .s_axi_rdata(s_axi_rdata),
        .s_axi_rready(s_axi_rready),
        .s_axi_rresp(\^s_axi_rresp ),
        .s_axi_rvalid_reg_0(s_axi_rvalid),
        .s_axi_wdata(s_axi_wdata),
        .s_axi_wready(s_axi_wready),
        .s_axi_wstrb(s_axi_wstrb),
        .s_axi_wvalid(s_axi_wvalid));
endmodule

(* ORIG_REF_NAME = "aura_m3_regs" *) 
module kv260_ispMipiRx_vcu_DP_aura_m3_regs_0_0_aura_m3_regs
   (s_axi_rdata,
    s_axi_rresp,
    s_axi_wready,
    s_axi_bvalid_reg_0,
    s_axi_awready,
    s_axi_bresp,
    s_axi_arready,
    s_axi_rvalid_reg_0,
    s_axi_awaddr,
    s_axi_aclk,
    s_axi_wstrb,
    s_axi_wdata,
    s_axi_aresetn,
    s_axi_awvalid,
    s_axi_wvalid,
    s_axi_arvalid,
    s_axi_araddr,
    s_axi_bready,
    s_axi_rready);
  output [31:0]s_axi_rdata;
  output [0:0]s_axi_rresp;
  output s_axi_wready;
  output s_axi_bvalid_reg_0;
  output s_axi_awready;
  output [0:0]s_axi_bresp;
  output s_axi_arready;
  output s_axi_rvalid_reg_0;
  input [11:0]s_axi_awaddr;
  input s_axi_aclk;
  input [3:0]s_axi_wstrb;
  input [31:0]s_axi_wdata;
  input s_axi_aresetn;
  input s_axi_awvalid;
  input s_axi_wvalid;
  input s_axi_arvalid;
  input [11:0]s_axi_araddr;
  input s_axi_bready;
  input s_axi_rready;

  wire [11:0]aw_address;
  wire aw_pending;
  wire aw_pending0;
  wire aw_pending_i_1_n_0;
  wire data00;
  wire p_0_in;
  wire [31:7]p_1_in;
  wire s_axi_aclk;
  wire [11:0]s_axi_araddr;
  wire s_axi_aresetn;
  wire s_axi_arready;
  wire s_axi_arvalid;
  wire [11:0]s_axi_awaddr;
  wire s_axi_awready;
  wire s_axi_awvalid;
  wire s_axi_bready;
  wire [0:0]s_axi_bresp;
  wire \s_axi_bresp[1]_i_1_n_0 ;
  wire \s_axi_bresp[1]_i_2_n_0 ;
  wire \s_axi_bresp[1]_i_3_n_0 ;
  wire \s_axi_bresp[1]_i_4_n_0 ;
  wire \s_axi_bresp[1]_i_5_n_0 ;
  wire s_axi_bvalid_i_2_n_0;
  wire s_axi_bvalid_reg_0;
  wire [31:0]s_axi_rdata;
  wire \s_axi_rdata[0]_i_1_n_0 ;
  wire \s_axi_rdata[10]_i_1_n_0 ;
  wire \s_axi_rdata[11]_i_1_n_0 ;
  wire \s_axi_rdata[12]_i_1_n_0 ;
  wire \s_axi_rdata[13]_i_1_n_0 ;
  wire \s_axi_rdata[14]_i_1_n_0 ;
  wire \s_axi_rdata[15]_i_1_n_0 ;
  wire \s_axi_rdata[16]_i_1_n_0 ;
  wire \s_axi_rdata[17]_i_1_n_0 ;
  wire \s_axi_rdata[18]_i_1_n_0 ;
  wire \s_axi_rdata[19]_i_1_n_0 ;
  wire \s_axi_rdata[1]_i_1_n_0 ;
  wire \s_axi_rdata[20]_i_1_n_0 ;
  wire \s_axi_rdata[21]_i_1_n_0 ;
  wire \s_axi_rdata[22]_i_1_n_0 ;
  wire \s_axi_rdata[23]_i_1_n_0 ;
  wire \s_axi_rdata[24]_i_1_n_0 ;
  wire \s_axi_rdata[25]_i_1_n_0 ;
  wire \s_axi_rdata[26]_i_1_n_0 ;
  wire \s_axi_rdata[27]_i_1_n_0 ;
  wire \s_axi_rdata[28]_i_1_n_0 ;
  wire \s_axi_rdata[29]_i_1_n_0 ;
  wire \s_axi_rdata[2]_i_1_n_0 ;
  wire \s_axi_rdata[30]_i_1_n_0 ;
  wire \s_axi_rdata[31]_i_2_n_0 ;
  wire \s_axi_rdata[31]_i_3_n_0 ;
  wire \s_axi_rdata[31]_i_4_n_0 ;
  wire \s_axi_rdata[3]_i_1_n_0 ;
  wire \s_axi_rdata[4]_i_1_n_0 ;
  wire \s_axi_rdata[5]_i_1_n_0 ;
  wire \s_axi_rdata[6]_i_1_n_0 ;
  wire \s_axi_rdata[7]_i_1_n_0 ;
  wire \s_axi_rdata[8]_i_1_n_0 ;
  wire \s_axi_rdata[9]_i_1_n_0 ;
  wire s_axi_rready;
  wire [0:0]s_axi_rresp;
  wire \s_axi_rresp[1]_i_1_n_0 ;
  wire s_axi_rvalid01_out;
  wire s_axi_rvalid_i_1_n_0;
  wire s_axi_rvalid_reg_0;
  wire [31:0]s_axi_wdata;
  wire s_axi_wready;
  wire [3:0]s_axi_wstrb;
  wire s_axi_wvalid;
  wire [31:0]scratch;
  wire [31:0]w_data;
  wire w_pending;
  wire w_pending0;
  wire w_pending_i_2_n_0;
  wire w_pending_reg_n_0;
  wire \w_strobes_reg_n_0_[0] ;
  wire \w_strobes_reg_n_0_[2] ;
  wire \w_strobes_reg_n_0_[3] ;

  LUT3 #(
    .INIT(8'h04)) 
    \aw_address[11]_i_1 
       (.I0(aw_pending),
        .I1(s_axi_awvalid),
        .I2(s_axi_bvalid_reg_0),
        .O(aw_pending0));
  FDRE \aw_address_reg[0] 
       (.C(s_axi_aclk),
        .CE(aw_pending0),
        .D(s_axi_awaddr[0]),
        .Q(aw_address[0]),
        .R(p_0_in));
  FDRE \aw_address_reg[10] 
       (.C(s_axi_aclk),
        .CE(aw_pending0),
        .D(s_axi_awaddr[10]),
        .Q(aw_address[10]),
        .R(p_0_in));
  FDRE \aw_address_reg[11] 
       (.C(s_axi_aclk),
        .CE(aw_pending0),
        .D(s_axi_awaddr[11]),
        .Q(aw_address[11]),
        .R(p_0_in));
  FDRE \aw_address_reg[1] 
       (.C(s_axi_aclk),
        .CE(aw_pending0),
        .D(s_axi_awaddr[1]),
        .Q(aw_address[1]),
        .R(p_0_in));
  FDRE \aw_address_reg[2] 
       (.C(s_axi_aclk),
        .CE(aw_pending0),
        .D(s_axi_awaddr[2]),
        .Q(aw_address[2]),
        .R(p_0_in));
  FDRE \aw_address_reg[3] 
       (.C(s_axi_aclk),
        .CE(aw_pending0),
        .D(s_axi_awaddr[3]),
        .Q(aw_address[3]),
        .R(p_0_in));
  FDRE \aw_address_reg[4] 
       (.C(s_axi_aclk),
        .CE(aw_pending0),
        .D(s_axi_awaddr[4]),
        .Q(aw_address[4]),
        .R(p_0_in));
  FDRE \aw_address_reg[5] 
       (.C(s_axi_aclk),
        .CE(aw_pending0),
        .D(s_axi_awaddr[5]),
        .Q(aw_address[5]),
        .R(p_0_in));
  FDRE \aw_address_reg[6] 
       (.C(s_axi_aclk),
        .CE(aw_pending0),
        .D(s_axi_awaddr[6]),
        .Q(aw_address[6]),
        .R(p_0_in));
  FDRE \aw_address_reg[7] 
       (.C(s_axi_aclk),
        .CE(aw_pending0),
        .D(s_axi_awaddr[7]),
        .Q(aw_address[7]),
        .R(p_0_in));
  FDRE \aw_address_reg[8] 
       (.C(s_axi_aclk),
        .CE(aw_pending0),
        .D(s_axi_awaddr[8]),
        .Q(aw_address[8]),
        .R(p_0_in));
  FDRE \aw_address_reg[9] 
       (.C(s_axi_aclk),
        .CE(aw_pending0),
        .D(s_axi_awaddr[9]),
        .Q(aw_address[9]),
        .R(p_0_in));
  (* SOFT_HLUTNM = "soft_lutpair3" *) 
  LUT3 #(
    .INIT(8'hF4)) 
    aw_pending_i_1
       (.I0(s_axi_bvalid_reg_0),
        .I1(s_axi_awvalid),
        .I2(aw_pending),
        .O(aw_pending_i_1_n_0));
  FDRE aw_pending_reg
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(aw_pending_i_1_n_0),
        .Q(aw_pending),
        .R(w_pending));
  (* SOFT_HLUTNM = "soft_lutpair2" *) 
  LUT2 #(
    .INIT(4'h2)) 
    s_axi_arready_INST_0
       (.I0(s_axi_aresetn),
        .I1(s_axi_rvalid_reg_0),
        .O(s_axi_arready));
  (* SOFT_HLUTNM = "soft_lutpair1" *) 
  LUT3 #(
    .INIT(8'h04)) 
    s_axi_awready_INST_0
       (.I0(s_axi_bvalid_reg_0),
        .I1(s_axi_aresetn),
        .I2(aw_pending),
        .O(s_axi_awready));
  LUT6 #(
    .INIT(64'hFF000000FE00FE00)) 
    \s_axi_bresp[1]_i_1 
       (.I0(\s_axi_bresp[1]_i_2_n_0 ),
        .I1(\s_axi_bresp[1]_i_3_n_0 ),
        .I2(\s_axi_bresp[1]_i_4_n_0 ),
        .I3(s_axi_aresetn),
        .I4(s_axi_bresp),
        .I5(\s_axi_bresp[1]_i_5_n_0 ),
        .O(\s_axi_bresp[1]_i_1_n_0 ));
  LUT4 #(
    .INIT(16'hFFFE)) 
    \s_axi_bresp[1]_i_2 
       (.I0(aw_address[9]),
        .I1(aw_address[8]),
        .I2(aw_address[11]),
        .I3(aw_address[10]),
        .O(\s_axi_bresp[1]_i_2_n_0 ));
  LUT4 #(
    .INIT(16'hEFFF)) 
    \s_axi_bresp[1]_i_3 
       (.I0(aw_address[1]),
        .I1(aw_address[0]),
        .I2(aw_address[3]),
        .I3(aw_address[2]),
        .O(\s_axi_bresp[1]_i_3_n_0 ));
  LUT4 #(
    .INIT(16'hFFFE)) 
    \s_axi_bresp[1]_i_4 
       (.I0(aw_address[5]),
        .I1(aw_address[4]),
        .I2(aw_address[7]),
        .I3(aw_address[6]),
        .O(\s_axi_bresp[1]_i_4_n_0 ));
  (* SOFT_HLUTNM = "soft_lutpair0" *) 
  LUT3 #(
    .INIT(8'hDF)) 
    \s_axi_bresp[1]_i_5 
       (.I0(w_pending_reg_n_0),
        .I1(s_axi_bvalid_reg_0),
        .I2(aw_pending),
        .O(\s_axi_bresp[1]_i_5_n_0 ));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI BRESP" *) 
  FDRE \s_axi_bresp_reg[1] 
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(\s_axi_bresp[1]_i_1_n_0 ),
        .Q(s_axi_bresp),
        .R(1'b0));
  LUT1 #(
    .INIT(2'h1)) 
    s_axi_bvalid_i_1
       (.I0(s_axi_aresetn),
        .O(p_0_in));
  (* SOFT_HLUTNM = "soft_lutpair0" *) 
  LUT4 #(
    .INIT(16'h5C50)) 
    s_axi_bvalid_i_2
       (.I0(s_axi_bready),
        .I1(aw_pending),
        .I2(s_axi_bvalid_reg_0),
        .I3(w_pending_reg_n_0),
        .O(s_axi_bvalid_i_2_n_0));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI BVALID" *) 
  FDRE s_axi_bvalid_reg
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(s_axi_bvalid_i_2_n_0),
        .Q(s_axi_bvalid_reg_0),
        .R(p_0_in));
  LUT5 #(
    .INIT(32'h00080003)) 
    \s_axi_rdata[0]_i_1 
       (.I0(scratch[0]),
        .I1(s_axi_araddr[3]),
        .I2(\s_axi_rdata[31]_i_3_n_0 ),
        .I3(\s_axi_rdata[31]_i_4_n_0 ),
        .I4(s_axi_araddr[2]),
        .O(\s_axi_rdata[0]_i_1_n_0 ));
  LUT5 #(
    .INIT(32'h000000B0)) 
    \s_axi_rdata[10]_i_1 
       (.I0(scratch[10]),
        .I1(s_axi_araddr[2]),
        .I2(s_axi_araddr[3]),
        .I3(\s_axi_rdata[31]_i_3_n_0 ),
        .I4(\s_axi_rdata[31]_i_4_n_0 ),
        .O(\s_axi_rdata[10]_i_1_n_0 ));
  LUT5 #(
    .INIT(32'h00080000)) 
    \s_axi_rdata[11]_i_1 
       (.I0(s_axi_araddr[2]),
        .I1(s_axi_araddr[3]),
        .I2(\s_axi_rdata[31]_i_3_n_0 ),
        .I3(\s_axi_rdata[31]_i_4_n_0 ),
        .I4(scratch[11]),
        .O(\s_axi_rdata[11]_i_1_n_0 ));
  LUT5 #(
    .INIT(32'h00080003)) 
    \s_axi_rdata[12]_i_1 
       (.I0(scratch[12]),
        .I1(s_axi_araddr[3]),
        .I2(\s_axi_rdata[31]_i_3_n_0 ),
        .I3(\s_axi_rdata[31]_i_4_n_0 ),
        .I4(s_axi_araddr[2]),
        .O(\s_axi_rdata[12]_i_1_n_0 ));
  LUT5 #(
    .INIT(32'h00080000)) 
    \s_axi_rdata[13]_i_1 
       (.I0(s_axi_araddr[2]),
        .I1(s_axi_araddr[3]),
        .I2(\s_axi_rdata[31]_i_3_n_0 ),
        .I3(\s_axi_rdata[31]_i_4_n_0 ),
        .I4(scratch[13]),
        .O(\s_axi_rdata[13]_i_1_n_0 ));
  LUT5 #(
    .INIT(32'h00080003)) 
    \s_axi_rdata[14]_i_1 
       (.I0(scratch[14]),
        .I1(s_axi_araddr[3]),
        .I2(\s_axi_rdata[31]_i_3_n_0 ),
        .I3(\s_axi_rdata[31]_i_4_n_0 ),
        .I4(s_axi_araddr[2]),
        .O(\s_axi_rdata[14]_i_1_n_0 ));
  LUT5 #(
    .INIT(32'h000000B0)) 
    \s_axi_rdata[15]_i_1 
       (.I0(scratch[15]),
        .I1(s_axi_araddr[2]),
        .I2(s_axi_araddr[3]),
        .I3(\s_axi_rdata[31]_i_3_n_0 ),
        .I4(\s_axi_rdata[31]_i_4_n_0 ),
        .O(\s_axi_rdata[15]_i_1_n_0 ));
  LUT5 #(
    .INIT(32'h000F0007)) 
    \s_axi_rdata[16]_i_1 
       (.I0(s_axi_araddr[2]),
        .I1(s_axi_araddr[3]),
        .I2(\s_axi_rdata[31]_i_4_n_0 ),
        .I3(\s_axi_rdata[31]_i_3_n_0 ),
        .I4(scratch[16]),
        .O(\s_axi_rdata[16]_i_1_n_0 ));
  LUT5 #(
    .INIT(32'h000000B0)) 
    \s_axi_rdata[17]_i_1 
       (.I0(scratch[17]),
        .I1(s_axi_araddr[2]),
        .I2(s_axi_araddr[3]),
        .I3(\s_axi_rdata[31]_i_3_n_0 ),
        .I4(\s_axi_rdata[31]_i_4_n_0 ),
        .O(\s_axi_rdata[17]_i_1_n_0 ));
  LUT5 #(
    .INIT(32'h0000008F)) 
    \s_axi_rdata[18]_i_1 
       (.I0(scratch[18]),
        .I1(s_axi_araddr[3]),
        .I2(s_axi_araddr[2]),
        .I3(\s_axi_rdata[31]_i_4_n_0 ),
        .I4(\s_axi_rdata[31]_i_3_n_0 ),
        .O(\s_axi_rdata[18]_i_1_n_0 ));
  LUT5 #(
    .INIT(32'h00080000)) 
    \s_axi_rdata[19]_i_1 
       (.I0(s_axi_araddr[2]),
        .I1(s_axi_araddr[3]),
        .I2(\s_axi_rdata[31]_i_3_n_0 ),
        .I3(\s_axi_rdata[31]_i_4_n_0 ),
        .I4(scratch[19]),
        .O(\s_axi_rdata[19]_i_1_n_0 ));
  LUT5 #(
    .INIT(32'h00080000)) 
    \s_axi_rdata[1]_i_1 
       (.I0(s_axi_araddr[2]),
        .I1(s_axi_araddr[3]),
        .I2(\s_axi_rdata[31]_i_3_n_0 ),
        .I3(\s_axi_rdata[31]_i_4_n_0 ),
        .I4(scratch[1]),
        .O(\s_axi_rdata[1]_i_1_n_0 ));
  LUT5 #(
    .INIT(32'h00080003)) 
    \s_axi_rdata[20]_i_1 
       (.I0(scratch[20]),
        .I1(s_axi_araddr[3]),
        .I2(\s_axi_rdata[31]_i_3_n_0 ),
        .I3(\s_axi_rdata[31]_i_4_n_0 ),
        .I4(s_axi_araddr[2]),
        .O(\s_axi_rdata[20]_i_1_n_0 ));
  LUT5 #(
    .INIT(32'h00080000)) 
    \s_axi_rdata[21]_i_1 
       (.I0(s_axi_araddr[2]),
        .I1(s_axi_araddr[3]),
        .I2(\s_axi_rdata[31]_i_3_n_0 ),
        .I3(\s_axi_rdata[31]_i_4_n_0 ),
        .I4(scratch[21]),
        .O(\s_axi_rdata[21]_i_1_n_0 ));
  LUT5 #(
    .INIT(32'h00080003)) 
    \s_axi_rdata[22]_i_1 
       (.I0(scratch[22]),
        .I1(s_axi_araddr[3]),
        .I2(\s_axi_rdata[31]_i_3_n_0 ),
        .I3(\s_axi_rdata[31]_i_4_n_0 ),
        .I4(s_axi_araddr[2]),
        .O(\s_axi_rdata[22]_i_1_n_0 ));
  LUT5 #(
    .INIT(32'h00080000)) 
    \s_axi_rdata[23]_i_1 
       (.I0(s_axi_araddr[2]),
        .I1(s_axi_araddr[3]),
        .I2(\s_axi_rdata[31]_i_3_n_0 ),
        .I3(\s_axi_rdata[31]_i_4_n_0 ),
        .I4(scratch[23]),
        .O(\s_axi_rdata[23]_i_1_n_0 ));
  LUT5 #(
    .INIT(32'h0000008F)) 
    \s_axi_rdata[24]_i_1 
       (.I0(scratch[24]),
        .I1(s_axi_araddr[3]),
        .I2(s_axi_araddr[2]),
        .I3(\s_axi_rdata[31]_i_4_n_0 ),
        .I4(\s_axi_rdata[31]_i_3_n_0 ),
        .O(\s_axi_rdata[24]_i_1_n_0 ));
  LUT5 #(
    .INIT(32'h00080000)) 
    \s_axi_rdata[25]_i_1 
       (.I0(s_axi_araddr[2]),
        .I1(s_axi_araddr[3]),
        .I2(\s_axi_rdata[31]_i_3_n_0 ),
        .I3(\s_axi_rdata[31]_i_4_n_0 ),
        .I4(scratch[25]),
        .O(\s_axi_rdata[25]_i_1_n_0 ));
  LUT5 #(
    .INIT(32'h000000B0)) 
    \s_axi_rdata[26]_i_1 
       (.I0(scratch[26]),
        .I1(s_axi_araddr[2]),
        .I2(s_axi_araddr[3]),
        .I3(\s_axi_rdata[31]_i_3_n_0 ),
        .I4(\s_axi_rdata[31]_i_4_n_0 ),
        .O(\s_axi_rdata[26]_i_1_n_0 ));
  LUT5 #(
    .INIT(32'h00080000)) 
    \s_axi_rdata[27]_i_1 
       (.I0(s_axi_araddr[2]),
        .I1(s_axi_araddr[3]),
        .I2(\s_axi_rdata[31]_i_3_n_0 ),
        .I3(\s_axi_rdata[31]_i_4_n_0 ),
        .I4(scratch[27]),
        .O(\s_axi_rdata[27]_i_1_n_0 ));
  LUT5 #(
    .INIT(32'h00080000)) 
    \s_axi_rdata[28]_i_1 
       (.I0(s_axi_araddr[2]),
        .I1(s_axi_araddr[3]),
        .I2(\s_axi_rdata[31]_i_3_n_0 ),
        .I3(\s_axi_rdata[31]_i_4_n_0 ),
        .I4(scratch[28]),
        .O(\s_axi_rdata[28]_i_1_n_0 ));
  LUT5 #(
    .INIT(32'h000000B0)) 
    \s_axi_rdata[29]_i_1 
       (.I0(scratch[29]),
        .I1(s_axi_araddr[2]),
        .I2(s_axi_araddr[3]),
        .I3(\s_axi_rdata[31]_i_3_n_0 ),
        .I4(\s_axi_rdata[31]_i_4_n_0 ),
        .O(\s_axi_rdata[29]_i_1_n_0 ));
  LUT5 #(
    .INIT(32'h00080000)) 
    \s_axi_rdata[2]_i_1 
       (.I0(s_axi_araddr[2]),
        .I1(s_axi_araddr[3]),
        .I2(\s_axi_rdata[31]_i_3_n_0 ),
        .I3(\s_axi_rdata[31]_i_4_n_0 ),
        .I4(scratch[2]),
        .O(\s_axi_rdata[2]_i_1_n_0 ));
  LUT5 #(
    .INIT(32'h00080003)) 
    \s_axi_rdata[30]_i_1 
       (.I0(scratch[30]),
        .I1(s_axi_araddr[3]),
        .I2(\s_axi_rdata[31]_i_3_n_0 ),
        .I3(\s_axi_rdata[31]_i_4_n_0 ),
        .I4(s_axi_araddr[2]),
        .O(\s_axi_rdata[30]_i_1_n_0 ));
  LUT2 #(
    .INIT(4'h2)) 
    \s_axi_rdata[31]_i_1 
       (.I0(s_axi_arvalid),
        .I1(s_axi_rvalid_reg_0),
        .O(s_axi_rvalid01_out));
  LUT5 #(
    .INIT(32'h000000B0)) 
    \s_axi_rdata[31]_i_2 
       (.I0(scratch[31]),
        .I1(s_axi_araddr[2]),
        .I2(s_axi_araddr[3]),
        .I3(\s_axi_rdata[31]_i_3_n_0 ),
        .I4(\s_axi_rdata[31]_i_4_n_0 ),
        .O(\s_axi_rdata[31]_i_2_n_0 ));
  LUT4 #(
    .INIT(16'hFFFE)) 
    \s_axi_rdata[31]_i_3 
       (.I0(s_axi_araddr[5]),
        .I1(s_axi_araddr[4]),
        .I2(s_axi_araddr[7]),
        .I3(s_axi_araddr[6]),
        .O(\s_axi_rdata[31]_i_3_n_0 ));
  LUT6 #(
    .INIT(64'hFFFFFFFFFFFFFFFE)) 
    \s_axi_rdata[31]_i_4 
       (.I0(s_axi_araddr[10]),
        .I1(s_axi_araddr[11]),
        .I2(s_axi_araddr[8]),
        .I3(s_axi_araddr[9]),
        .I4(s_axi_araddr[1]),
        .I5(s_axi_araddr[0]),
        .O(\s_axi_rdata[31]_i_4_n_0 ));
  LUT5 #(
    .INIT(32'h00080000)) 
    \s_axi_rdata[3]_i_1 
       (.I0(s_axi_araddr[2]),
        .I1(s_axi_araddr[3]),
        .I2(\s_axi_rdata[31]_i_3_n_0 ),
        .I3(\s_axi_rdata[31]_i_4_n_0 ),
        .I4(scratch[3]),
        .O(\s_axi_rdata[3]_i_1_n_0 ));
  LUT5 #(
    .INIT(32'h000000B0)) 
    \s_axi_rdata[4]_i_1 
       (.I0(scratch[4]),
        .I1(s_axi_araddr[2]),
        .I2(s_axi_araddr[3]),
        .I3(\s_axi_rdata[31]_i_3_n_0 ),
        .I4(\s_axi_rdata[31]_i_4_n_0 ),
        .O(\s_axi_rdata[4]_i_1_n_0 ));
  LUT5 #(
    .INIT(32'h00080000)) 
    \s_axi_rdata[5]_i_1 
       (.I0(s_axi_araddr[2]),
        .I1(s_axi_araddr[3]),
        .I2(\s_axi_rdata[31]_i_3_n_0 ),
        .I3(\s_axi_rdata[31]_i_4_n_0 ),
        .I4(scratch[5]),
        .O(\s_axi_rdata[5]_i_1_n_0 ));
  LUT5 #(
    .INIT(32'h0000008F)) 
    \s_axi_rdata[6]_i_1 
       (.I0(scratch[6]),
        .I1(s_axi_araddr[3]),
        .I2(s_axi_araddr[2]),
        .I3(\s_axi_rdata[31]_i_4_n_0 ),
        .I4(\s_axi_rdata[31]_i_3_n_0 ),
        .O(\s_axi_rdata[6]_i_1_n_0 ));
  LUT5 #(
    .INIT(32'h00080000)) 
    \s_axi_rdata[7]_i_1 
       (.I0(s_axi_araddr[2]),
        .I1(s_axi_araddr[3]),
        .I2(\s_axi_rdata[31]_i_3_n_0 ),
        .I3(\s_axi_rdata[31]_i_4_n_0 ),
        .I4(scratch[7]),
        .O(\s_axi_rdata[7]_i_1_n_0 ));
  LUT5 #(
    .INIT(32'h00080000)) 
    \s_axi_rdata[8]_i_1 
       (.I0(s_axi_araddr[2]),
        .I1(s_axi_araddr[3]),
        .I2(\s_axi_rdata[31]_i_3_n_0 ),
        .I3(\s_axi_rdata[31]_i_4_n_0 ),
        .I4(scratch[8]),
        .O(\s_axi_rdata[8]_i_1_n_0 ));
  LUT5 #(
    .INIT(32'h00080003)) 
    \s_axi_rdata[9]_i_1 
       (.I0(scratch[9]),
        .I1(s_axi_araddr[3]),
        .I2(\s_axi_rdata[31]_i_3_n_0 ),
        .I3(\s_axi_rdata[31]_i_4_n_0 ),
        .I4(s_axi_araddr[2]),
        .O(\s_axi_rdata[9]_i_1_n_0 ));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[0] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(\s_axi_rdata[0]_i_1_n_0 ),
        .Q(s_axi_rdata[0]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[10] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(\s_axi_rdata[10]_i_1_n_0 ),
        .Q(s_axi_rdata[10]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[11] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(\s_axi_rdata[11]_i_1_n_0 ),
        .Q(s_axi_rdata[11]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[12] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(\s_axi_rdata[12]_i_1_n_0 ),
        .Q(s_axi_rdata[12]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[13] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(\s_axi_rdata[13]_i_1_n_0 ),
        .Q(s_axi_rdata[13]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[14] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(\s_axi_rdata[14]_i_1_n_0 ),
        .Q(s_axi_rdata[14]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[15] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(\s_axi_rdata[15]_i_1_n_0 ),
        .Q(s_axi_rdata[15]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[16] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(\s_axi_rdata[16]_i_1_n_0 ),
        .Q(s_axi_rdata[16]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[17] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(\s_axi_rdata[17]_i_1_n_0 ),
        .Q(s_axi_rdata[17]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[18] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(\s_axi_rdata[18]_i_1_n_0 ),
        .Q(s_axi_rdata[18]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[19] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(\s_axi_rdata[19]_i_1_n_0 ),
        .Q(s_axi_rdata[19]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[1] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(\s_axi_rdata[1]_i_1_n_0 ),
        .Q(s_axi_rdata[1]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[20] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(\s_axi_rdata[20]_i_1_n_0 ),
        .Q(s_axi_rdata[20]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[21] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(\s_axi_rdata[21]_i_1_n_0 ),
        .Q(s_axi_rdata[21]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[22] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(\s_axi_rdata[22]_i_1_n_0 ),
        .Q(s_axi_rdata[22]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[23] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(\s_axi_rdata[23]_i_1_n_0 ),
        .Q(s_axi_rdata[23]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[24] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(\s_axi_rdata[24]_i_1_n_0 ),
        .Q(s_axi_rdata[24]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[25] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(\s_axi_rdata[25]_i_1_n_0 ),
        .Q(s_axi_rdata[25]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[26] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(\s_axi_rdata[26]_i_1_n_0 ),
        .Q(s_axi_rdata[26]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[27] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(\s_axi_rdata[27]_i_1_n_0 ),
        .Q(s_axi_rdata[27]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[28] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(\s_axi_rdata[28]_i_1_n_0 ),
        .Q(s_axi_rdata[28]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[29] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(\s_axi_rdata[29]_i_1_n_0 ),
        .Q(s_axi_rdata[29]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[2] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(\s_axi_rdata[2]_i_1_n_0 ),
        .Q(s_axi_rdata[2]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[30] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(\s_axi_rdata[30]_i_1_n_0 ),
        .Q(s_axi_rdata[30]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[31] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(\s_axi_rdata[31]_i_2_n_0 ),
        .Q(s_axi_rdata[31]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[3] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(\s_axi_rdata[3]_i_1_n_0 ),
        .Q(s_axi_rdata[3]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[4] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(\s_axi_rdata[4]_i_1_n_0 ),
        .Q(s_axi_rdata[4]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[5] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(\s_axi_rdata[5]_i_1_n_0 ),
        .Q(s_axi_rdata[5]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[6] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(\s_axi_rdata[6]_i_1_n_0 ),
        .Q(s_axi_rdata[6]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[7] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(\s_axi_rdata[7]_i_1_n_0 ),
        .Q(s_axi_rdata[7]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[8] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(\s_axi_rdata[8]_i_1_n_0 ),
        .Q(s_axi_rdata[8]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[9] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(\s_axi_rdata[9]_i_1_n_0 ),
        .Q(s_axi_rdata[9]),
        .R(p_0_in));
  LUT5 #(
    .INIT(32'hFFFFFFFE)) 
    \s_axi_rresp[1]_i_1 
       (.I0(\s_axi_rdata[31]_i_4_n_0 ),
        .I1(s_axi_araddr[6]),
        .I2(s_axi_araddr[7]),
        .I3(s_axi_araddr[4]),
        .I4(s_axi_araddr[5]),
        .O(\s_axi_rresp[1]_i_1_n_0 ));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RRESP" *) 
  FDRE \s_axi_rresp_reg[1] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(\s_axi_rresp[1]_i_1_n_0 ),
        .Q(s_axi_rresp),
        .R(p_0_in));
  (* SOFT_HLUTNM = "soft_lutpair2" *) 
  LUT3 #(
    .INIT(8'h74)) 
    s_axi_rvalid_i_1
       (.I0(s_axi_rready),
        .I1(s_axi_rvalid_reg_0),
        .I2(s_axi_arvalid),
        .O(s_axi_rvalid_i_1_n_0));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RVALID" *) 
  FDRE s_axi_rvalid_reg
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(s_axi_rvalid_i_1_n_0),
        .Q(s_axi_rvalid_reg_0),
        .R(p_0_in));
  (* SOFT_HLUTNM = "soft_lutpair1" *) 
  LUT3 #(
    .INIT(8'h04)) 
    s_axi_wready_INST_0
       (.I0(s_axi_bvalid_reg_0),
        .I1(s_axi_aresetn),
        .I2(w_pending_reg_n_0),
        .O(s_axi_wready));
  LUT5 #(
    .INIT(32'h00000002)) 
    \scratch[15]_i_1 
       (.I0(data00),
        .I1(\s_axi_bresp[1]_i_2_n_0 ),
        .I2(\s_axi_bresp[1]_i_5_n_0 ),
        .I3(\s_axi_bresp[1]_i_3_n_0 ),
        .I4(\s_axi_bresp[1]_i_4_n_0 ),
        .O(p_1_in[15]));
  LUT5 #(
    .INIT(32'h00000002)) 
    \scratch[23]_i_1 
       (.I0(\w_strobes_reg_n_0_[2] ),
        .I1(\s_axi_bresp[1]_i_2_n_0 ),
        .I2(\s_axi_bresp[1]_i_5_n_0 ),
        .I3(\s_axi_bresp[1]_i_3_n_0 ),
        .I4(\s_axi_bresp[1]_i_4_n_0 ),
        .O(p_1_in[23]));
  LUT5 #(
    .INIT(32'h00000002)) 
    \scratch[31]_i_1 
       (.I0(\w_strobes_reg_n_0_[3] ),
        .I1(\s_axi_bresp[1]_i_2_n_0 ),
        .I2(\s_axi_bresp[1]_i_5_n_0 ),
        .I3(\s_axi_bresp[1]_i_3_n_0 ),
        .I4(\s_axi_bresp[1]_i_4_n_0 ),
        .O(p_1_in[31]));
  LUT5 #(
    .INIT(32'h00000002)) 
    \scratch[7]_i_1 
       (.I0(\w_strobes_reg_n_0_[0] ),
        .I1(\s_axi_bresp[1]_i_2_n_0 ),
        .I2(\s_axi_bresp[1]_i_5_n_0 ),
        .I3(\s_axi_bresp[1]_i_3_n_0 ),
        .I4(\s_axi_bresp[1]_i_4_n_0 ),
        .O(p_1_in[7]));
  FDRE \scratch_reg[0] 
       (.C(s_axi_aclk),
        .CE(p_1_in[7]),
        .D(w_data[0]),
        .Q(scratch[0]),
        .R(p_0_in));
  FDRE \scratch_reg[10] 
       (.C(s_axi_aclk),
        .CE(p_1_in[15]),
        .D(w_data[10]),
        .Q(scratch[10]),
        .R(p_0_in));
  FDRE \scratch_reg[11] 
       (.C(s_axi_aclk),
        .CE(p_1_in[15]),
        .D(w_data[11]),
        .Q(scratch[11]),
        .R(p_0_in));
  FDRE \scratch_reg[12] 
       (.C(s_axi_aclk),
        .CE(p_1_in[15]),
        .D(w_data[12]),
        .Q(scratch[12]),
        .R(p_0_in));
  FDRE \scratch_reg[13] 
       (.C(s_axi_aclk),
        .CE(p_1_in[15]),
        .D(w_data[13]),
        .Q(scratch[13]),
        .R(p_0_in));
  FDRE \scratch_reg[14] 
       (.C(s_axi_aclk),
        .CE(p_1_in[15]),
        .D(w_data[14]),
        .Q(scratch[14]),
        .R(p_0_in));
  FDRE \scratch_reg[15] 
       (.C(s_axi_aclk),
        .CE(p_1_in[15]),
        .D(w_data[15]),
        .Q(scratch[15]),
        .R(p_0_in));
  FDRE \scratch_reg[16] 
       (.C(s_axi_aclk),
        .CE(p_1_in[23]),
        .D(w_data[16]),
        .Q(scratch[16]),
        .R(p_0_in));
  FDRE \scratch_reg[17] 
       (.C(s_axi_aclk),
        .CE(p_1_in[23]),
        .D(w_data[17]),
        .Q(scratch[17]),
        .R(p_0_in));
  FDRE \scratch_reg[18] 
       (.C(s_axi_aclk),
        .CE(p_1_in[23]),
        .D(w_data[18]),
        .Q(scratch[18]),
        .R(p_0_in));
  FDRE \scratch_reg[19] 
       (.C(s_axi_aclk),
        .CE(p_1_in[23]),
        .D(w_data[19]),
        .Q(scratch[19]),
        .R(p_0_in));
  FDRE \scratch_reg[1] 
       (.C(s_axi_aclk),
        .CE(p_1_in[7]),
        .D(w_data[1]),
        .Q(scratch[1]),
        .R(p_0_in));
  FDRE \scratch_reg[20] 
       (.C(s_axi_aclk),
        .CE(p_1_in[23]),
        .D(w_data[20]),
        .Q(scratch[20]),
        .R(p_0_in));
  FDRE \scratch_reg[21] 
       (.C(s_axi_aclk),
        .CE(p_1_in[23]),
        .D(w_data[21]),
        .Q(scratch[21]),
        .R(p_0_in));
  FDRE \scratch_reg[22] 
       (.C(s_axi_aclk),
        .CE(p_1_in[23]),
        .D(w_data[22]),
        .Q(scratch[22]),
        .R(p_0_in));
  FDRE \scratch_reg[23] 
       (.C(s_axi_aclk),
        .CE(p_1_in[23]),
        .D(w_data[23]),
        .Q(scratch[23]),
        .R(p_0_in));
  FDRE \scratch_reg[24] 
       (.C(s_axi_aclk),
        .CE(p_1_in[31]),
        .D(w_data[24]),
        .Q(scratch[24]),
        .R(p_0_in));
  FDRE \scratch_reg[25] 
       (.C(s_axi_aclk),
        .CE(p_1_in[31]),
        .D(w_data[25]),
        .Q(scratch[25]),
        .R(p_0_in));
  FDRE \scratch_reg[26] 
       (.C(s_axi_aclk),
        .CE(p_1_in[31]),
        .D(w_data[26]),
        .Q(scratch[26]),
        .R(p_0_in));
  FDRE \scratch_reg[27] 
       (.C(s_axi_aclk),
        .CE(p_1_in[31]),
        .D(w_data[27]),
        .Q(scratch[27]),
        .R(p_0_in));
  FDRE \scratch_reg[28] 
       (.C(s_axi_aclk),
        .CE(p_1_in[31]),
        .D(w_data[28]),
        .Q(scratch[28]),
        .R(p_0_in));
  FDRE \scratch_reg[29] 
       (.C(s_axi_aclk),
        .CE(p_1_in[31]),
        .D(w_data[29]),
        .Q(scratch[29]),
        .R(p_0_in));
  FDRE \scratch_reg[2] 
       (.C(s_axi_aclk),
        .CE(p_1_in[7]),
        .D(w_data[2]),
        .Q(scratch[2]),
        .R(p_0_in));
  FDRE \scratch_reg[30] 
       (.C(s_axi_aclk),
        .CE(p_1_in[31]),
        .D(w_data[30]),
        .Q(scratch[30]),
        .R(p_0_in));
  FDRE \scratch_reg[31] 
       (.C(s_axi_aclk),
        .CE(p_1_in[31]),
        .D(w_data[31]),
        .Q(scratch[31]),
        .R(p_0_in));
  FDRE \scratch_reg[3] 
       (.C(s_axi_aclk),
        .CE(p_1_in[7]),
        .D(w_data[3]),
        .Q(scratch[3]),
        .R(p_0_in));
  FDRE \scratch_reg[4] 
       (.C(s_axi_aclk),
        .CE(p_1_in[7]),
        .D(w_data[4]),
        .Q(scratch[4]),
        .R(p_0_in));
  FDRE \scratch_reg[5] 
       (.C(s_axi_aclk),
        .CE(p_1_in[7]),
        .D(w_data[5]),
        .Q(scratch[5]),
        .R(p_0_in));
  FDRE \scratch_reg[6] 
       (.C(s_axi_aclk),
        .CE(p_1_in[7]),
        .D(w_data[6]),
        .Q(scratch[6]),
        .R(p_0_in));
  FDRE \scratch_reg[7] 
       (.C(s_axi_aclk),
        .CE(p_1_in[7]),
        .D(w_data[7]),
        .Q(scratch[7]),
        .R(p_0_in));
  FDRE \scratch_reg[8] 
       (.C(s_axi_aclk),
        .CE(p_1_in[15]),
        .D(w_data[8]),
        .Q(scratch[8]),
        .R(p_0_in));
  FDRE \scratch_reg[9] 
       (.C(s_axi_aclk),
        .CE(p_1_in[15]),
        .D(w_data[9]),
        .Q(scratch[9]),
        .R(p_0_in));
  FDRE \w_data_reg[0] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[0]),
        .Q(w_data[0]),
        .R(p_0_in));
  FDRE \w_data_reg[10] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[10]),
        .Q(w_data[10]),
        .R(p_0_in));
  FDRE \w_data_reg[11] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[11]),
        .Q(w_data[11]),
        .R(p_0_in));
  FDRE \w_data_reg[12] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[12]),
        .Q(w_data[12]),
        .R(p_0_in));
  FDRE \w_data_reg[13] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[13]),
        .Q(w_data[13]),
        .R(p_0_in));
  FDRE \w_data_reg[14] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[14]),
        .Q(w_data[14]),
        .R(p_0_in));
  FDRE \w_data_reg[15] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[15]),
        .Q(w_data[15]),
        .R(p_0_in));
  FDRE \w_data_reg[16] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[16]),
        .Q(w_data[16]),
        .R(p_0_in));
  FDRE \w_data_reg[17] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[17]),
        .Q(w_data[17]),
        .R(p_0_in));
  FDRE \w_data_reg[18] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[18]),
        .Q(w_data[18]),
        .R(p_0_in));
  FDRE \w_data_reg[19] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[19]),
        .Q(w_data[19]),
        .R(p_0_in));
  FDRE \w_data_reg[1] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[1]),
        .Q(w_data[1]),
        .R(p_0_in));
  FDRE \w_data_reg[20] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[20]),
        .Q(w_data[20]),
        .R(p_0_in));
  FDRE \w_data_reg[21] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[21]),
        .Q(w_data[21]),
        .R(p_0_in));
  FDRE \w_data_reg[22] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[22]),
        .Q(w_data[22]),
        .R(p_0_in));
  FDRE \w_data_reg[23] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[23]),
        .Q(w_data[23]),
        .R(p_0_in));
  FDRE \w_data_reg[24] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[24]),
        .Q(w_data[24]),
        .R(p_0_in));
  FDRE \w_data_reg[25] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[25]),
        .Q(w_data[25]),
        .R(p_0_in));
  FDRE \w_data_reg[26] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[26]),
        .Q(w_data[26]),
        .R(p_0_in));
  FDRE \w_data_reg[27] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[27]),
        .Q(w_data[27]),
        .R(p_0_in));
  FDRE \w_data_reg[28] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[28]),
        .Q(w_data[28]),
        .R(p_0_in));
  FDRE \w_data_reg[29] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[29]),
        .Q(w_data[29]),
        .R(p_0_in));
  FDRE \w_data_reg[2] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[2]),
        .Q(w_data[2]),
        .R(p_0_in));
  FDRE \w_data_reg[30] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[30]),
        .Q(w_data[30]),
        .R(p_0_in));
  FDRE \w_data_reg[31] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[31]),
        .Q(w_data[31]),
        .R(p_0_in));
  FDRE \w_data_reg[3] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[3]),
        .Q(w_data[3]),
        .R(p_0_in));
  FDRE \w_data_reg[4] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[4]),
        .Q(w_data[4]),
        .R(p_0_in));
  FDRE \w_data_reg[5] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[5]),
        .Q(w_data[5]),
        .R(p_0_in));
  FDRE \w_data_reg[6] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[6]),
        .Q(w_data[6]),
        .R(p_0_in));
  FDRE \w_data_reg[7] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[7]),
        .Q(w_data[7]),
        .R(p_0_in));
  FDRE \w_data_reg[8] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[8]),
        .Q(w_data[8]),
        .R(p_0_in));
  FDRE \w_data_reg[9] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[9]),
        .Q(w_data[9]),
        .R(p_0_in));
  LUT4 #(
    .INIT(16'h20FF)) 
    w_pending_i_1
       (.I0(aw_pending),
        .I1(s_axi_bvalid_reg_0),
        .I2(w_pending_reg_n_0),
        .I3(s_axi_aresetn),
        .O(w_pending));
  (* SOFT_HLUTNM = "soft_lutpair3" *) 
  LUT3 #(
    .INIT(8'hF4)) 
    w_pending_i_2
       (.I0(s_axi_bvalid_reg_0),
        .I1(s_axi_wvalid),
        .I2(w_pending_reg_n_0),
        .O(w_pending_i_2_n_0));
  FDRE w_pending_reg
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(w_pending_i_2_n_0),
        .Q(w_pending_reg_n_0),
        .R(w_pending));
  LUT3 #(
    .INIT(8'h04)) 
    \w_strobes[3]_i_1 
       (.I0(w_pending_reg_n_0),
        .I1(s_axi_wvalid),
        .I2(s_axi_bvalid_reg_0),
        .O(w_pending0));
  FDRE \w_strobes_reg[0] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wstrb[0]),
        .Q(\w_strobes_reg_n_0_[0] ),
        .R(p_0_in));
  FDRE \w_strobes_reg[1] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wstrb[1]),
        .Q(data00),
        .R(p_0_in));
  FDRE \w_strobes_reg[2] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wstrb[2]),
        .Q(\w_strobes_reg_n_0_[2] ),
        .R(p_0_in));
  FDRE \w_strobes_reg[3] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wstrb[3]),
        .Q(\w_strobes_reg_n_0_[3] ),
        .R(p_0_in));
endmodule
`ifndef GLBL
`define GLBL
`timescale  1 ps / 1 ps

module glbl ();

    parameter ROC_WIDTH = 100000;
    parameter TOC_WIDTH = 0;
    parameter GRES_WIDTH = 10000;
    parameter GRES_START = 10000;

//--------   STARTUP Globals --------------
    wire GSR;
    wire GTS;
    wire GWE;
    wire PRLD;
    wire GRESTORE;
    tri1 p_up_tmp;
    tri (weak1, strong0) PLL_LOCKG = p_up_tmp;

    wire PROGB_GLBL;
    wire CCLKO_GLBL;
    wire FCSBO_GLBL;
    wire [3:0] DO_GLBL;
    wire [3:0] DI_GLBL;
   
    reg GSR_int;
    reg GTS_int;
    reg PRLD_int;
    reg GRESTORE_int;

//--------   JTAG Globals --------------
    wire JTAG_TDO_GLBL;
    wire JTAG_TCK_GLBL;
    wire JTAG_TDI_GLBL;
    wire JTAG_TMS_GLBL;
    wire JTAG_TRST_GLBL;

    reg JTAG_CAPTURE_GLBL;
    reg JTAG_RESET_GLBL;
    reg JTAG_SHIFT_GLBL;
    reg JTAG_UPDATE_GLBL;
    reg JTAG_RUNTEST_GLBL;

    reg JTAG_SEL1_GLBL = 0;
    reg JTAG_SEL2_GLBL = 0 ;
    reg JTAG_SEL3_GLBL = 0;
    reg JTAG_SEL4_GLBL = 0;

    reg JTAG_USER_TDO1_GLBL = 1'bz;
    reg JTAG_USER_TDO2_GLBL = 1'bz;
    reg JTAG_USER_TDO3_GLBL = 1'bz;
    reg JTAG_USER_TDO4_GLBL = 1'bz;

    assign (strong1, weak0) GSR = GSR_int;
    assign (strong1, weak0) GTS = GTS_int;
    assign (weak1, weak0) PRLD = PRLD_int;
    assign (strong1, weak0) GRESTORE = GRESTORE_int;

    initial begin
	GSR_int = 1'b1;
	PRLD_int = 1'b1;
	#(ROC_WIDTH)
	GSR_int = 1'b0;
	PRLD_int = 1'b0;
    end

    initial begin
	GTS_int = 1'b1;
	#(TOC_WIDTH)
	GTS_int = 1'b0;
    end

    initial begin 
	GRESTORE_int = 1'b0;
	#(GRES_START);
	GRESTORE_int = 1'b1;
	#(GRES_WIDTH);
	GRESTORE_int = 1'b0;
    end

endmodule
`endif
