// Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
// --------------------------------------------------------------------------------
// Tool Version: Vivado v.2022.2 (lin64) Build 3671981 Fri Oct 14 04:59:54 MDT 2022
// Date        : Mon Oct  5 23:20:35 2026
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
   (s_axi_bvalid_reg_0,
    servo_pwm,
    s_axi_rdata,
    s_axi_rresp,
    s_axi_wready,
    s_axi_awready,
    s_axi_arready,
    s_axi_rvalid_reg_0,
    s_axi_bresp,
    s_axi_aresetn,
    s_axi_araddr,
    s_axi_aclk,
    s_axi_awaddr,
    s_axi_wdata,
    s_axi_wstrb,
    s_axi_awvalid,
    s_axi_wvalid,
    s_axi_arvalid,
    s_axi_bready,
    s_axi_rready);
  output s_axi_bvalid_reg_0;
  output servo_pwm;
  output [31:0]s_axi_rdata;
  output [0:0]s_axi_rresp;
  output s_axi_wready;
  output s_axi_awready;
  output s_axi_arready;
  output s_axi_rvalid_reg_0;
  output [0:0]s_axi_bresp;
  input s_axi_aresetn;
  input [11:0]s_axi_araddr;
  input s_axi_aclk;
  input [11:0]s_axi_awaddr;
  input [31:0]s_axi_wdata;
  input [3:0]s_axi_wstrb;
  input s_axi_awvalid;
  input s_axi_wvalid;
  input s_axi_arvalid;
  input s_axi_bready;
  input s_axi_rready;

  wire [11:0]aw_address;
  wire aw_pending;
  wire aw_pending0;
  wire aw_pending_i_1_n_0;
  wire burst_n_1;
  wire burst_n_2;
  wire burst_n_3;
  wire burst_n_4;
  wire p_0_in;
  wire p_0_in_1;
  wire [31:7]p_1_in;
  wire p_1_in_0;
  wire p_2_in;
  wire p_5_in;
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
  wire \s_axi_bresp[1]_i_13_n_0 ;
  wire \s_axi_bresp[1]_i_5_n_0 ;
  wire s_axi_bvalid_i_1_n_0;
  wire s_axi_bvalid_reg_0;
  wire [31:0]s_axi_rdata;
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
  wire \s_axi_rdata[1]_i_2_n_0 ;
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
  wire \scratch[31]_i_2_n_0 ;
  wire \scratch[31]_i_3_n_0 ;
  wire servo_pwm;
  wire [31:0]w_data;
  wire w_pending0;
  wire w_pending_i_1_n_0;
  wire w_pending_i_2_n_0;
  wire w_pending_reg_n_0;
  wire \w_strobes_reg_n_0_[3] ;

  LUT3 #(
    .INIT(8'h02)) 
    \aw_address[11]_i_1 
       (.I0(s_axi_awvalid),
        .I1(s_axi_bvalid_reg_0),
        .I2(aw_pending),
        .O(aw_pending0));
  FDRE #(
    .INIT(1'b0)) 
    \aw_address_reg[0] 
       (.C(s_axi_aclk),
        .CE(aw_pending0),
        .D(s_axi_awaddr[0]),
        .Q(aw_address[0]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \aw_address_reg[10] 
       (.C(s_axi_aclk),
        .CE(aw_pending0),
        .D(s_axi_awaddr[10]),
        .Q(aw_address[10]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \aw_address_reg[11] 
       (.C(s_axi_aclk),
        .CE(aw_pending0),
        .D(s_axi_awaddr[11]),
        .Q(aw_address[11]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \aw_address_reg[1] 
       (.C(s_axi_aclk),
        .CE(aw_pending0),
        .D(s_axi_awaddr[1]),
        .Q(aw_address[1]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \aw_address_reg[2] 
       (.C(s_axi_aclk),
        .CE(aw_pending0),
        .D(s_axi_awaddr[2]),
        .Q(aw_address[2]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \aw_address_reg[3] 
       (.C(s_axi_aclk),
        .CE(aw_pending0),
        .D(s_axi_awaddr[3]),
        .Q(aw_address[3]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \aw_address_reg[4] 
       (.C(s_axi_aclk),
        .CE(aw_pending0),
        .D(s_axi_awaddr[4]),
        .Q(aw_address[4]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \aw_address_reg[5] 
       (.C(s_axi_aclk),
        .CE(aw_pending0),
        .D(s_axi_awaddr[5]),
        .Q(aw_address[5]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \aw_address_reg[6] 
       (.C(s_axi_aclk),
        .CE(aw_pending0),
        .D(s_axi_awaddr[6]),
        .Q(aw_address[6]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \aw_address_reg[7] 
       (.C(s_axi_aclk),
        .CE(aw_pending0),
        .D(s_axi_awaddr[7]),
        .Q(aw_address[7]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \aw_address_reg[8] 
       (.C(s_axi_aclk),
        .CE(aw_pending0),
        .D(s_axi_awaddr[8]),
        .Q(aw_address[8]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \aw_address_reg[9] 
       (.C(s_axi_aclk),
        .CE(aw_pending0),
        .D(s_axi_awaddr[9]),
        .Q(aw_address[9]),
        .R(p_0_in));
  (* SOFT_HLUTNM = "soft_lutpair4" *) 
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
        .R(w_pending_i_1_n_0));
  decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_pwm_burst burst
       (.D({burst_n_2,burst_n_3}),
        .Q(scratch[1:0]),
        .\aw_address_reg[10] (burst_n_1),
        .\aw_address_reg[5] (burst_n_4),
        .aw_pending(aw_pending),
        .p_5_in(p_5_in),
        .s_axi_aclk(s_axi_aclk),
        .s_axi_araddr(s_axi_araddr[5:0]),
        .s_axi_aresetn(s_axi_aresetn),
        .s_axi_bresp(s_axi_bresp),
        .\s_axi_bresp[1]_i_14_0 ({\w_strobes_reg_n_0_[3] ,p_2_in,p_1_in_0,p_0_in_1}),
        .\s_axi_bresp[1]_i_4_0 (w_data),
        .\s_axi_bresp[1]_i_4_1 (w_pending_reg_n_0),
        .\s_axi_bresp[1]_i_4_2 (s_axi_bvalid_reg_0),
        .\s_axi_bresp_reg[1] (\s_axi_bresp[1]_i_5_n_0 ),
        .\s_axi_rdata_reg[0] (\s_axi_rdata[31]_i_3_n_0 ),
        .\s_axi_rdata_reg[1] (\s_axi_rdata[1]_i_2_n_0 ),
        .\scratch[31]_i_2 (aw_address),
        .servo_pwm(servo_pwm));
  (* SOFT_HLUTNM = "soft_lutpair3" *) 
  LUT2 #(
    .INIT(4'h2)) 
    s_axi_arready_INST_0
       (.I0(s_axi_aresetn),
        .I1(s_axi_rvalid_reg_0),
        .O(s_axi_arready));
  (* SOFT_HLUTNM = "soft_lutpair2" *) 
  LUT3 #(
    .INIT(8'h04)) 
    s_axi_awready_INST_0
       (.I0(aw_pending),
        .I1(s_axi_aresetn),
        .I2(s_axi_bvalid_reg_0),
        .O(s_axi_awready));
  LUT1 #(
    .INIT(2'h1)) 
    \s_axi_bresp[1]_i_1 
       (.I0(s_axi_aresetn),
        .O(p_0_in));
  LUT2 #(
    .INIT(4'hE)) 
    \s_axi_bresp[1]_i_13 
       (.I0(aw_address[1]),
        .I1(aw_address[0]),
        .O(\s_axi_bresp[1]_i_13_n_0 ));
  LUT6 #(
    .INIT(64'hFFFFEFFEEFFFEFFE)) 
    \s_axi_bresp[1]_i_5 
       (.I0(burst_n_1),
        .I1(\s_axi_bresp[1]_i_13_n_0 ),
        .I2(aw_address[3]),
        .I3(aw_address[2]),
        .I4(aw_address[5]),
        .I5(aw_address[4]),
        .O(\s_axi_bresp[1]_i_5_n_0 ));
  (* SOFT_HLUTNM = "soft_lutpair1" *) 
  LUT3 #(
    .INIT(8'h08)) 
    \s_axi_bresp[1]_i_6 
       (.I0(aw_pending),
        .I1(w_pending_reg_n_0),
        .I2(s_axi_bvalid_reg_0),
        .O(p_5_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI BRESP" *) 
  FDRE \s_axi_bresp_reg[1] 
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(burst_n_4),
        .Q(s_axi_bresp),
        .R(p_0_in));
  (* SOFT_HLUTNM = "soft_lutpair1" *) 
  LUT4 #(
    .INIT(16'h7444)) 
    s_axi_bvalid_i_1
       (.I0(s_axi_bready),
        .I1(s_axi_bvalid_reg_0),
        .I2(w_pending_reg_n_0),
        .I3(aw_pending),
        .O(s_axi_bvalid_i_1_n_0));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI BVALID" *) 
  FDRE s_axi_bvalid_reg
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(s_axi_bvalid_i_1_n_0),
        .Q(s_axi_bvalid_reg_0),
        .R(p_0_in));
  LUT6 #(
    .INIT(64'h000A00A08000AA0A)) 
    \s_axi_rdata[10]_i_1 
       (.I0(\s_axi_rdata[31]_i_3_n_0 ),
        .I1(scratch[10]),
        .I2(s_axi_araddr[3]),
        .I3(s_axi_araddr[5]),
        .I4(s_axi_araddr[2]),
        .I5(s_axi_araddr[4]),
        .O(\s_axi_rdata[10]_i_1_n_0 ));
  LUT6 #(
    .INIT(64'h00800000000A00AA)) 
    \s_axi_rdata[11]_i_1 
       (.I0(\s_axi_rdata[31]_i_3_n_0 ),
        .I1(scratch[11]),
        .I2(s_axi_araddr[5]),
        .I3(s_axi_araddr[4]),
        .I4(s_axi_araddr[3]),
        .I5(s_axi_araddr[2]),
        .O(\s_axi_rdata[11]_i_1_n_0 ));
  LUT6 #(
    .INIT(64'h0822002220082008)) 
    \s_axi_rdata[12]_i_1 
       (.I0(\s_axi_rdata[31]_i_3_n_0 ),
        .I1(s_axi_araddr[5]),
        .I2(s_axi_araddr[4]),
        .I3(s_axi_araddr[2]),
        .I4(scratch[12]),
        .I5(s_axi_araddr[3]),
        .O(\s_axi_rdata[12]_i_1_n_0 ));
  LUT6 #(
    .INIT(64'h0800000800000008)) 
    \s_axi_rdata[13]_i_1 
       (.I0(s_axi_araddr[3]),
        .I1(\s_axi_rdata[31]_i_3_n_0 ),
        .I2(s_axi_araddr[4]),
        .I3(s_axi_araddr[2]),
        .I4(s_axi_araddr[5]),
        .I5(scratch[13]),
        .O(\s_axi_rdata[13]_i_1_n_0 ));
  LUT6 #(
    .INIT(64'h00800000000A00AA)) 
    \s_axi_rdata[14]_i_1 
       (.I0(\s_axi_rdata[31]_i_3_n_0 ),
        .I1(scratch[14]),
        .I2(s_axi_araddr[5]),
        .I3(s_axi_araddr[4]),
        .I4(s_axi_araddr[3]),
        .I5(s_axi_araddr[2]),
        .O(\s_axi_rdata[14]_i_1_n_0 ));
  LUT6 #(
    .INIT(64'h0A02020220802080)) 
    \s_axi_rdata[15]_i_1 
       (.I0(\s_axi_rdata[31]_i_3_n_0 ),
        .I1(s_axi_araddr[2]),
        .I2(s_axi_araddr[4]),
        .I3(s_axi_araddr[3]),
        .I4(scratch[15]),
        .I5(s_axi_araddr[5]),
        .O(\s_axi_rdata[15]_i_1_n_0 ));
  LUT6 #(
    .INIT(64'h00000000A22A222A)) 
    \s_axi_rdata[16]_i_1 
       (.I0(\s_axi_rdata[31]_i_3_n_0 ),
        .I1(s_axi_araddr[2]),
        .I2(s_axi_araddr[3]),
        .I3(s_axi_araddr[5]),
        .I4(scratch[16]),
        .I5(s_axi_araddr[4]),
        .O(\s_axi_rdata[16]_i_1_n_0 ));
  LUT6 #(
    .INIT(64'h008000000000000A)) 
    \s_axi_rdata[17]_i_1 
       (.I0(\s_axi_rdata[31]_i_3_n_0 ),
        .I1(scratch[17]),
        .I2(s_axi_araddr[5]),
        .I3(s_axi_araddr[4]),
        .I4(s_axi_araddr[3]),
        .I5(s_axi_araddr[2]),
        .O(\s_axi_rdata[17]_i_1_n_0 ));
  LUT6 #(
    .INIT(64'h2002020200020202)) 
    \s_axi_rdata[18]_i_1 
       (.I0(\s_axi_rdata[31]_i_3_n_0 ),
        .I1(s_axi_araddr[4]),
        .I2(s_axi_araddr[2]),
        .I3(s_axi_araddr[5]),
        .I4(s_axi_araddr[3]),
        .I5(scratch[18]),
        .O(\s_axi_rdata[18]_i_1_n_0 ));
  LUT6 #(
    .INIT(64'h00800A000A0A0000)) 
    \s_axi_rdata[19]_i_1 
       (.I0(\s_axi_rdata[31]_i_3_n_0 ),
        .I1(scratch[19]),
        .I2(s_axi_araddr[5]),
        .I3(s_axi_araddr[4]),
        .I4(s_axi_araddr[3]),
        .I5(s_axi_araddr[2]),
        .O(\s_axi_rdata[19]_i_1_n_0 ));
  LUT6 #(
    .INIT(64'h0000000000000001)) 
    \s_axi_rdata[1]_i_2 
       (.I0(s_axi_araddr[10]),
        .I1(s_axi_araddr[9]),
        .I2(s_axi_araddr[6]),
        .I3(s_axi_araddr[11]),
        .I4(s_axi_araddr[7]),
        .I5(s_axi_araddr[8]),
        .O(\s_axi_rdata[1]_i_2_n_0 ));
  LUT6 #(
    .INIT(64'h2002088200020882)) 
    \s_axi_rdata[20]_i_1 
       (.I0(\s_axi_rdata[31]_i_3_n_0 ),
        .I1(s_axi_araddr[4]),
        .I2(s_axi_araddr[2]),
        .I3(s_axi_araddr[3]),
        .I4(s_axi_araddr[5]),
        .I5(scratch[20]),
        .O(\s_axi_rdata[20]_i_1_n_0 ));
  LUT6 #(
    .INIT(64'h2002020000020200)) 
    \s_axi_rdata[21]_i_1 
       (.I0(\s_axi_rdata[31]_i_3_n_0 ),
        .I1(s_axi_araddr[4]),
        .I2(s_axi_araddr[2]),
        .I3(s_axi_araddr[5]),
        .I4(s_axi_araddr[3]),
        .I5(scratch[21]),
        .O(\s_axi_rdata[21]_i_1_n_0 ));
  LUT6 #(
    .INIT(64'h00800000000000AA)) 
    \s_axi_rdata[22]_i_1 
       (.I0(\s_axi_rdata[31]_i_3_n_0 ),
        .I1(scratch[22]),
        .I2(s_axi_araddr[5]),
        .I3(s_axi_araddr[4]),
        .I4(s_axi_araddr[3]),
        .I5(s_axi_araddr[2]),
        .O(\s_axi_rdata[22]_i_1_n_0 ));
  LUT6 #(
    .INIT(64'h0822002220082008)) 
    \s_axi_rdata[23]_i_1 
       (.I0(\s_axi_rdata[31]_i_3_n_0 ),
        .I1(s_axi_araddr[5]),
        .I2(s_axi_araddr[4]),
        .I3(s_axi_araddr[2]),
        .I4(scratch[23]),
        .I5(s_axi_araddr[3]),
        .O(\s_axi_rdata[23]_i_1_n_0 ));
  LUT6 #(
    .INIT(64'h2002020000020200)) 
    \s_axi_rdata[24]_i_1 
       (.I0(\s_axi_rdata[31]_i_3_n_0 ),
        .I1(s_axi_araddr[4]),
        .I2(s_axi_araddr[2]),
        .I3(s_axi_araddr[5]),
        .I4(s_axi_araddr[3]),
        .I5(scratch[24]),
        .O(\s_axi_rdata[24]_i_1_n_0 ));
  LUT6 #(
    .INIT(64'h0800000800000008)) 
    \s_axi_rdata[25]_i_1 
       (.I0(s_axi_araddr[3]),
        .I1(\s_axi_rdata[31]_i_3_n_0 ),
        .I2(s_axi_araddr[4]),
        .I3(s_axi_araddr[2]),
        .I4(s_axi_araddr[5]),
        .I5(scratch[25]),
        .O(\s_axi_rdata[25]_i_1_n_0 ));
  LUT6 #(
    .INIT(64'h0000000080080008)) 
    \s_axi_rdata[26]_i_1 
       (.I0(s_axi_araddr[5]),
        .I1(\s_axi_rdata[31]_i_3_n_0 ),
        .I2(s_axi_araddr[2]),
        .I3(s_axi_araddr[3]),
        .I4(scratch[26]),
        .I5(s_axi_araddr[4]),
        .O(\s_axi_rdata[26]_i_1_n_0 ));
  LUT6 #(
    .INIT(64'h0800000000080008)) 
    \s_axi_rdata[27]_i_1 
       (.I0(s_axi_araddr[3]),
        .I1(\s_axi_rdata[31]_i_3_n_0 ),
        .I2(s_axi_araddr[4]),
        .I3(s_axi_araddr[5]),
        .I4(scratch[27]),
        .I5(s_axi_araddr[2]),
        .O(\s_axi_rdata[27]_i_1_n_0 ));
  LUT6 #(
    .INIT(64'h008000000000000A)) 
    \s_axi_rdata[28]_i_1 
       (.I0(\s_axi_rdata[31]_i_3_n_0 ),
        .I1(scratch[28]),
        .I2(s_axi_araddr[5]),
        .I3(s_axi_araddr[4]),
        .I4(s_axi_araddr[3]),
        .I5(s_axi_araddr[2]),
        .O(\s_axi_rdata[28]_i_1_n_0 ));
  LUT6 #(
    .INIT(64'h0800000000000000)) 
    \s_axi_rdata[29]_i_1 
       (.I0(scratch[29]),
        .I1(\s_axi_rdata[31]_i_3_n_0 ),
        .I2(s_axi_araddr[4]),
        .I3(s_axi_araddr[5]),
        .I4(s_axi_araddr[3]),
        .I5(s_axi_araddr[2]),
        .O(\s_axi_rdata[29]_i_1_n_0 ));
  LUT6 #(
    .INIT(64'h000080002828A2A2)) 
    \s_axi_rdata[2]_i_1 
       (.I0(\s_axi_rdata[31]_i_3_n_0 ),
        .I1(s_axi_araddr[2]),
        .I2(s_axi_araddr[3]),
        .I3(scratch[2]),
        .I4(s_axi_araddr[4]),
        .I5(s_axi_araddr[5]),
        .O(\s_axi_rdata[2]_i_1_n_0 ));
  LUT6 #(
    .INIT(64'h008000000000000A)) 
    \s_axi_rdata[30]_i_1 
       (.I0(\s_axi_rdata[31]_i_3_n_0 ),
        .I1(scratch[30]),
        .I2(s_axi_araddr[5]),
        .I3(s_axi_araddr[4]),
        .I4(s_axi_araddr[3]),
        .I5(s_axi_araddr[2]),
        .O(\s_axi_rdata[30]_i_1_n_0 ));
  LUT2 #(
    .INIT(4'h2)) 
    \s_axi_rdata[31]_i_1 
       (.I0(s_axi_arvalid),
        .I1(s_axi_rvalid_reg_0),
        .O(s_axi_rvalid01_out));
  LUT6 #(
    .INIT(64'h0800000000000000)) 
    \s_axi_rdata[31]_i_2 
       (.I0(scratch[31]),
        .I1(\s_axi_rdata[31]_i_3_n_0 ),
        .I2(s_axi_araddr[4]),
        .I3(s_axi_araddr[5]),
        .I4(s_axi_araddr[3]),
        .I5(s_axi_araddr[2]),
        .O(\s_axi_rdata[31]_i_2_n_0 ));
  LUT3 #(
    .INIT(8'h10)) 
    \s_axi_rdata[31]_i_3 
       (.I0(s_axi_araddr[0]),
        .I1(s_axi_araddr[1]),
        .I2(\s_axi_rdata[1]_i_2_n_0 ),
        .O(\s_axi_rdata[31]_i_3_n_0 ));
  LUT6 #(
    .INIT(64'h0822002220082008)) 
    \s_axi_rdata[3]_i_1 
       (.I0(\s_axi_rdata[31]_i_3_n_0 ),
        .I1(s_axi_araddr[5]),
        .I2(s_axi_araddr[4]),
        .I3(s_axi_araddr[2]),
        .I4(scratch[3]),
        .I5(s_axi_araddr[3]),
        .O(\s_axi_rdata[3]_i_1_n_0 ));
  LUT6 #(
    .INIT(64'h000A00A080000A0A)) 
    \s_axi_rdata[4]_i_1 
       (.I0(\s_axi_rdata[31]_i_3_n_0 ),
        .I1(scratch[4]),
        .I2(s_axi_araddr[3]),
        .I3(s_axi_araddr[5]),
        .I4(s_axi_araddr[2]),
        .I5(s_axi_araddr[4]),
        .O(\s_axi_rdata[4]_i_1_n_0 ));
  LUT6 #(
    .INIT(64'h0080000000880088)) 
    \s_axi_rdata[5]_i_1 
       (.I0(s_axi_araddr[3]),
        .I1(\s_axi_rdata[31]_i_3_n_0 ),
        .I2(scratch[5]),
        .I3(s_axi_araddr[4]),
        .I4(s_axi_araddr[5]),
        .I5(s_axi_araddr[2]),
        .O(\s_axi_rdata[5]_i_1_n_0 ));
  LUT6 #(
    .INIT(64'h008000000000000A)) 
    \s_axi_rdata[6]_i_1 
       (.I0(\s_axi_rdata[31]_i_3_n_0 ),
        .I1(scratch[6]),
        .I2(s_axi_araddr[5]),
        .I3(s_axi_araddr[4]),
        .I4(s_axi_araddr[3]),
        .I5(s_axi_araddr[2]),
        .O(\s_axi_rdata[6]_i_1_n_0 ));
  LUT6 #(
    .INIT(64'h0080000000880088)) 
    \s_axi_rdata[7]_i_1 
       (.I0(s_axi_araddr[3]),
        .I1(\s_axi_rdata[31]_i_3_n_0 ),
        .I2(scratch[7]),
        .I3(s_axi_araddr[4]),
        .I4(s_axi_araddr[5]),
        .I5(s_axi_araddr[2]),
        .O(\s_axi_rdata[7]_i_1_n_0 ));
  LUT6 #(
    .INIT(64'h00800000000A00AA)) 
    \s_axi_rdata[8]_i_1 
       (.I0(\s_axi_rdata[31]_i_3_n_0 ),
        .I1(scratch[8]),
        .I2(s_axi_araddr[5]),
        .I3(s_axi_araddr[4]),
        .I4(s_axi_araddr[3]),
        .I5(s_axi_araddr[2]),
        .O(\s_axi_rdata[8]_i_1_n_0 ));
  LUT6 #(
    .INIT(64'h0A00020020802080)) 
    \s_axi_rdata[9]_i_1 
       (.I0(\s_axi_rdata[31]_i_3_n_0 ),
        .I1(s_axi_araddr[2]),
        .I2(s_axi_araddr[4]),
        .I3(s_axi_araddr[3]),
        .I4(scratch[9]),
        .I5(s_axi_araddr[5]),
        .O(\s_axi_rdata[9]_i_1_n_0 ));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) 
  FDRE \s_axi_rdata_reg[0] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(burst_n_3),
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
        .D(burst_n_2),
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
    .INIT(32'hF100FFFF)) 
    \s_axi_rresp[1]_i_1 
       (.I0(s_axi_araddr[3]),
        .I1(s_axi_araddr[2]),
        .I2(s_axi_araddr[5]),
        .I3(s_axi_araddr[4]),
        .I4(\s_axi_rdata[31]_i_3_n_0 ),
        .O(\s_axi_rresp[1]_i_1_n_0 ));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RRESP" *) 
  FDRE \s_axi_rresp_reg[1] 
       (.C(s_axi_aclk),
        .CE(s_axi_rvalid01_out),
        .D(\s_axi_rresp[1]_i_1_n_0 ),
        .Q(s_axi_rresp),
        .R(p_0_in));
  (* SOFT_HLUTNM = "soft_lutpair3" *) 
  LUT3 #(
    .INIT(8'h3A)) 
    s_axi_rvalid_i_1
       (.I0(s_axi_arvalid),
        .I1(s_axi_rready),
        .I2(s_axi_rvalid_reg_0),
        .O(s_axi_rvalid_i_1_n_0));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RVALID" *) 
  FDRE s_axi_rvalid_reg
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(s_axi_rvalid_i_1_n_0),
        .Q(s_axi_rvalid_reg_0),
        .R(p_0_in));
  (* SOFT_HLUTNM = "soft_lutpair2" *) 
  LUT3 #(
    .INIT(8'h04)) 
    s_axi_wready_INST_0
       (.I0(w_pending_reg_n_0),
        .I1(s_axi_aresetn),
        .I2(s_axi_bvalid_reg_0),
        .O(s_axi_wready));
  LUT6 #(
    .INIT(64'h0000000800000000)) 
    \scratch[15]_i_1 
       (.I0(\scratch[31]_i_2_n_0 ),
        .I1(p_1_in_0),
        .I2(aw_address[0]),
        .I3(aw_address[1]),
        .I4(aw_address[4]),
        .I5(aw_address[3]),
        .O(p_1_in[15]));
  LUT6 #(
    .INIT(64'h0000000800000000)) 
    \scratch[23]_i_1 
       (.I0(\scratch[31]_i_2_n_0 ),
        .I1(p_2_in),
        .I2(aw_address[0]),
        .I3(aw_address[1]),
        .I4(aw_address[4]),
        .I5(aw_address[3]),
        .O(p_1_in[23]));
  LUT6 #(
    .INIT(64'h0000000800000000)) 
    \scratch[31]_i_1 
       (.I0(\scratch[31]_i_2_n_0 ),
        .I1(\w_strobes_reg_n_0_[3] ),
        .I2(aw_address[0]),
        .I3(aw_address[1]),
        .I4(aw_address[4]),
        .I5(aw_address[3]),
        .O(p_1_in[31]));
  LUT5 #(
    .INIT(32'h11111000)) 
    \scratch[31]_i_2 
       (.I0(burst_n_1),
        .I1(\scratch[31]_i_3_n_0 ),
        .I2(aw_address[3]),
        .I3(aw_address[2]),
        .I4(aw_address[4]),
        .O(\scratch[31]_i_2_n_0 ));
  LUT6 #(
    .INIT(64'hFF45FFFFFFFFFFFF)) 
    \scratch[31]_i_3 
       (.I0(aw_address[1]),
        .I1(aw_address[0]),
        .I2(aw_address[5]),
        .I3(s_axi_bvalid_reg_0),
        .I4(w_pending_reg_n_0),
        .I5(aw_pending),
        .O(\scratch[31]_i_3_n_0 ));
  LUT6 #(
    .INIT(64'h0000000800000000)) 
    \scratch[7]_i_1 
       (.I0(\scratch[31]_i_2_n_0 ),
        .I1(p_0_in_1),
        .I2(aw_address[0]),
        .I3(aw_address[1]),
        .I4(aw_address[4]),
        .I5(aw_address[3]),
        .O(p_1_in[7]));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[0] 
       (.C(s_axi_aclk),
        .CE(p_1_in[7]),
        .D(w_data[0]),
        .Q(scratch[0]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[10] 
       (.C(s_axi_aclk),
        .CE(p_1_in[15]),
        .D(w_data[10]),
        .Q(scratch[10]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[11] 
       (.C(s_axi_aclk),
        .CE(p_1_in[15]),
        .D(w_data[11]),
        .Q(scratch[11]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[12] 
       (.C(s_axi_aclk),
        .CE(p_1_in[15]),
        .D(w_data[12]),
        .Q(scratch[12]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[13] 
       (.C(s_axi_aclk),
        .CE(p_1_in[15]),
        .D(w_data[13]),
        .Q(scratch[13]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[14] 
       (.C(s_axi_aclk),
        .CE(p_1_in[15]),
        .D(w_data[14]),
        .Q(scratch[14]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[15] 
       (.C(s_axi_aclk),
        .CE(p_1_in[15]),
        .D(w_data[15]),
        .Q(scratch[15]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[16] 
       (.C(s_axi_aclk),
        .CE(p_1_in[23]),
        .D(w_data[16]),
        .Q(scratch[16]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[17] 
       (.C(s_axi_aclk),
        .CE(p_1_in[23]),
        .D(w_data[17]),
        .Q(scratch[17]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[18] 
       (.C(s_axi_aclk),
        .CE(p_1_in[23]),
        .D(w_data[18]),
        .Q(scratch[18]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[19] 
       (.C(s_axi_aclk),
        .CE(p_1_in[23]),
        .D(w_data[19]),
        .Q(scratch[19]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[1] 
       (.C(s_axi_aclk),
        .CE(p_1_in[7]),
        .D(w_data[1]),
        .Q(scratch[1]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[20] 
       (.C(s_axi_aclk),
        .CE(p_1_in[23]),
        .D(w_data[20]),
        .Q(scratch[20]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[21] 
       (.C(s_axi_aclk),
        .CE(p_1_in[23]),
        .D(w_data[21]),
        .Q(scratch[21]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[22] 
       (.C(s_axi_aclk),
        .CE(p_1_in[23]),
        .D(w_data[22]),
        .Q(scratch[22]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[23] 
       (.C(s_axi_aclk),
        .CE(p_1_in[23]),
        .D(w_data[23]),
        .Q(scratch[23]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[24] 
       (.C(s_axi_aclk),
        .CE(p_1_in[31]),
        .D(w_data[24]),
        .Q(scratch[24]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[25] 
       (.C(s_axi_aclk),
        .CE(p_1_in[31]),
        .D(w_data[25]),
        .Q(scratch[25]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[26] 
       (.C(s_axi_aclk),
        .CE(p_1_in[31]),
        .D(w_data[26]),
        .Q(scratch[26]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[27] 
       (.C(s_axi_aclk),
        .CE(p_1_in[31]),
        .D(w_data[27]),
        .Q(scratch[27]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[28] 
       (.C(s_axi_aclk),
        .CE(p_1_in[31]),
        .D(w_data[28]),
        .Q(scratch[28]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[29] 
       (.C(s_axi_aclk),
        .CE(p_1_in[31]),
        .D(w_data[29]),
        .Q(scratch[29]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[2] 
       (.C(s_axi_aclk),
        .CE(p_1_in[7]),
        .D(w_data[2]),
        .Q(scratch[2]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[30] 
       (.C(s_axi_aclk),
        .CE(p_1_in[31]),
        .D(w_data[30]),
        .Q(scratch[30]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[31] 
       (.C(s_axi_aclk),
        .CE(p_1_in[31]),
        .D(w_data[31]),
        .Q(scratch[31]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[3] 
       (.C(s_axi_aclk),
        .CE(p_1_in[7]),
        .D(w_data[3]),
        .Q(scratch[3]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[4] 
       (.C(s_axi_aclk),
        .CE(p_1_in[7]),
        .D(w_data[4]),
        .Q(scratch[4]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[5] 
       (.C(s_axi_aclk),
        .CE(p_1_in[7]),
        .D(w_data[5]),
        .Q(scratch[5]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[6] 
       (.C(s_axi_aclk),
        .CE(p_1_in[7]),
        .D(w_data[6]),
        .Q(scratch[6]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[7] 
       (.C(s_axi_aclk),
        .CE(p_1_in[7]),
        .D(w_data[7]),
        .Q(scratch[7]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[8] 
       (.C(s_axi_aclk),
        .CE(p_1_in[15]),
        .D(w_data[8]),
        .Q(scratch[8]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \scratch_reg[9] 
       (.C(s_axi_aclk),
        .CE(p_1_in[15]),
        .D(w_data[9]),
        .Q(scratch[9]),
        .R(p_0_in));
  LUT3 #(
    .INIT(8'h02)) 
    \w_data[31]_i_1 
       (.I0(s_axi_wvalid),
        .I1(s_axi_bvalid_reg_0),
        .I2(w_pending_reg_n_0),
        .O(w_pending0));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[0] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[0]),
        .Q(w_data[0]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[10] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[10]),
        .Q(w_data[10]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[11] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[11]),
        .Q(w_data[11]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[12] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[12]),
        .Q(w_data[12]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[13] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[13]),
        .Q(w_data[13]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[14] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[14]),
        .Q(w_data[14]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[15] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[15]),
        .Q(w_data[15]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[16] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[16]),
        .Q(w_data[16]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[17] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[17]),
        .Q(w_data[17]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[18] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[18]),
        .Q(w_data[18]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[19] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[19]),
        .Q(w_data[19]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[1] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[1]),
        .Q(w_data[1]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[20] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[20]),
        .Q(w_data[20]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[21] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[21]),
        .Q(w_data[21]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[22] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[22]),
        .Q(w_data[22]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[23] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[23]),
        .Q(w_data[23]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[24] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[24]),
        .Q(w_data[24]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[25] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[25]),
        .Q(w_data[25]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[26] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[26]),
        .Q(w_data[26]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[27] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[27]),
        .Q(w_data[27]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[28] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[28]),
        .Q(w_data[28]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[29] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[29]),
        .Q(w_data[29]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[2] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[2]),
        .Q(w_data[2]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[30] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[30]),
        .Q(w_data[30]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[31] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[31]),
        .Q(w_data[31]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[3] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[3]),
        .Q(w_data[3]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[4] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[4]),
        .Q(w_data[4]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[5] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[5]),
        .Q(w_data[5]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[6] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[6]),
        .Q(w_data[6]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[7] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[7]),
        .Q(w_data[7]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[8] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[8]),
        .Q(w_data[8]),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \w_data_reg[9] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wdata[9]),
        .Q(w_data[9]),
        .R(p_0_in));
  LUT4 #(
    .INIT(16'h40FF)) 
    w_pending_i_1
       (.I0(s_axi_bvalid_reg_0),
        .I1(w_pending_reg_n_0),
        .I2(aw_pending),
        .I3(s_axi_aresetn),
        .O(w_pending_i_1_n_0));
  (* SOFT_HLUTNM = "soft_lutpair4" *) 
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
        .R(w_pending_i_1_n_0));
  FDRE #(
    .INIT(1'b0)) 
    \w_strobes_reg[0] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wstrb[0]),
        .Q(p_0_in_1),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \w_strobes_reg[1] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wstrb[1]),
        .Q(p_1_in_0),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \w_strobes_reg[2] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wstrb[2]),
        .Q(p_2_in),
        .R(p_0_in));
  FDRE #(
    .INIT(1'b0)) 
    \w_strobes_reg[3] 
       (.C(s_axi_aclk),
        .CE(w_pending0),
        .D(s_axi_wstrb[3]),
        .Q(\w_strobes_reg_n_0_[3] ),
        .R(p_0_in));
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
   (servo_pwm,
    \aw_address_reg[10] ,
    D,
    \aw_address_reg[5] ,
    s_axi_aclk,
    s_axi_aresetn,
    s_axi_araddr,
    Q,
    \s_axi_bresp[1]_i_4_0 ,
    aw_pending,
    \s_axi_bresp[1]_i_4_1 ,
    \s_axi_bresp[1]_i_4_2 ,
    \scratch[31]_i_2 ,
    \s_axi_bresp[1]_i_14_0 ,
    \s_axi_rdata_reg[1] ,
    \s_axi_rdata_reg[0] ,
    \s_axi_bresp_reg[1] ,
    p_5_in,
    s_axi_bresp);
  output servo_pwm;
  output \aw_address_reg[10] ;
  output [1:0]D;
  output \aw_address_reg[5] ;
  input s_axi_aclk;
  input s_axi_aresetn;
  input [5:0]s_axi_araddr;
  input [1:0]Q;
  input [31:0]\s_axi_bresp[1]_i_4_0 ;
  input aw_pending;
  input \s_axi_bresp[1]_i_4_1 ;
  input \s_axi_bresp[1]_i_4_2 ;
  input [11:0]\scratch[31]_i_2 ;
  input [3:0]\s_axi_bresp[1]_i_14_0 ;
  input \s_axi_rdata_reg[1] ;
  input \s_axi_rdata_reg[0] ;
  input \s_axi_bresp_reg[1] ;
  input p_5_in;
  input [0:0]s_axi_bresp;

  wire [1:0]D;
  wire [1:0]Q;
  wire \aw_address_reg[10] ;
  wire \aw_address_reg[5] ;
  wire aw_pending;
  wire busy;
  wire busy_i_1_n_0;
  wire p_5_in;
  wire \phase[0]_i_10_n_0 ;
  wire \phase[0]_i_11_n_0 ;
  wire \phase[0]_i_1_n_0 ;
  wire \phase[0]_i_3_n_0 ;
  wire \phase[0]_i_4_n_0 ;
  wire \phase[0]_i_5_n_0 ;
  wire \phase[0]_i_6_n_0 ;
  wire \phase[0]_i_7_n_0 ;
  wire \phase[0]_i_8_n_0 ;
  wire \phase[0]_i_9_n_0 ;
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
  wire [32:2]pwm1;
  wire pwm_i_10_n_0;
  wire pwm_i_11_n_0;
  wire pwm_i_13_n_0;
  wire pwm_i_15_n_0;
  wire pwm_i_16_n_0;
  wire pwm_i_1_n_0;
  wire pwm_i_2_n_0;
  wire pwm_i_3_n_0;
  wire pwm_i_4_n_0;
  wire pwm_i_6_n_0;
  wire pwm_i_7_n_0;
  wire pwm_i_8_n_0;
  wire pwm_reg_i_12_n_2;
  wire pwm_reg_i_12_n_3;
  wire pwm_reg_i_12_n_4;
  wire pwm_reg_i_12_n_5;
  wire pwm_reg_i_12_n_6;
  wire pwm_reg_i_12_n_7;
  wire pwm_reg_i_14_n_0;
  wire pwm_reg_i_14_n_1;
  wire pwm_reg_i_14_n_2;
  wire pwm_reg_i_14_n_3;
  wire pwm_reg_i_14_n_4;
  wire pwm_reg_i_14_n_5;
  wire pwm_reg_i_14_n_6;
  wire pwm_reg_i_14_n_7;
  wire pwm_reg_i_5_n_0;
  wire pwm_reg_i_5_n_1;
  wire pwm_reg_i_5_n_2;
  wire pwm_reg_i_5_n_3;
  wire pwm_reg_i_5_n_4;
  wire pwm_reg_i_5_n_5;
  wire pwm_reg_i_5_n_6;
  wire pwm_reg_i_5_n_7;
  wire pwm_reg_i_9_n_0;
  wire pwm_reg_i_9_n_1;
  wire pwm_reg_i_9_n_2;
  wire pwm_reg_i_9_n_3;
  wire pwm_reg_i_9_n_4;
  wire pwm_reg_i_9_n_5;
  wire pwm_reg_i_9_n_6;
  wire pwm_reg_i_9_n_7;
  wire s_axi_aclk;
  wire [5:0]s_axi_araddr;
  wire s_axi_aresetn;
  wire [0:0]s_axi_bresp;
  wire \s_axi_bresp[1]_i_10_n_0 ;
  wire \s_axi_bresp[1]_i_11_n_0 ;
  wire [3:0]\s_axi_bresp[1]_i_14_0 ;
  wire \s_axi_bresp[1]_i_14_n_0 ;
  wire \s_axi_bresp[1]_i_15_n_0 ;
  wire \s_axi_bresp[1]_i_16_n_0 ;
  wire \s_axi_bresp[1]_i_17_n_0 ;
  wire \s_axi_bresp[1]_i_18_n_0 ;
  wire \s_axi_bresp[1]_i_19_n_0 ;
  wire \s_axi_bresp[1]_i_20_n_0 ;
  wire \s_axi_bresp[1]_i_3_n_0 ;
  wire [31:0]\s_axi_bresp[1]_i_4_0 ;
  wire \s_axi_bresp[1]_i_4_1 ;
  wire \s_axi_bresp[1]_i_4_2 ;
  wire \s_axi_bresp[1]_i_7_n_0 ;
  wire \s_axi_bresp[1]_i_8_n_0 ;
  wire \s_axi_bresp[1]_i_9_n_0 ;
  wire \s_axi_bresp_reg[1] ;
  wire \s_axi_rdata[0]_i_2_n_0 ;
  wire \s_axi_rdata[1]_i_3_n_0 ;
  wire \s_axi_rdata_reg[0] ;
  wire \s_axi_rdata_reg[1] ;
  wire [11:0]\scratch[31]_i_2 ;
  wire servo_pwm;
  wire start;
  wire [7:7]\NLW_phase_reg[24]_i_1_CO_UNCONNECTED ;
  wire [6:6]NLW_pwm_reg_i_12_CO_UNCONNECTED;
  wire [7:7]NLW_pwm_reg_i_12_O_UNCONNECTED;
  wire [0:0]NLW_pwm_reg_i_14_O_UNCONNECTED;

  LUT2 #(
    .INIT(4'hE)) 
    busy_i_1
       (.I0(start),
        .I1(busy),
        .O(busy_i_1_n_0));
  FDRE #(
    .INIT(1'b0)) 
    busy_reg
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(busy_i_1_n_0),
        .Q(busy),
        .R(pwm_i_1_n_0));
  LUT6 #(
    .INIT(64'hFFFF0004FFFFFFFF)) 
    \phase[0]_i_1 
       (.I0(\phase[0]_i_3_n_0 ),
        .I1(\phase[0]_i_4_n_0 ),
        .I2(\phase[0]_i_5_n_0 ),
        .I3(\phase[0]_i_6_n_0 ),
        .I4(pwm_i_1_n_0),
        .I5(busy),
        .O(\phase[0]_i_1_n_0 ));
  LUT4 #(
    .INIT(16'hFFEF)) 
    \phase[0]_i_10 
       (.I0(phase_reg[2]),
        .I1(phase_reg[6]),
        .I2(phase_reg[10]),
        .I3(phase_reg[16]),
        .O(\phase[0]_i_10_n_0 ));
  LUT4 #(
    .INIT(16'hDFFF)) 
    \phase[0]_i_11 
       (.I0(phase_reg[3]),
        .I1(phase_reg[14]),
        .I2(phase_reg[19]),
        .I3(phase_reg[15]),
        .O(\phase[0]_i_11_n_0 ));
  LUT5 #(
    .INIT(32'hFFFFFEFF)) 
    \phase[0]_i_3 
       (.I0(phase_reg[21]),
        .I1(phase_reg[27]),
        .I2(phase_reg[28]),
        .I3(phase_reg[9]),
        .I4(\phase[0]_i_8_n_0 ),
        .O(\phase[0]_i_3_n_0 ));
  LUT5 #(
    .INIT(32'h00000001)) 
    \phase[0]_i_4 
       (.I0(phase_reg[24]),
        .I1(phase_reg[29]),
        .I2(phase_reg[5]),
        .I3(phase_reg[30]),
        .I4(\phase[0]_i_9_n_0 ),
        .O(\phase[0]_i_4_n_0 ));
  LUT5 #(
    .INIT(32'hFFFFFBFF)) 
    \phase[0]_i_5 
       (.I0(phase_reg[7]),
        .I1(phase_reg[12]),
        .I2(phase_reg[17]),
        .I3(phase_reg[0]),
        .I4(\phase[0]_i_10_n_0 ),
        .O(\phase[0]_i_5_n_0 ));
  LUT5 #(
    .INIT(32'hFFFFFEFF)) 
    \phase[0]_i_6 
       (.I0(phase_reg[22]),
        .I1(phase_reg[25]),
        .I2(phase_reg[31]),
        .I3(phase_reg[1]),
        .I4(\phase[0]_i_11_n_0 ),
        .O(\phase[0]_i_6_n_0 ));
  LUT1 #(
    .INIT(2'h1)) 
    \phase[0]_i_7 
       (.I0(phase_reg[0]),
        .O(\phase[0]_i_7_n_0 ));
  LUT4 #(
    .INIT(16'hFFFE)) 
    \phase[0]_i_8 
       (.I0(phase_reg[26]),
        .I1(phase_reg[13]),
        .I2(phase_reg[8]),
        .I3(phase_reg[18]),
        .O(\phase[0]_i_8_n_0 ));
  LUT4 #(
    .INIT(16'hDFFF)) 
    \phase[0]_i_9 
       (.I0(phase_reg[23]),
        .I1(phase_reg[11]),
        .I2(phase_reg[20]),
        .I3(phase_reg[4]),
        .O(\phase[0]_i_9_n_0 ));
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
        .S({phase_reg[7:1],\phase[0]_i_7_n_0 }));
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
  LUT2 #(
    .INIT(4'hB)) 
    pwm_i_1
       (.I0(\s_axi_bresp[1]_i_3_n_0 ),
        .I1(s_axi_aresetn),
        .O(pwm_i_1_n_0));
  LUT6 #(
    .INIT(64'h5555555557FFFFFF)) 
    pwm_i_10
       (.I0(pwm1[12]),
        .I1(pwm_i_15_n_0),
        .I2(pwm_i_16_n_0),
        .I3(pwm1[9]),
        .I4(pwm1[10]),
        .I5(pwm1[11]),
        .O(pwm_i_10_n_0));
  LUT2 #(
    .INIT(4'h7)) 
    pwm_i_11
       (.I0(pwm1[20]),
        .I1(pwm1[19]),
        .O(pwm_i_11_n_0));
  LUT6 #(
    .INIT(64'hFFFFFFFFFFFFFFFE)) 
    pwm_i_13
       (.I0(pwm1[26]),
        .I1(pwm1[30]),
        .I2(pwm1[31]),
        .I3(pwm1[25]),
        .I4(pwm1[27]),
        .I5(pwm1[24]),
        .O(pwm_i_13_n_0));
  LUT4 #(
    .INIT(16'hFFFE)) 
    pwm_i_15
       (.I0(pwm1[5]),
        .I1(pwm1[8]),
        .I2(pwm1[6]),
        .I3(pwm1[7]),
        .O(pwm_i_15_n_0));
  LUT3 #(
    .INIT(8'h80)) 
    pwm_i_16
       (.I0(pwm1[4]),
        .I1(pwm1[2]),
        .I2(pwm1[3]),
        .O(pwm_i_16_n_0));
  LUT6 #(
    .INIT(64'hFFFFFFFFFFFF004F)) 
    pwm_i_2
       (.I0(pwm_i_3_n_0),
        .I1(pwm_i_4_n_0),
        .I2(pwm1[23]),
        .I3(pwm_i_6_n_0),
        .I4(start),
        .I5(pwm_i_7_n_0),
        .O(pwm_i_2_n_0));
  LUT2 #(
    .INIT(4'hE)) 
    pwm_i_3
       (.I0(pwm1[22]),
        .I1(pwm1[21]),
        .O(pwm_i_3_n_0));
  LUT6 #(
    .INIT(64'hFFFFFFFF11111151)) 
    pwm_i_4
       (.I0(pwm_i_8_n_0),
        .I1(pwm1[15]),
        .I2(pwm_i_10_n_0),
        .I3(pwm1[14]),
        .I4(pwm1[13]),
        .I5(pwm_i_11_n_0),
        .O(pwm_i_4_n_0));
  LUT5 #(
    .INIT(32'hFFFFFEFF)) 
    pwm_i_6
       (.I0(pwm1[32]),
        .I1(pwm1[28]),
        .I2(pwm1[29]),
        .I3(busy),
        .I4(pwm_i_13_n_0),
        .O(pwm_i_6_n_0));
  LUT5 #(
    .INIT(32'h00040000)) 
    pwm_i_7
       (.I0(\phase[0]_i_3_n_0 ),
        .I1(\phase[0]_i_4_n_0 ),
        .I2(\phase[0]_i_5_n_0 ),
        .I3(\phase[0]_i_6_n_0 ),
        .I4(busy),
        .O(pwm_i_7_n_0));
  LUT3 #(
    .INIT(8'hFE)) 
    pwm_i_8
       (.I0(pwm1[18]),
        .I1(pwm1[16]),
        .I2(pwm1[17]),
        .O(pwm_i_8_n_0));
  FDRE #(
    .INIT(1'b0)) 
    pwm_reg
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(pwm_i_2_n_0),
        .Q(servo_pwm),
        .R(pwm_i_1_n_0));
  CARRY8 pwm_reg_i_12
       (.CI(pwm_reg_i_5_n_0),
        .CI_TOP(1'b0),
        .CO({pwm1[32],NLW_pwm_reg_i_12_CO_UNCONNECTED[6],pwm_reg_i_12_n_2,pwm_reg_i_12_n_3,pwm_reg_i_12_n_4,pwm_reg_i_12_n_5,pwm_reg_i_12_n_6,pwm_reg_i_12_n_7}),
        .DI({1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0}),
        .O({NLW_pwm_reg_i_12_O_UNCONNECTED[7],pwm1[31:25]}),
        .S({1'b1,phase_reg[31:25]}));
  CARRY8 pwm_reg_i_14
       (.CI(phase_reg[0]),
        .CI_TOP(1'b0),
        .CO({pwm_reg_i_14_n_0,pwm_reg_i_14_n_1,pwm_reg_i_14_n_2,pwm_reg_i_14_n_3,pwm_reg_i_14_n_4,pwm_reg_i_14_n_5,pwm_reg_i_14_n_6,pwm_reg_i_14_n_7}),
        .DI({1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0}),
        .O({pwm1[8:2],NLW_pwm_reg_i_14_O_UNCONNECTED[0]}),
        .S(phase_reg[8:1]));
  CARRY8 pwm_reg_i_5
       (.CI(pwm_reg_i_9_n_0),
        .CI_TOP(1'b0),
        .CO({pwm_reg_i_5_n_0,pwm_reg_i_5_n_1,pwm_reg_i_5_n_2,pwm_reg_i_5_n_3,pwm_reg_i_5_n_4,pwm_reg_i_5_n_5,pwm_reg_i_5_n_6,pwm_reg_i_5_n_7}),
        .DI({1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0}),
        .O(pwm1[24:17]),
        .S(phase_reg[24:17]));
  CARRY8 pwm_reg_i_9
       (.CI(pwm_reg_i_14_n_0),
        .CI_TOP(1'b0),
        .CO({pwm_reg_i_9_n_0,pwm_reg_i_9_n_1,pwm_reg_i_9_n_2,pwm_reg_i_9_n_3,pwm_reg_i_9_n_4,pwm_reg_i_9_n_5,pwm_reg_i_9_n_6,pwm_reg_i_9_n_7}),
        .DI({1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0}),
        .O(pwm1[16:9]),
        .S(phase_reg[16:9]));
  LUT6 #(
    .INIT(64'hFFFDFFFFFFFFFFFF)) 
    \s_axi_bresp[1]_i_10 
       (.I0(\s_axi_bresp[1]_i_4_0 [28]),
        .I1(\s_axi_bresp[1]_i_4_0 [2]),
        .I2(\s_axi_bresp[1]_i_4_0 [19]),
        .I3(\s_axi_bresp[1]_i_4_0 [31]),
        .I4(\s_axi_bresp[1]_i_4_0 [8]),
        .I5(\s_axi_bresp[1]_i_4_0 [4]),
        .O(\s_axi_bresp[1]_i_10_n_0 ));
  LUT6 #(
    .INIT(64'hFFFFFFFFFFFFFFEF)) 
    \s_axi_bresp[1]_i_11 
       (.I0(\s_axi_bresp[1]_i_4_0 [9]),
        .I1(\s_axi_bresp[1]_i_4_0 [11]),
        .I2(\s_axi_bresp[1]_i_4_0 [1]),
        .I3(busy),
        .I4(\s_axi_bresp[1]_i_4_0 [10]),
        .I5(\s_axi_bresp[1]_i_17_n_0 ),
        .O(\s_axi_bresp[1]_i_11_n_0 ));
  LUT6 #(
    .INIT(64'hFFFFFFFFFFFFFFFE)) 
    \s_axi_bresp[1]_i_12 
       (.I0(\scratch[31]_i_2 [10]),
        .I1(\scratch[31]_i_2 [11]),
        .I2(\scratch[31]_i_2 [8]),
        .I3(\scratch[31]_i_2 [9]),
        .I4(\scratch[31]_i_2 [6]),
        .I5(\scratch[31]_i_2 [7]),
        .O(\aw_address_reg[10] ));
  LUT5 #(
    .INIT(32'hFFFFFBFF)) 
    \s_axi_bresp[1]_i_14 
       (.I0(\scratch[31]_i_2 [1]),
        .I1(\s_axi_bresp[1]_i_14_0 [1]),
        .I2(\scratch[31]_i_2 [5]),
        .I3(\s_axi_bresp[1]_i_14_0 [2]),
        .I4(\s_axi_bresp[1]_i_18_n_0 ),
        .O(\s_axi_bresp[1]_i_14_n_0 ));
  LUT6 #(
    .INIT(64'hFFFFFFFFFFFFFFFE)) 
    \s_axi_bresp[1]_i_15 
       (.I0(\s_axi_bresp[1]_i_19_n_0 ),
        .I1(\s_axi_bresp[1]_i_20_n_0 ),
        .I2(\s_axi_bresp[1]_i_4_0 [17]),
        .I3(\s_axi_bresp[1]_i_4_0 [16]),
        .I4(\s_axi_bresp[1]_i_4_0 [7]),
        .I5(\s_axi_bresp[1]_i_4_0 [29]),
        .O(\s_axi_bresp[1]_i_15_n_0 ));
  LUT4 #(
    .INIT(16'hFFDF)) 
    \s_axi_bresp[1]_i_16 
       (.I0(\s_axi_bresp[1]_i_4_0 [6]),
        .I1(\s_axi_bresp[1]_i_4_0 [27]),
        .I2(\s_axi_bresp[1]_i_4_0 [20]),
        .I3(\s_axi_bresp[1]_i_4_0 [26]),
        .O(\s_axi_bresp[1]_i_16_n_0 ));
  LUT2 #(
    .INIT(4'h7)) 
    \s_axi_bresp[1]_i_17 
       (.I0(\s_axi_bresp[1]_i_4_0 [18]),
        .I1(\s_axi_bresp[1]_i_4_0 [22]),
        .O(\s_axi_bresp[1]_i_17_n_0 ));
  LUT4 #(
    .INIT(16'hFFDF)) 
    \s_axi_bresp[1]_i_18 
       (.I0(\s_axi_bresp[1]_i_14_0 [0]),
        .I1(\scratch[31]_i_2 [0]),
        .I2(\s_axi_bresp[1]_i_14_0 [3]),
        .I3(\scratch[31]_i_2 [2]),
        .O(\s_axi_bresp[1]_i_18_n_0 ));
  LUT6 #(
    .INIT(64'hFFFFFFFFFFFFFDFF)) 
    \s_axi_bresp[1]_i_19 
       (.I0(\scratch[31]_i_2 [4]),
        .I1(\scratch[31]_i_2 [3]),
        .I2(\s_axi_bresp[1]_i_4_0 [21]),
        .I3(\s_axi_bresp[1]_i_4_0 [25]),
        .I4(\s_axi_bresp[1]_i_4_0 [13]),
        .I5(\s_axi_bresp[1]_i_4_0 [23]),
        .O(\s_axi_bresp[1]_i_19_n_0 ));
  LUT6 #(
    .INIT(64'hFF01FFFFFF010000)) 
    \s_axi_bresp[1]_i_2 
       (.I0(\scratch[31]_i_2 [5]),
        .I1(\s_axi_bresp[1]_i_3_n_0 ),
        .I2(start),
        .I3(\s_axi_bresp_reg[1] ),
        .I4(p_5_in),
        .I5(s_axi_bresp),
        .O(\aw_address_reg[5] ));
  LUT4 #(
    .INIT(16'hFFFD)) 
    \s_axi_bresp[1]_i_20 
       (.I0(\s_axi_bresp[1]_i_4_0 [24]),
        .I1(\s_axi_bresp[1]_i_4_0 [0]),
        .I2(\s_axi_bresp[1]_i_4_0 [3]),
        .I3(\s_axi_bresp[1]_i_4_0 [5]),
        .O(\s_axi_bresp[1]_i_20_n_0 ));
  (* SOFT_HLUTNM = "soft_lutpair0" *) 
  LUT4 #(
    .INIT(16'h0002)) 
    \s_axi_bresp[1]_i_3 
       (.I0(\s_axi_bresp[1]_i_7_n_0 ),
        .I1(\s_axi_bresp[1]_i_8_n_0 ),
        .I2(\s_axi_bresp[1]_i_9_n_0 ),
        .I3(\s_axi_bresp[1]_i_10_n_0 ),
        .O(\s_axi_bresp[1]_i_3_n_0 ));
  (* SOFT_HLUTNM = "soft_lutpair0" *) 
  LUT4 #(
    .INIT(16'h0002)) 
    \s_axi_bresp[1]_i_4 
       (.I0(\s_axi_bresp[1]_i_7_n_0 ),
        .I1(\s_axi_bresp[1]_i_9_n_0 ),
        .I2(\s_axi_bresp[1]_i_11_n_0 ),
        .I3(\s_axi_bresp[1]_i_10_n_0 ),
        .O(start));
  LUT6 #(
    .INIT(64'h0000000000000040)) 
    \s_axi_bresp[1]_i_7 
       (.I0(\s_axi_bresp[1]_i_14_n_0 ),
        .I1(aw_pending),
        .I2(\s_axi_bresp[1]_i_4_1 ),
        .I3(\s_axi_bresp[1]_i_4_2 ),
        .I4(\s_axi_bresp[1]_i_15_n_0 ),
        .I5(\aw_address_reg[10] ),
        .O(\s_axi_bresp[1]_i_7_n_0 ));
  LUT6 #(
    .INIT(64'hF7FFFFFFFFFFFFFF)) 
    \s_axi_bresp[1]_i_8 
       (.I0(\s_axi_bresp[1]_i_4_0 [22]),
        .I1(\s_axi_bresp[1]_i_4_0 [18]),
        .I2(\s_axi_bresp[1]_i_4_0 [1]),
        .I3(\s_axi_bresp[1]_i_4_0 [11]),
        .I4(\s_axi_bresp[1]_i_4_0 [10]),
        .I5(\s_axi_bresp[1]_i_4_0 [9]),
        .O(\s_axi_bresp[1]_i_8_n_0 ));
  LUT5 #(
    .INIT(32'hFFFFEFFF)) 
    \s_axi_bresp[1]_i_9 
       (.I0(\s_axi_bresp[1]_i_4_0 [12]),
        .I1(\s_axi_bresp[1]_i_4_0 [15]),
        .I2(\s_axi_bresp[1]_i_4_0 [14]),
        .I3(\s_axi_bresp[1]_i_4_0 [30]),
        .I4(\s_axi_bresp[1]_i_16_n_0 ),
        .O(\s_axi_bresp[1]_i_9_n_0 ));
  LUT2 #(
    .INIT(4'h2)) 
    \s_axi_rdata[0]_i_1 
       (.I0(\s_axi_rdata_reg[0] ),
        .I1(\s_axi_rdata[0]_i_2_n_0 ),
        .O(D[0]));
  LUT6 #(
    .INIT(64'hF5F3FFFFFFFFF0FF)) 
    \s_axi_rdata[0]_i_2 
       (.I0(Q[0]),
        .I1(busy),
        .I2(s_axi_araddr[4]),
        .I3(s_axi_araddr[5]),
        .I4(s_axi_araddr[3]),
        .I5(s_axi_araddr[2]),
        .O(\s_axi_rdata[0]_i_2_n_0 ));
  LUT6 #(
    .INIT(64'h0002000000000000)) 
    \s_axi_rdata[1]_i_1 
       (.I0(\s_axi_rdata_reg[1] ),
        .I1(\s_axi_rdata[1]_i_3_n_0 ),
        .I2(s_axi_araddr[0]),
        .I3(s_axi_araddr[1]),
        .I4(s_axi_araddr[2]),
        .I5(s_axi_araddr[3]),
        .O(D[1]));
  LUT4 #(
    .INIT(16'hABFB)) 
    \s_axi_rdata[1]_i_3 
       (.I0(s_axi_araddr[4]),
        .I1(servo_pwm),
        .I2(s_axi_araddr[5]),
        .I3(Q[1]),
        .O(\s_axi_rdata[1]_i_3_n_0 ));
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
