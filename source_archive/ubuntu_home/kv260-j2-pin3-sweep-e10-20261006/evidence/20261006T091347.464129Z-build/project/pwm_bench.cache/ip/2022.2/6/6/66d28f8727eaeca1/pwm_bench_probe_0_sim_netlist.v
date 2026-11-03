// Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
// --------------------------------------------------------------------------------
// Tool Version: Vivado v.2022.2 (lin64) Build 3671981 Fri Oct 14 04:59:54 MDT 2022
// Date        : Tue Oct  6 02:16:07 2026
// Host        : ghmd-MRA-XXX running 64-bit Ubuntu 20.04.4 LTS
// Command     : write_verilog -force -mode funcsim -rename_top decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix -prefix
//               decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_ pwm_bench_probe_0_sim_netlist.v
// Design      : pwm_bench_probe_0
// Purpose     : This verilog netlist is a functional simulation representation of the design and should not be modified
//               or synthesized. This netlist cannot be used for SDF annotated simulation.
// Device      : xck26-sfvc784-2LV-c
// --------------------------------------------------------------------------------
`timescale 1 ps / 1 ps

module decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_aura_pwm_probe
   (servo_pwm,
    s_axi_rdata,
    s_axi_rresp,
    s_axi_bvalid_reg_0,
    s_axi_wready,
    s_axi_awready,
    s_axi_arready,
    s_axi_rvalid_reg_0,
    s_axi_bresp,
    s_axi_aclk,
    s_axi_awaddr,
    s_axi_wdata,
    s_axi_wstrb,
    s_axi_aresetn,
    s_axi_araddr,
    s_axi_awvalid,
    s_axi_wvalid,
    s_axi_arvalid,
    s_axi_bready,
    s_axi_rready);
  output servo_pwm;
  output [31:0]s_axi_rdata;
  output [0:0]s_axi_rresp;
  output s_axi_bvalid_reg_0;
  output s_axi_wready;
  output s_axi_awready;
  output s_axi_arready;
  output s_axi_rvalid_reg_0;
  output [0:0]s_axi_bresp;
  input s_axi_aclk;
  input [11:0]s_axi_awaddr;
  input [31:0]s_axi_wdata;
  input [3:0]s_axi_wstrb;
  input s_axi_aresetn;
  input [11:0]s_axi_araddr;
  input s_axi_awvalid;
  input s_axi_wvalid;
  input s_axi_arvalid;
  input s_axi_bready;
  input s_axi_rready;

  wire [11:0]aw_address;
  wire aw_pending;
  wire aw_pending0;
  wire aw_pending_i_1_n_0;
  wire burst_n_0;
  wire burst_n_1;
  wire burst_n_10;
  wire burst_n_11;
  wire burst_n_12;
  wire burst_n_13;
  wire burst_n_14;
  wire burst_n_15;
  wire burst_n_16;
  wire burst_n_17;
  wire burst_n_18;
  wire burst_n_19;
  wire burst_n_2;
  wire burst_n_20;
  wire burst_n_21;
  wire burst_n_22;
  wire burst_n_23;
  wire burst_n_24;
  wire burst_n_25;
  wire burst_n_26;
  wire burst_n_27;
  wire burst_n_28;
  wire burst_n_29;
  wire burst_n_3;
  wire burst_n_30;
  wire burst_n_31;
  wire burst_n_32;
  wire burst_n_33;
  wire burst_n_34;
  wire burst_n_35;
  wire burst_n_36;
  wire burst_n_37;
  wire burst_n_39;
  wire burst_n_4;
  wire burst_n_5;
  wire burst_n_6;
  wire burst_n_7;
  wire burst_n_8;
  wire burst_n_9;
  wire p_0_in_0;
  wire p_1_in;
  wire p_2_in;
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
  wire \s_axi_bresp[1]_i_4_n_0 ;
  wire \s_axi_bresp[1]_i_5_n_0 ;
  wire \s_axi_bresp[1]_i_7_n_0 ;
  wire s_axi_bvalid_i_1_n_0;
  wire s_axi_bvalid_reg_0;
  wire [31:0]s_axi_rdata;
  wire \s_axi_rdata[10]_i_3_n_0 ;
  wire \s_axi_rdata[12]_i_2_n_0 ;
  wire \s_axi_rdata[13]_i_2_n_0 ;
  wire \s_axi_rdata[15]_i_2_n_0 ;
  wire \s_axi_rdata[17]_i_3_n_0 ;
  wire \s_axi_rdata[17]_i_4_n_0 ;
  wire \s_axi_rdata[17]_i_5_n_0 ;
  wire \s_axi_rdata[19]_i_2_n_0 ;
  wire \s_axi_rdata[19]_i_3_n_0 ;
  wire \s_axi_rdata[19]_i_4_n_0 ;
  wire \s_axi_rdata[1]_i_3_n_0 ;
  wire \s_axi_rdata[1]_i_4_n_0 ;
  wire \s_axi_rdata[20]_i_2_n_0 ;
  wire \s_axi_rdata[22]_i_2_n_0 ;
  wire \s_axi_rdata[24]_i_2_n_0 ;
  wire \s_axi_rdata[25]_i_2_n_0 ;
  wire \s_axi_rdata[26]_i_2_n_0 ;
  wire \s_axi_rdata[2]_i_2_n_0 ;
  wire \s_axi_rdata[30]_i_2_n_0 ;
  wire \s_axi_rdata[31]_i_3_n_0 ;
  wire \s_axi_rdata[31]_i_4_n_0 ;
  wire \s_axi_rdata[31]_i_5_n_0 ;
  wire \s_axi_rdata[31]_i_6_n_0 ;
  wire \s_axi_rdata[3]_i_3_n_0 ;
  wire \s_axi_rdata[4]_i_2_n_0 ;
  wire \s_axi_rdata[4]_i_3_n_0 ;
  wire \s_axi_rdata[4]_i_5_n_0 ;
  wire \s_axi_rdata[5]_i_2_n_0 ;
  wire \s_axi_rdata[5]_i_4_n_0 ;
  wire \s_axi_rdata[6]_i_2_n_0 ;
  wire \s_axi_rdata[6]_i_3_n_0 ;
  wire \s_axi_rdata[9]_i_2_n_0 ;
  wire s_axi_rready;
  wire [0:0]s_axi_rresp;
  wire \s_axi_rresp[1]_i_1_n_0 ;
  wire \s_axi_rresp[1]_i_2_n_0 ;
  wire s_axi_rvalid01_out;
  wire s_axi_rvalid_i_1_n_0;
  wire s_axi_rvalid_reg_0;
  wire [31:0]s_axi_wdata;
  wire s_axi_wready;
  wire [3:0]s_axi_wstrb;
  wire s_axi_wvalid;
  wire [31:0]scratch;
  wire \scratch[15]_i_1_n_0 ;
  wire \scratch[23]_i_1_n_0 ;
  wire \scratch[31]_i_1_n_0 ;
  wire \scratch[7]_i_1_n_0 ;
  wire servo_pwm;
  wire [31:0]w_data;
  wire w_pending;
  wire w_pending0;
  wire w_pending_i_2_n_0;
  wire w_pending_reg_n_0;
  wire \w_strobes_reg_n_0_[3] ;

  LUT3 #(
    .INIT(8'h04)) 
    \aw_address[11]_i_1 
       (.I0(aw_pending),
        .I1(s_axi_awvalid),
        .I2(s_axi_bvalid_reg_0),
        .O(aw_pending0));
  FDRE #(
    .INIT(1'b0)) 
    \aw_address_reg[0] 
       (.C(s_axi_aclk),
        .CE(aw_pending0),
        .D(s_axi_awaddr[0]),
        .Q(aw_address[0]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \aw_address_reg[10] 
       (.C(s_axi_aclk),
        .CE(aw_pending0),
        .D(s_axi_awaddr[10]),
        .Q(aw_address[10]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \aw_address_reg[11] 
       (.C(s_axi_aclk),
        .CE(aw_pending0),
        .D(s_axi_awaddr[11]),
        .Q(aw_address[11]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \aw_address_reg[1] 
       (.C(s_axi_aclk),
        .CE(aw_pending0),
        .D(s_axi_awaddr[1]),
        .Q(aw_address[1]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \aw_address_reg[2] 
       (.C(s_axi_aclk),
        .CE(aw_pending0),
        .D(s_axi_awaddr[2]),
        .Q(aw_address[2]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \aw_address_reg[3] 
       (.C(s_axi_aclk),
        .CE(aw_pending0),
        .D(s_axi_awaddr[3]),
        .Q(aw_address[3]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \aw_address_reg[4] 
       (.C(s_axi_aclk),
        .CE(aw_pending0),
        .D(s_axi_awaddr[4]),
        .Q(aw_address[4]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \aw_address_reg[5] 
       (.C(s_axi_aclk),
        .CE(aw_pending0),
        .D(s_axi_awaddr[5]),
        .Q(aw_address[5]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \aw_address_reg[6] 
       (.C(s_axi_aclk),
        .CE(aw_pending0),
        .D(s_axi_awaddr[6]),
        .Q(aw_address[6]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \aw_address_reg[7] 
       (.C(s_axi_aclk),
        .CE(aw_pending0),
        .D(s_axi_awaddr[7]),
        .Q(aw_address[7]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \aw_address_reg[8] 
       (.C(s_axi_aclk),
        .CE(aw_pending0),
        .D(s_axi_awaddr[8]),
        .Q(aw_address[8]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \aw_address_reg[9] 
       (.C(s_axi_aclk),
        .CE(aw_pending0),
        .D(s_axi_awaddr[9]),
        .Q(aw_address[9]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  LUT3 #(
    .INIT(8'hF4)) 
    aw_pending_i_1
       (.I0(s_axi_bvalid_reg_0),
        .I1(s_axi_awvalid),
        .I2(aw_pending),
        .O(aw_pending_i_1_n_0));
  FDRE #(
    .INIT(1'b0)) 
    aw_pending_reg
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(aw_pending_i_1_n_0),
        .Q(aw_pending),
        .R(w_pending));
  decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_pwm_burst burst
       (.D({burst_n_6,burst_n_7,burst_n_8,burst_n_9,burst_n_10,burst_n_11,burst_n_12,burst_n_13,burst_n_14,burst_n_15,burst_n_16,burst_n_17,burst_n_18,burst_n_19,burst_n_20,burst_n_21,burst_n_22,burst_n_23,burst_n_24,burst_n_25,burst_n_26,burst_n_27,burst_n_28,burst_n_29,burst_n_30,burst_n_31,burst_n_32,burst_n_33,burst_n_34,burst_n_35,burst_n_36,burst_n_37}),
        .Q(aw_address),
        .\aw_address_reg[1] (burst_n_2),
        .\aw_address_reg[9] (burst_n_5),
        .aw_pending(aw_pending),
        .s_axi_aclk(s_axi_aclk),
        .s_axi_araddr(s_axi_araddr[6:2]),
        .s_axi_aresetn(s_axi_aresetn),
        .s_axi_bresp(s_axi_bresp),
        .\s_axi_bresp[1]_i_5 (w_data),
        .\s_axi_bresp[1]_i_9_0 ({\w_strobes_reg_n_0_[3] ,p_2_in,p_1_in,p_0_in_0}),
        .\s_axi_bresp_reg[1] (burst_n_39),
        .\s_axi_bresp_reg[1]_0 (w_pending_reg_n_0),
        .\s_axi_bresp_reg[1]_1 (s_axi_bvalid_reg_0),
        .\s_axi_bresp_reg[1]_2 (\s_axi_bresp[1]_i_4_n_0 ),
        .\s_axi_bresp_reg[1]_3 (\s_axi_bresp[1]_i_5_n_0 ),
        .\s_axi_rdata_reg[12] (\s_axi_rdata[12]_i_2_n_0 ),
        .\s_axi_rdata_reg[12]_0 (\s_axi_rdata[24]_i_2_n_0 ),
        .\s_axi_rdata_reg[14] (\s_axi_rdata[22]_i_2_n_0 ),
        .\s_axi_rdata_reg[15] (\s_axi_rdata[31]_i_4_n_0 ),
        .\s_axi_rdata_reg[15]_0 (\s_axi_rdata[15]_i_2_n_0 ),
        .\s_axi_rdata_reg[17] (\s_axi_rdata[17]_i_3_n_0 ),
        .\s_axi_rdata_reg[17]_0 (\s_axi_rdata[17]_i_4_n_0 ),
        .\s_axi_rdata_reg[17]_1 (\s_axi_rdata[17]_i_5_n_0 ),
        .\s_axi_rdata_reg[18] (\s_axi_rdata[20]_i_2_n_0 ),
        .\s_axi_rdata_reg[19] (\s_axi_rdata[19]_i_2_n_0 ),
        .\s_axi_rdata_reg[1] (\s_axi_rdata[1]_i_3_n_0 ),
        .\s_axi_rdata_reg[1]_0 (\s_axi_rdata[1]_i_4_n_0 ),
        .\s_axi_rdata_reg[25] (\s_axi_rdata[25]_i_2_n_0 ),
        .\s_axi_rdata_reg[26] (\s_axi_rdata[26]_i_2_n_0 ),
        .\s_axi_rdata_reg[2] (\s_axi_rdata[31]_i_3_n_0 ),
        .\s_axi_rdata_reg[2]_0 (\s_axi_rdata[9]_i_2_n_0 ),
        .\s_axi_rdata_reg[2]_1 (\s_axi_rdata[19]_i_3_n_0 ),
        .\s_axi_rdata_reg[2]_2 (\s_axi_rdata[2]_i_2_n_0 ),
        .\s_axi_rdata_reg[31] ({scratch[31:5],scratch[3],scratch[1:0]}),
        .\s_axi_rdata_reg[3] (\s_axi_rdata[13]_i_2_n_0 ),
        .\s_axi_rdata_reg[3]_0 (\s_axi_rdata[30]_i_2_n_0 ),
        .\s_axi_rdata_reg[3]_1 (\s_axi_rdata[3]_i_3_n_0 ),
        .\s_axi_rdata_reg[4] (\s_axi_rdata[4]_i_2_n_0 ),
        .\s_axi_rdata_reg[4]_0 (\s_axi_rdata[4]_i_3_n_0 ),
        .\s_axi_rdata_reg[4]_1 (\s_axi_rdata[4]_i_5_n_0 ),
        .\s_axi_rdata_reg[5] (\s_axi_rdata[5]_i_2_n_0 ),
        .\s_axi_rdata_reg[5]_0 (\s_axi_rdata[5]_i_4_n_0 ),
        .\s_axi_rdata_reg[6] (\s_axi_rdata[6]_i_2_n_0 ),
        .\s_axi_rdata_reg[6]_0 (\s_axi_rdata[6]_i_3_n_0 ),
        .\s_axi_rdata_reg[6]_1 (\s_axi_rdata[10]_i_3_n_0 ),
        .servo_pwm(servo_pwm),
        .\w_data_reg[0] (burst_n_0),
        .\w_data_reg[12] (burst_n_3),
        .\w_data_reg[21] (burst_n_4),
        .\w_data_reg[30] (burst_n_1));
  (* SOFT_HLUTNM = "soft_lutpair30" *) 
  LUT2 #(
    .INIT(4'h2)) 
    s_axi_arready_INST_0
       (.I0(s_axi_aresetn),
        .I1(s_axi_rvalid_reg_0),
        .O(s_axi_arready));
  (* SOFT_HLUTNM = "soft_lutpair27" *) 
  LUT3 #(
    .INIT(8'h04)) 
    s_axi_awready_INST_0
       (.I0(s_axi_bvalid_reg_0),
        .I1(s_axi_aresetn),
        .I2(aw_pending),
        .O(s_axi_awready));
  LUT1 #(
    .INIT(2'h1)) 
    \s_axi_bresp[1]_i_1 
       (.I0(s_axi_aresetn),
        .O(\s_axi_bresp[1]_i_1_n_0 ));
  LUT5 #(
    .INIT(32'hFFFFA2AA)) 
    \s_axi_bresp[1]_i_4 
       (.I0(aw_address[3]),
        .I1(aw_address[5]),
        .I2(aw_address[4]),
        .I3(aw_address[2]),
        .I4(\s_axi_bresp[1]_i_7_n_0 ),
        .O(\s_axi_bresp[1]_i_4_n_0 ));
  LUT4 #(
    .INIT(16'hFFFE)) 
    \s_axi_bresp[1]_i_5 
       (.I0(burst_n_0),
        .I1(burst_n_1),
        .I2(burst_n_4),
        .I3(burst_n_3),
        .O(\s_axi_bresp[1]_i_5_n_0 ));
  LUT5 #(
    .INIT(32'hFFFFFFFE)) 
    \s_axi_bresp[1]_i_7 
       (.I0(aw_address[6]),
        .I1(aw_address[7]),
        .I2(aw_address[0]),
        .I3(aw_address[1]),
        .I4(burst_n_5),
        .O(\s_axi_bresp[1]_i_7_n_0 ));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI BRESP" *) 
  FDRE \s_axi_bresp_reg[1] 
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(burst_n_39),
        .Q(s_axi_bresp),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  (* SOFT_HLUTNM = "soft_lutpair27" *) 
  LUT4 #(
    .INIT(16'h5C50)) 
    s_axi_bvalid_i_1
       (.I0(s_axi_bready),
        .I1(aw_pending),
        .I2(s_axi_bvalid_reg_0),
        .I3(w_pending_reg_n_0),
        .O(s_axi_bvalid_i_1_n_0));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI BVALID" *) 
  FDRE s_axi_bvalid_reg
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(s_axi_bvalid_i_1_n_0),
        .Q(s_axi_bvalid_reg_0),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  (* SOFT_HLUTNM = "soft_lutpair24" *) 
  LUT5 #(
    .INIT(32'h00000001)) 
    \s_axi_rdata[10]_i_3 
       (.I0(s_axi_araddr[11]),
        .I1(s_axi_araddr[10]),
        .I2(s_axi_araddr[0]),
        .I3(\s_axi_rdata[31]_i_5_n_0 ),
        .I4(s_axi_araddr[6]),
        .O(\s_axi_rdata[10]_i_3_n_0 ));
  LUT6 #(
    .INIT(64'h0000000100000000)) 
    \s_axi_rdata[12]_i_2 
       (.I0(\s_axi_rresp[1]_i_2_n_0 ),
        .I1(s_axi_araddr[2]),
        .I2(s_axi_araddr[3]),
        .I3(s_axi_araddr[5]),
        .I4(s_axi_araddr[4]),
        .I5(s_axi_araddr[6]),
        .O(\s_axi_rdata[12]_i_2_n_0 ));
  LUT6 #(
    .INIT(64'h0000000000000402)) 
    \s_axi_rdata[13]_i_2 
       (.I0(s_axi_araddr[6]),
        .I1(s_axi_araddr[4]),
        .I2(s_axi_araddr[5]),
        .I3(s_axi_araddr[3]),
        .I4(s_axi_araddr[2]),
        .I5(\s_axi_rresp[1]_i_2_n_0 ),
        .O(\s_axi_rdata[13]_i_2_n_0 ));
  (* SOFT_HLUTNM = "soft_lutpair26" *) 
  LUT4 #(
    .INIT(16'h0400)) 
    \s_axi_rdata[15]_i_2 
       (.I0(s_axi_araddr[3]),
        .I1(s_axi_araddr[5]),
        .I2(s_axi_araddr[4]),
        .I3(\s_axi_rdata[17]_i_4_n_0 ),
        .O(\s_axi_rdata[15]_i_2_n_0 ));
  (* SOFT_HLUTNM = "soft_lutpair21" *) 
  LUT5 #(
    .INIT(32'h00000001)) 
    \s_axi_rdata[17]_i_3 
       (.I0(s_axi_araddr[4]),
        .I1(s_axi_araddr[5]),
        .I2(s_axi_araddr[3]),
        .I3(s_axi_araddr[2]),
        .I4(\s_axi_rresp[1]_i_2_n_0 ),
        .O(\s_axi_rdata[17]_i_3_n_0 ));
  LUT6 #(
    .INIT(64'h0000000000000001)) 
    \s_axi_rdata[17]_i_4 
       (.I0(s_axi_araddr[6]),
        .I1(\s_axi_rdata[31]_i_5_n_0 ),
        .I2(s_axi_araddr[0]),
        .I3(s_axi_araddr[10]),
        .I4(s_axi_araddr[11]),
        .I5(s_axi_araddr[2]),
        .O(\s_axi_rdata[17]_i_4_n_0 ));
  LUT6 #(
    .INIT(64'h0000000100000000)) 
    \s_axi_rdata[17]_i_5 
       (.I0(s_axi_araddr[6]),
        .I1(\s_axi_rdata[31]_i_5_n_0 ),
        .I2(s_axi_araddr[0]),
        .I3(s_axi_araddr[10]),
        .I4(s_axi_araddr[11]),
        .I5(s_axi_araddr[2]),
        .O(\s_axi_rdata[17]_i_5_n_0 ));
  (* SOFT_HLUTNM = "soft_lutpair26" *) 
  LUT4 #(
    .INIT(16'h0040)) 
    \s_axi_rdata[19]_i_2 
       (.I0(s_axi_araddr[4]),
        .I1(\s_axi_rdata[17]_i_4_n_0 ),
        .I2(s_axi_araddr[3]),
        .I3(s_axi_araddr[5]),
        .O(\s_axi_rdata[19]_i_2_n_0 ));
  LUT6 #(
    .INIT(64'h0000000000020000)) 
    \s_axi_rdata[19]_i_3 
       (.I0(s_axi_araddr[4]),
        .I1(s_axi_araddr[6]),
        .I2(\s_axi_rdata[31]_i_5_n_0 ),
        .I3(\s_axi_rdata[31]_i_6_n_0 ),
        .I4(s_axi_araddr[2]),
        .I5(\s_axi_rdata[19]_i_4_n_0 ),
        .O(\s_axi_rdata[19]_i_3_n_0 ));
  (* SOFT_HLUTNM = "soft_lutpair21" *) 
  LUT2 #(
    .INIT(4'hE)) 
    \s_axi_rdata[19]_i_4 
       (.I0(s_axi_araddr[3]),
        .I1(s_axi_araddr[5]),
        .O(\s_axi_rdata[19]_i_4_n_0 ));
  (* SOFT_HLUTNM = "soft_lutpair20" *) 
  LUT5 #(
    .INIT(32'h40000000)) 
    \s_axi_rdata[1]_i_3 
       (.I0(s_axi_araddr[3]),
        .I1(s_axi_araddr[5]),
        .I2(s_axi_araddr[4]),
        .I3(\s_axi_rdata[10]_i_3_n_0 ),
        .I4(s_axi_araddr[2]),
        .O(\s_axi_rdata[1]_i_3_n_0 ));
  LUT6 #(
    .INIT(64'h0000000000000001)) 
    \s_axi_rdata[1]_i_4 
       (.I0(s_axi_araddr[6]),
        .I1(\s_axi_rdata[31]_i_5_n_0 ),
        .I2(s_axi_araddr[0]),
        .I3(s_axi_araddr[10]),
        .I4(s_axi_araddr[11]),
        .I5(s_axi_araddr[4]),
        .O(\s_axi_rdata[1]_i_4_n_0 ));
  (* SOFT_HLUTNM = "soft_lutpair20" *) 
  LUT5 #(
    .INIT(32'h10000700)) 
    \s_axi_rdata[20]_i_2 
       (.I0(s_axi_araddr[3]),
        .I1(s_axi_araddr[5]),
        .I2(s_axi_araddr[2]),
        .I3(\s_axi_rdata[10]_i_3_n_0 ),
        .I4(s_axi_araddr[4]),
        .O(\s_axi_rdata[20]_i_2_n_0 ));
  (* SOFT_HLUTNM = "soft_lutpair25" *) 
  LUT4 #(
    .INIT(16'h0444)) 
    \s_axi_rdata[22]_i_2 
       (.I0(s_axi_araddr[4]),
        .I1(\s_axi_rdata[17]_i_4_n_0 ),
        .I2(s_axi_araddr[5]),
        .I3(s_axi_araddr[3]),
        .O(\s_axi_rdata[22]_i_2_n_0 ));
  (* SOFT_HLUTNM = "soft_lutpair25" *) 
  LUT4 #(
    .INIT(16'h0600)) 
    \s_axi_rdata[24]_i_2 
       (.I0(s_axi_araddr[5]),
        .I1(s_axi_araddr[3]),
        .I2(s_axi_araddr[4]),
        .I3(\s_axi_rdata[17]_i_4_n_0 ),
        .O(\s_axi_rdata[24]_i_2_n_0 ));
  (* SOFT_HLUTNM = "soft_lutpair31" *) 
  LUT2 #(
    .INIT(4'hB)) 
    \s_axi_rdata[25]_i_2 
       (.I0(s_axi_araddr[5]),
        .I1(s_axi_araddr[3]),
        .O(\s_axi_rdata[25]_i_2_n_0 ));
  (* SOFT_HLUTNM = "soft_lutpair31" *) 
  LUT2 #(
    .INIT(4'h2)) 
    \s_axi_rdata[26]_i_2 
       (.I0(s_axi_araddr[5]),
        .I1(s_axi_araddr[3]),
        .O(\s_axi_rdata[26]_i_2_n_0 ));
  LUT6 #(
    .INIT(64'h00C4000000440000)) 
    \s_axi_rdata[2]_i_2 
       (.I0(s_axi_araddr[5]),
        .I1(\s_axi_rdata[10]_i_3_n_0 ),
        .I2(s_axi_araddr[2]),
        .I3(s_axi_araddr[4]),
        .I4(s_axi_araddr[3]),
        .I5(scratch[2]),
        .O(\s_axi_rdata[2]_i_2_n_0 ));
  LUT2 #(
    .INIT(4'h2)) 
    \s_axi_rdata[30]_i_2 
       (.I0(\s_axi_rdata[17]_i_4_n_0 ),
        .I1(s_axi_araddr[4]),
        .O(\s_axi_rdata[30]_i_2_n_0 ));
  LUT2 #(
    .INIT(4'h2)) 
    \s_axi_rdata[31]_i_1 
       (.I0(s_axi_arvalid),
        .I1(s_axi_rvalid_reg_0),
        .O(s_axi_rvalid01_out));
  (* SOFT_HLUTNM = "soft_lutpair23" *) 
  LUT5 #(
    .INIT(32'h80000000)) 
    \s_axi_rdata[31]_i_3 
       (.I0(s_axi_araddr[3]),
        .I1(s_axi_araddr[5]),
        .I2(\s_axi_rdata[10]_i_3_n_0 ),
        .I3(s_axi_araddr[2]),
        .I4(s_axi_araddr[4]),
        .O(\s_axi_rdata[31]_i_3_n_0 ));
  LUT6 #(
    .INIT(64'h0000000000010000)) 
    \s_axi_rdata[31]_i_4 
       (.I0(\s_axi_rdata[6]_i_3_n_0 ),
        .I1(s_axi_araddr[6]),
        .I2(\s_axi_rdata[31]_i_5_n_0 ),
        .I3(\s_axi_rdata[31]_i_6_n_0 ),
        .I4(s_axi_araddr[2]),
        .I5(s_axi_araddr[4]),
        .O(\s_axi_rdata[31]_i_4_n_0 ));
  LUT4 #(
    .INIT(16'hFFFE)) 
    \s_axi_rdata[31]_i_5 
       (.I0(s_axi_araddr[7]),
        .I1(s_axi_araddr[1]),
        .I2(s_axi_araddr[9]),
        .I3(s_axi_araddr[8]),
        .O(\s_axi_rdata[31]_i_5_n_0 ));
  LUT3 #(
    .INIT(8'hFE)) 
    \s_axi_rdata[31]_i_6 
       (.I0(s_axi_araddr[11]),
        .I1(s_axi_araddr[10]),
        .I2(s_axi_araddr[0]),
        .O(\s_axi_rdata[31]_i_6_n_0 ));
  (* SOFT_HLUTNM = "soft_lutpair22" *) 
  LUT5 #(
    .INIT(32'h00010000)) 
    \s_axi_rdata[3]_i_3 
       (.I0(s_axi_araddr[2]),
        .I1(\s_axi_rdata[31]_i_6_n_0 ),
        .I2(\s_axi_rdata[31]_i_5_n_0 ),
        .I3(s_axi_araddr[6]),
        .I4(s_axi_araddr[4]),
        .O(\s_axi_rdata[3]_i_3_n_0 ));
  LUT6 #(
    .INIT(64'h0000010000000003)) 
    \s_axi_rdata[4]_i_2 
       (.I0(s_axi_araddr[6]),
        .I1(\s_axi_rresp[1]_i_2_n_0 ),
        .I2(s_axi_araddr[2]),
        .I3(s_axi_araddr[3]),
        .I4(s_axi_araddr[5]),
        .I5(s_axi_araddr[4]),
        .O(\s_axi_rdata[4]_i_2_n_0 ));
  (* SOFT_HLUTNM = "soft_lutpair22" *) 
  LUT5 #(
    .INIT(32'h00020000)) 
    \s_axi_rdata[4]_i_3 
       (.I0(s_axi_araddr[2]),
        .I1(\s_axi_rdata[31]_i_6_n_0 ),
        .I2(\s_axi_rdata[31]_i_5_n_0 ),
        .I3(s_axi_araddr[6]),
        .I4(s_axi_araddr[4]),
        .O(\s_axi_rdata[4]_i_3_n_0 ));
  LUT6 #(
    .INIT(64'h00B00000C0300000)) 
    \s_axi_rdata[4]_i_5 
       (.I0(scratch[4]),
        .I1(s_axi_araddr[2]),
        .I2(\s_axi_rdata[10]_i_3_n_0 ),
        .I3(s_axi_araddr[4]),
        .I4(s_axi_araddr[5]),
        .I5(s_axi_araddr[3]),
        .O(\s_axi_rdata[4]_i_5_n_0 ));
  LUT6 #(
    .INIT(64'h0001000000000000)) 
    \s_axi_rdata[5]_i_2 
       (.I0(s_axi_araddr[4]),
        .I1(\s_axi_rdata[31]_i_6_n_0 ),
        .I2(\s_axi_rdata[31]_i_5_n_0 ),
        .I3(s_axi_araddr[6]),
        .I4(s_axi_araddr[5]),
        .I5(s_axi_araddr[3]),
        .O(\s_axi_rdata[5]_i_2_n_0 ));
  (* SOFT_HLUTNM = "soft_lutpair23" *) 
  LUT4 #(
    .INIT(16'h4020)) 
    \s_axi_rdata[5]_i_4 
       (.I0(s_axi_araddr[3]),
        .I1(s_axi_araddr[2]),
        .I2(\s_axi_rdata[10]_i_3_n_0 ),
        .I3(s_axi_araddr[4]),
        .O(\s_axi_rdata[5]_i_4_n_0 ));
  LUT6 #(
    .INIT(64'h0003000300020205)) 
    \s_axi_rdata[6]_i_2 
       (.I0(s_axi_araddr[4]),
        .I1(s_axi_araddr[6]),
        .I2(\s_axi_rresp[1]_i_2_n_0 ),
        .I3(s_axi_araddr[2]),
        .I4(s_axi_araddr[5]),
        .I5(s_axi_araddr[3]),
        .O(\s_axi_rdata[6]_i_2_n_0 ));
  (* SOFT_HLUTNM = "soft_lutpair29" *) 
  LUT2 #(
    .INIT(4'h7)) 
    \s_axi_rdata[6]_i_3 
       (.I0(s_axi_araddr[3]),
        .I1(s_axi_araddr[5]),
        .O(\s_axi_rdata[6]_i_3_n_0 ));
  (* SOFT_HLUTNM = "soft_lutpair29" *) 
  LUT3 #(
    .INIT(8'h08)) 
    \s_axi_rdata[9]_i_2 
       (.I0(\s_axi_rdata[17]_i_4_n_0 ),
        .I1(s_axi_araddr[3]),
        .I2(s_axi_araddr[5]),
        .O(\s_axi_rdata[9]_i_2_n_0 ));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[0] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(burst_n_37),
        .Q(s_axi_rdata[0]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[10] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(burst_n_27),
        .Q(s_axi_rdata[10]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[11] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(burst_n_26),
        .Q(s_axi_rdata[11]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[12] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(burst_n_25),
        .Q(s_axi_rdata[12]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[13] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(burst_n_24),
        .Q(s_axi_rdata[13]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[14] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(burst_n_23),
        .Q(s_axi_rdata[14]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[15] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(burst_n_22),
        .Q(s_axi_rdata[15]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[16] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(burst_n_21),
        .Q(s_axi_rdata[16]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[17] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(burst_n_20),
        .Q(s_axi_rdata[17]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[18] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(burst_n_19),
        .Q(s_axi_rdata[18]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[19] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(burst_n_18),
        .Q(s_axi_rdata[19]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[1] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(burst_n_36),
        .Q(s_axi_rdata[1]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[20] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(burst_n_17),
        .Q(s_axi_rdata[20]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[21] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(burst_n_16),
        .Q(s_axi_rdata[21]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[22] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(burst_n_15),
        .Q(s_axi_rdata[22]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[23] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(burst_n_14),
        .Q(s_axi_rdata[23]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[24] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(burst_n_13),
        .Q(s_axi_rdata[24]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[25] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(burst_n_12),
        .Q(s_axi_rdata[25]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[26] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(burst_n_11),
        .Q(s_axi_rdata[26]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[27] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(burst_n_10),
        .Q(s_axi_rdata[27]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[28] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(burst_n_9),
        .Q(s_axi_rdata[28]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[29] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(burst_n_8),
        .Q(s_axi_rdata[29]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[2] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(burst_n_35),
        .Q(s_axi_rdata[2]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[30] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(burst_n_7),
        .Q(s_axi_rdata[30]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[31] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(burst_n_6),
        .Q(s_axi_rdata[31]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[3] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(burst_n_34),
        .Q(s_axi_rdata[3]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[4] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(burst_n_33),
        .Q(s_axi_rdata[4]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[5] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(burst_n_32),
        .Q(s_axi_rdata[5]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[6] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(burst_n_31),
        .Q(s_axi_rdata[6]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[7] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(burst_n_30),
        .Q(s_axi_rdata[7]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[8] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(burst_n_29),
        .Q(s_axi_rdata[8]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[9] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(burst_n_28),
        .Q(s_axi_rdata[9]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  LUT6 #(
    .INIT(64'hEEEEEEEFEEEEEEEA)) 
    \s_axi_rresp[1]_i_1 
       (.I0(\s_axi_rresp[1]_i_2_n_0 ),
        .I1(s_axi_araddr[6]),
        .I2(s_axi_araddr[5]),
        .I3(s_axi_araddr[3]),
        .I4(s_axi_araddr[2]),
        .I5(s_axi_araddr[4]),
        .O(\s_axi_rresp[1]_i_1_n_0 ));
  (* SOFT_HLUTNM = "soft_lutpair24" *) 
  LUT4 #(
    .INIT(16'hFFFE)) 
    \s_axi_rresp[1]_i_2 
       (.I0(\s_axi_rdata[31]_i_5_n_0 ),
        .I1(s_axi_araddr[0]),
        .I2(s_axi_araddr[10]),
        .I3(s_axi_araddr[11]),
        .O(\s_axi_rresp[1]_i_2_n_0 ));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RRESP" *) 
  FDRE \s_axi_rresp_reg[1] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(\s_axi_rresp[1]_i_1_n_0 ),
        .Q(s_axi_rresp),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  (* SOFT_HLUTNM = "soft_lutpair30" *) 
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
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  (* SOFT_HLUTNM = "soft_lutpair28" *) 
  LUT3 #(
    .INIT(8'h04)) 
    s_axi_wready_INST_0
       (.I0(s_axi_bvalid_reg_0),
        .I1(s_axi_aresetn),
        .I2(w_pending_reg_n_0),
        .O(s_axi_wready));
  LUT6 #(
    .INIT(64'h0000200000000000)) 
    \scratch[15]_i_1 
       (.I0(aw_address[5]),
        .I1(aw_address[4]),
        .I2(aw_address[2]),
        .I3(aw_address[3]),
        .I4(burst_n_2),
        .I5(p_1_in),
        .O(\scratch[15]_i_1_n_0 ));
  LUT6 #(
    .INIT(64'h0000200000000000)) 
    \scratch[23]_i_1 
       (.I0(aw_address[5]),
        .I1(aw_address[4]),
        .I2(aw_address[2]),
        .I3(aw_address[3]),
        .I4(burst_n_2),
        .I5(p_2_in),
        .O(\scratch[23]_i_1_n_0 ));
  LUT6 #(
    .INIT(64'h0000200000000000)) 
    \scratch[31]_i_1 
       (.I0(aw_address[5]),
        .I1(aw_address[4]),
        .I2(aw_address[2]),
        .I3(aw_address[3]),
        .I4(burst_n_2),
        .I5(\w_strobes_reg_n_0_[3] ),
        .O(\scratch[31]_i_1_n_0 ));
  LUT6 #(
    .INIT(64'h0000200000000000)) 
    \scratch[7]_i_1 
       (.I0(aw_address[5]),
        .I1(aw_address[4]),
        .I2(aw_address[2]),
        .I3(aw_address[3]),
        .I4(burst_n_2),
        .I5(p_0_in_0),
        .O(\scratch[7]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[0] 
       (.C(s_axi_aclk),
        .CE(\scratch[7]_i_1_n_0 ),
        .D(w_data[0]),
        .Q(scratch[0]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[10] 
       (.C(s_axi_aclk),
        .CE(\scratch[15]_i_1_n_0 ),
        .D(w_data[10]),
        .Q(scratch[10]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[11] 
       (.C(s_axi_aclk),
        .CE(\scratch[15]_i_1_n_0 ),
        .D(w_data[11]),
        .Q(scratch[11]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[12] 
       (.C(s_axi_aclk),
        .CE(\scratch[15]_i_1_n_0 ),
        .D(w_data[12]),
        .Q(scratch[12]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[13] 
       (.C(s_axi_aclk),
        .CE(\scratch[15]_i_1_n_0 ),
        .D(w_data[13]),
        .Q(scratch[13]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[14] 
       (.C(s_axi_aclk),
        .CE(\scratch[15]_i_1_n_0 ),
        .D(w_data[14]),
        .Q(scratch[14]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[15] 
       (.C(s_axi_aclk),
        .CE(\scratch[15]_i_1_n_0 ),
        .D(w_data[15]),
        .Q(scratch[15]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[16] 
       (.C(s_axi_aclk),
        .CE(\scratch[23]_i_1_n_0 ),
        .D(w_data[16]),
        .Q(scratch[16]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[17] 
       (.C(s_axi_aclk),
        .CE(\scratch[23]_i_1_n_0 ),
        .D(w_data[17]),
        .Q(scratch[17]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[18] 
       (.C(s_axi_aclk),
        .CE(\scratch[23]_i_1_n_0 ),
        .D(w_data[18]),
        .Q(scratch[18]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[19] 
       (.C(s_axi_aclk),
        .CE(\scratch[23]_i_1_n_0 ),
        .D(w_data[19]),
        .Q(scratch[19]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[1] 
       (.C(s_axi_aclk),
        .CE(\scratch[7]_i_1_n_0 ),
        .D(w_data[1]),
        .Q(scratch[1]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[20] 
       (.C(s_axi_aclk),
        .CE(\scratch[23]_i_1_n_0 ),
        .D(w_data[20]),
        .Q(scratch[20]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[21] 
       (.C(s_axi_aclk),
        .CE(\scratch[23]_i_1_n_0 ),
        .D(w_data[21]),
        .Q(scratch[21]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[22] 
       (.C(s_axi_aclk),
        .CE(\scratch[23]_i_1_n_0 ),
        .D(w_data[22]),
        .Q(scratch[22]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[23] 
       (.C(s_axi_aclk),
        .CE(\scratch[23]_i_1_n_0 ),
        .D(w_data[23]),
        .Q(scratch[23]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[24] 
       (.C(s_axi_aclk),
        .CE(\scratch[31]_i_1_n_0 ),
        .D(w_data[24]),
        .Q(scratch[24]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[25] 
       (.C(s_axi_aclk),
        .CE(\scratch[31]_i_1_n_0 ),
        .D(w_data[25]),
        .Q(scratch[25]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[26] 
       (.C(s_axi_aclk),
        .CE(\scratch[31]_i_1_n_0 ),
        .D(w_data[26]),
        .Q(scratch[26]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[27] 
       (.C(s_axi_aclk),
        .CE(\scratch[31]_i_1_n_0 ),
        .D(w_data[27]),
        .Q(scratch[27]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[28] 
       (.C(s_axi_aclk),
        .CE(\scratch[31]_i_1_n_0 ),
        .D(w_data[28]),
        .Q(scratch[28]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[29] 
       (.C(s_axi_aclk),
        .CE(\scratch[31]_i_1_n_0 ),
        .D(w_data[29]),
        .Q(scratch[29]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[2] 
       (.C(s_axi_aclk),
        .CE(\scratch[7]_i_1_n_0 ),
        .D(w_data[2]),
        .Q(scratch[2]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[30] 
       (.C(s_axi_aclk),
        .CE(\scratch[31]_i_1_n_0 ),
        .D(w_data[30]),
        .Q(scratch[30]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[31] 
       (.C(s_axi_aclk),
        .CE(\scratch[31]_i_1_n_0 ),
        .D(w_data[31]),
        .Q(scratch[31]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[3] 
       (.C(s_axi_aclk),
        .CE(\scratch[7]_i_1_n_0 ),
        .D(w_data[3]),
        .Q(scratch[3]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[4] 
       (.C(s_axi_aclk),
        .CE(\scratch[7]_i_1_n_0 ),
        .D(w_data[4]),
        .Q(scratch[4]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[5] 
       (.C(s_axi_aclk),
        .CE(\scratch[7]_i_1_n_0 ),
        .D(w_data[5]),
        .Q(scratch[5]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[6] 
       (.C(s_axi_aclk),
        .CE(\scratch[7]_i_1_n_0 ),
        .D(w_data[6]),
        .Q(scratch[6]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[7] 
       (.C(s_axi_aclk),
        .CE(\scratch[7]_i_1_n_0 ),
        .D(w_data[7]),
        .Q(scratch[7]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[8] 
       (.C(s_axi_aclk),
        .CE(\scratch[15]_i_1_n_0 ),
        .D(w_data[8]),
        .Q(scratch[8]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[9] 
       (.C(s_axi_aclk),
        .CE(\scratch[15]_i_1_n_0 ),
        .D(w_data[9]),
        .Q(scratch[9]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  LUT3 #(
    .INIT(8'h04)) 
    \w_data[31]_i_1 
       (.I0(w_pending_reg_n_0),
        .I1(s_axi_wvalid),
        .I2(s_axi_bvalid_reg_0),
        .O(w_pending0));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[0] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[0]),
        .Q(w_data[0]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[10] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[10]),
        .Q(w_data[10]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[11] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[11]),
        .Q(w_data[11]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[12] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[12]),
        .Q(w_data[12]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[13] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[13]),
        .Q(w_data[13]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[14] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[14]),
        .Q(w_data[14]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[15] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[15]),
        .Q(w_data[15]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[16] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[16]),
        .Q(w_data[16]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[17] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[17]),
        .Q(w_data[17]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[18] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[18]),
        .Q(w_data[18]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[19] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[19]),
        .Q(w_data[19]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[1] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[1]),
        .Q(w_data[1]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[20] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[20]),
        .Q(w_data[20]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[21] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[21]),
        .Q(w_data[21]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[22] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[22]),
        .Q(w_data[22]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[23] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[23]),
        .Q(w_data[23]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[24] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[24]),
        .Q(w_data[24]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[25] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[25]),
        .Q(w_data[25]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[26] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[26]),
        .Q(w_data[26]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[27] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[27]),
        .Q(w_data[27]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[28] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[28]),
        .Q(w_data[28]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[29] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[29]),
        .Q(w_data[29]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[2] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[2]),
        .Q(w_data[2]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[30] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[30]),
        .Q(w_data[30]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[31] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[31]),
        .Q(w_data[31]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[3] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[3]),
        .Q(w_data[3]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[4] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[4]),
        .Q(w_data[4]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[5] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[5]),
        .Q(w_data[5]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[6] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[6]),
        .Q(w_data[6]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[7] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[7]),
        .Q(w_data[7]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[8] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[8]),
        .Q(w_data[8]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[9] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[9]),
        .Q(w_data[9]),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  LUT4 #(
    .INIT(16'h20FF)) 
    w_pending_i_1
       (.I0(aw_pending),
        .I1(s_axi_bvalid_reg_0),
        .I2(w_pending_reg_n_0),
        .I3(s_axi_aresetn),
        .O(w_pending));
  (* SOFT_HLUTNM = "soft_lutpair28" *) 
  LUT3 #(
    .INIT(8'hF4)) 
    w_pending_i_2
       (.I0(s_axi_bvalid_reg_0),
        .I1(s_axi_wvalid),
        .I2(w_pending_reg_n_0),
        .O(w_pending_i_2_n_0));
  FDRE #(
    .INIT(1'b0)) 
    w_pending_reg
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(w_pending_i_2_n_0),
        .Q(w_pending_reg_n_0),
        .R(w_pending));
  FDRE #(
    .INIT(1'b0)) 
    \w_strobes_reg[0] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wstrb[0]),
        .Q(p_0_in_0),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \w_strobes_reg[1] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wstrb[1]),
        .Q(p_1_in),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \w_strobes_reg[2] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wstrb[2]),
        .Q(p_2_in),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \w_strobes_reg[3] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wstrb[3]),
        .Q(\w_strobes_reg_n_0_[3] ),
        .R(\s_axi_bresp[1]_i_1_n_0 ));
endmodule

(* CHECK_LICENSE_TYPE = "pwm_bench_probe_0,aura_pwm_probe,{}" *) (* DowngradeIPIdentifiedWarnings = "yes" *) (* IP_DEFINITION_SOURCE = "package_project" *) 
(* X_CORE_INFO = "aura_pwm_probe,Vivado 2022.2" *) 
(* NotValidForBitStream *)
module decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix
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
    s_axi_rready,
    servo_pwm);
  (* X_INTERFACE_INFO = "xilinx.com:signal:clock:1.0 s_axi_aclk CLK" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME s_axi_aclk, ASSOCIATED_BUSIF S_AXI, ASSOCIATED_RESET s_axi_aresetn, FREQ_HZ 99999001, FREQ_TOLERANCE_HZ 0, PHASE 0.0, CLK_DOMAIN pwm_bench_PS_0_0_pl_clk0, INSERT_VIP 0" *) input s_axi_aclk;
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
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RREADY" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME S_AXI, PROTOCOL AXI4LITE, DATA_WIDTH 32, ADDR_WIDTH 12, READ_WRITE_MODE READ_WRITE, FREQ_HZ 99999001, ID_WIDTH 0, AWUSER_WIDTH 0, ARUSER_WIDTH 0, WUSER_WIDTH 0, RUSER_WIDTH 0, BUSER_WIDTH 0, HAS_BURST 0, HAS_LOCK 0, HAS_PROT 1, HAS_CACHE 0, HAS_QOS 0, HAS_REGION 0, HAS_WSTRB 1, HAS_BRESP 1, HAS_RRESP 1, SUPPORTS_NARROW_BURST 0, NUM_READ_OUTSTANDING 1, NUM_WRITE_OUTSTANDING 1, MAX_BURST_LENGTH 1, PHASE 0.0, CLK_DOMAIN pwm_bench_PS_0_0_pl_clk0, NUM_READ_THREADS 4, NUM_WRITE_THREADS 4, RUSER_BITS_PER_BYTE 0, WUSER_BITS_PER_BYTE 0, INSERT_VIP 0" *) input s_axi_rready;
  output servo_pwm;

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
  wire servo_pwm;

  assign s_axi_bresp[1] = \^s_axi_bresp [1];
  assign s_axi_bresp[0] = \<const0> ;
  assign s_axi_rresp[1] = \^s_axi_rresp [1];
  assign s_axi_rresp[0] = \<const0> ;
  GND GND
       (.G(\<const0> ));
  decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_aura_pwm_probe inst
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
        .s_axi_wvalid(s_axi_wvalid),
        .servo_pwm(servo_pwm));
endmodule

module decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_pwm_burst
   (\w_data_reg[0] ,
    \w_data_reg[30] ,
    \aw_address_reg[1] ,
    \w_data_reg[12] ,
    \w_data_reg[21] ,
    \aw_address_reg[9] ,
    D,
    servo_pwm,
    \s_axi_bresp_reg[1] ,
    s_axi_aclk,
    s_axi_aresetn,
    Q,
    \s_axi_bresp[1]_i_5 ,
    \s_axi_bresp[1]_i_9_0 ,
    \s_axi_bresp_reg[1]_0 ,
    \s_axi_bresp_reg[1]_1 ,
    aw_pending,
    \s_axi_rdata_reg[17] ,
    s_axi_araddr,
    \s_axi_rdata_reg[17]_0 ,
    \s_axi_rdata_reg[31] ,
    \s_axi_rdata_reg[17]_1 ,
    \s_axi_rdata_reg[2] ,
    \s_axi_rdata_reg[2]_0 ,
    \s_axi_rdata_reg[2]_1 ,
    \s_axi_rdata_reg[2]_2 ,
    \s_axi_rdata_reg[3] ,
    \s_axi_rdata_reg[3]_0 ,
    \s_axi_rdata_reg[3]_1 ,
    \s_axi_rdata_reg[5] ,
    \s_axi_rdata_reg[6] ,
    \s_axi_rdata_reg[6]_0 ,
    \s_axi_rdata_reg[6]_1 ,
    \s_axi_rdata_reg[15] ,
    \s_axi_rdata_reg[15]_0 ,
    \s_axi_rdata_reg[19] ,
    \s_axi_rdata_reg[18] ,
    \s_axi_rdata_reg[12] ,
    \s_axi_rdata_reg[12]_0 ,
    \s_axi_rdata_reg[5]_0 ,
    \s_axi_rdata_reg[1] ,
    \s_axi_rdata_reg[14] ,
    \s_axi_rdata_reg[4] ,
    \s_axi_rdata_reg[4]_0 ,
    \s_axi_rdata_reg[4]_1 ,
    \s_axi_rdata_reg[1]_0 ,
    \s_axi_rdata_reg[25] ,
    \s_axi_rdata_reg[26] ,
    s_axi_bresp,
    \s_axi_bresp_reg[1]_2 ,
    \s_axi_bresp_reg[1]_3 );
  output \w_data_reg[0] ;
  output \w_data_reg[30] ;
  output \aw_address_reg[1] ;
  output \w_data_reg[12] ;
  output \w_data_reg[21] ;
  output \aw_address_reg[9] ;
  output [31:0]D;
  output servo_pwm;
  output \s_axi_bresp_reg[1] ;
  input s_axi_aclk;
  input s_axi_aresetn;
  input [11:0]Q;
  input [31:0]\s_axi_bresp[1]_i_5 ;
  input [3:0]\s_axi_bresp[1]_i_9_0 ;
  input \s_axi_bresp_reg[1]_0 ;
  input \s_axi_bresp_reg[1]_1 ;
  input aw_pending;
  input \s_axi_rdata_reg[17] ;
  input [4:0]s_axi_araddr;
  input \s_axi_rdata_reg[17]_0 ;
  input [29:0]\s_axi_rdata_reg[31] ;
  input \s_axi_rdata_reg[17]_1 ;
  input \s_axi_rdata_reg[2] ;
  input \s_axi_rdata_reg[2]_0 ;
  input \s_axi_rdata_reg[2]_1 ;
  input \s_axi_rdata_reg[2]_2 ;
  input \s_axi_rdata_reg[3] ;
  input \s_axi_rdata_reg[3]_0 ;
  input \s_axi_rdata_reg[3]_1 ;
  input \s_axi_rdata_reg[5] ;
  input \s_axi_rdata_reg[6] ;
  input \s_axi_rdata_reg[6]_0 ;
  input \s_axi_rdata_reg[6]_1 ;
  input \s_axi_rdata_reg[15] ;
  input \s_axi_rdata_reg[15]_0 ;
  input \s_axi_rdata_reg[19] ;
  input \s_axi_rdata_reg[18] ;
  input \s_axi_rdata_reg[12] ;
  input \s_axi_rdata_reg[12]_0 ;
  input \s_axi_rdata_reg[5]_0 ;
  input \s_axi_rdata_reg[1] ;
  input \s_axi_rdata_reg[14] ;
  input \s_axi_rdata_reg[4] ;
  input \s_axi_rdata_reg[4]_0 ;
  input \s_axi_rdata_reg[4]_1 ;
  input \s_axi_rdata_reg[1]_0 ;
  input \s_axi_rdata_reg[25] ;
  input \s_axi_rdata_reg[26] ;
  input [0:0]s_axi_bresp;
  input \s_axi_bresp_reg[1]_2 ;
  input \s_axi_bresp_reg[1]_3 ;

  wire [31:0]D;
  wire [11:0]Q;
  wire \aw_address_reg[1] ;
  wire \aw_address_reg[9] ;
  wire aw_pending;
  wire busy;
  wire busy_i_1_n_0;
  wire [31:1]data0;
  wire [31:0]dwell_frame;
  wire \dwell_frame[31]_i_10_n_0 ;
  wire \dwell_frame[31]_i_11_n_0 ;
  wire \dwell_frame[31]_i_12_n_0 ;
  wire \dwell_frame[31]_i_13_n_0 ;
  wire \dwell_frame[31]_i_14_n_0 ;
  wire \dwell_frame[31]_i_15_n_0 ;
  wire \dwell_frame[31]_i_16_n_0 ;
  wire \dwell_frame[31]_i_17_n_0 ;
  wire \dwell_frame[31]_i_18_n_0 ;
  wire \dwell_frame[31]_i_19_n_0 ;
  wire \dwell_frame[31]_i_1_n_0 ;
  wire \dwell_frame[31]_i_20_n_0 ;
  wire \dwell_frame[31]_i_21_n_0 ;
  wire \dwell_frame[31]_i_2_n_0 ;
  wire \dwell_frame[31]_i_4_n_0 ;
  wire \dwell_frame[31]_i_5_n_0 ;
  wire \dwell_frame[31]_i_6_n_0 ;
  wire \dwell_frame[31]_i_7_n_0 ;
  wire \dwell_frame[31]_i_8_n_0 ;
  wire [31:0]dwell_frame_0;
  wire \dwell_frame_reg[16]_i_2_n_0 ;
  wire \dwell_frame_reg[16]_i_2_n_1 ;
  wire \dwell_frame_reg[16]_i_2_n_2 ;
  wire \dwell_frame_reg[16]_i_2_n_3 ;
  wire \dwell_frame_reg[16]_i_2_n_4 ;
  wire \dwell_frame_reg[16]_i_2_n_5 ;
  wire \dwell_frame_reg[16]_i_2_n_6 ;
  wire \dwell_frame_reg[16]_i_2_n_7 ;
  wire \dwell_frame_reg[24]_i_2_n_0 ;
  wire \dwell_frame_reg[24]_i_2_n_1 ;
  wire \dwell_frame_reg[24]_i_2_n_2 ;
  wire \dwell_frame_reg[24]_i_2_n_3 ;
  wire \dwell_frame_reg[24]_i_2_n_4 ;
  wire \dwell_frame_reg[24]_i_2_n_5 ;
  wire \dwell_frame_reg[24]_i_2_n_6 ;
  wire \dwell_frame_reg[24]_i_2_n_7 ;
  wire \dwell_frame_reg[31]_i_9_n_2 ;
  wire \dwell_frame_reg[31]_i_9_n_3 ;
  wire \dwell_frame_reg[31]_i_9_n_4 ;
  wire \dwell_frame_reg[31]_i_9_n_5 ;
  wire \dwell_frame_reg[31]_i_9_n_6 ;
  wire \dwell_frame_reg[31]_i_9_n_7 ;
  wire \dwell_frame_reg[8]_i_2_n_0 ;
  wire \dwell_frame_reg[8]_i_2_n_1 ;
  wire \dwell_frame_reg[8]_i_2_n_2 ;
  wire \dwell_frame_reg[8]_i_2_n_3 ;
  wire \dwell_frame_reg[8]_i_2_n_4 ;
  wire \dwell_frame_reg[8]_i_2_n_5 ;
  wire \dwell_frame_reg[8]_i_2_n_6 ;
  wire \dwell_frame_reg[8]_i_2_n_7 ;
  wire i__carry__0_i_10_n_0;
  wire i__carry__0_i_10_n_1;
  wire i__carry__0_i_10_n_2;
  wire i__carry__0_i_10_n_3;
  wire i__carry__0_i_10_n_4;
  wire i__carry__0_i_10_n_5;
  wire i__carry__0_i_10_n_6;
  wire i__carry__0_i_10_n_7;
  wire i__carry__0_i_11_n_2;
  wire i__carry__0_i_11_n_3;
  wire i__carry__0_i_11_n_4;
  wire i__carry__0_i_11_n_5;
  wire i__carry__0_i_11_n_6;
  wire i__carry__0_i_11_n_7;
  wire i__carry__0_i_1_n_0;
  wire i__carry__0_i_2_n_0;
  wire i__carry__0_i_3_n_0;
  wire i__carry__0_i_4_n_0;
  wire i__carry__0_i_5_n_0;
  wire i__carry__0_i_6_n_0;
  wire i__carry__0_i_7_n_0;
  wire i__carry__0_i_8_n_0;
  wire i__carry__0_i_9_n_0;
  wire i__carry_i_10_n_0;
  wire i__carry_i_11_n_0;
  wire i__carry_i_12_n_0;
  wire i__carry_i_13_n_0;
  wire i__carry_i_14_n_0;
  wire i__carry_i_15_n_0;
  wire i__carry_i_16_n_0;
  wire i__carry_i_16_n_1;
  wire i__carry_i_16_n_2;
  wire i__carry_i_16_n_3;
  wire i__carry_i_16_n_4;
  wire i__carry_i_16_n_5;
  wire i__carry_i_16_n_6;
  wire i__carry_i_16_n_7;
  wire i__carry_i_17_n_0;
  wire i__carry_i_17_n_1;
  wire i__carry_i_17_n_2;
  wire i__carry_i_17_n_3;
  wire i__carry_i_17_n_4;
  wire i__carry_i_17_n_5;
  wire i__carry_i_17_n_6;
  wire i__carry_i_17_n_7;
  wire i__carry_i_1_n_0;
  wire i__carry_i_2_n_0;
  wire i__carry_i_3_n_0;
  wire i__carry_i_4_n_0;
  wire i__carry_i_5_n_0;
  wire i__carry_i_6_n_0;
  wire i__carry_i_7_n_0;
  wire i__carry_i_8_n_0;
  wire i__carry_i_9_n_0;
  wire [31:0]p_0_in;
  wire \phase[0]_i_1_n_0 ;
  wire [31:0]phase_reg;
  wire \phase_reg[0]_i_2_n_0 ;
  wire \phase_reg[0]_i_2_n_1 ;
  wire \phase_reg[0]_i_2_n_10 ;
  wire \phase_reg[0]_i_2_n_11 ;
  wire \phase_reg[0]_i_2_n_12 ;
  wire \phase_reg[0]_i_2_n_13 ;
  wire \phase_reg[0]_i_2_n_14 ;
  wire \phase_reg[0]_i_2_n_15 ;
  wire \phase_reg[0]_i_2_n_2 ;
  wire \phase_reg[0]_i_2_n_3 ;
  wire \phase_reg[0]_i_2_n_4 ;
  wire \phase_reg[0]_i_2_n_5 ;
  wire \phase_reg[0]_i_2_n_6 ;
  wire \phase_reg[0]_i_2_n_7 ;
  wire \phase_reg[0]_i_2_n_8 ;
  wire \phase_reg[0]_i_2_n_9 ;
  wire \phase_reg[16]_i_1_n_0 ;
  wire \phase_reg[16]_i_1_n_1 ;
  wire \phase_reg[16]_i_1_n_10 ;
  wire \phase_reg[16]_i_1_n_11 ;
  wire \phase_reg[16]_i_1_n_12 ;
  wire \phase_reg[16]_i_1_n_13 ;
  wire \phase_reg[16]_i_1_n_14 ;
  wire \phase_reg[16]_i_1_n_15 ;
  wire \phase_reg[16]_i_1_n_2 ;
  wire \phase_reg[16]_i_1_n_3 ;
  wire \phase_reg[16]_i_1_n_4 ;
  wire \phase_reg[16]_i_1_n_5 ;
  wire \phase_reg[16]_i_1_n_6 ;
  wire \phase_reg[16]_i_1_n_7 ;
  wire \phase_reg[16]_i_1_n_8 ;
  wire \phase_reg[16]_i_1_n_9 ;
  wire \phase_reg[24]_i_1_n_1 ;
  wire \phase_reg[24]_i_1_n_10 ;
  wire \phase_reg[24]_i_1_n_11 ;
  wire \phase_reg[24]_i_1_n_12 ;
  wire \phase_reg[24]_i_1_n_13 ;
  wire \phase_reg[24]_i_1_n_14 ;
  wire \phase_reg[24]_i_1_n_15 ;
  wire \phase_reg[24]_i_1_n_2 ;
  wire \phase_reg[24]_i_1_n_3 ;
  wire \phase_reg[24]_i_1_n_4 ;
  wire \phase_reg[24]_i_1_n_5 ;
  wire \phase_reg[24]_i_1_n_6 ;
  wire \phase_reg[24]_i_1_n_7 ;
  wire \phase_reg[24]_i_1_n_8 ;
  wire \phase_reg[24]_i_1_n_9 ;
  wire \phase_reg[8]_i_1_n_0 ;
  wire \phase_reg[8]_i_1_n_1 ;
  wire \phase_reg[8]_i_1_n_10 ;
  wire \phase_reg[8]_i_1_n_11 ;
  wire \phase_reg[8]_i_1_n_12 ;
  wire \phase_reg[8]_i_1_n_13 ;
  wire \phase_reg[8]_i_1_n_14 ;
  wire \phase_reg[8]_i_1_n_15 ;
  wire \phase_reg[8]_i_1_n_2 ;
  wire \phase_reg[8]_i_1_n_3 ;
  wire \phase_reg[8]_i_1_n_4 ;
  wire \phase_reg[8]_i_1_n_5 ;
  wire \phase_reg[8]_i_1_n_6 ;
  wire \phase_reg[8]_i_1_n_7 ;
  wire \phase_reg[8]_i_1_n_8 ;
  wire \phase_reg[8]_i_1_n_9 ;
  wire \pwm0_inferred__0/i__carry__0_n_0 ;
  wire \pwm0_inferred__0/i__carry__0_n_1 ;
  wire \pwm0_inferred__0/i__carry__0_n_2 ;
  wire \pwm0_inferred__0/i__carry__0_n_3 ;
  wire \pwm0_inferred__0/i__carry__0_n_4 ;
  wire \pwm0_inferred__0/i__carry__0_n_5 ;
  wire \pwm0_inferred__0/i__carry__0_n_6 ;
  wire \pwm0_inferred__0/i__carry__0_n_7 ;
  wire \pwm0_inferred__0/i__carry_n_0 ;
  wire \pwm0_inferred__0/i__carry_n_1 ;
  wire \pwm0_inferred__0/i__carry_n_2 ;
  wire \pwm0_inferred__0/i__carry_n_3 ;
  wire \pwm0_inferred__0/i__carry_n_4 ;
  wire \pwm0_inferred__0/i__carry_n_5 ;
  wire \pwm0_inferred__0/i__carry_n_6 ;
  wire \pwm0_inferred__0/i__carry_n_7 ;
  wire pwm_i_1_n_0;
  wire pwm_i_2_n_0;
  wire pwm_i_3_n_0;
  wire pwm_i_4_n_0;
  wire pwm_i_5_n_0;
  wire pwm_i_6_n_0;
  wire pwm_i_7_n_0;
  wire pwm_i_8_n_0;
  wire pwm_i_9_n_0;
  wire s_axi_aclk;
  wire [4:0]s_axi_araddr;
  wire s_axi_aresetn;
  wire [0:0]s_axi_bresp;
  wire \s_axi_bresp[1]_i_12_n_0 ;
  wire \s_axi_bresp[1]_i_13_n_0 ;
  wire \s_axi_bresp[1]_i_14_n_0 ;
  wire \s_axi_bresp[1]_i_15_n_0 ;
  wire \s_axi_bresp[1]_i_16_n_0 ;
  wire \s_axi_bresp[1]_i_3_n_0 ;
  wire [31:0]\s_axi_bresp[1]_i_5 ;
  wire \s_axi_bresp[1]_i_6_n_0 ;
  wire [3:0]\s_axi_bresp[1]_i_9_0 ;
  wire \s_axi_bresp_reg[1] ;
  wire \s_axi_bresp_reg[1]_0 ;
  wire \s_axi_bresp_reg[1]_1 ;
  wire \s_axi_bresp_reg[1]_2 ;
  wire \s_axi_bresp_reg[1]_3 ;
  wire \s_axi_rdata[0]_i_2_n_0 ;
  wire \s_axi_rdata[10]_i_2_n_0 ;
  wire \s_axi_rdata[17]_i_2_n_0 ;
  wire \s_axi_rdata[1]_i_2_n_0 ;
  wire \s_axi_rdata[3]_i_2_n_0 ;
  wire \s_axi_rdata[4]_i_4_n_0 ;
  wire \s_axi_rdata[5]_i_3_n_0 ;
  wire \s_axi_rdata[8]_i_2_n_0 ;
  wire \s_axi_rdata[9]_i_3_n_0 ;
  wire \s_axi_rdata_reg[12] ;
  wire \s_axi_rdata_reg[12]_0 ;
  wire \s_axi_rdata_reg[14] ;
  wire \s_axi_rdata_reg[15] ;
  wire \s_axi_rdata_reg[15]_0 ;
  wire \s_axi_rdata_reg[17] ;
  wire \s_axi_rdata_reg[17]_0 ;
  wire \s_axi_rdata_reg[17]_1 ;
  wire \s_axi_rdata_reg[18] ;
  wire \s_axi_rdata_reg[19] ;
  wire \s_axi_rdata_reg[1] ;
  wire \s_axi_rdata_reg[1]_0 ;
  wire \s_axi_rdata_reg[25] ;
  wire \s_axi_rdata_reg[26] ;
  wire \s_axi_rdata_reg[2] ;
  wire \s_axi_rdata_reg[2]_0 ;
  wire \s_axi_rdata_reg[2]_1 ;
  wire \s_axi_rdata_reg[2]_2 ;
  wire [29:0]\s_axi_rdata_reg[31] ;
  wire \s_axi_rdata_reg[3] ;
  wire \s_axi_rdata_reg[3]_0 ;
  wire \s_axi_rdata_reg[3]_1 ;
  wire \s_axi_rdata_reg[4] ;
  wire \s_axi_rdata_reg[4]_0 ;
  wire \s_axi_rdata_reg[4]_1 ;
  wire \s_axi_rdata_reg[5] ;
  wire \s_axi_rdata_reg[5]_0 ;
  wire \s_axi_rdata_reg[6] ;
  wire \s_axi_rdata_reg[6]_0 ;
  wire \s_axi_rdata_reg[6]_1 ;
  wire select_high;
  wire select_high_i_1_n_0;
  wire servo_pwm;
  wire \w_data_reg[0] ;
  wire \w_data_reg[12] ;
  wire \w_data_reg[21] ;
  wire \w_data_reg[30] ;
  wire [7:6]\NLW_dwell_frame_reg[31]_i_9_CO_UNCONNECTED ;
  wire [7:7]\NLW_dwell_frame_reg[31]_i_9_O_UNCONNECTED ;
  wire [7:6]NLW_i__carry__0_i_11_CO_UNCONNECTED;
  wire [7:7]NLW_i__carry__0_i_11_O_UNCONNECTED;
  wire [7:7]\NLW_phase_reg[24]_i_1_CO_UNCONNECTED ;
  wire [7:0]\NLW_pwm0_inferred__0/i__carry_O_UNCONNECTED ;
  wire [7:0]\NLW_pwm0_inferred__0/i__carry__0_O_UNCONNECTED ;

  LUT6 #(
    .INIT(64'hFFFFFFFF00000004)) 
    busy_i_1
       (.I0(pwm_i_5_n_0),
        .I1(\s_axi_bresp[1]_i_5 [1]),
        .I2(\s_axi_bresp[1]_i_5 [11]),
        .I3(\s_axi_bresp[1]_i_5 [9]),
        .I4(\s_axi_bresp[1]_i_5 [10]),
        .I5(busy),
        .O(busy_i_1_n_0));
  FDRE #(
    .INIT(1'b0)) 
    busy_reg
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(busy_i_1_n_0),
        .Q(busy),
        .R(pwm_i_1_n_0));
  (* SOFT_HLUTNM = "soft_lutpair2" *) 
  LUT1 #(
    .INIT(2'h1)) 
    \dwell_frame[0]_i_1 
       (.I0(dwell_frame[0]),
        .O(dwell_frame_0[0]));
  (* SOFT_HLUTNM = "soft_lutpair9" *) 
  LUT2 #(
    .INIT(4'h8)) 
    \dwell_frame[10]_i_1 
       (.I0(\dwell_frame[31]_i_8_n_0 ),
        .I1(data0[10]),
        .O(dwell_frame_0[10]));
  (* SOFT_HLUTNM = "soft_lutpair10" *) 
  LUT2 #(
    .INIT(4'h8)) 
    \dwell_frame[11]_i_1 
       (.I0(\dwell_frame[31]_i_8_n_0 ),
        .I1(data0[11]),
        .O(dwell_frame_0[11]));
  (* SOFT_HLUTNM = "soft_lutpair10" *) 
  LUT2 #(
    .INIT(4'h8)) 
    \dwell_frame[12]_i_1 
       (.I0(\dwell_frame[31]_i_8_n_0 ),
        .I1(data0[12]),
        .O(dwell_frame_0[12]));
  (* SOFT_HLUTNM = "soft_lutpair11" *) 
  LUT2 #(
    .INIT(4'h8)) 
    \dwell_frame[13]_i_1 
       (.I0(\dwell_frame[31]_i_8_n_0 ),
        .I1(data0[13]),
        .O(dwell_frame_0[13]));
  (* SOFT_HLUTNM = "soft_lutpair11" *) 
  LUT2 #(
    .INIT(4'h8)) 
    \dwell_frame[14]_i_1 
       (.I0(\dwell_frame[31]_i_8_n_0 ),
        .I1(data0[14]),
        .O(dwell_frame_0[14]));
  (* SOFT_HLUTNM = "soft_lutpair12" *) 
  LUT2 #(
    .INIT(4'h8)) 
    \dwell_frame[15]_i_1 
       (.I0(\dwell_frame[31]_i_8_n_0 ),
        .I1(data0[15]),
        .O(dwell_frame_0[15]));
  (* SOFT_HLUTNM = "soft_lutpair12" *) 
  LUT2 #(
    .INIT(4'h8)) 
    \dwell_frame[16]_i_1 
       (.I0(\dwell_frame[31]_i_8_n_0 ),
        .I1(data0[16]),
        .O(dwell_frame_0[16]));
  (* SOFT_HLUTNM = "soft_lutpair13" *) 
  LUT2 #(
    .INIT(4'h8)) 
    \dwell_frame[17]_i_1 
       (.I0(\dwell_frame[31]_i_8_n_0 ),
        .I1(data0[17]),
        .O(dwell_frame_0[17]));
  (* SOFT_HLUTNM = "soft_lutpair13" *) 
  LUT2 #(
    .INIT(4'h8)) 
    \dwell_frame[18]_i_1 
       (.I0(\dwell_frame[31]_i_8_n_0 ),
        .I1(data0[18]),
        .O(dwell_frame_0[18]));
  (* SOFT_HLUTNM = "soft_lutpair14" *) 
  LUT2 #(
    .INIT(4'h8)) 
    \dwell_frame[19]_i_1 
       (.I0(\dwell_frame[31]_i_8_n_0 ),
        .I1(data0[19]),
        .O(dwell_frame_0[19]));
  (* SOFT_HLUTNM = "soft_lutpair5" *) 
  LUT2 #(
    .INIT(4'h8)) 
    \dwell_frame[1]_i_1 
       (.I0(\dwell_frame[31]_i_8_n_0 ),
        .I1(data0[1]),
        .O(dwell_frame_0[1]));
  (* SOFT_HLUTNM = "soft_lutpair14" *) 
  LUT2 #(
    .INIT(4'h8)) 
    \dwell_frame[20]_i_1 
       (.I0(\dwell_frame[31]_i_8_n_0 ),
        .I1(data0[20]),
        .O(dwell_frame_0[20]));
  (* SOFT_HLUTNM = "soft_lutpair15" *) 
  LUT2 #(
    .INIT(4'h8)) 
    \dwell_frame[21]_i_1 
       (.I0(\dwell_frame[31]_i_8_n_0 ),
        .I1(data0[21]),
        .O(dwell_frame_0[21]));
  (* SOFT_HLUTNM = "soft_lutpair15" *) 
  LUT2 #(
    .INIT(4'h8)) 
    \dwell_frame[22]_i_1 
       (.I0(\dwell_frame[31]_i_8_n_0 ),
        .I1(data0[22]),
        .O(dwell_frame_0[22]));
  (* SOFT_HLUTNM = "soft_lutpair16" *) 
  LUT2 #(
    .INIT(4'h8)) 
    \dwell_frame[23]_i_1 
       (.I0(\dwell_frame[31]_i_8_n_0 ),
        .I1(data0[23]),
        .O(dwell_frame_0[23]));
  (* SOFT_HLUTNM = "soft_lutpair16" *) 
  LUT2 #(
    .INIT(4'h8)) 
    \dwell_frame[24]_i_1 
       (.I0(\dwell_frame[31]_i_8_n_0 ),
        .I1(data0[24]),
        .O(dwell_frame_0[24]));
  (* SOFT_HLUTNM = "soft_lutpair17" *) 
  LUT2 #(
    .INIT(4'h8)) 
    \dwell_frame[25]_i_1 
       (.I0(\dwell_frame[31]_i_8_n_0 ),
        .I1(data0[25]),
        .O(dwell_frame_0[25]));
  (* SOFT_HLUTNM = "soft_lutpair17" *) 
  LUT2 #(
    .INIT(4'h8)) 
    \dwell_frame[26]_i_1 
       (.I0(\dwell_frame[31]_i_8_n_0 ),
        .I1(data0[26]),
        .O(dwell_frame_0[26]));
  (* SOFT_HLUTNM = "soft_lutpair18" *) 
  LUT2 #(
    .INIT(4'h8)) 
    \dwell_frame[27]_i_1 
       (.I0(\dwell_frame[31]_i_8_n_0 ),
        .I1(data0[27]),
        .O(dwell_frame_0[27]));
  (* SOFT_HLUTNM = "soft_lutpair18" *) 
  LUT2 #(
    .INIT(4'h8)) 
    \dwell_frame[28]_i_1 
       (.I0(\dwell_frame[31]_i_8_n_0 ),
        .I1(data0[28]),
        .O(dwell_frame_0[28]));
  (* SOFT_HLUTNM = "soft_lutpair19" *) 
  LUT2 #(
    .INIT(4'h8)) 
    \dwell_frame[29]_i_1 
       (.I0(\dwell_frame[31]_i_8_n_0 ),
        .I1(data0[29]),
        .O(dwell_frame_0[29]));
  (* SOFT_HLUTNM = "soft_lutpair5" *) 
  LUT2 #(
    .INIT(4'h8)) 
    \dwell_frame[2]_i_1 
       (.I0(\dwell_frame[31]_i_8_n_0 ),
        .I1(data0[2]),
        .O(dwell_frame_0[2]));
  (* SOFT_HLUTNM = "soft_lutpair19" *) 
  LUT2 #(
    .INIT(4'h8)) 
    \dwell_frame[30]_i_1 
       (.I0(\dwell_frame[31]_i_8_n_0 ),
        .I1(data0[30]),
        .O(dwell_frame_0[30]));
  LUT3 #(
    .INIT(8'h7F)) 
    \dwell_frame[31]_i_1 
       (.I0(s_axi_aresetn),
        .I1(busy),
        .I2(pwm_i_3_n_0),
        .O(\dwell_frame[31]_i_1_n_0 ));
  LUT4 #(
    .INIT(16'h0400)) 
    \dwell_frame[31]_i_10 
       (.I0(phase_reg[7]),
        .I1(phase_reg[6]),
        .I2(phase_reg[4]),
        .I3(phase_reg[5]),
        .O(\dwell_frame[31]_i_10_n_0 ));
  LUT4 #(
    .INIT(16'h0004)) 
    \dwell_frame[31]_i_11 
       (.I0(phase_reg[14]),
        .I1(phase_reg[15]),
        .I2(phase_reg[13]),
        .I3(phase_reg[12]),
        .O(\dwell_frame[31]_i_11_n_0 ));
  LUT4 #(
    .INIT(16'h0100)) 
    \dwell_frame[31]_i_12 
       (.I0(phase_reg[23]),
        .I1(phase_reg[22]),
        .I2(phase_reg[21]),
        .I3(phase_reg[20]),
        .O(\dwell_frame[31]_i_12_n_0 ));
  LUT4 #(
    .INIT(16'h0001)) 
    \dwell_frame[31]_i_13 
       (.I0(phase_reg[31]),
        .I1(phase_reg[30]),
        .I2(phase_reg[29]),
        .I3(phase_reg[28]),
        .O(\dwell_frame[31]_i_13_n_0 ));
  LUT5 #(
    .INIT(32'hFFFFFFFE)) 
    \dwell_frame[31]_i_14 
       (.I0(dwell_frame[10]),
        .I1(dwell_frame[11]),
        .I2(dwell_frame[8]),
        .I3(dwell_frame[9]),
        .I4(\dwell_frame[31]_i_18_n_0 ),
        .O(\dwell_frame[31]_i_14_n_0 ));
  LUT5 #(
    .INIT(32'hFFFFFEFF)) 
    \dwell_frame[31]_i_15 
       (.I0(dwell_frame[2]),
        .I1(dwell_frame[3]),
        .I2(dwell_frame[1]),
        .I3(dwell_frame[0]),
        .I4(\dwell_frame[31]_i_19_n_0 ),
        .O(\dwell_frame[31]_i_15_n_0 ));
  LUT5 #(
    .INIT(32'hFFFFFFFE)) 
    \dwell_frame[31]_i_16 
       (.I0(dwell_frame[26]),
        .I1(dwell_frame[27]),
        .I2(dwell_frame[24]),
        .I3(dwell_frame[25]),
        .I4(\dwell_frame[31]_i_20_n_0 ),
        .O(\dwell_frame[31]_i_16_n_0 ));
  LUT5 #(
    .INIT(32'hFFFFFFFE)) 
    \dwell_frame[31]_i_17 
       (.I0(dwell_frame[18]),
        .I1(dwell_frame[19]),
        .I2(dwell_frame[16]),
        .I3(dwell_frame[17]),
        .I4(\dwell_frame[31]_i_21_n_0 ),
        .O(\dwell_frame[31]_i_17_n_0 ));
  LUT4 #(
    .INIT(16'hFFFE)) 
    \dwell_frame[31]_i_18 
       (.I0(dwell_frame[13]),
        .I1(dwell_frame[12]),
        .I2(dwell_frame[15]),
        .I3(dwell_frame[14]),
        .O(\dwell_frame[31]_i_18_n_0 ));
  LUT4 #(
    .INIT(16'hFFF7)) 
    \dwell_frame[31]_i_19 
       (.I0(dwell_frame[5]),
        .I1(dwell_frame[4]),
        .I2(dwell_frame[7]),
        .I3(dwell_frame[6]),
        .O(\dwell_frame[31]_i_19_n_0 ));
  LUT4 #(
    .INIT(16'h8000)) 
    \dwell_frame[31]_i_2 
       (.I0(\dwell_frame[31]_i_4_n_0 ),
        .I1(\dwell_frame[31]_i_5_n_0 ),
        .I2(\dwell_frame[31]_i_6_n_0 ),
        .I3(\dwell_frame[31]_i_7_n_0 ),
        .O(\dwell_frame[31]_i_2_n_0 ));
  LUT4 #(
    .INIT(16'hFFFE)) 
    \dwell_frame[31]_i_20 
       (.I0(dwell_frame[29]),
        .I1(dwell_frame[28]),
        .I2(dwell_frame[31]),
        .I3(dwell_frame[30]),
        .O(\dwell_frame[31]_i_20_n_0 ));
  LUT4 #(
    .INIT(16'hFFFE)) 
    \dwell_frame[31]_i_21 
       (.I0(dwell_frame[21]),
        .I1(dwell_frame[20]),
        .I2(dwell_frame[23]),
        .I3(dwell_frame[22]),
        .O(\dwell_frame[31]_i_21_n_0 ));
  LUT2 #(
    .INIT(4'h8)) 
    \dwell_frame[31]_i_3 
       (.I0(\dwell_frame[31]_i_8_n_0 ),
        .I1(data0[31]),
        .O(dwell_frame_0[31]));
  LUT5 #(
    .INIT(32'h00800000)) 
    \dwell_frame[31]_i_4 
       (.I0(phase_reg[0]),
        .I1(phase_reg[1]),
        .I2(phase_reg[3]),
        .I3(phase_reg[2]),
        .I4(\dwell_frame[31]_i_10_n_0 ),
        .O(\dwell_frame[31]_i_4_n_0 ));
  LUT5 #(
    .INIT(32'h00100000)) 
    \dwell_frame[31]_i_5 
       (.I0(phase_reg[8]),
        .I1(phase_reg[9]),
        .I2(phase_reg[10]),
        .I3(phase_reg[11]),
        .I4(\dwell_frame[31]_i_11_n_0 ),
        .O(\dwell_frame[31]_i_5_n_0 ));
  LUT5 #(
    .INIT(32'h20000000)) 
    \dwell_frame[31]_i_6 
       (.I0(phase_reg[17]),
        .I1(phase_reg[16]),
        .I2(phase_reg[18]),
        .I3(phase_reg[19]),
        .I4(\dwell_frame[31]_i_12_n_0 ),
        .O(\dwell_frame[31]_i_6_n_0 ));
  LUT5 #(
    .INIT(32'h00010000)) 
    \dwell_frame[31]_i_7 
       (.I0(phase_reg[24]),
        .I1(phase_reg[25]),
        .I2(phase_reg[26]),
        .I3(phase_reg[27]),
        .I4(\dwell_frame[31]_i_13_n_0 ),
        .O(\dwell_frame[31]_i_7_n_0 ));
  LUT4 #(
    .INIT(16'hFFFE)) 
    \dwell_frame[31]_i_8 
       (.I0(\dwell_frame[31]_i_14_n_0 ),
        .I1(\dwell_frame[31]_i_15_n_0 ),
        .I2(\dwell_frame[31]_i_16_n_0 ),
        .I3(\dwell_frame[31]_i_17_n_0 ),
        .O(\dwell_frame[31]_i_8_n_0 ));
  (* SOFT_HLUTNM = "soft_lutpair6" *) 
  LUT2 #(
    .INIT(4'h8)) 
    \dwell_frame[3]_i_1 
       (.I0(\dwell_frame[31]_i_8_n_0 ),
        .I1(data0[3]),
        .O(dwell_frame_0[3]));
  (* SOFT_HLUTNM = "soft_lutpair6" *) 
  LUT2 #(
    .INIT(4'h8)) 
    \dwell_frame[4]_i_1 
       (.I0(\dwell_frame[31]_i_8_n_0 ),
        .I1(data0[4]),
        .O(dwell_frame_0[4]));
  (* SOFT_HLUTNM = "soft_lutpair7" *) 
  LUT2 #(
    .INIT(4'h8)) 
    \dwell_frame[5]_i_1 
       (.I0(\dwell_frame[31]_i_8_n_0 ),
        .I1(data0[5]),
        .O(dwell_frame_0[5]));
  (* SOFT_HLUTNM = "soft_lutpair7" *) 
  LUT2 #(
    .INIT(4'h8)) 
    \dwell_frame[6]_i_1 
       (.I0(\dwell_frame[31]_i_8_n_0 ),
        .I1(data0[6]),
        .O(dwell_frame_0[6]));
  (* SOFT_HLUTNM = "soft_lutpair8" *) 
  LUT2 #(
    .INIT(4'h8)) 
    \dwell_frame[7]_i_1 
       (.I0(\dwell_frame[31]_i_8_n_0 ),
        .I1(data0[7]),
        .O(dwell_frame_0[7]));
  (* SOFT_HLUTNM = "soft_lutpair8" *) 
  LUT2 #(
    .INIT(4'h8)) 
    \dwell_frame[8]_i_1 
       (.I0(\dwell_frame[31]_i_8_n_0 ),
        .I1(data0[8]),
        .O(dwell_frame_0[8]));
  (* SOFT_HLUTNM = "soft_lutpair9" *) 
  LUT2 #(
    .INIT(4'h8)) 
    \dwell_frame[9]_i_1 
       (.I0(\dwell_frame[31]_i_8_n_0 ),
        .I1(data0[9]),
        .O(dwell_frame_0[9]));
  FDRE #(
    .INIT(1'b0)) 
    \dwell_frame_reg[0] 
       (.C(s_axi_aclk),
        .CE(\dwell_frame[31]_i_2_n_0 ),
        .D(dwell_frame_0[0]),
        .Q(dwell_frame[0]),
        .R(\dwell_frame[31]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \dwell_frame_reg[10] 
       (.C(s_axi_aclk),
        .CE(\dwell_frame[31]_i_2_n_0 ),
        .D(dwell_frame_0[10]),
        .Q(dwell_frame[10]),
        .R(\dwell_frame[31]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \dwell_frame_reg[11] 
       (.C(s_axi_aclk),
        .CE(\dwell_frame[31]_i_2_n_0 ),
        .D(dwell_frame_0[11]),
        .Q(dwell_frame[11]),
        .R(\dwell_frame[31]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \dwell_frame_reg[12] 
       (.C(s_axi_aclk),
        .CE(\dwell_frame[31]_i_2_n_0 ),
        .D(dwell_frame_0[12]),
        .Q(dwell_frame[12]),
        .R(\dwell_frame[31]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \dwell_frame_reg[13] 
       (.C(s_axi_aclk),
        .CE(\dwell_frame[31]_i_2_n_0 ),
        .D(dwell_frame_0[13]),
        .Q(dwell_frame[13]),
        .R(\dwell_frame[31]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \dwell_frame_reg[14] 
       (.C(s_axi_aclk),
        .CE(\dwell_frame[31]_i_2_n_0 ),
        .D(dwell_frame_0[14]),
        .Q(dwell_frame[14]),
        .R(\dwell_frame[31]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \dwell_frame_reg[15] 
       (.C(s_axi_aclk),
        .CE(\dwell_frame[31]_i_2_n_0 ),
        .D(dwell_frame_0[15]),
        .Q(dwell_frame[15]),
        .R(\dwell_frame[31]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \dwell_frame_reg[16] 
       (.C(s_axi_aclk),
        .CE(\dwell_frame[31]_i_2_n_0 ),
        .D(dwell_frame_0[16]),
        .Q(dwell_frame[16]),
        .R(\dwell_frame[31]_i_1_n_0 ));
  (* ADDER_THRESHOLD = "35" *) 
  CARRY8 \dwell_frame_reg[16]_i_2 
       (.CI(\dwell_frame_reg[8]_i_2_n_0 ),
        .CI_TOP(1'b0),
        .CO({\dwell_frame_reg[16]_i_2_n_0 ,\dwell_frame_reg[16]_i_2_n_1 ,\dwell_frame_reg[16]_i_2_n_2 ,\dwell_frame_reg[16]_i_2_n_3 ,\dwell_frame_reg[16]_i_2_n_4 ,\dwell_frame_reg[16]_i_2_n_5 ,\dwell_frame_reg[16]_i_2_n_6 ,\dwell_frame_reg[16]_i_2_n_7 }),
        .DI({1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0}),
        .O(data0[16:9]),
        .S(dwell_frame[16:9]));
  FDRE #(
    .INIT(1'b0)) 
    \dwell_frame_reg[17] 
       (.C(s_axi_aclk),
        .CE(\dwell_frame[31]_i_2_n_0 ),
        .D(dwell_frame_0[17]),
        .Q(dwell_frame[17]),
        .R(\dwell_frame[31]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \dwell_frame_reg[18] 
       (.C(s_axi_aclk),
        .CE(\dwell_frame[31]_i_2_n_0 ),
        .D(dwell_frame_0[18]),
        .Q(dwell_frame[18]),
        .R(\dwell_frame[31]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \dwell_frame_reg[19] 
       (.C(s_axi_aclk),
        .CE(\dwell_frame[31]_i_2_n_0 ),
        .D(dwell_frame_0[19]),
        .Q(dwell_frame[19]),
        .R(\dwell_frame[31]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \dwell_frame_reg[1] 
       (.C(s_axi_aclk),
        .CE(\dwell_frame[31]_i_2_n_0 ),
        .D(dwell_frame_0[1]),
        .Q(dwell_frame[1]),
        .R(\dwell_frame[31]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \dwell_frame_reg[20] 
       (.C(s_axi_aclk),
        .CE(\dwell_frame[31]_i_2_n_0 ),
        .D(dwell_frame_0[20]),
        .Q(dwell_frame[20]),
        .R(\dwell_frame[31]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \dwell_frame_reg[21] 
       (.C(s_axi_aclk),
        .CE(\dwell_frame[31]_i_2_n_0 ),
        .D(dwell_frame_0[21]),
        .Q(dwell_frame[21]),
        .R(\dwell_frame[31]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \dwell_frame_reg[22] 
       (.C(s_axi_aclk),
        .CE(\dwell_frame[31]_i_2_n_0 ),
        .D(dwell_frame_0[22]),
        .Q(dwell_frame[22]),
        .R(\dwell_frame[31]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \dwell_frame_reg[23] 
       (.C(s_axi_aclk),
        .CE(\dwell_frame[31]_i_2_n_0 ),
        .D(dwell_frame_0[23]),
        .Q(dwell_frame[23]),
        .R(\dwell_frame[31]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \dwell_frame_reg[24] 
       (.C(s_axi_aclk),
        .CE(\dwell_frame[31]_i_2_n_0 ),
        .D(dwell_frame_0[24]),
        .Q(dwell_frame[24]),
        .R(\dwell_frame[31]_i_1_n_0 ));
  (* ADDER_THRESHOLD = "35" *) 
  CARRY8 \dwell_frame_reg[24]_i_2 
       (.CI(\dwell_frame_reg[16]_i_2_n_0 ),
        .CI_TOP(1'b0),
        .CO({\dwell_frame_reg[24]_i_2_n_0 ,\dwell_frame_reg[24]_i_2_n_1 ,\dwell_frame_reg[24]_i_2_n_2 ,\dwell_frame_reg[24]_i_2_n_3 ,\dwell_frame_reg[24]_i_2_n_4 ,\dwell_frame_reg[24]_i_2_n_5 ,\dwell_frame_reg[24]_i_2_n_6 ,\dwell_frame_reg[24]_i_2_n_7 }),
        .DI({1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0}),
        .O(data0[24:17]),
        .S(dwell_frame[24:17]));
  FDRE #(
    .INIT(1'b0)) 
    \dwell_frame_reg[25] 
       (.C(s_axi_aclk),
        .CE(\dwell_frame[31]_i_2_n_0 ),
        .D(dwell_frame_0[25]),
        .Q(dwell_frame[25]),
        .R(\dwell_frame[31]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \dwell_frame_reg[26] 
       (.C(s_axi_aclk),
        .CE(\dwell_frame[31]_i_2_n_0 ),
        .D(dwell_frame_0[26]),
        .Q(dwell_frame[26]),
        .R(\dwell_frame[31]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \dwell_frame_reg[27] 
       (.C(s_axi_aclk),
        .CE(\dwell_frame[31]_i_2_n_0 ),
        .D(dwell_frame_0[27]),
        .Q(dwell_frame[27]),
        .R(\dwell_frame[31]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \dwell_frame_reg[28] 
       (.C(s_axi_aclk),
        .CE(\dwell_frame[31]_i_2_n_0 ),
        .D(dwell_frame_0[28]),
        .Q(dwell_frame[28]),
        .R(\dwell_frame[31]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \dwell_frame_reg[29] 
       (.C(s_axi_aclk),
        .CE(\dwell_frame[31]_i_2_n_0 ),
        .D(dwell_frame_0[29]),
        .Q(dwell_frame[29]),
        .R(\dwell_frame[31]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \dwell_frame_reg[2] 
       (.C(s_axi_aclk),
        .CE(\dwell_frame[31]_i_2_n_0 ),
        .D(dwell_frame_0[2]),
        .Q(dwell_frame[2]),
        .R(\dwell_frame[31]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \dwell_frame_reg[30] 
       (.C(s_axi_aclk),
        .CE(\dwell_frame[31]_i_2_n_0 ),
        .D(dwell_frame_0[30]),
        .Q(dwell_frame[30]),
        .R(\dwell_frame[31]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \dwell_frame_reg[31] 
       (.C(s_axi_aclk),
        .CE(\dwell_frame[31]_i_2_n_0 ),
        .D(dwell_frame_0[31]),
        .Q(dwell_frame[31]),
        .R(\dwell_frame[31]_i_1_n_0 ));
  (* ADDER_THRESHOLD = "35" *) 
  CARRY8 \dwell_frame_reg[31]_i_9 
       (.CI(\dwell_frame_reg[24]_i_2_n_0 ),
        .CI_TOP(1'b0),
        .CO({\NLW_dwell_frame_reg[31]_i_9_CO_UNCONNECTED [7:6],\dwell_frame_reg[31]_i_9_n_2 ,\dwell_frame_reg[31]_i_9_n_3 ,\dwell_frame_reg[31]_i_9_n_4 ,\dwell_frame_reg[31]_i_9_n_5 ,\dwell_frame_reg[31]_i_9_n_6 ,\dwell_frame_reg[31]_i_9_n_7 }),
        .DI({1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0}),
        .O({\NLW_dwell_frame_reg[31]_i_9_O_UNCONNECTED [7],data0[31:25]}),
        .S({1'b0,dwell_frame[31:25]}));
  FDRE #(
    .INIT(1'b0)) 
    \dwell_frame_reg[3] 
       (.C(s_axi_aclk),
        .CE(\dwell_frame[31]_i_2_n_0 ),
        .D(dwell_frame_0[3]),
        .Q(dwell_frame[3]),
        .R(\dwell_frame[31]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \dwell_frame_reg[4] 
       (.C(s_axi_aclk),
        .CE(\dwell_frame[31]_i_2_n_0 ),
        .D(dwell_frame_0[4]),
        .Q(dwell_frame[4]),
        .R(\dwell_frame[31]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \dwell_frame_reg[5] 
       (.C(s_axi_aclk),
        .CE(\dwell_frame[31]_i_2_n_0 ),
        .D(dwell_frame_0[5]),
        .Q(dwell_frame[5]),
        .R(\dwell_frame[31]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \dwell_frame_reg[6] 
       (.C(s_axi_aclk),
        .CE(\dwell_frame[31]_i_2_n_0 ),
        .D(dwell_frame_0[6]),
        .Q(dwell_frame[6]),
        .R(\dwell_frame[31]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \dwell_frame_reg[7] 
       (.C(s_axi_aclk),
        .CE(\dwell_frame[31]_i_2_n_0 ),
        .D(dwell_frame_0[7]),
        .Q(dwell_frame[7]),
        .R(\dwell_frame[31]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \dwell_frame_reg[8] 
       (.C(s_axi_aclk),
        .CE(\dwell_frame[31]_i_2_n_0 ),
        .D(dwell_frame_0[8]),
        .Q(dwell_frame[8]),
        .R(\dwell_frame[31]_i_1_n_0 ));
  (* ADDER_THRESHOLD = "35" *) 
  CARRY8 \dwell_frame_reg[8]_i_2 
       (.CI(dwell_frame[0]),
        .CI_TOP(1'b0),
        .CO({\dwell_frame_reg[8]_i_2_n_0 ,\dwell_frame_reg[8]_i_2_n_1 ,\dwell_frame_reg[8]_i_2_n_2 ,\dwell_frame_reg[8]_i_2_n_3 ,\dwell_frame_reg[8]_i_2_n_4 ,\dwell_frame_reg[8]_i_2_n_5 ,\dwell_frame_reg[8]_i_2_n_6 ,\dwell_frame_reg[8]_i_2_n_7 }),
        .DI({1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0}),
        .O(data0[8:1]),
        .S(dwell_frame[8:1]));
  FDRE #(
    .INIT(1'b0)) 
    \dwell_frame_reg[9] 
       (.C(s_axi_aclk),
        .CE(\dwell_frame[31]_i_2_n_0 ),
        .D(dwell_frame_0[9]),
        .Q(dwell_frame[9]),
        .R(\dwell_frame[31]_i_1_n_0 ));
  LUT1 #(
    .INIT(2'h1)) 
    i__carry__0_i_1
       (.I0(p_0_in[17]),
        .O(i__carry__0_i_1_n_0));
  (* ADDER_THRESHOLD = "35" *) 
  CARRY8 i__carry__0_i_10
       (.CI(i__carry_i_16_n_0),
        .CI_TOP(1'b0),
        .CO({i__carry__0_i_10_n_0,i__carry__0_i_10_n_1,i__carry__0_i_10_n_2,i__carry__0_i_10_n_3,i__carry__0_i_10_n_4,i__carry__0_i_10_n_5,i__carry__0_i_10_n_6,i__carry__0_i_10_n_7}),
        .DI({1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0}),
        .O(p_0_in[24:17]),
        .S(phase_reg[24:17]));
  (* ADDER_THRESHOLD = "35" *) 
  CARRY8 i__carry__0_i_11
       (.CI(i__carry__0_i_10_n_0),
        .CI_TOP(1'b0),
        .CO({NLW_i__carry__0_i_11_CO_UNCONNECTED[7:6],i__carry__0_i_11_n_2,i__carry__0_i_11_n_3,i__carry__0_i_11_n_4,i__carry__0_i_11_n_5,i__carry__0_i_11_n_6,i__carry__0_i_11_n_7}),
        .DI({1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0}),
        .O({NLW_i__carry__0_i_11_O_UNCONNECTED[7],p_0_in[31:25]}),
        .S({1'b0,phase_reg[31:25]}));
  LUT2 #(
    .INIT(4'h1)) 
    i__carry__0_i_2
       (.I0(p_0_in[30]),
        .I1(p_0_in[31]),
        .O(i__carry__0_i_2_n_0));
  LUT2 #(
    .INIT(4'h1)) 
    i__carry__0_i_3
       (.I0(p_0_in[28]),
        .I1(p_0_in[29]),
        .O(i__carry__0_i_3_n_0));
  LUT2 #(
    .INIT(4'h1)) 
    i__carry__0_i_4
       (.I0(p_0_in[26]),
        .I1(p_0_in[27]),
        .O(i__carry__0_i_4_n_0));
  LUT2 #(
    .INIT(4'h1)) 
    i__carry__0_i_5
       (.I0(p_0_in[24]),
        .I1(p_0_in[25]),
        .O(i__carry__0_i_5_n_0));
  LUT2 #(
    .INIT(4'h1)) 
    i__carry__0_i_6
       (.I0(p_0_in[22]),
        .I1(p_0_in[23]),
        .O(i__carry__0_i_6_n_0));
  LUT2 #(
    .INIT(4'h1)) 
    i__carry__0_i_7
       (.I0(p_0_in[20]),
        .I1(p_0_in[21]),
        .O(i__carry__0_i_7_n_0));
  LUT2 #(
    .INIT(4'h1)) 
    i__carry__0_i_8
       (.I0(p_0_in[18]),
        .I1(p_0_in[19]),
        .O(i__carry__0_i_8_n_0));
  LUT2 #(
    .INIT(4'h2)) 
    i__carry__0_i_9
       (.I0(p_0_in[17]),
        .I1(p_0_in[16]),
        .O(i__carry__0_i_9_n_0));
  LUT3 #(
    .INIT(8'h10)) 
    i__carry_i_1
       (.I0(p_0_in[15]),
        .I1(p_0_in[14]),
        .I2(select_high),
        .O(i__carry_i_1_n_0));
  LUT2 #(
    .INIT(4'h1)) 
    i__carry_i_10
       (.I0(p_0_in[10]),
        .I1(p_0_in[11]),
        .O(i__carry_i_10_n_0));
  LUT3 #(
    .INIT(8'h12)) 
    i__carry_i_11
       (.I0(select_high),
        .I1(p_0_in[8]),
        .I2(p_0_in[9]),
        .O(i__carry_i_11_n_0));
  LUT2 #(
    .INIT(4'h8)) 
    i__carry_i_12
       (.I0(p_0_in[6]),
        .I1(p_0_in[7]),
        .O(i__carry_i_12_n_0));
  LUT3 #(
    .INIT(8'h84)) 
    i__carry_i_13
       (.I0(select_high),
        .I1(p_0_in[4]),
        .I2(p_0_in[5]),
        .O(i__carry_i_13_n_0));
  LUT2 #(
    .INIT(4'h8)) 
    i__carry_i_14
       (.I0(p_0_in[2]),
        .I1(p_0_in[3]),
        .O(i__carry_i_14_n_0));
  LUT3 #(
    .INIT(8'h84)) 
    i__carry_i_15
       (.I0(select_high),
        .I1(p_0_in[1]),
        .I2(phase_reg[0]),
        .O(i__carry_i_15_n_0));
  (* ADDER_THRESHOLD = "35" *) 
  CARRY8 i__carry_i_16
       (.CI(i__carry_i_17_n_0),
        .CI_TOP(1'b0),
        .CO({i__carry_i_16_n_0,i__carry_i_16_n_1,i__carry_i_16_n_2,i__carry_i_16_n_3,i__carry_i_16_n_4,i__carry_i_16_n_5,i__carry_i_16_n_6,i__carry_i_16_n_7}),
        .DI({1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0}),
        .O(p_0_in[16:9]),
        .S(phase_reg[16:9]));
  (* ADDER_THRESHOLD = "35" *) 
  CARRY8 i__carry_i_17
       (.CI(phase_reg[0]),
        .CI_TOP(1'b0),
        .CO({i__carry_i_17_n_0,i__carry_i_17_n_1,i__carry_i_17_n_2,i__carry_i_17_n_3,i__carry_i_17_n_4,i__carry_i_17_n_5,i__carry_i_17_n_6,i__carry_i_17_n_7}),
        .DI({1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0}),
        .O(p_0_in[8:1]),
        .S(phase_reg[8:1]));
  LUT3 #(
    .INIT(8'h4F)) 
    i__carry_i_2
       (.I0(p_0_in[12]),
        .I1(select_high),
        .I2(p_0_in[13]),
        .O(i__carry_i_2_n_0));
  LUT2 #(
    .INIT(4'h1)) 
    i__carry_i_3
       (.I0(p_0_in[9]),
        .I1(select_high),
        .O(i__carry_i_3_n_0));
  LUT2 #(
    .INIT(4'h7)) 
    i__carry_i_4
       (.I0(p_0_in[6]),
        .I1(p_0_in[7]),
        .O(i__carry_i_4_n_0));
  LUT3 #(
    .INIT(8'h2B)) 
    i__carry_i_5
       (.I0(select_high),
        .I1(p_0_in[5]),
        .I2(p_0_in[4]),
        .O(i__carry_i_5_n_0));
  LUT2 #(
    .INIT(4'h7)) 
    i__carry_i_6
       (.I0(p_0_in[2]),
        .I1(p_0_in[3]),
        .O(i__carry_i_6_n_0));
  LUT3 #(
    .INIT(8'h4F)) 
    i__carry_i_7
       (.I0(select_high),
        .I1(phase_reg[0]),
        .I2(p_0_in[1]),
        .O(i__carry_i_7_n_0));
  LUT3 #(
    .INIT(8'h09)) 
    i__carry_i_8
       (.I0(select_high),
        .I1(p_0_in[14]),
        .I2(p_0_in[15]),
        .O(i__carry_i_8_n_0));
  LUT3 #(
    .INIT(8'h84)) 
    i__carry_i_9
       (.I0(select_high),
        .I1(p_0_in[13]),
        .I2(p_0_in[12]),
        .O(i__carry_i_9_n_0));
  LUT4 #(
    .INIT(16'hF7FF)) 
    \phase[0]_i_1 
       (.I0(busy),
        .I1(s_axi_aresetn),
        .I2(\dwell_frame[31]_i_2_n_0 ),
        .I3(pwm_i_3_n_0),
        .O(\phase[0]_i_1_n_0 ));
  LUT1 #(
    .INIT(2'h1)) 
    \phase[0]_i_3 
       (.I0(phase_reg[0]),
        .O(p_0_in[0]));
  FDRE #(
    .INIT(1'b0)) 
    \phase_reg[0] 
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(\phase_reg[0]_i_2_n_15 ),
        .Q(phase_reg[0]),
        .R(\phase[0]_i_1_n_0 ));
  (* ADDER_THRESHOLD = "16" *) 
  CARRY8 \phase_reg[0]_i_2 
       (.CI(1'b0),
        .CI_TOP(1'b0),
        .CO({\phase_reg[0]_i_2_n_0 ,\phase_reg[0]_i_2_n_1 ,\phase_reg[0]_i_2_n_2 ,\phase_reg[0]_i_2_n_3 ,\phase_reg[0]_i_2_n_4 ,\phase_reg[0]_i_2_n_5 ,\phase_reg[0]_i_2_n_6 ,\phase_reg[0]_i_2_n_7 }),
        .DI({1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b1}),
        .O({\phase_reg[0]_i_2_n_8 ,\phase_reg[0]_i_2_n_9 ,\phase_reg[0]_i_2_n_10 ,\phase_reg[0]_i_2_n_11 ,\phase_reg[0]_i_2_n_12 ,\phase_reg[0]_i_2_n_13 ,\phase_reg[0]_i_2_n_14 ,\phase_reg[0]_i_2_n_15 }),
        .S({phase_reg[7:1],p_0_in[0]}));
  FDRE #(
    .INIT(1'b0)) 
    \phase_reg[10] 
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(\phase_reg[8]_i_1_n_13 ),
        .Q(phase_reg[10]),
        .R(\phase[0]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \phase_reg[11] 
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(\phase_reg[8]_i_1_n_12 ),
        .Q(phase_reg[11]),
        .R(\phase[0]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \phase_reg[12] 
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(\phase_reg[8]_i_1_n_11 ),
        .Q(phase_reg[12]),
        .R(\phase[0]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \phase_reg[13] 
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(\phase_reg[8]_i_1_n_10 ),
        .Q(phase_reg[13]),
        .R(\phase[0]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \phase_reg[14] 
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(\phase_reg[8]_i_1_n_9 ),
        .Q(phase_reg[14]),
        .R(\phase[0]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \phase_reg[15] 
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(\phase_reg[8]_i_1_n_8 ),
        .Q(phase_reg[15]),
        .R(\phase[0]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \phase_reg[16] 
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(\phase_reg[16]_i_1_n_15 ),
        .Q(phase_reg[16]),
        .R(\phase[0]_i_1_n_0 ));
  (* ADDER_THRESHOLD = "16" *) 
  CARRY8 \phase_reg[16]_i_1 
       (.CI(\phase_reg[8]_i_1_n_0 ),
        .CI_TOP(1'b0),
        .CO({\phase_reg[16]_i_1_n_0 ,\phase_reg[16]_i_1_n_1 ,\phase_reg[16]_i_1_n_2 ,\phase_reg[16]_i_1_n_3 ,\phase_reg[16]_i_1_n_4 ,\phase_reg[16]_i_1_n_5 ,\phase_reg[16]_i_1_n_6 ,\phase_reg[16]_i_1_n_7 }),
        .DI({1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0}),
        .O({\phase_reg[16]_i_1_n_8 ,\phase_reg[16]_i_1_n_9 ,\phase_reg[16]_i_1_n_10 ,\phase_reg[16]_i_1_n_11 ,\phase_reg[16]_i_1_n_12 ,\phase_reg[16]_i_1_n_13 ,\phase_reg[16]_i_1_n_14 ,\phase_reg[16]_i_1_n_15 }),
        .S(phase_reg[23:16]));
  FDRE #(
    .INIT(1'b0)) 
    \phase_reg[17] 
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(\phase_reg[16]_i_1_n_14 ),
        .Q(phase_reg[17]),
        .R(\phase[0]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \phase_reg[18] 
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(\phase_reg[16]_i_1_n_13 ),
        .Q(phase_reg[18]),
        .R(\phase[0]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \phase_reg[19] 
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(\phase_reg[16]_i_1_n_12 ),
        .Q(phase_reg[19]),
        .R(\phase[0]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \phase_reg[1] 
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(\phase_reg[0]_i_2_n_14 ),
        .Q(phase_reg[1]),
        .R(\phase[0]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \phase_reg[20] 
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(\phase_reg[16]_i_1_n_11 ),
        .Q(phase_reg[20]),
        .R(\phase[0]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \phase_reg[21] 
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(\phase_reg[16]_i_1_n_10 ),
        .Q(phase_reg[21]),
        .R(\phase[0]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \phase_reg[22] 
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(\phase_reg[16]_i_1_n_9 ),
        .Q(phase_reg[22]),
        .R(\phase[0]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \phase_reg[23] 
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(\phase_reg[16]_i_1_n_8 ),
        .Q(phase_reg[23]),
        .R(\phase[0]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \phase_reg[24] 
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(\phase_reg[24]_i_1_n_15 ),
        .Q(phase_reg[24]),
        .R(\phase[0]_i_1_n_0 ));
  (* ADDER_THRESHOLD = "16" *) 
  CARRY8 \phase_reg[24]_i_1 
       (.CI(\phase_reg[16]_i_1_n_0 ),
        .CI_TOP(1'b0),
        .CO({\NLW_phase_reg[24]_i_1_CO_UNCONNECTED [7],\phase_reg[24]_i_1_n_1 ,\phase_reg[24]_i_1_n_2 ,\phase_reg[24]_i_1_n_3 ,\phase_reg[24]_i_1_n_4 ,\phase_reg[24]_i_1_n_5 ,\phase_reg[24]_i_1_n_6 ,\phase_reg[24]_i_1_n_7 }),
        .DI({1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0}),
        .O({\phase_reg[24]_i_1_n_8 ,\phase_reg[24]_i_1_n_9 ,\phase_reg[24]_i_1_n_10 ,\phase_reg[24]_i_1_n_11 ,\phase_reg[24]_i_1_n_12 ,\phase_reg[24]_i_1_n_13 ,\phase_reg[24]_i_1_n_14 ,\phase_reg[24]_i_1_n_15 }),
        .S(phase_reg[31:24]));
  FDRE #(
    .INIT(1'b0)) 
    \phase_reg[25] 
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(\phase_reg[24]_i_1_n_14 ),
        .Q(phase_reg[25]),
        .R(\phase[0]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \phase_reg[26] 
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(\phase_reg[24]_i_1_n_13 ),
        .Q(phase_reg[26]),
        .R(\phase[0]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \phase_reg[27] 
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(\phase_reg[24]_i_1_n_12 ),
        .Q(phase_reg[27]),
        .R(\phase[0]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \phase_reg[28] 
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(\phase_reg[24]_i_1_n_11 ),
        .Q(phase_reg[28]),
        .R(\phase[0]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \phase_reg[29] 
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(\phase_reg[24]_i_1_n_10 ),
        .Q(phase_reg[29]),
        .R(\phase[0]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \phase_reg[2] 
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(\phase_reg[0]_i_2_n_13 ),
        .Q(phase_reg[2]),
        .R(\phase[0]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \phase_reg[30] 
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(\phase_reg[24]_i_1_n_9 ),
        .Q(phase_reg[30]),
        .R(\phase[0]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \phase_reg[31] 
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(\phase_reg[24]_i_1_n_8 ),
        .Q(phase_reg[31]),
        .R(\phase[0]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \phase_reg[3] 
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(\phase_reg[0]_i_2_n_12 ),
        .Q(phase_reg[3]),
        .R(\phase[0]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \phase_reg[4] 
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(\phase_reg[0]_i_2_n_11 ),
        .Q(phase_reg[4]),
        .R(\phase[0]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \phase_reg[5] 
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(\phase_reg[0]_i_2_n_10 ),
        .Q(phase_reg[5]),
        .R(\phase[0]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \phase_reg[6] 
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(\phase_reg[0]_i_2_n_9 ),
        .Q(phase_reg[6]),
        .R(\phase[0]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \phase_reg[7] 
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(\phase_reg[0]_i_2_n_8 ),
        .Q(phase_reg[7]),
        .R(\phase[0]_i_1_n_0 ));
  FDRE #(
    .INIT(1'b0)) 
    \phase_reg[8] 
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(\phase_reg[8]_i_1_n_15 ),
        .Q(phase_reg[8]),
        .R(\phase[0]_i_1_n_0 ));
  (* ADDER_THRESHOLD = "16" *) 
  CARRY8 \phase_reg[8]_i_1 
       (.CI(\phase_reg[0]_i_2_n_0 ),
        .CI_TOP(1'b0),
        .CO({\phase_reg[8]_i_1_n_0 ,\phase_reg[8]_i_1_n_1 ,\phase_reg[8]_i_1_n_2 ,\phase_reg[8]_i_1_n_3 ,\phase_reg[8]_i_1_n_4 ,\phase_reg[8]_i_1_n_5 ,\phase_reg[8]_i_1_n_6 ,\phase_reg[8]_i_1_n_7 }),
        .DI({1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0}),
        .O({\phase_reg[8]_i_1_n_8 ,\phase_reg[8]_i_1_n_9 ,\phase_reg[8]_i_1_n_10 ,\phase_reg[8]_i_1_n_11 ,\phase_reg[8]_i_1_n_12 ,\phase_reg[8]_i_1_n_13 ,\phase_reg[8]_i_1_n_14 ,\phase_reg[8]_i_1_n_15 }),
        .S(phase_reg[15:8]));
  FDRE #(
    .INIT(1'b0)) 
    \phase_reg[9] 
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(\phase_reg[8]_i_1_n_14 ),
        .Q(phase_reg[9]),
        .R(\phase[0]_i_1_n_0 ));
  (* COMPARATOR_THRESHOLD = "11" *) 
  CARRY8 \pwm0_inferred__0/i__carry 
       (.CI(1'b0),
        .CI_TOP(1'b0),
        .CO({\pwm0_inferred__0/i__carry_n_0 ,\pwm0_inferred__0/i__carry_n_1 ,\pwm0_inferred__0/i__carry_n_2 ,\pwm0_inferred__0/i__carry_n_3 ,\pwm0_inferred__0/i__carry_n_4 ,\pwm0_inferred__0/i__carry_n_5 ,\pwm0_inferred__0/i__carry_n_6 ,\pwm0_inferred__0/i__carry_n_7 }),
        .DI({i__carry_i_1_n_0,i__carry_i_2_n_0,1'b0,i__carry_i_3_n_0,i__carry_i_4_n_0,i__carry_i_5_n_0,i__carry_i_6_n_0,i__carry_i_7_n_0}),
        .O(\NLW_pwm0_inferred__0/i__carry_O_UNCONNECTED [7:0]),
        .S({i__carry_i_8_n_0,i__carry_i_9_n_0,i__carry_i_10_n_0,i__carry_i_11_n_0,i__carry_i_12_n_0,i__carry_i_13_n_0,i__carry_i_14_n_0,i__carry_i_15_n_0}));
  (* COMPARATOR_THRESHOLD = "11" *) 
  CARRY8 \pwm0_inferred__0/i__carry__0 
       (.CI(\pwm0_inferred__0/i__carry_n_0 ),
        .CI_TOP(1'b0),
        .CO({\pwm0_inferred__0/i__carry__0_n_0 ,\pwm0_inferred__0/i__carry__0_n_1 ,\pwm0_inferred__0/i__carry__0_n_2 ,\pwm0_inferred__0/i__carry__0_n_3 ,\pwm0_inferred__0/i__carry__0_n_4 ,\pwm0_inferred__0/i__carry__0_n_5 ,\pwm0_inferred__0/i__carry__0_n_6 ,\pwm0_inferred__0/i__carry__0_n_7 }),
        .DI({1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,i__carry__0_i_1_n_0}),
        .O(\NLW_pwm0_inferred__0/i__carry__0_O_UNCONNECTED [7:0]),
        .S({i__carry__0_i_2_n_0,i__carry__0_i_3_n_0,i__carry__0_i_4_n_0,i__carry__0_i_5_n_0,i__carry__0_i_6_n_0,i__carry__0_i_7_n_0,i__carry__0_i_8_n_0,i__carry__0_i_9_n_0}));
  LUT2 #(
    .INIT(4'h7)) 
    pwm_i_1
       (.I0(pwm_i_3_n_0),
        .I1(s_axi_aresetn),
        .O(pwm_i_1_n_0));
  LUT6 #(
    .INIT(64'hFFFF0404FF040404)) 
    pwm_i_2
       (.I0(pwm_i_4_n_0),
        .I1(\s_axi_bresp[1]_i_5 [1]),
        .I2(pwm_i_5_n_0),
        .I3(\pwm0_inferred__0/i__carry__0_n_0 ),
        .I4(busy),
        .I5(\dwell_frame[31]_i_2_n_0 ),
        .O(pwm_i_2_n_0));
  LUT6 #(
    .INIT(64'hFFFFFFFFFFFFFFFE)) 
    pwm_i_3
       (.I0(pwm_i_6_n_0),
        .I1(\w_data_reg[0] ),
        .I2(\w_data_reg[30] ),
        .I3(pwm_i_7_n_0),
        .I4(\aw_address_reg[1] ),
        .I5(Q[3]),
        .O(pwm_i_3_n_0));
  (* SOFT_HLUTNM = "soft_lutpair4" *) 
  LUT4 #(
    .INIT(16'hFFFE)) 
    pwm_i_4
       (.I0(\s_axi_bresp[1]_i_5 [10]),
        .I1(\s_axi_bresp[1]_i_5 [9]),
        .I2(busy),
        .I3(\s_axi_bresp[1]_i_5 [11]),
        .O(pwm_i_4_n_0));
  LUT6 #(
    .INIT(64'hFFFFFFFFFFFFFFFE)) 
    pwm_i_5
       (.I0(Q[3]),
        .I1(\aw_address_reg[1] ),
        .I2(\w_data_reg[12] ),
        .I3(\w_data_reg[21] ),
        .I4(\w_data_reg[30] ),
        .I5(\w_data_reg[0] ),
        .O(pwm_i_5_n_0));
  (* SOFT_HLUTNM = "soft_lutpair4" *) 
  LUT4 #(
    .INIT(16'hFF7F)) 
    pwm_i_6
       (.I0(\s_axi_bresp[1]_i_5 [9]),
        .I1(\s_axi_bresp[1]_i_5 [10]),
        .I2(\s_axi_bresp[1]_i_5 [11]),
        .I3(\s_axi_bresp[1]_i_5 [1]),
        .O(pwm_i_6_n_0));
  LUT4 #(
    .INIT(16'hFFFE)) 
    pwm_i_7
       (.I0(\s_axi_bresp[1]_i_16_n_0 ),
        .I1(pwm_i_8_n_0),
        .I2(\s_axi_bresp[1]_i_15_n_0 ),
        .I3(pwm_i_9_n_0),
        .O(pwm_i_7_n_0));
  (* SOFT_HLUTNM = "soft_lutpair1" *) 
  LUT4 #(
    .INIT(16'hFFFD)) 
    pwm_i_8
       (.I0(\s_axi_bresp[1]_i_5 [8]),
        .I1(\s_axi_bresp[1]_i_5 [7]),
        .I2(\s_axi_bresp[1]_i_5 [13]),
        .I3(\s_axi_bresp[1]_i_5 [12]),
        .O(pwm_i_8_n_0));
  (* SOFT_HLUTNM = "soft_lutpair0" *) 
  LUT4 #(
    .INIT(16'hFFDF)) 
    pwm_i_9
       (.I0(\s_axi_bresp[1]_i_5 [18]),
        .I1(\s_axi_bresp[1]_i_5 [19]),
        .I2(\s_axi_bresp[1]_i_5 [20]),
        .I3(\s_axi_bresp[1]_i_5 [21]),
        .O(pwm_i_9_n_0));
  FDRE #(
    .INIT(1'b0)) 
    pwm_reg
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(pwm_i_2_n_0),
        .Q(servo_pwm),
        .R(pwm_i_1_n_0));
  (* SOFT_HLUTNM = "soft_lutpair0" *) 
  LUT5 #(
    .INIT(32'hFFFFFBFF)) 
    \s_axi_bresp[1]_i_10 
       (.I0(\s_axi_bresp[1]_i_5 [21]),
        .I1(\s_axi_bresp[1]_i_5 [20]),
        .I2(\s_axi_bresp[1]_i_5 [19]),
        .I3(\s_axi_bresp[1]_i_5 [18]),
        .I4(\s_axi_bresp[1]_i_15_n_0 ),
        .O(\w_data_reg[21] ));
  (* SOFT_HLUTNM = "soft_lutpair1" *) 
  LUT5 #(
    .INIT(32'hFFFFFEFF)) 
    \s_axi_bresp[1]_i_11 
       (.I0(\s_axi_bresp[1]_i_5 [12]),
        .I1(\s_axi_bresp[1]_i_5 [13]),
        .I2(\s_axi_bresp[1]_i_5 [7]),
        .I3(\s_axi_bresp[1]_i_5 [8]),
        .I4(\s_axi_bresp[1]_i_16_n_0 ),
        .O(\w_data_reg[12] ));
  LUT4 #(
    .INIT(16'hFFDF)) 
    \s_axi_bresp[1]_i_12 
       (.I0(\s_axi_bresp[1]_i_5 [4]),
        .I1(\s_axi_bresp[1]_i_5 [3]),
        .I2(\s_axi_bresp[1]_i_5 [6]),
        .I3(\s_axi_bresp[1]_i_5 [5]),
        .O(\s_axi_bresp[1]_i_12_n_0 ));
  LUT4 #(
    .INIT(16'hFFEF)) 
    \s_axi_bresp[1]_i_13 
       (.I0(\s_axi_bresp[1]_i_5 [27]),
        .I1(\s_axi_bresp[1]_i_5 [26]),
        .I2(\s_axi_bresp[1]_i_5 [28]),
        .I3(\s_axi_bresp[1]_i_5 [29]),
        .O(\s_axi_bresp[1]_i_13_n_0 ));
  LUT4 #(
    .INIT(16'hFF7F)) 
    \s_axi_bresp[1]_i_14 
       (.I0(\s_axi_bresp[1]_i_9_0 [2]),
        .I1(\s_axi_bresp[1]_i_9_0 [1]),
        .I2(\s_axi_bresp[1]_i_9_0 [3]),
        .I3(Q[2]),
        .O(\s_axi_bresp[1]_i_14_n_0 ));
  LUT4 #(
    .INIT(16'hDFFF)) 
    \s_axi_bresp[1]_i_15 
       (.I0(\s_axi_bresp[1]_i_5 [22]),
        .I1(\s_axi_bresp[1]_i_5 [23]),
        .I2(\s_axi_bresp[1]_i_5 [25]),
        .I3(\s_axi_bresp[1]_i_5 [24]),
        .O(\s_axi_bresp[1]_i_15_n_0 ));
  LUT4 #(
    .INIT(16'hFFFD)) 
    \s_axi_bresp[1]_i_16 
       (.I0(\s_axi_bresp[1]_i_5 [14]),
        .I1(\s_axi_bresp[1]_i_5 [15]),
        .I2(\s_axi_bresp[1]_i_5 [17]),
        .I3(\s_axi_bresp[1]_i_5 [16]),
        .O(\s_axi_bresp[1]_i_16_n_0 ));
  LUT6 #(
    .INIT(64'hBBBBBBBBB8B8BBB8)) 
    \s_axi_bresp[1]_i_2 
       (.I0(s_axi_bresp),
        .I1(\s_axi_bresp[1]_i_3_n_0 ),
        .I2(\s_axi_bresp_reg[1]_2 ),
        .I3(\s_axi_bresp_reg[1]_3 ),
        .I4(Q[3]),
        .I5(\s_axi_bresp[1]_i_6_n_0 ),
        .O(\s_axi_bresp_reg[1] ));
  LUT3 #(
    .INIT(8'hDF)) 
    \s_axi_bresp[1]_i_3 
       (.I0(\s_axi_bresp_reg[1]_0 ),
        .I1(\s_axi_bresp_reg[1]_1 ),
        .I2(aw_pending),
        .O(\s_axi_bresp[1]_i_3_n_0 ));
  LUT6 #(
    .INIT(64'h00000000FFFE77FF)) 
    \s_axi_bresp[1]_i_6 
       (.I0(\s_axi_bresp[1]_i_5 [10]),
        .I1(\s_axi_bresp[1]_i_5 [9]),
        .I2(busy),
        .I3(\s_axi_bresp[1]_i_5 [11]),
        .I4(\s_axi_bresp[1]_i_5 [1]),
        .I5(Q[3]),
        .O(\s_axi_bresp[1]_i_6_n_0 ));
  LUT5 #(
    .INIT(32'hFFFFFEFF)) 
    \s_axi_bresp[1]_i_8 
       (.I0(\s_axi_bresp[1]_i_5 [0]),
        .I1(\s_axi_bresp[1]_i_5 [2]),
        .I2(Q[5]),
        .I3(Q[4]),
        .I4(\s_axi_bresp[1]_i_12_n_0 ),
        .O(\w_data_reg[0] ));
  LUT5 #(
    .INIT(32'hFFFFFFDF)) 
    \s_axi_bresp[1]_i_9 
       (.I0(\s_axi_bresp[1]_i_5 [30]),
        .I1(\s_axi_bresp[1]_i_5 [31]),
        .I2(\s_axi_bresp[1]_i_9_0 [0]),
        .I3(\s_axi_bresp[1]_i_13_n_0 ),
        .I4(\s_axi_bresp[1]_i_14_n_0 ),
        .O(\w_data_reg[30] ));
  (* SOFT_HLUTNM = "soft_lutpair2" *) 
  LUT5 #(
    .INIT(32'hFFEAEAEA)) 
    \s_axi_rdata[0]_i_1 
       (.I0(\s_axi_rdata[0]_i_2_n_0 ),
        .I1(\s_axi_rdata_reg[15] ),
        .I2(\s_axi_rdata_reg[31] [0]),
        .I3(dwell_frame[0]),
        .I4(\s_axi_rdata_reg[2] ),
        .O(D[0]));
  LUT6 #(
    .INIT(64'h000030B000300000)) 
    \s_axi_rdata[0]_i_2 
       (.I0(busy),
        .I1(s_axi_araddr[0]),
        .I2(\s_axi_rdata_reg[6]_1 ),
        .I3(s_axi_araddr[2]),
        .I4(s_axi_araddr[3]),
        .I5(s_axi_araddr[1]),
        .O(\s_axi_rdata[0]_i_2_n_0 ));
  LUT6 #(
    .INIT(64'hAAFAAAAAAAFAEABA)) 
    \s_axi_rdata[10]_i_1 
       (.I0(\s_axi_rdata[10]_i_2_n_0 ),
        .I1(s_axi_araddr[2]),
        .I2(\s_axi_rdata_reg[6]_1 ),
        .I3(s_axi_araddr[0]),
        .I4(s_axi_araddr[3]),
        .I5(s_axi_araddr[1]),
        .O(D[10]));
  LUT6 #(
    .INIT(64'hC808000000000000)) 
    \s_axi_rdata[10]_i_2 
       (.I0(\s_axi_rdata_reg[31] [8]),
        .I1(\s_axi_rdata_reg[6]_1 ),
        .I2(s_axi_araddr[2]),
        .I3(dwell_frame[10]),
        .I4(s_axi_araddr[3]),
        .I5(s_axi_araddr[1]),
        .O(\s_axi_rdata[10]_i_2_n_0 ));
  LUT5 #(
    .INIT(32'hFFEAEAEA)) 
    \s_axi_rdata[11]_i_1 
       (.I0(\s_axi_rdata_reg[14] ),
        .I1(\s_axi_rdata_reg[15] ),
        .I2(\s_axi_rdata_reg[31] [9]),
        .I3(dwell_frame[11]),
        .I4(\s_axi_rdata_reg[2] ),
        .O(D[11]));
  LUT6 #(
    .INIT(64'hFFFFFFFFFFEAEAEA)) 
    \s_axi_rdata[12]_i_1 
       (.I0(\s_axi_rdata_reg[12] ),
        .I1(dwell_frame[12]),
        .I2(\s_axi_rdata_reg[2] ),
        .I3(\s_axi_rdata_reg[31] [10]),
        .I4(\s_axi_rdata_reg[15] ),
        .I5(\s_axi_rdata_reg[12]_0 ),
        .O(D[12]));
  LUT5 #(
    .INIT(32'hFFEAEAEA)) 
    \s_axi_rdata[13]_i_1 
       (.I0(\s_axi_rdata_reg[3] ),
        .I1(\s_axi_rdata_reg[15] ),
        .I2(\s_axi_rdata_reg[31] [11]),
        .I3(dwell_frame[13]),
        .I4(\s_axi_rdata_reg[2] ),
        .O(D[13]));
  LUT6 #(
    .INIT(64'hFFFFFFFFFFFFF888)) 
    \s_axi_rdata[14]_i_1 
       (.I0(\s_axi_rdata_reg[15] ),
        .I1(\s_axi_rdata_reg[31] [12]),
        .I2(\s_axi_rdata_reg[2] ),
        .I3(dwell_frame[14]),
        .I4(\s_axi_rdata_reg[14] ),
        .I5(\s_axi_rdata_reg[17] ),
        .O(D[14]));
  LUT6 #(
    .INIT(64'hFFFFFFFFFFFFF888)) 
    \s_axi_rdata[15]_i_1 
       (.I0(\s_axi_rdata_reg[2] ),
        .I1(dwell_frame[15]),
        .I2(\s_axi_rdata_reg[31] [13]),
        .I3(\s_axi_rdata_reg[15] ),
        .I4(\s_axi_rdata_reg[15]_0 ),
        .I5(\s_axi_rdata_reg[2]_1 ),
        .O(D[15]));
  LUT5 #(
    .INIT(32'hFFEAEAEA)) 
    \s_axi_rdata[16]_i_1 
       (.I0(\s_axi_rdata_reg[14] ),
        .I1(\s_axi_rdata_reg[15] ),
        .I2(\s_axi_rdata_reg[31] [14]),
        .I3(dwell_frame[16]),
        .I4(\s_axi_rdata_reg[2] ),
        .O(D[16]));
  LUT6 #(
    .INIT(64'hEEEEEEEEFEEEEEEE)) 
    \s_axi_rdata[17]_i_1 
       (.I0(\s_axi_rdata[17]_i_2_n_0 ),
        .I1(\s_axi_rdata_reg[17] ),
        .I2(s_axi_araddr[2]),
        .I3(\s_axi_rdata_reg[17]_0 ),
        .I4(s_axi_araddr[1]),
        .I5(s_axi_araddr[3]),
        .O(D[17]));
  LUT6 #(
    .INIT(64'hC00F0000A00F0000)) 
    \s_axi_rdata[17]_i_2 
       (.I0(\s_axi_rdata_reg[31] [15]),
        .I1(dwell_frame[17]),
        .I2(s_axi_araddr[1]),
        .I3(s_axi_araddr[3]),
        .I4(\s_axi_rdata_reg[17]_1 ),
        .I5(s_axi_araddr[2]),
        .O(\s_axi_rdata[17]_i_2_n_0 ));
  LUT5 #(
    .INIT(32'hFFFFF888)) 
    \s_axi_rdata[18]_i_1 
       (.I0(\s_axi_rdata_reg[15] ),
        .I1(\s_axi_rdata_reg[31] [16]),
        .I2(\s_axi_rdata_reg[2] ),
        .I3(dwell_frame[18]),
        .I4(\s_axi_rdata_reg[18] ),
        .O(D[18]));
  LUT6 #(
    .INIT(64'hFFFFFFFFFFFFF888)) 
    \s_axi_rdata[19]_i_1 
       (.I0(\s_axi_rdata_reg[2] ),
        .I1(dwell_frame[19]),
        .I2(\s_axi_rdata_reg[31] [17]),
        .I3(\s_axi_rdata_reg[15] ),
        .I4(\s_axi_rdata_reg[19] ),
        .I5(\s_axi_rdata_reg[2]_1 ),
        .O(D[19]));
  LUT6 #(
    .INIT(64'hFFFFFFFEFFFEFFFE)) 
    \s_axi_rdata[1]_i_1 
       (.I0(\s_axi_rdata_reg[2]_0 ),
        .I1(\s_axi_rdata[1]_i_2_n_0 ),
        .I2(\s_axi_rdata_reg[12] ),
        .I3(\s_axi_rdata_reg[1] ),
        .I4(\s_axi_rdata_reg[31] [1]),
        .I5(\s_axi_rdata_reg[15] ),
        .O(D[1]));
  LUT6 #(
    .INIT(64'h88888888F0000000)) 
    \s_axi_rdata[1]_i_2 
       (.I0(\s_axi_rdata_reg[4]_0 ),
        .I1(dwell_frame[1]),
        .I2(\s_axi_rdata_reg[1]_0 ),
        .I3(servo_pwm),
        .I4(s_axi_araddr[1]),
        .I5(s_axi_araddr[3]),
        .O(\s_axi_rdata[1]_i_2_n_0 ));
  LUT5 #(
    .INIT(32'hFFFFF888)) 
    \s_axi_rdata[20]_i_1 
       (.I0(\s_axi_rdata_reg[15] ),
        .I1(\s_axi_rdata_reg[31] [18]),
        .I2(\s_axi_rdata_reg[2] ),
        .I3(dwell_frame[20]),
        .I4(\s_axi_rdata_reg[18] ),
        .O(D[20]));
  LUT5 #(
    .INIT(32'hFFEAEAEA)) 
    \s_axi_rdata[21]_i_1 
       (.I0(\s_axi_rdata_reg[12]_0 ),
        .I1(\s_axi_rdata_reg[15] ),
        .I2(\s_axi_rdata_reg[31] [19]),
        .I3(dwell_frame[21]),
        .I4(\s_axi_rdata_reg[2] ),
        .O(D[21]));
  LUT5 #(
    .INIT(32'hFFEAEAEA)) 
    \s_axi_rdata[22]_i_1 
       (.I0(\s_axi_rdata_reg[14] ),
        .I1(\s_axi_rdata_reg[15] ),
        .I2(\s_axi_rdata_reg[31] [20]),
        .I3(dwell_frame[22]),
        .I4(\s_axi_rdata_reg[2] ),
        .O(D[22]));
  LUT5 #(
    .INIT(32'hFFEAEAEA)) 
    \s_axi_rdata[23]_i_1 
       (.I0(\s_axi_rdata_reg[12]_0 ),
        .I1(\s_axi_rdata_reg[15] ),
        .I2(\s_axi_rdata_reg[31] [21]),
        .I3(dwell_frame[23]),
        .I4(\s_axi_rdata_reg[2] ),
        .O(D[23]));
  LUT5 #(
    .INIT(32'hFFEAEAEA)) 
    \s_axi_rdata[24]_i_1 
       (.I0(\s_axi_rdata_reg[12]_0 ),
        .I1(\s_axi_rdata_reg[15] ),
        .I2(\s_axi_rdata_reg[31] [22]),
        .I3(dwell_frame[24]),
        .I4(\s_axi_rdata_reg[2] ),
        .O(D[24]));
  LUT6 #(
    .INIT(64'hFFFFF222F222F222)) 
    \s_axi_rdata[25]_i_1 
       (.I0(\s_axi_rdata_reg[3]_0 ),
        .I1(\s_axi_rdata_reg[25] ),
        .I2(\s_axi_rdata_reg[15] ),
        .I3(\s_axi_rdata_reg[31] [23]),
        .I4(dwell_frame[25]),
        .I5(\s_axi_rdata_reg[2] ),
        .O(D[25]));
  LUT6 #(
    .INIT(64'hFFFFF888F888F888)) 
    \s_axi_rdata[26]_i_1 
       (.I0(\s_axi_rdata_reg[26] ),
        .I1(\s_axi_rdata_reg[3]_0 ),
        .I2(\s_axi_rdata_reg[15] ),
        .I3(\s_axi_rdata_reg[31] [24]),
        .I4(dwell_frame[26]),
        .I5(\s_axi_rdata_reg[2] ),
        .O(D[26]));
  LUT4 #(
    .INIT(16'hF888)) 
    \s_axi_rdata[27]_i_1 
       (.I0(dwell_frame[27]),
        .I1(\s_axi_rdata_reg[2] ),
        .I2(\s_axi_rdata_reg[31] [25]),
        .I3(\s_axi_rdata_reg[15] ),
        .O(D[27]));
  LUT6 #(
    .INIT(64'hFFFFF222F222F222)) 
    \s_axi_rdata[28]_i_1 
       (.I0(\s_axi_rdata_reg[3]_0 ),
        .I1(s_axi_araddr[3]),
        .I2(\s_axi_rdata_reg[15] ),
        .I3(\s_axi_rdata_reg[31] [26]),
        .I4(dwell_frame[28]),
        .I5(\s_axi_rdata_reg[2] ),
        .O(D[28]));
  LUT4 #(
    .INIT(16'hF888)) 
    \s_axi_rdata[29]_i_1 
       (.I0(dwell_frame[29]),
        .I1(\s_axi_rdata_reg[2] ),
        .I2(\s_axi_rdata_reg[31] [27]),
        .I3(\s_axi_rdata_reg[15] ),
        .O(D[29]));
  LUT6 #(
    .INIT(64'hFFFFFFFFFFFFFFF8)) 
    \s_axi_rdata[2]_i_1 
       (.I0(\s_axi_rdata_reg[2] ),
        .I1(dwell_frame[2]),
        .I2(\s_axi_rdata_reg[2]_0 ),
        .I3(\s_axi_rdata_reg[2]_1 ),
        .I4(\s_axi_rdata_reg[17] ),
        .I5(\s_axi_rdata_reg[2]_2 ),
        .O(D[2]));
  LUT6 #(
    .INIT(64'hFFFFF222F222F222)) 
    \s_axi_rdata[30]_i_1 
       (.I0(\s_axi_rdata_reg[3]_0 ),
        .I1(s_axi_araddr[3]),
        .I2(\s_axi_rdata_reg[15] ),
        .I3(\s_axi_rdata_reg[31] [28]),
        .I4(dwell_frame[30]),
        .I5(\s_axi_rdata_reg[2] ),
        .O(D[30]));
  LUT4 #(
    .INIT(16'hF888)) 
    \s_axi_rdata[31]_i_2 
       (.I0(dwell_frame[31]),
        .I1(\s_axi_rdata_reg[2] ),
        .I2(\s_axi_rdata_reg[31] [29]),
        .I3(\s_axi_rdata_reg[15] ),
        .O(D[31]));
  LUT6 #(
    .INIT(64'hFFFFFFEAFFEAFFEA)) 
    \s_axi_rdata[3]_i_1 
       (.I0(\s_axi_rdata[3]_i_2_n_0 ),
        .I1(\s_axi_rdata_reg[2] ),
        .I2(dwell_frame[3]),
        .I3(\s_axi_rdata_reg[3] ),
        .I4(\s_axi_rdata_reg[3]_0 ),
        .I5(s_axi_araddr[3]),
        .O(D[3]));
  LUT6 #(
    .INIT(64'hFFFFBAAABAAABAAA)) 
    \s_axi_rdata[3]_i_2 
       (.I0(\s_axi_rdata_reg[2]_1 ),
        .I1(select_high),
        .I2(s_axi_araddr[1]),
        .I3(\s_axi_rdata_reg[3]_1 ),
        .I4(\s_axi_rdata_reg[31] [2]),
        .I5(\s_axi_rdata_reg[5] ),
        .O(\s_axi_rdata[3]_i_2_n_0 ));
  LUT6 #(
    .INIT(64'hFFFFFFFFFFFFEAAA)) 
    \s_axi_rdata[4]_i_1 
       (.I0(\s_axi_rdata_reg[4] ),
        .I1(\s_axi_rdata_reg[4]_0 ),
        .I2(dwell_frame[4]),
        .I3(s_axi_araddr[3]),
        .I4(\s_axi_rdata[4]_i_4_n_0 ),
        .I5(\s_axi_rdata_reg[4]_1 ),
        .O(D[4]));
  (* SOFT_HLUTNM = "soft_lutpair3" *) 
  LUT4 #(
    .INIT(16'h4000)) 
    \s_axi_rdata[4]_i_4 
       (.I0(select_high),
        .I1(s_axi_araddr[1]),
        .I2(s_axi_araddr[2]),
        .I3(\s_axi_rdata_reg[17]_0 ),
        .O(\s_axi_rdata[4]_i_4_n_0 ));
  LUT6 #(
    .INIT(64'hFFFFFFFFFFFFF888)) 
    \s_axi_rdata[5]_i_1 
       (.I0(s_axi_araddr[4]),
        .I1(\s_axi_rdata_reg[17] ),
        .I2(\s_axi_rdata_reg[31] [3]),
        .I3(\s_axi_rdata_reg[5] ),
        .I4(\s_axi_rdata[5]_i_3_n_0 ),
        .I5(\s_axi_rdata_reg[5]_0 ),
        .O(D[5]));
  LUT6 #(
    .INIT(64'h88008800F8008800)) 
    \s_axi_rdata[5]_i_3 
       (.I0(\s_axi_rdata_reg[4]_0 ),
        .I1(dwell_frame[5]),
        .I2(\s_axi_rdata_reg[17]_0 ),
        .I3(s_axi_araddr[3]),
        .I4(s_axi_araddr[1]),
        .I5(select_high),
        .O(\s_axi_rdata[5]_i_3_n_0 ));
  LUT6 #(
    .INIT(64'hBABBAAAABAAAAAAA)) 
    \s_axi_rdata[6]_i_1 
       (.I0(\s_axi_rdata_reg[6] ),
        .I1(\s_axi_rdata_reg[6]_0 ),
        .I2(dwell_frame[6]),
        .I3(s_axi_araddr[2]),
        .I4(\s_axi_rdata_reg[6]_1 ),
        .I5(\s_axi_rdata_reg[31] [4]),
        .O(D[6]));
  LUT5 #(
    .INIT(32'hFFEAEAEA)) 
    \s_axi_rdata[7]_i_1 
       (.I0(\s_axi_rdata_reg[3] ),
        .I1(\s_axi_rdata_reg[15] ),
        .I2(\s_axi_rdata_reg[31] [5]),
        .I3(dwell_frame[7]),
        .I4(\s_axi_rdata_reg[2] ),
        .O(D[7]));
  LUT6 #(
    .INIT(64'hFFEAEAEAFFEAFFEA)) 
    \s_axi_rdata[8]_i_1 
       (.I0(\s_axi_rdata[8]_i_2_n_0 ),
        .I1(\s_axi_rdata_reg[2] ),
        .I2(dwell_frame[8]),
        .I3(\s_axi_rdata_reg[3]_0 ),
        .I4(s_axi_araddr[3]),
        .I5(s_axi_araddr[1]),
        .O(D[8]));
  LUT6 #(
    .INIT(64'h00002020000020F0)) 
    \s_axi_rdata[8]_i_2 
       (.I0(\s_axi_rdata_reg[31] [6]),
        .I1(s_axi_araddr[2]),
        .I2(\s_axi_rdata_reg[6]_1 ),
        .I3(s_axi_araddr[0]),
        .I4(\s_axi_rdata_reg[6]_0 ),
        .I5(select_high),
        .O(\s_axi_rdata[8]_i_2_n_0 ));
  LUT6 #(
    .INIT(64'hFFFFFFFFFFEAEAEA)) 
    \s_axi_rdata[9]_i_1 
       (.I0(\s_axi_rdata_reg[2]_0 ),
        .I1(\s_axi_rdata_reg[2] ),
        .I2(dwell_frame[9]),
        .I3(\s_axi_rdata_reg[15] ),
        .I4(\s_axi_rdata_reg[31] [7]),
        .I5(\s_axi_rdata[9]_i_3_n_0 ),
        .O(D[9]));
  (* SOFT_HLUTNM = "soft_lutpair3" *) 
  LUT5 #(
    .INIT(32'hC0004000)) 
    \s_axi_rdata[9]_i_3 
       (.I0(s_axi_araddr[1]),
        .I1(\s_axi_rdata_reg[17]_0 ),
        .I2(s_axi_araddr[2]),
        .I3(s_axi_araddr[3]),
        .I4(select_high),
        .O(\s_axi_rdata[9]_i_3_n_0 ));
  LUT6 #(
    .INIT(64'hFFFFFFFFFFFFFFFE)) 
    \scratch[31]_i_2 
       (.I0(\aw_address_reg[9] ),
        .I1(Q[1]),
        .I2(Q[0]),
        .I3(Q[7]),
        .I4(Q[6]),
        .I5(\s_axi_bresp[1]_i_3_n_0 ),
        .O(\aw_address_reg[1] ));
  LUT4 #(
    .INIT(16'hFFFE)) 
    \scratch[31]_i_3 
       (.I0(Q[9]),
        .I1(Q[8]),
        .I2(Q[11]),
        .I3(Q[10]),
        .O(\aw_address_reg[9] ));
  LUT6 #(
    .INIT(64'h8000808000800000)) 
    select_high_i_1
       (.I0(pwm_i_3_n_0),
        .I1(busy),
        .I2(s_axi_aresetn),
        .I3(\dwell_frame[31]_i_8_n_0 ),
        .I4(\dwell_frame[31]_i_2_n_0 ),
        .I5(select_high),
        .O(select_high_i_1_n_0));
  FDRE #(
    .INIT(1'b0)) 
    select_high_reg
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(select_high_i_1_n_0),
        .Q(select_high),
        .R(1'b0));
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
