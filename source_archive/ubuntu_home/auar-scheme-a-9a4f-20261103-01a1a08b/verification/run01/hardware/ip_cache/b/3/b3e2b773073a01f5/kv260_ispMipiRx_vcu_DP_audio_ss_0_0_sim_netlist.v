// Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
// --------------------------------------------------------------------------------
// Tool Version: Vivado v.2022.2 (lin64) Build 3671981 Fri Oct 14 04:59:54 MDT 2022
// Date        : Tue Nov  3 02:15:47 2026
// Host        : ghmd-MRA-XXX running 64-bit Ubuntu 20.04.4 LTS
// Command     : write_verilog -force -mode funcsim -rename_top decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix -prefix
//               decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_ kv260_ispMipiRx_vcu_DP_audio_ss_0_0_sim_netlist.v
// Design      : kv260_ispMipiRx_vcu_DP_audio_ss_0_0
// Purpose     : This verilog netlist is a functional simulation representation of the design and should not be modified
//               or synthesized. This netlist cannot be used for SDF annotated simulation.
// Device      : xck26-sfvc784-2LV-c
// --------------------------------------------------------------------------------
`timescale 1 ps / 1 ps

module decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_aura_audio_decerr
   (bvalid_reg_0,
    s_axi_ctrl_i2s_rx_rvalid,
    s_axi_ctrl_i2s_rx_wready,
    s_axi_ctrl_i2s_rx_awready,
    s_axi_ctrl_i2s_rx_arready,
    ACLK,
    ARESETN,
    s_axi_ctrl_i2s_rx_bready,
    s_axi_ctrl_i2s_rx_arvalid,
    s_axi_ctrl_i2s_rx_rready,
    s_axi_ctrl_i2s_rx_wvalid,
    s_axi_ctrl_i2s_rx_awvalid);
  output bvalid_reg_0;
  output [0:0]s_axi_ctrl_i2s_rx_rvalid;
  output [0:0]s_axi_ctrl_i2s_rx_wready;
  output [0:0]s_axi_ctrl_i2s_rx_awready;
  output [0:0]s_axi_ctrl_i2s_rx_arready;
  input ACLK;
  input ARESETN;
  input [0:0]s_axi_ctrl_i2s_rx_bready;
  input [0:0]s_axi_ctrl_i2s_rx_arvalid;
  input [0:0]s_axi_ctrl_i2s_rx_rready;
  input [0:0]s_axi_ctrl_i2s_rx_wvalid;
  input [0:0]s_axi_ctrl_i2s_rx_awvalid;

  wire ACLK;
  wire ARESETN;
  wire aw_pending;
  wire aw_pending_i_1_n_0;
  wire bvalid_i_1_n_0;
  wire bvalid_reg_0;
  wire rvalid_i_1_n_0;
  wire [0:0]s_axi_ctrl_i2s_rx_arready;
  wire [0:0]s_axi_ctrl_i2s_rx_arvalid;
  wire [0:0]s_axi_ctrl_i2s_rx_awready;
  wire [0:0]s_axi_ctrl_i2s_rx_awvalid;
  wire [0:0]s_axi_ctrl_i2s_rx_bready;
  wire [0:0]s_axi_ctrl_i2s_rx_rready;
  wire [0:0]s_axi_ctrl_i2s_rx_rvalid;
  wire [0:0]s_axi_ctrl_i2s_rx_wready;
  wire [0:0]s_axi_ctrl_i2s_rx_wvalid;
  wire w_pending_i_1_n_0;
  wire w_pending_i_2_n_0;
  wire w_pending_reg_n_0;

  (* SOFT_HLUTNM = "soft_lutpair2" *) 
  LUT3 #(
    .INIT(8'hF2)) 
    aw_pending_i_1
       (.I0(s_axi_ctrl_i2s_rx_awvalid),
        .I1(bvalid_reg_0),
        .I2(aw_pending),
        .O(aw_pending_i_1_n_0));
  FDRE aw_pending_reg
       (.C(ACLK),
        .CE(1'b1),
        .D(aw_pending_i_1_n_0),
        .Q(aw_pending),
        .R(w_pending_i_1_n_0));
  (* SOFT_HLUTNM = "soft_lutpair0" *) 
  LUT5 #(
    .INIT(32'h00F08080)) 
    bvalid_i_1
       (.I0(aw_pending),
        .I1(w_pending_reg_n_0),
        .I2(ARESETN),
        .I3(s_axi_ctrl_i2s_rx_bready),
        .I4(bvalid_reg_0),
        .O(bvalid_i_1_n_0));
  FDRE bvalid_reg
       (.C(ACLK),
        .CE(1'b1),
        .D(bvalid_i_1_n_0),
        .Q(bvalid_reg_0),
        .R(1'b0));
  (* SOFT_HLUTNM = "soft_lutpair1" *) 
  LUT4 #(
    .INIT(16'h0C88)) 
    rvalid_i_1
       (.I0(s_axi_ctrl_i2s_rx_arvalid),
        .I1(ARESETN),
        .I2(s_axi_ctrl_i2s_rx_rready),
        .I3(s_axi_ctrl_i2s_rx_rvalid),
        .O(rvalid_i_1_n_0));
  FDRE rvalid_reg
       (.C(ACLK),
        .CE(1'b1),
        .D(rvalid_i_1_n_0),
        .Q(s_axi_ctrl_i2s_rx_rvalid),
        .R(1'b0));
  (* SOFT_HLUTNM = "soft_lutpair1" *) 
  LUT2 #(
    .INIT(4'h2)) 
    \s_axi_ctrl_i2s_rx_arready[0]_INST_0 
       (.I0(ARESETN),
        .I1(s_axi_ctrl_i2s_rx_rvalid),
        .O(s_axi_ctrl_i2s_rx_arready));
  (* SOFT_HLUTNM = "soft_lutpair2" *) 
  LUT3 #(
    .INIT(8'h04)) 
    \s_axi_ctrl_i2s_rx_awready[0]_INST_0 
       (.I0(bvalid_reg_0),
        .I1(ARESETN),
        .I2(aw_pending),
        .O(s_axi_ctrl_i2s_rx_awready));
  (* SOFT_HLUTNM = "soft_lutpair0" *) 
  LUT3 #(
    .INIT(8'h04)) 
    \s_axi_ctrl_i2s_rx_wready[0]_INST_0 
       (.I0(bvalid_reg_0),
        .I1(ARESETN),
        .I2(w_pending_reg_n_0),
        .O(s_axi_ctrl_i2s_rx_wready));
  LUT4 #(
    .INIT(16'h20FF)) 
    w_pending_i_1
       (.I0(w_pending_reg_n_0),
        .I1(bvalid_reg_0),
        .I2(aw_pending),
        .I3(ARESETN),
        .O(w_pending_i_1_n_0));
  LUT3 #(
    .INIT(8'hF2)) 
    w_pending_i_2
       (.I0(s_axi_ctrl_i2s_rx_wvalid),
        .I1(bvalid_reg_0),
        .I2(w_pending_reg_n_0),
        .O(w_pending_i_2_n_0));
  FDRE w_pending_reg
       (.C(ACLK),
        .CE(1'b1),
        .D(w_pending_i_2_n_0),
        .Q(w_pending_reg_n_0),
        .R(w_pending_i_1_n_0));
endmodule

(* ORIG_REF_NAME = "aura_audio_decerr" *) 
module decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_aura_audio_decerr_0
   (bvalid_reg_0,
    s_axi_ctrl_i2s_tx_rvalid,
    s_axi_ctrl_i2s_tx_wready,
    s_axi_ctrl_i2s_tx_awready,
    s_axi_ctrl_i2s_tx_arready,
    ACLK,
    ARESETN,
    s_axi_ctrl_i2s_tx_bready,
    s_axi_ctrl_i2s_tx_arvalid,
    s_axi_ctrl_i2s_tx_rready,
    s_axi_ctrl_i2s_tx_wvalid,
    s_axi_ctrl_i2s_tx_awvalid);
  output bvalid_reg_0;
  output [0:0]s_axi_ctrl_i2s_tx_rvalid;
  output [0:0]s_axi_ctrl_i2s_tx_wready;
  output [0:0]s_axi_ctrl_i2s_tx_awready;
  output [0:0]s_axi_ctrl_i2s_tx_arready;
  input ACLK;
  input ARESETN;
  input [0:0]s_axi_ctrl_i2s_tx_bready;
  input [0:0]s_axi_ctrl_i2s_tx_arvalid;
  input [0:0]s_axi_ctrl_i2s_tx_rready;
  input [0:0]s_axi_ctrl_i2s_tx_wvalid;
  input [0:0]s_axi_ctrl_i2s_tx_awvalid;

  wire ACLK;
  wire ARESETN;
  wire aw_pending;
  wire aw_pending_i_1__0_n_0;
  wire bvalid_i_1__0_n_0;
  wire bvalid_reg_0;
  wire rvalid_i_1__0_n_0;
  wire [0:0]s_axi_ctrl_i2s_tx_arready;
  wire [0:0]s_axi_ctrl_i2s_tx_arvalid;
  wire [0:0]s_axi_ctrl_i2s_tx_awready;
  wire [0:0]s_axi_ctrl_i2s_tx_awvalid;
  wire [0:0]s_axi_ctrl_i2s_tx_bready;
  wire [0:0]s_axi_ctrl_i2s_tx_rready;
  wire [0:0]s_axi_ctrl_i2s_tx_rvalid;
  wire [0:0]s_axi_ctrl_i2s_tx_wready;
  wire [0:0]s_axi_ctrl_i2s_tx_wvalid;
  wire w_pending_i_1__0_n_0;
  wire w_pending_i_2__0_n_0;
  wire w_pending_reg_n_0;

  (* SOFT_HLUTNM = "soft_lutpair5" *) 
  LUT3 #(
    .INIT(8'hF2)) 
    aw_pending_i_1__0
       (.I0(s_axi_ctrl_i2s_tx_awvalid),
        .I1(bvalid_reg_0),
        .I2(aw_pending),
        .O(aw_pending_i_1__0_n_0));
  FDRE aw_pending_reg
       (.C(ACLK),
        .CE(1'b1),
        .D(aw_pending_i_1__0_n_0),
        .Q(aw_pending),
        .R(w_pending_i_1__0_n_0));
  (* SOFT_HLUTNM = "soft_lutpair3" *) 
  LUT5 #(
    .INIT(32'h00F08080)) 
    bvalid_i_1__0
       (.I0(aw_pending),
        .I1(w_pending_reg_n_0),
        .I2(ARESETN),
        .I3(s_axi_ctrl_i2s_tx_bready),
        .I4(bvalid_reg_0),
        .O(bvalid_i_1__0_n_0));
  FDRE bvalid_reg
       (.C(ACLK),
        .CE(1'b1),
        .D(bvalid_i_1__0_n_0),
        .Q(bvalid_reg_0),
        .R(1'b0));
  (* SOFT_HLUTNM = "soft_lutpair4" *) 
  LUT4 #(
    .INIT(16'h0C88)) 
    rvalid_i_1__0
       (.I0(s_axi_ctrl_i2s_tx_arvalid),
        .I1(ARESETN),
        .I2(s_axi_ctrl_i2s_tx_rready),
        .I3(s_axi_ctrl_i2s_tx_rvalid),
        .O(rvalid_i_1__0_n_0));
  FDRE rvalid_reg
       (.C(ACLK),
        .CE(1'b1),
        .D(rvalid_i_1__0_n_0),
        .Q(s_axi_ctrl_i2s_tx_rvalid),
        .R(1'b0));
  (* SOFT_HLUTNM = "soft_lutpair4" *) 
  LUT2 #(
    .INIT(4'h2)) 
    \s_axi_ctrl_i2s_tx_arready[0]_INST_0 
       (.I0(ARESETN),
        .I1(s_axi_ctrl_i2s_tx_rvalid),
        .O(s_axi_ctrl_i2s_tx_arready));
  (* SOFT_HLUTNM = "soft_lutpair5" *) 
  LUT3 #(
    .INIT(8'h04)) 
    \s_axi_ctrl_i2s_tx_awready[0]_INST_0 
       (.I0(bvalid_reg_0),
        .I1(ARESETN),
        .I2(aw_pending),
        .O(s_axi_ctrl_i2s_tx_awready));
  (* SOFT_HLUTNM = "soft_lutpair3" *) 
  LUT3 #(
    .INIT(8'h04)) 
    \s_axi_ctrl_i2s_tx_wready[0]_INST_0 
       (.I0(bvalid_reg_0),
        .I1(ARESETN),
        .I2(w_pending_reg_n_0),
        .O(s_axi_ctrl_i2s_tx_wready));
  LUT4 #(
    .INIT(16'h20FF)) 
    w_pending_i_1__0
       (.I0(w_pending_reg_n_0),
        .I1(bvalid_reg_0),
        .I2(aw_pending),
        .I3(ARESETN),
        .O(w_pending_i_1__0_n_0));
  LUT3 #(
    .INIT(8'hF2)) 
    w_pending_i_2__0
       (.I0(s_axi_ctrl_i2s_tx_wvalid),
        .I1(bvalid_reg_0),
        .I2(w_pending_reg_n_0),
        .O(w_pending_i_2__0_n_0));
  FDRE w_pending_reg
       (.C(ACLK),
        .CE(1'b1),
        .D(w_pending_i_2__0_n_0),
        .Q(w_pending_reg_n_0),
        .R(w_pending_i_1__0_n_0));
endmodule

(* ORIG_REF_NAME = "aura_audio_decerr" *) 
module decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_aura_audio_decerr_1
   (bvalid_reg_0,
    s_axi_lite_audio_fmt_rvalid,
    s_axi_lite_audio_fmt_wready,
    s_axi_lite_audio_fmt_awready,
    s_axi_lite_audio_fmt_arready,
    ACLK,
    ARESETN,
    s_axi_lite_audio_fmt_bready,
    s_axi_lite_audio_fmt_arvalid,
    s_axi_lite_audio_fmt_rready,
    s_axi_lite_audio_fmt_wvalid,
    s_axi_lite_audio_fmt_awvalid);
  output bvalid_reg_0;
  output [0:0]s_axi_lite_audio_fmt_rvalid;
  output [0:0]s_axi_lite_audio_fmt_wready;
  output [0:0]s_axi_lite_audio_fmt_awready;
  output [0:0]s_axi_lite_audio_fmt_arready;
  input ACLK;
  input ARESETN;
  input [0:0]s_axi_lite_audio_fmt_bready;
  input [0:0]s_axi_lite_audio_fmt_arvalid;
  input [0:0]s_axi_lite_audio_fmt_rready;
  input [0:0]s_axi_lite_audio_fmt_wvalid;
  input [0:0]s_axi_lite_audio_fmt_awvalid;

  wire ACLK;
  wire ARESETN;
  wire aw_pending;
  wire aw_pending_i_1__1_n_0;
  wire bvalid_i_1__1_n_0;
  wire bvalid_reg_0;
  wire rvalid_i_1__1_n_0;
  wire [0:0]s_axi_lite_audio_fmt_arready;
  wire [0:0]s_axi_lite_audio_fmt_arvalid;
  wire [0:0]s_axi_lite_audio_fmt_awready;
  wire [0:0]s_axi_lite_audio_fmt_awvalid;
  wire [0:0]s_axi_lite_audio_fmt_bready;
  wire [0:0]s_axi_lite_audio_fmt_rready;
  wire [0:0]s_axi_lite_audio_fmt_rvalid;
  wire [0:0]s_axi_lite_audio_fmt_wready;
  wire [0:0]s_axi_lite_audio_fmt_wvalid;
  wire w_pending_i_1__1_n_0;
  wire w_pending_i_2__1_n_0;
  wire w_pending_reg_n_0;

  (* SOFT_HLUTNM = "soft_lutpair8" *) 
  LUT3 #(
    .INIT(8'hF2)) 
    aw_pending_i_1__1
       (.I0(s_axi_lite_audio_fmt_awvalid),
        .I1(bvalid_reg_0),
        .I2(aw_pending),
        .O(aw_pending_i_1__1_n_0));
  FDRE aw_pending_reg
       (.C(ACLK),
        .CE(1'b1),
        .D(aw_pending_i_1__1_n_0),
        .Q(aw_pending),
        .R(w_pending_i_1__1_n_0));
  (* SOFT_HLUTNM = "soft_lutpair6" *) 
  LUT5 #(
    .INIT(32'h00F08080)) 
    bvalid_i_1__1
       (.I0(aw_pending),
        .I1(w_pending_reg_n_0),
        .I2(ARESETN),
        .I3(s_axi_lite_audio_fmt_bready),
        .I4(bvalid_reg_0),
        .O(bvalid_i_1__1_n_0));
  FDRE bvalid_reg
       (.C(ACLK),
        .CE(1'b1),
        .D(bvalid_i_1__1_n_0),
        .Q(bvalid_reg_0),
        .R(1'b0));
  (* SOFT_HLUTNM = "soft_lutpair7" *) 
  LUT4 #(
    .INIT(16'h0C88)) 
    rvalid_i_1__1
       (.I0(s_axi_lite_audio_fmt_arvalid),
        .I1(ARESETN),
        .I2(s_axi_lite_audio_fmt_rready),
        .I3(s_axi_lite_audio_fmt_rvalid),
        .O(rvalid_i_1__1_n_0));
  FDRE rvalid_reg
       (.C(ACLK),
        .CE(1'b1),
        .D(rvalid_i_1__1_n_0),
        .Q(s_axi_lite_audio_fmt_rvalid),
        .R(1'b0));
  (* SOFT_HLUTNM = "soft_lutpair7" *) 
  LUT2 #(
    .INIT(4'h2)) 
    \s_axi_lite_audio_fmt_arready[0]_INST_0 
       (.I0(ARESETN),
        .I1(s_axi_lite_audio_fmt_rvalid),
        .O(s_axi_lite_audio_fmt_arready));
  (* SOFT_HLUTNM = "soft_lutpair8" *) 
  LUT3 #(
    .INIT(8'h04)) 
    \s_axi_lite_audio_fmt_awready[0]_INST_0 
       (.I0(bvalid_reg_0),
        .I1(ARESETN),
        .I2(aw_pending),
        .O(s_axi_lite_audio_fmt_awready));
  (* SOFT_HLUTNM = "soft_lutpair6" *) 
  LUT3 #(
    .INIT(8'h04)) 
    \s_axi_lite_audio_fmt_wready[0]_INST_0 
       (.I0(bvalid_reg_0),
        .I1(ARESETN),
        .I2(w_pending_reg_n_0),
        .O(s_axi_lite_audio_fmt_wready));
  LUT4 #(
    .INIT(16'h20FF)) 
    w_pending_i_1__1
       (.I0(w_pending_reg_n_0),
        .I1(bvalid_reg_0),
        .I2(aw_pending),
        .I3(ARESETN),
        .O(w_pending_i_1__1_n_0));
  LUT3 #(
    .INIT(8'hF2)) 
    w_pending_i_2__1
       (.I0(s_axi_lite_audio_fmt_wvalid),
        .I1(bvalid_reg_0),
        .I2(w_pending_reg_n_0),
        .O(w_pending_i_2__1_n_0));
  FDRE w_pending_reg
       (.C(ACLK),
        .CE(1'b1),
        .D(w_pending_i_2__1_n_0),
        .Q(w_pending_reg_n_0),
        .R(w_pending_i_1__1_n_0));
endmodule

module decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_aura_disabled_audio
   (bvalid_reg,
    bvalid_reg_0,
    bvalid_reg_1,
    s_axi_ctrl_i2s_rx_wready,
    s_axi_ctrl_i2s_rx_awready,
    s_axi_ctrl_i2s_rx_rvalid,
    s_axi_ctrl_i2s_rx_arready,
    s_axi_ctrl_i2s_tx_wready,
    s_axi_ctrl_i2s_tx_awready,
    s_axi_ctrl_i2s_tx_rvalid,
    s_axi_ctrl_i2s_tx_arready,
    s_axi_lite_audio_fmt_wready,
    s_axi_lite_audio_fmt_awready,
    s_axi_lite_audio_fmt_rvalid,
    s_axi_lite_audio_fmt_arready,
    ARESETN,
    s_axi_ctrl_i2s_rx_bready,
    s_axi_ctrl_i2s_rx_arvalid,
    s_axi_ctrl_i2s_rx_rready,
    s_axi_ctrl_i2s_tx_bready,
    s_axi_ctrl_i2s_tx_arvalid,
    s_axi_ctrl_i2s_tx_rready,
    s_axi_lite_audio_fmt_bready,
    s_axi_lite_audio_fmt_arvalid,
    s_axi_lite_audio_fmt_rready,
    s_axi_ctrl_i2s_rx_wvalid,
    s_axi_ctrl_i2s_rx_awvalid,
    s_axi_ctrl_i2s_tx_wvalid,
    s_axi_ctrl_i2s_tx_awvalid,
    s_axi_lite_audio_fmt_wvalid,
    s_axi_lite_audio_fmt_awvalid,
    ACLK);
  output bvalid_reg;
  output bvalid_reg_0;
  output bvalid_reg_1;
  output [0:0]s_axi_ctrl_i2s_rx_wready;
  output [0:0]s_axi_ctrl_i2s_rx_awready;
  output [0:0]s_axi_ctrl_i2s_rx_rvalid;
  output [0:0]s_axi_ctrl_i2s_rx_arready;
  output [0:0]s_axi_ctrl_i2s_tx_wready;
  output [0:0]s_axi_ctrl_i2s_tx_awready;
  output [0:0]s_axi_ctrl_i2s_tx_rvalid;
  output [0:0]s_axi_ctrl_i2s_tx_arready;
  output [0:0]s_axi_lite_audio_fmt_wready;
  output [0:0]s_axi_lite_audio_fmt_awready;
  output [0:0]s_axi_lite_audio_fmt_rvalid;
  output [0:0]s_axi_lite_audio_fmt_arready;
  input ARESETN;
  input [0:0]s_axi_ctrl_i2s_rx_bready;
  input [0:0]s_axi_ctrl_i2s_rx_arvalid;
  input [0:0]s_axi_ctrl_i2s_rx_rready;
  input [0:0]s_axi_ctrl_i2s_tx_bready;
  input [0:0]s_axi_ctrl_i2s_tx_arvalid;
  input [0:0]s_axi_ctrl_i2s_tx_rready;
  input [0:0]s_axi_lite_audio_fmt_bready;
  input [0:0]s_axi_lite_audio_fmt_arvalid;
  input [0:0]s_axi_lite_audio_fmt_rready;
  input [0:0]s_axi_ctrl_i2s_rx_wvalid;
  input [0:0]s_axi_ctrl_i2s_rx_awvalid;
  input [0:0]s_axi_ctrl_i2s_tx_wvalid;
  input [0:0]s_axi_ctrl_i2s_tx_awvalid;
  input [0:0]s_axi_lite_audio_fmt_wvalid;
  input [0:0]s_axi_lite_audio_fmt_awvalid;
  input ACLK;

  wire ACLK;
  wire ARESETN;
  wire bvalid_reg;
  wire bvalid_reg_0;
  wire bvalid_reg_1;
  wire [0:0]s_axi_ctrl_i2s_rx_arready;
  wire [0:0]s_axi_ctrl_i2s_rx_arvalid;
  wire [0:0]s_axi_ctrl_i2s_rx_awready;
  wire [0:0]s_axi_ctrl_i2s_rx_awvalid;
  wire [0:0]s_axi_ctrl_i2s_rx_bready;
  wire [0:0]s_axi_ctrl_i2s_rx_rready;
  wire [0:0]s_axi_ctrl_i2s_rx_rvalid;
  wire [0:0]s_axi_ctrl_i2s_rx_wready;
  wire [0:0]s_axi_ctrl_i2s_rx_wvalid;
  wire [0:0]s_axi_ctrl_i2s_tx_arready;
  wire [0:0]s_axi_ctrl_i2s_tx_arvalid;
  wire [0:0]s_axi_ctrl_i2s_tx_awready;
  wire [0:0]s_axi_ctrl_i2s_tx_awvalid;
  wire [0:0]s_axi_ctrl_i2s_tx_bready;
  wire [0:0]s_axi_ctrl_i2s_tx_rready;
  wire [0:0]s_axi_ctrl_i2s_tx_rvalid;
  wire [0:0]s_axi_ctrl_i2s_tx_wready;
  wire [0:0]s_axi_ctrl_i2s_tx_wvalid;
  wire [0:0]s_axi_lite_audio_fmt_arready;
  wire [0:0]s_axi_lite_audio_fmt_arvalid;
  wire [0:0]s_axi_lite_audio_fmt_awready;
  wire [0:0]s_axi_lite_audio_fmt_awvalid;
  wire [0:0]s_axi_lite_audio_fmt_bready;
  wire [0:0]s_axi_lite_audio_fmt_rready;
  wire [0:0]s_axi_lite_audio_fmt_rvalid;
  wire [0:0]s_axi_lite_audio_fmt_wready;
  wire [0:0]s_axi_lite_audio_fmt_wvalid;

  decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_aura_audio_decerr s_axi_ctrl_i2s_rx_stub
       (.ACLK(ACLK),
        .ARESETN(ARESETN),
        .bvalid_reg_0(bvalid_reg),
        .s_axi_ctrl_i2s_rx_arready(s_axi_ctrl_i2s_rx_arready),
        .s_axi_ctrl_i2s_rx_arvalid(s_axi_ctrl_i2s_rx_arvalid),
        .s_axi_ctrl_i2s_rx_awready(s_axi_ctrl_i2s_rx_awready),
        .s_axi_ctrl_i2s_rx_awvalid(s_axi_ctrl_i2s_rx_awvalid),
        .s_axi_ctrl_i2s_rx_bready(s_axi_ctrl_i2s_rx_bready),
        .s_axi_ctrl_i2s_rx_rready(s_axi_ctrl_i2s_rx_rready),
        .s_axi_ctrl_i2s_rx_rvalid(s_axi_ctrl_i2s_rx_rvalid),
        .s_axi_ctrl_i2s_rx_wready(s_axi_ctrl_i2s_rx_wready),
        .s_axi_ctrl_i2s_rx_wvalid(s_axi_ctrl_i2s_rx_wvalid));
  decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_aura_audio_decerr_0 s_axi_ctrl_i2s_tx_stub
       (.ACLK(ACLK),
        .ARESETN(ARESETN),
        .bvalid_reg_0(bvalid_reg_0),
        .s_axi_ctrl_i2s_tx_arready(s_axi_ctrl_i2s_tx_arready),
        .s_axi_ctrl_i2s_tx_arvalid(s_axi_ctrl_i2s_tx_arvalid),
        .s_axi_ctrl_i2s_tx_awready(s_axi_ctrl_i2s_tx_awready),
        .s_axi_ctrl_i2s_tx_awvalid(s_axi_ctrl_i2s_tx_awvalid),
        .s_axi_ctrl_i2s_tx_bready(s_axi_ctrl_i2s_tx_bready),
        .s_axi_ctrl_i2s_tx_rready(s_axi_ctrl_i2s_tx_rready),
        .s_axi_ctrl_i2s_tx_rvalid(s_axi_ctrl_i2s_tx_rvalid),
        .s_axi_ctrl_i2s_tx_wready(s_axi_ctrl_i2s_tx_wready),
        .s_axi_ctrl_i2s_tx_wvalid(s_axi_ctrl_i2s_tx_wvalid));
  decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_aura_audio_decerr_1 s_axi_lite_audio_fmt_stub
       (.ACLK(ACLK),
        .ARESETN(ARESETN),
        .bvalid_reg_0(bvalid_reg_1),
        .s_axi_lite_audio_fmt_arready(s_axi_lite_audio_fmt_arready),
        .s_axi_lite_audio_fmt_arvalid(s_axi_lite_audio_fmt_arvalid),
        .s_axi_lite_audio_fmt_awready(s_axi_lite_audio_fmt_awready),
        .s_axi_lite_audio_fmt_awvalid(s_axi_lite_audio_fmt_awvalid),
        .s_axi_lite_audio_fmt_bready(s_axi_lite_audio_fmt_bready),
        .s_axi_lite_audio_fmt_rready(s_axi_lite_audio_fmt_rready),
        .s_axi_lite_audio_fmt_rvalid(s_axi_lite_audio_fmt_rvalid),
        .s_axi_lite_audio_fmt_wready(s_axi_lite_audio_fmt_wready),
        .s_axi_lite_audio_fmt_wvalid(s_axi_lite_audio_fmt_wvalid));
endmodule

(* CHECK_LICENSE_TYPE = "kv260_ispMipiRx_vcu_DP_audio_ss_0_0,aura_disabled_audio,{}" *) (* DowngradeIPIdentifiedWarnings = "yes" *) (* IP_DEFINITION_SOURCE = "package_project" *) 
(* X_CORE_INFO = "aura_disabled_audio,Vivado 2022.2" *) 
(* NotValidForBitStream *)
module decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix
   (ACLK,
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
    sdata_tx);
  (* X_INTERFACE_INFO = "xilinx.com:signal:clock:1.0 ACLK CLK" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ACLK, ASSOCIATED_BUSIF s_axi_ctrl_i2s_rx:s_axi_ctrl_i2s_tx:s_axi_lite_audio_fmt, ASSOCIATED_RESET ARESETN, FREQ_HZ 99999000, FREQ_TOLERANCE_HZ 0, PHASE 0.0, CLK_DOMAIN kv260_ispMipiRx_vcu_DP_clk_wiz_0_0_clk_200M, INSERT_VIP 0" *) input ACLK;
  (* X_INTERFACE_INFO = "xilinx.com:signal:reset:1.0 ARESETN RST" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ARESETN, POLARITY ACTIVE_LOW, INSERT_VIP 0" *) input ARESETN;
  output clk_out_audio;
  output irq_i2s_rx;
  output irq_i2s_tx;
  output irq_mm2s_audio;
  output irq_s2mm_audio;
  output lrclk_rx;
  output lrclk_tx;
  (* X_INTERFACE_INFO = "xilinx.com:signal:clock:1.0 m_axi_aclk CLK" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME m_axi_aclk, ASSOCIATED_RESET m_axi_aresetn, ASSOCIATED_BUSIF m_axi_mm2s_audio:m_axi_s2mm_audio, FREQ_HZ 299997000, FREQ_TOLERANCE_HZ 0, PHASE 0.0, CLK_DOMAIN kv260_ispMipiRx_vcu_DP_clk_wiz_0_0_clk_200M, INSERT_VIP 0" *) input m_axi_aclk;
  (* X_INTERFACE_INFO = "xilinx.com:signal:reset:1.0 m_axi_aresetn RST" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME m_axi_aresetn, POLARITY ACTIVE_LOW, INSERT_VIP 0" *) input m_axi_aresetn;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio ARADDR" *) output [63:0]m_axi_mm2s_audio_araddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio ARBURST" *) output [1:0]m_axi_mm2s_audio_arburst;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio ARCACHE" *) output [3:0]m_axi_mm2s_audio_arcache;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio ARLEN" *) output [7:0]m_axi_mm2s_audio_arlen;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio ARLOCK" *) output [0:0]m_axi_mm2s_audio_arlock;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio ARPROT" *) output [2:0]m_axi_mm2s_audio_arprot;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio ARQOS" *) output [3:0]m_axi_mm2s_audio_arqos;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio ARREADY" *) input m_axi_mm2s_audio_arready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio ARREGION" *) output [3:0]m_axi_mm2s_audio_arregion;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio ARSIZE" *) output [2:0]m_axi_mm2s_audio_arsize;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio ARUSER" *) output [3:0]m_axi_mm2s_audio_aruser;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio ARVALID" *) output m_axi_mm2s_audio_arvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio RDATA" *) input [31:0]m_axi_mm2s_audio_rdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio RLAST" *) input m_axi_mm2s_audio_rlast;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio RREADY" *) output m_axi_mm2s_audio_rready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio RRESP" *) input [1:0]m_axi_mm2s_audio_rresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio RVALID" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME m_axi_mm2s_audio, PROTOCOL AXI4, READ_WRITE_MODE READ_ONLY, DATA_WIDTH 32, FREQ_HZ 299997000, ID_WIDTH 0, ADDR_WIDTH 64, AWUSER_WIDTH 0, ARUSER_WIDTH 4, WUSER_WIDTH 0, RUSER_WIDTH 0, BUSER_WIDTH 0, HAS_BURST 1, HAS_LOCK 1, HAS_PROT 1, HAS_CACHE 1, HAS_QOS 1, HAS_REGION 1, HAS_WSTRB 0, HAS_BRESP 0, HAS_RRESP 1, SUPPORTS_NARROW_BURST 1, NUM_READ_OUTSTANDING 2, NUM_WRITE_OUTSTANDING 2, MAX_BURST_LENGTH 256, PHASE 0.0, CLK_DOMAIN kv260_ispMipiRx_vcu_DP_clk_wiz_0_0_clk_200M, NUM_READ_THREADS 1, NUM_WRITE_THREADS 1, RUSER_BITS_PER_BYTE 0, WUSER_BITS_PER_BYTE 0, INSERT_VIP 0" *) input m_axi_mm2s_audio_rvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio AWADDR" *) output [63:0]m_axi_s2mm_audio_awaddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio AWBURST" *) output [1:0]m_axi_s2mm_audio_awburst;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio AWCACHE" *) output [3:0]m_axi_s2mm_audio_awcache;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio AWLEN" *) output [7:0]m_axi_s2mm_audio_awlen;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio AWLOCK" *) output [0:0]m_axi_s2mm_audio_awlock;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio AWPROT" *) output [2:0]m_axi_s2mm_audio_awprot;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio AWQOS" *) output [3:0]m_axi_s2mm_audio_awqos;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio AWREADY" *) input m_axi_s2mm_audio_awready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio AWREGION" *) output [3:0]m_axi_s2mm_audio_awregion;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio AWSIZE" *) output [2:0]m_axi_s2mm_audio_awsize;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio AWUSER" *) output [3:0]m_axi_s2mm_audio_awuser;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio AWVALID" *) output m_axi_s2mm_audio_awvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio BREADY" *) output m_axi_s2mm_audio_bready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio BRESP" *) input [1:0]m_axi_s2mm_audio_bresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio BVALID" *) input m_axi_s2mm_audio_bvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio WDATA" *) output [31:0]m_axi_s2mm_audio_wdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio WLAST" *) output m_axi_s2mm_audio_wlast;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio WREADY" *) input m_axi_s2mm_audio_wready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio WSTRB" *) output [3:0]m_axi_s2mm_audio_wstrb;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio WVALID" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME m_axi_s2mm_audio, PROTOCOL AXI4, READ_WRITE_MODE WRITE_ONLY, DATA_WIDTH 32, FREQ_HZ 299997000, ID_WIDTH 0, ADDR_WIDTH 64, AWUSER_WIDTH 4, ARUSER_WIDTH 0, WUSER_WIDTH 0, RUSER_WIDTH 0, BUSER_WIDTH 0, HAS_BURST 1, HAS_LOCK 1, HAS_PROT 1, HAS_CACHE 1, HAS_QOS 1, HAS_REGION 1, HAS_WSTRB 1, HAS_BRESP 1, HAS_RRESP 0, SUPPORTS_NARROW_BURST 1, NUM_READ_OUTSTANDING 2, NUM_WRITE_OUTSTANDING 2, MAX_BURST_LENGTH 256, PHASE 0.0, CLK_DOMAIN kv260_ispMipiRx_vcu_DP_clk_wiz_0_0_clk_200M, NUM_READ_THREADS 1, NUM_WRITE_THREADS 1, RUSER_BITS_PER_BYTE 0, WUSER_BITS_PER_BYTE 0, INSERT_VIP 0" *) output m_axi_s2mm_audio_wvalid;
  output mclk_out_rx;
  output mclk_out_tx;
  (* X_INTERFACE_INFO = "xilinx.com:signal:reset:1.0 peripheral_aresetn RST" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME peripheral_aresetn, POLARITY ACTIVE_LOW, INSERT_VIP 0" *) output [0:0]peripheral_aresetn;
  input pl_clk1;
  input pl_rstn1;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx ARADDR" *) (* X_INTERFACE_PARAMETER = "PROTOCOL AXI4LITE, READ_WRITE_MODE READ_WRITE" *) input [39:0]s_axi_ctrl_i2s_rx_araddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx ARREADY" *) output [0:0]s_axi_ctrl_i2s_rx_arready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx ARVALID" *) input [0:0]s_axi_ctrl_i2s_rx_arvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx AWADDR" *) input [39:0]s_axi_ctrl_i2s_rx_awaddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx AWREADY" *) output [0:0]s_axi_ctrl_i2s_rx_awready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx AWVALID" *) input [0:0]s_axi_ctrl_i2s_rx_awvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx BREADY" *) input [0:0]s_axi_ctrl_i2s_rx_bready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx BRESP" *) output [1:0]s_axi_ctrl_i2s_rx_bresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx BVALID" *) output [0:0]s_axi_ctrl_i2s_rx_bvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx RDATA" *) output [31:0]s_axi_ctrl_i2s_rx_rdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx RREADY" *) input [0:0]s_axi_ctrl_i2s_rx_rready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx RRESP" *) output [1:0]s_axi_ctrl_i2s_rx_rresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx RVALID" *) output [0:0]s_axi_ctrl_i2s_rx_rvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx WDATA" *) input [31:0]s_axi_ctrl_i2s_rx_wdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx WREADY" *) output [0:0]s_axi_ctrl_i2s_rx_wready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx WVALID" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME s_axi_ctrl_i2s_rx, PROTOCOL AXI4LITE, READ_WRITE_MODE READ_WRITE, DATA_WIDTH 32, FREQ_HZ 99999000, ID_WIDTH 0, ADDR_WIDTH 40, AWUSER_WIDTH 0, ARUSER_WIDTH 0, WUSER_WIDTH 0, RUSER_WIDTH 0, BUSER_WIDTH 0, HAS_BURST 0, HAS_LOCK 0, HAS_PROT 0, HAS_CACHE 0, HAS_QOS 0, HAS_REGION 0, HAS_WSTRB 0, HAS_BRESP 1, HAS_RRESP 1, SUPPORTS_NARROW_BURST 0, NUM_READ_OUTSTANDING 1, NUM_WRITE_OUTSTANDING 1, MAX_BURST_LENGTH 1, PHASE 0.0, CLK_DOMAIN kv260_ispMipiRx_vcu_DP_clk_wiz_0_0_clk_200M, NUM_READ_THREADS 1, NUM_WRITE_THREADS 1, RUSER_BITS_PER_BYTE 0, WUSER_BITS_PER_BYTE 0, INSERT_VIP 0" *) input [0:0]s_axi_ctrl_i2s_rx_wvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx ARADDR" *) (* X_INTERFACE_PARAMETER = "PROTOCOL AXI4LITE, READ_WRITE_MODE READ_WRITE" *) input [39:0]s_axi_ctrl_i2s_tx_araddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx ARREADY" *) output [0:0]s_axi_ctrl_i2s_tx_arready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx ARVALID" *) input [0:0]s_axi_ctrl_i2s_tx_arvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx AWADDR" *) input [39:0]s_axi_ctrl_i2s_tx_awaddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx AWREADY" *) output [0:0]s_axi_ctrl_i2s_tx_awready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx AWVALID" *) input [0:0]s_axi_ctrl_i2s_tx_awvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx BREADY" *) input [0:0]s_axi_ctrl_i2s_tx_bready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx BRESP" *) output [1:0]s_axi_ctrl_i2s_tx_bresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx BVALID" *) output [0:0]s_axi_ctrl_i2s_tx_bvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx RDATA" *) output [31:0]s_axi_ctrl_i2s_tx_rdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx RREADY" *) input [0:0]s_axi_ctrl_i2s_tx_rready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx RRESP" *) output [1:0]s_axi_ctrl_i2s_tx_rresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx RVALID" *) output [0:0]s_axi_ctrl_i2s_tx_rvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx WDATA" *) input [31:0]s_axi_ctrl_i2s_tx_wdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx WREADY" *) output [0:0]s_axi_ctrl_i2s_tx_wready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx WVALID" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME s_axi_ctrl_i2s_tx, PROTOCOL AXI4LITE, READ_WRITE_MODE READ_WRITE, DATA_WIDTH 32, FREQ_HZ 99999000, ID_WIDTH 0, ADDR_WIDTH 40, AWUSER_WIDTH 0, ARUSER_WIDTH 0, WUSER_WIDTH 0, RUSER_WIDTH 0, BUSER_WIDTH 0, HAS_BURST 0, HAS_LOCK 0, HAS_PROT 0, HAS_CACHE 0, HAS_QOS 0, HAS_REGION 0, HAS_WSTRB 0, HAS_BRESP 1, HAS_RRESP 1, SUPPORTS_NARROW_BURST 0, NUM_READ_OUTSTANDING 1, NUM_WRITE_OUTSTANDING 1, MAX_BURST_LENGTH 1, PHASE 0.0, CLK_DOMAIN kv260_ispMipiRx_vcu_DP_clk_wiz_0_0_clk_200M, NUM_READ_THREADS 1, NUM_WRITE_THREADS 1, RUSER_BITS_PER_BYTE 0, WUSER_BITS_PER_BYTE 0, INSERT_VIP 0" *) input [0:0]s_axi_ctrl_i2s_tx_wvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt ARADDR" *) (* X_INTERFACE_PARAMETER = "PROTOCOL AXI4LITE, READ_WRITE_MODE READ_WRITE" *) input [39:0]s_axi_lite_audio_fmt_araddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt ARREADY" *) output [0:0]s_axi_lite_audio_fmt_arready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt ARVALID" *) input [0:0]s_axi_lite_audio_fmt_arvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt AWADDR" *) input [39:0]s_axi_lite_audio_fmt_awaddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt AWREADY" *) output [0:0]s_axi_lite_audio_fmt_awready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt AWVALID" *) input [0:0]s_axi_lite_audio_fmt_awvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt BREADY" *) input [0:0]s_axi_lite_audio_fmt_bready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt BRESP" *) output [1:0]s_axi_lite_audio_fmt_bresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt BVALID" *) output [0:0]s_axi_lite_audio_fmt_bvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt RDATA" *) output [31:0]s_axi_lite_audio_fmt_rdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt RREADY" *) input [0:0]s_axi_lite_audio_fmt_rready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt RRESP" *) output [1:0]s_axi_lite_audio_fmt_rresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt RVALID" *) output [0:0]s_axi_lite_audio_fmt_rvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt WDATA" *) input [31:0]s_axi_lite_audio_fmt_wdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt WREADY" *) output [0:0]s_axi_lite_audio_fmt_wready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt WVALID" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME s_axi_lite_audio_fmt, PROTOCOL AXI4LITE, READ_WRITE_MODE READ_WRITE, DATA_WIDTH 32, FREQ_HZ 99999000, ID_WIDTH 0, ADDR_WIDTH 40, AWUSER_WIDTH 0, ARUSER_WIDTH 0, WUSER_WIDTH 0, RUSER_WIDTH 0, BUSER_WIDTH 0, HAS_BURST 0, HAS_LOCK 0, HAS_PROT 0, HAS_CACHE 0, HAS_QOS 0, HAS_REGION 0, HAS_WSTRB 0, HAS_BRESP 1, HAS_RRESP 1, SUPPORTS_NARROW_BURST 0, NUM_READ_OUTSTANDING 1, NUM_WRITE_OUTSTANDING 1, MAX_BURST_LENGTH 1, PHASE 0.0, CLK_DOMAIN kv260_ispMipiRx_vcu_DP_clk_wiz_0_0_clk_200M, NUM_READ_THREADS 1, NUM_WRITE_THREADS 1, RUSER_BITS_PER_BYTE 0, WUSER_BITS_PER_BYTE 0, INSERT_VIP 0" *) input [0:0]s_axi_lite_audio_fmt_wvalid;
  output sclk_rx;
  output sclk_tx;
  input sdata_rx;
  output sdata_tx;

  wire \<const0> ;
  wire \<const1> ;
  wire ACLK;
  wire ARESETN;
  wire [0:0]s_axi_ctrl_i2s_rx_arready;
  wire [0:0]s_axi_ctrl_i2s_rx_arvalid;
  wire [0:0]s_axi_ctrl_i2s_rx_awready;
  wire [0:0]s_axi_ctrl_i2s_rx_awvalid;
  wire [0:0]s_axi_ctrl_i2s_rx_bready;
  wire [0:0]s_axi_ctrl_i2s_rx_bvalid;
  wire [0:0]s_axi_ctrl_i2s_rx_rready;
  wire [0:0]s_axi_ctrl_i2s_rx_rvalid;
  wire [0:0]s_axi_ctrl_i2s_rx_wready;
  wire [0:0]s_axi_ctrl_i2s_rx_wvalid;
  wire [0:0]s_axi_ctrl_i2s_tx_arready;
  wire [0:0]s_axi_ctrl_i2s_tx_arvalid;
  wire [0:0]s_axi_ctrl_i2s_tx_awready;
  wire [0:0]s_axi_ctrl_i2s_tx_awvalid;
  wire [0:0]s_axi_ctrl_i2s_tx_bready;
  wire [0:0]s_axi_ctrl_i2s_tx_bvalid;
  wire [0:0]s_axi_ctrl_i2s_tx_rready;
  wire [0:0]s_axi_ctrl_i2s_tx_rvalid;
  wire [0:0]s_axi_ctrl_i2s_tx_wready;
  wire [0:0]s_axi_ctrl_i2s_tx_wvalid;
  wire [0:0]s_axi_lite_audio_fmt_arready;
  wire [0:0]s_axi_lite_audio_fmt_arvalid;
  wire [0:0]s_axi_lite_audio_fmt_awready;
  wire [0:0]s_axi_lite_audio_fmt_awvalid;
  wire [0:0]s_axi_lite_audio_fmt_bready;
  wire [0:0]s_axi_lite_audio_fmt_bvalid;
  wire [0:0]s_axi_lite_audio_fmt_rready;
  wire [0:0]s_axi_lite_audio_fmt_rvalid;
  wire [0:0]s_axi_lite_audio_fmt_wready;
  wire [0:0]s_axi_lite_audio_fmt_wvalid;

  assign clk_out_audio = \<const0> ;
  assign irq_i2s_rx = \<const0> ;
  assign irq_i2s_tx = \<const0> ;
  assign irq_mm2s_audio = \<const0> ;
  assign irq_s2mm_audio = \<const0> ;
  assign lrclk_rx = \<const0> ;
  assign lrclk_tx = \<const0> ;
  assign m_axi_mm2s_audio_araddr[63] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[62] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[61] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[60] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[59] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[58] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[57] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[56] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[55] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[54] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[53] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[52] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[51] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[50] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[49] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[48] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[47] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[46] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[45] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[44] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[43] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[42] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[41] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[40] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[39] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[38] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[37] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[36] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[35] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[34] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[33] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[32] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[31] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[30] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[29] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[28] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[27] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[26] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[25] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[24] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[23] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[22] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[21] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[20] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[19] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[18] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[17] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[16] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[15] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[14] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[13] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[12] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[11] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[10] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[9] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[8] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[7] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[6] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[5] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[4] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[3] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[2] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[1] = \<const0> ;
  assign m_axi_mm2s_audio_araddr[0] = \<const0> ;
  assign m_axi_mm2s_audio_arburst[1] = \<const0> ;
  assign m_axi_mm2s_audio_arburst[0] = \<const0> ;
  assign m_axi_mm2s_audio_arcache[3] = \<const0> ;
  assign m_axi_mm2s_audio_arcache[2] = \<const0> ;
  assign m_axi_mm2s_audio_arcache[1] = \<const0> ;
  assign m_axi_mm2s_audio_arcache[0] = \<const0> ;
  assign m_axi_mm2s_audio_arlen[7] = \<const0> ;
  assign m_axi_mm2s_audio_arlen[6] = \<const0> ;
  assign m_axi_mm2s_audio_arlen[5] = \<const0> ;
  assign m_axi_mm2s_audio_arlen[4] = \<const0> ;
  assign m_axi_mm2s_audio_arlen[3] = \<const0> ;
  assign m_axi_mm2s_audio_arlen[2] = \<const0> ;
  assign m_axi_mm2s_audio_arlen[1] = \<const0> ;
  assign m_axi_mm2s_audio_arlen[0] = \<const0> ;
  assign m_axi_mm2s_audio_arlock[0] = \<const0> ;
  assign m_axi_mm2s_audio_arprot[2] = \<const0> ;
  assign m_axi_mm2s_audio_arprot[1] = \<const0> ;
  assign m_axi_mm2s_audio_arprot[0] = \<const0> ;
  assign m_axi_mm2s_audio_arqos[3] = \<const0> ;
  assign m_axi_mm2s_audio_arqos[2] = \<const0> ;
  assign m_axi_mm2s_audio_arqos[1] = \<const0> ;
  assign m_axi_mm2s_audio_arqos[0] = \<const0> ;
  assign m_axi_mm2s_audio_arregion[3] = \<const0> ;
  assign m_axi_mm2s_audio_arregion[2] = \<const0> ;
  assign m_axi_mm2s_audio_arregion[1] = \<const0> ;
  assign m_axi_mm2s_audio_arregion[0] = \<const0> ;
  assign m_axi_mm2s_audio_arsize[2] = \<const0> ;
  assign m_axi_mm2s_audio_arsize[1] = \<const0> ;
  assign m_axi_mm2s_audio_arsize[0] = \<const0> ;
  assign m_axi_mm2s_audio_aruser[3] = \<const0> ;
  assign m_axi_mm2s_audio_aruser[2] = \<const0> ;
  assign m_axi_mm2s_audio_aruser[1] = \<const0> ;
  assign m_axi_mm2s_audio_aruser[0] = \<const0> ;
  assign m_axi_mm2s_audio_arvalid = \<const0> ;
  assign m_axi_mm2s_audio_rready = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[63] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[62] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[61] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[60] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[59] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[58] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[57] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[56] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[55] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[54] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[53] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[52] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[51] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[50] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[49] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[48] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[47] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[46] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[45] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[44] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[43] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[42] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[41] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[40] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[39] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[38] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[37] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[36] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[35] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[34] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[33] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[32] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[31] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[30] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[29] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[28] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[27] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[26] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[25] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[24] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[23] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[22] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[21] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[20] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[19] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[18] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[17] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[16] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[15] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[14] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[13] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[12] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[11] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[10] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[9] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[8] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[7] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[6] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[5] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[4] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[3] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[2] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[1] = \<const0> ;
  assign m_axi_s2mm_audio_awaddr[0] = \<const0> ;
  assign m_axi_s2mm_audio_awburst[1] = \<const0> ;
  assign m_axi_s2mm_audio_awburst[0] = \<const0> ;
  assign m_axi_s2mm_audio_awcache[3] = \<const0> ;
  assign m_axi_s2mm_audio_awcache[2] = \<const0> ;
  assign m_axi_s2mm_audio_awcache[1] = \<const0> ;
  assign m_axi_s2mm_audio_awcache[0] = \<const0> ;
  assign m_axi_s2mm_audio_awlen[7] = \<const0> ;
  assign m_axi_s2mm_audio_awlen[6] = \<const0> ;
  assign m_axi_s2mm_audio_awlen[5] = \<const0> ;
  assign m_axi_s2mm_audio_awlen[4] = \<const0> ;
  assign m_axi_s2mm_audio_awlen[3] = \<const0> ;
  assign m_axi_s2mm_audio_awlen[2] = \<const0> ;
  assign m_axi_s2mm_audio_awlen[1] = \<const0> ;
  assign m_axi_s2mm_audio_awlen[0] = \<const0> ;
  assign m_axi_s2mm_audio_awlock[0] = \<const0> ;
  assign m_axi_s2mm_audio_awprot[2] = \<const0> ;
  assign m_axi_s2mm_audio_awprot[1] = \<const0> ;
  assign m_axi_s2mm_audio_awprot[0] = \<const0> ;
  assign m_axi_s2mm_audio_awqos[3] = \<const0> ;
  assign m_axi_s2mm_audio_awqos[2] = \<const0> ;
  assign m_axi_s2mm_audio_awqos[1] = \<const0> ;
  assign m_axi_s2mm_audio_awqos[0] = \<const0> ;
  assign m_axi_s2mm_audio_awregion[3] = \<const0> ;
  assign m_axi_s2mm_audio_awregion[2] = \<const0> ;
  assign m_axi_s2mm_audio_awregion[1] = \<const0> ;
  assign m_axi_s2mm_audio_awregion[0] = \<const0> ;
  assign m_axi_s2mm_audio_awsize[2] = \<const0> ;
  assign m_axi_s2mm_audio_awsize[1] = \<const0> ;
  assign m_axi_s2mm_audio_awsize[0] = \<const0> ;
  assign m_axi_s2mm_audio_awuser[3] = \<const0> ;
  assign m_axi_s2mm_audio_awuser[2] = \<const0> ;
  assign m_axi_s2mm_audio_awuser[1] = \<const0> ;
  assign m_axi_s2mm_audio_awuser[0] = \<const0> ;
  assign m_axi_s2mm_audio_awvalid = \<const0> ;
  assign m_axi_s2mm_audio_bready = \<const0> ;
  assign m_axi_s2mm_audio_wdata[31] = \<const0> ;
  assign m_axi_s2mm_audio_wdata[30] = \<const0> ;
  assign m_axi_s2mm_audio_wdata[29] = \<const0> ;
  assign m_axi_s2mm_audio_wdata[28] = \<const0> ;
  assign m_axi_s2mm_audio_wdata[27] = \<const0> ;
  assign m_axi_s2mm_audio_wdata[26] = \<const0> ;
  assign m_axi_s2mm_audio_wdata[25] = \<const0> ;
  assign m_axi_s2mm_audio_wdata[24] = \<const0> ;
  assign m_axi_s2mm_audio_wdata[23] = \<const0> ;
  assign m_axi_s2mm_audio_wdata[22] = \<const0> ;
  assign m_axi_s2mm_audio_wdata[21] = \<const0> ;
  assign m_axi_s2mm_audio_wdata[20] = \<const0> ;
  assign m_axi_s2mm_audio_wdata[19] = \<const0> ;
  assign m_axi_s2mm_audio_wdata[18] = \<const0> ;
  assign m_axi_s2mm_audio_wdata[17] = \<const0> ;
  assign m_axi_s2mm_audio_wdata[16] = \<const0> ;
  assign m_axi_s2mm_audio_wdata[15] = \<const0> ;
  assign m_axi_s2mm_audio_wdata[14] = \<const0> ;
  assign m_axi_s2mm_audio_wdata[13] = \<const0> ;
  assign m_axi_s2mm_audio_wdata[12] = \<const0> ;
  assign m_axi_s2mm_audio_wdata[11] = \<const0> ;
  assign m_axi_s2mm_audio_wdata[10] = \<const0> ;
  assign m_axi_s2mm_audio_wdata[9] = \<const0> ;
  assign m_axi_s2mm_audio_wdata[8] = \<const0> ;
  assign m_axi_s2mm_audio_wdata[7] = \<const0> ;
  assign m_axi_s2mm_audio_wdata[6] = \<const0> ;
  assign m_axi_s2mm_audio_wdata[5] = \<const0> ;
  assign m_axi_s2mm_audio_wdata[4] = \<const0> ;
  assign m_axi_s2mm_audio_wdata[3] = \<const0> ;
  assign m_axi_s2mm_audio_wdata[2] = \<const0> ;
  assign m_axi_s2mm_audio_wdata[1] = \<const0> ;
  assign m_axi_s2mm_audio_wdata[0] = \<const0> ;
  assign m_axi_s2mm_audio_wlast = \<const0> ;
  assign m_axi_s2mm_audio_wstrb[3] = \<const0> ;
  assign m_axi_s2mm_audio_wstrb[2] = \<const0> ;
  assign m_axi_s2mm_audio_wstrb[1] = \<const0> ;
  assign m_axi_s2mm_audio_wstrb[0] = \<const0> ;
  assign m_axi_s2mm_audio_wvalid = \<const0> ;
  assign mclk_out_rx = \<const0> ;
  assign mclk_out_tx = \<const0> ;
  assign peripheral_aresetn[0] = \<const0> ;
  assign s_axi_ctrl_i2s_rx_bresp[1] = \<const1> ;
  assign s_axi_ctrl_i2s_rx_bresp[0] = \<const1> ;
  assign s_axi_ctrl_i2s_rx_rdata[31] = \<const0> ;
  assign s_axi_ctrl_i2s_rx_rdata[30] = \<const0> ;
  assign s_axi_ctrl_i2s_rx_rdata[29] = \<const0> ;
  assign s_axi_ctrl_i2s_rx_rdata[28] = \<const0> ;
  assign s_axi_ctrl_i2s_rx_rdata[27] = \<const0> ;
  assign s_axi_ctrl_i2s_rx_rdata[26] = \<const0> ;
  assign s_axi_ctrl_i2s_rx_rdata[25] = \<const0> ;
  assign s_axi_ctrl_i2s_rx_rdata[24] = \<const0> ;
  assign s_axi_ctrl_i2s_rx_rdata[23] = \<const0> ;
  assign s_axi_ctrl_i2s_rx_rdata[22] = \<const0> ;
  assign s_axi_ctrl_i2s_rx_rdata[21] = \<const0> ;
  assign s_axi_ctrl_i2s_rx_rdata[20] = \<const0> ;
  assign s_axi_ctrl_i2s_rx_rdata[19] = \<const0> ;
  assign s_axi_ctrl_i2s_rx_rdata[18] = \<const0> ;
  assign s_axi_ctrl_i2s_rx_rdata[17] = \<const0> ;
  assign s_axi_ctrl_i2s_rx_rdata[16] = \<const0> ;
  assign s_axi_ctrl_i2s_rx_rdata[15] = \<const0> ;
  assign s_axi_ctrl_i2s_rx_rdata[14] = \<const0> ;
  assign s_axi_ctrl_i2s_rx_rdata[13] = \<const0> ;
  assign s_axi_ctrl_i2s_rx_rdata[12] = \<const0> ;
  assign s_axi_ctrl_i2s_rx_rdata[11] = \<const0> ;
  assign s_axi_ctrl_i2s_rx_rdata[10] = \<const0> ;
  assign s_axi_ctrl_i2s_rx_rdata[9] = \<const0> ;
  assign s_axi_ctrl_i2s_rx_rdata[8] = \<const0> ;
  assign s_axi_ctrl_i2s_rx_rdata[7] = \<const0> ;
  assign s_axi_ctrl_i2s_rx_rdata[6] = \<const0> ;
  assign s_axi_ctrl_i2s_rx_rdata[5] = \<const0> ;
  assign s_axi_ctrl_i2s_rx_rdata[4] = \<const0> ;
  assign s_axi_ctrl_i2s_rx_rdata[3] = \<const0> ;
  assign s_axi_ctrl_i2s_rx_rdata[2] = \<const0> ;
  assign s_axi_ctrl_i2s_rx_rdata[1] = \<const0> ;
  assign s_axi_ctrl_i2s_rx_rdata[0] = \<const0> ;
  assign s_axi_ctrl_i2s_rx_rresp[1] = \<const1> ;
  assign s_axi_ctrl_i2s_rx_rresp[0] = \<const1> ;
  assign s_axi_ctrl_i2s_tx_bresp[1] = \<const1> ;
  assign s_axi_ctrl_i2s_tx_bresp[0] = \<const1> ;
  assign s_axi_ctrl_i2s_tx_rdata[31] = \<const0> ;
  assign s_axi_ctrl_i2s_tx_rdata[30] = \<const0> ;
  assign s_axi_ctrl_i2s_tx_rdata[29] = \<const0> ;
  assign s_axi_ctrl_i2s_tx_rdata[28] = \<const0> ;
  assign s_axi_ctrl_i2s_tx_rdata[27] = \<const0> ;
  assign s_axi_ctrl_i2s_tx_rdata[26] = \<const0> ;
  assign s_axi_ctrl_i2s_tx_rdata[25] = \<const0> ;
  assign s_axi_ctrl_i2s_tx_rdata[24] = \<const0> ;
  assign s_axi_ctrl_i2s_tx_rdata[23] = \<const0> ;
  assign s_axi_ctrl_i2s_tx_rdata[22] = \<const0> ;
  assign s_axi_ctrl_i2s_tx_rdata[21] = \<const0> ;
  assign s_axi_ctrl_i2s_tx_rdata[20] = \<const0> ;
  assign s_axi_ctrl_i2s_tx_rdata[19] = \<const0> ;
  assign s_axi_ctrl_i2s_tx_rdata[18] = \<const0> ;
  assign s_axi_ctrl_i2s_tx_rdata[17] = \<const0> ;
  assign s_axi_ctrl_i2s_tx_rdata[16] = \<const0> ;
  assign s_axi_ctrl_i2s_tx_rdata[15] = \<const0> ;
  assign s_axi_ctrl_i2s_tx_rdata[14] = \<const0> ;
  assign s_axi_ctrl_i2s_tx_rdata[13] = \<const0> ;
  assign s_axi_ctrl_i2s_tx_rdata[12] = \<const0> ;
  assign s_axi_ctrl_i2s_tx_rdata[11] = \<const0> ;
  assign s_axi_ctrl_i2s_tx_rdata[10] = \<const0> ;
  assign s_axi_ctrl_i2s_tx_rdata[9] = \<const0> ;
  assign s_axi_ctrl_i2s_tx_rdata[8] = \<const0> ;
  assign s_axi_ctrl_i2s_tx_rdata[7] = \<const0> ;
  assign s_axi_ctrl_i2s_tx_rdata[6] = \<const0> ;
  assign s_axi_ctrl_i2s_tx_rdata[5] = \<const0> ;
  assign s_axi_ctrl_i2s_tx_rdata[4] = \<const0> ;
  assign s_axi_ctrl_i2s_tx_rdata[3] = \<const0> ;
  assign s_axi_ctrl_i2s_tx_rdata[2] = \<const0> ;
  assign s_axi_ctrl_i2s_tx_rdata[1] = \<const0> ;
  assign s_axi_ctrl_i2s_tx_rdata[0] = \<const0> ;
  assign s_axi_ctrl_i2s_tx_rresp[1] = \<const1> ;
  assign s_axi_ctrl_i2s_tx_rresp[0] = \<const1> ;
  assign s_axi_lite_audio_fmt_bresp[1] = \<const1> ;
  assign s_axi_lite_audio_fmt_bresp[0] = \<const1> ;
  assign s_axi_lite_audio_fmt_rdata[31] = \<const0> ;
  assign s_axi_lite_audio_fmt_rdata[30] = \<const0> ;
  assign s_axi_lite_audio_fmt_rdata[29] = \<const0> ;
  assign s_axi_lite_audio_fmt_rdata[28] = \<const0> ;
  assign s_axi_lite_audio_fmt_rdata[27] = \<const0> ;
  assign s_axi_lite_audio_fmt_rdata[26] = \<const0> ;
  assign s_axi_lite_audio_fmt_rdata[25] = \<const0> ;
  assign s_axi_lite_audio_fmt_rdata[24] = \<const0> ;
  assign s_axi_lite_audio_fmt_rdata[23] = \<const0> ;
  assign s_axi_lite_audio_fmt_rdata[22] = \<const0> ;
  assign s_axi_lite_audio_fmt_rdata[21] = \<const0> ;
  assign s_axi_lite_audio_fmt_rdata[20] = \<const0> ;
  assign s_axi_lite_audio_fmt_rdata[19] = \<const0> ;
  assign s_axi_lite_audio_fmt_rdata[18] = \<const0> ;
  assign s_axi_lite_audio_fmt_rdata[17] = \<const0> ;
  assign s_axi_lite_audio_fmt_rdata[16] = \<const0> ;
  assign s_axi_lite_audio_fmt_rdata[15] = \<const0> ;
  assign s_axi_lite_audio_fmt_rdata[14] = \<const0> ;
  assign s_axi_lite_audio_fmt_rdata[13] = \<const0> ;
  assign s_axi_lite_audio_fmt_rdata[12] = \<const0> ;
  assign s_axi_lite_audio_fmt_rdata[11] = \<const0> ;
  assign s_axi_lite_audio_fmt_rdata[10] = \<const0> ;
  assign s_axi_lite_audio_fmt_rdata[9] = \<const0> ;
  assign s_axi_lite_audio_fmt_rdata[8] = \<const0> ;
  assign s_axi_lite_audio_fmt_rdata[7] = \<const0> ;
  assign s_axi_lite_audio_fmt_rdata[6] = \<const0> ;
  assign s_axi_lite_audio_fmt_rdata[5] = \<const0> ;
  assign s_axi_lite_audio_fmt_rdata[4] = \<const0> ;
  assign s_axi_lite_audio_fmt_rdata[3] = \<const0> ;
  assign s_axi_lite_audio_fmt_rdata[2] = \<const0> ;
  assign s_axi_lite_audio_fmt_rdata[1] = \<const0> ;
  assign s_axi_lite_audio_fmt_rdata[0] = \<const0> ;
  assign s_axi_lite_audio_fmt_rresp[1] = \<const1> ;
  assign s_axi_lite_audio_fmt_rresp[0] = \<const1> ;
  assign sclk_rx = \<const0> ;
  assign sclk_tx = \<const0> ;
  assign sdata_tx = \<const0> ;
  GND GND
       (.G(\<const0> ));
  VCC VCC
       (.P(\<const1> ));
  decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_aura_disabled_audio inst
       (.ACLK(ACLK),
        .ARESETN(ARESETN),
        .bvalid_reg(s_axi_ctrl_i2s_rx_bvalid),
        .bvalid_reg_0(s_axi_ctrl_i2s_tx_bvalid),
        .bvalid_reg_1(s_axi_lite_audio_fmt_bvalid),
        .s_axi_ctrl_i2s_rx_arready(s_axi_ctrl_i2s_rx_arready),
        .s_axi_ctrl_i2s_rx_arvalid(s_axi_ctrl_i2s_rx_arvalid),
        .s_axi_ctrl_i2s_rx_awready(s_axi_ctrl_i2s_rx_awready),
        .s_axi_ctrl_i2s_rx_awvalid(s_axi_ctrl_i2s_rx_awvalid),
        .s_axi_ctrl_i2s_rx_bready(s_axi_ctrl_i2s_rx_bready),
        .s_axi_ctrl_i2s_rx_rready(s_axi_ctrl_i2s_rx_rready),
        .s_axi_ctrl_i2s_rx_rvalid(s_axi_ctrl_i2s_rx_rvalid),
        .s_axi_ctrl_i2s_rx_wready(s_axi_ctrl_i2s_rx_wready),
        .s_axi_ctrl_i2s_rx_wvalid(s_axi_ctrl_i2s_rx_wvalid),
        .s_axi_ctrl_i2s_tx_arready(s_axi_ctrl_i2s_tx_arready),
        .s_axi_ctrl_i2s_tx_arvalid(s_axi_ctrl_i2s_tx_arvalid),
        .s_axi_ctrl_i2s_tx_awready(s_axi_ctrl_i2s_tx_awready),
        .s_axi_ctrl_i2s_tx_awvalid(s_axi_ctrl_i2s_tx_awvalid),
        .s_axi_ctrl_i2s_tx_bready(s_axi_ctrl_i2s_tx_bready),
        .s_axi_ctrl_i2s_tx_rready(s_axi_ctrl_i2s_tx_rready),
        .s_axi_ctrl_i2s_tx_rvalid(s_axi_ctrl_i2s_tx_rvalid),
        .s_axi_ctrl_i2s_tx_wready(s_axi_ctrl_i2s_tx_wready),
        .s_axi_ctrl_i2s_tx_wvalid(s_axi_ctrl_i2s_tx_wvalid),
        .s_axi_lite_audio_fmt_arready(s_axi_lite_audio_fmt_arready),
        .s_axi_lite_audio_fmt_arvalid(s_axi_lite_audio_fmt_arvalid),
        .s_axi_lite_audio_fmt_awready(s_axi_lite_audio_fmt_awready),
        .s_axi_lite_audio_fmt_awvalid(s_axi_lite_audio_fmt_awvalid),
        .s_axi_lite_audio_fmt_bready(s_axi_lite_audio_fmt_bready),
        .s_axi_lite_audio_fmt_rready(s_axi_lite_audio_fmt_rready),
        .s_axi_lite_audio_fmt_rvalid(s_axi_lite_audio_fmt_rvalid),
        .s_axi_lite_audio_fmt_wready(s_axi_lite_audio_fmt_wready),
        .s_axi_lite_audio_fmt_wvalid(s_axi_lite_audio_fmt_wvalid));
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
