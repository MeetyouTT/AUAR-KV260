-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- --------------------------------------------------------------------------------
-- Tool Version: Vivado v.2022.2 (lin64) Build 3671981 Fri Oct 14 04:59:54 MDT 2022
-- Date        : Fri Oct  2 04:33:13 2026
-- Host        : ghmd-MRA-XXX running 64-bit Ubuntu 20.04.4 LTS
-- Command     : write_vhdl -force -mode funcsim
--               /home/ghmd/kv260-m3-axilite-20261002/src/kv260/platforms/vivado/kv260_ispMipiRx_vcu_DP/project/kv260_ispMipiRx_vcu_DP.gen/sources_1/bd/kv260_ispMipiRx_vcu_DP/ip/kv260_ispMipiRx_vcu_DP_aura_m3_regs_0_0/kv260_ispMipiRx_vcu_DP_aura_m3_regs_0_0_sim_netlist.vhdl
-- Design      : kv260_ispMipiRx_vcu_DP_aura_m3_regs_0_0
-- Purpose     : This VHDL netlist is a functional simulation representation of the design and should not be modified or
--               synthesized. This netlist cannot be used for SDF annotated simulation.
-- Device      : xck26-sfvc784-2LV-c
-- --------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
library UNISIM;
use UNISIM.VCOMPONENTS.ALL;
entity kv260_ispMipiRx_vcu_DP_aura_m3_regs_0_0_aura_m3_regs is
  port (
    s_axi_rdata : out STD_LOGIC_VECTOR ( 31 downto 0 );
    s_axi_rresp : out STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_wready : out STD_LOGIC;
    s_axi_bvalid_reg_0 : out STD_LOGIC;
    s_axi_awready : out STD_LOGIC;
    s_axi_bresp : out STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_arready : out STD_LOGIC;
    s_axi_rvalid_reg_0 : out STD_LOGIC;
    s_axi_awaddr : in STD_LOGIC_VECTOR ( 11 downto 0 );
    s_axi_aclk : in STD_LOGIC;
    s_axi_wstrb : in STD_LOGIC_VECTOR ( 3 downto 0 );
    s_axi_wdata : in STD_LOGIC_VECTOR ( 31 downto 0 );
    s_axi_aresetn : in STD_LOGIC;
    s_axi_awvalid : in STD_LOGIC;
    s_axi_wvalid : in STD_LOGIC;
    s_axi_arvalid : in STD_LOGIC;
    s_axi_araddr : in STD_LOGIC_VECTOR ( 11 downto 0 );
    s_axi_bready : in STD_LOGIC;
    s_axi_rready : in STD_LOGIC
  );
  attribute ORIG_REF_NAME : string;
  attribute ORIG_REF_NAME of kv260_ispMipiRx_vcu_DP_aura_m3_regs_0_0_aura_m3_regs : entity is "aura_m3_regs";
end kv260_ispMipiRx_vcu_DP_aura_m3_regs_0_0_aura_m3_regs;

architecture STRUCTURE of kv260_ispMipiRx_vcu_DP_aura_m3_regs_0_0_aura_m3_regs is
  signal aw_address : STD_LOGIC_VECTOR ( 11 downto 0 );
  signal aw_pending : STD_LOGIC;
  signal aw_pending0 : STD_LOGIC;
  signal aw_pending_i_1_n_0 : STD_LOGIC;
  signal data00 : STD_LOGIC;
  signal p_0_in : STD_LOGIC;
  signal p_1_in : STD_LOGIC_VECTOR ( 31 downto 7 );
  signal \^s_axi_bresp\ : STD_LOGIC_VECTOR ( 0 to 0 );
  signal \s_axi_bresp[1]_i_1_n_0\ : STD_LOGIC;
  signal \s_axi_bresp[1]_i_2_n_0\ : STD_LOGIC;
  signal \s_axi_bresp[1]_i_3_n_0\ : STD_LOGIC;
  signal \s_axi_bresp[1]_i_4_n_0\ : STD_LOGIC;
  signal \s_axi_bresp[1]_i_5_n_0\ : STD_LOGIC;
  signal s_axi_bvalid_i_2_n_0 : STD_LOGIC;
  signal \^s_axi_bvalid_reg_0\ : STD_LOGIC;
  signal \s_axi_rdata[0]_i_1_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[10]_i_1_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[11]_i_1_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[12]_i_1_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[13]_i_1_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[14]_i_1_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[15]_i_1_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[16]_i_1_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[17]_i_1_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[18]_i_1_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[19]_i_1_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[1]_i_1_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[20]_i_1_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[21]_i_1_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[22]_i_1_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[23]_i_1_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[24]_i_1_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[25]_i_1_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[26]_i_1_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[27]_i_1_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[28]_i_1_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[29]_i_1_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[2]_i_1_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[30]_i_1_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[31]_i_2_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[31]_i_3_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[31]_i_4_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[3]_i_1_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[4]_i_1_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[5]_i_1_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[6]_i_1_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[7]_i_1_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[8]_i_1_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[9]_i_1_n_0\ : STD_LOGIC;
  signal \s_axi_rresp[1]_i_1_n_0\ : STD_LOGIC;
  signal s_axi_rvalid01_out : STD_LOGIC;
  signal s_axi_rvalid_i_1_n_0 : STD_LOGIC;
  signal \^s_axi_rvalid_reg_0\ : STD_LOGIC;
  signal scratch : STD_LOGIC_VECTOR ( 31 downto 0 );
  signal w_data : STD_LOGIC_VECTOR ( 31 downto 0 );
  signal w_pending : STD_LOGIC;
  signal w_pending0 : STD_LOGIC;
  signal w_pending_i_2_n_0 : STD_LOGIC;
  signal w_pending_reg_n_0 : STD_LOGIC;
  signal \w_strobes_reg_n_0_[0]\ : STD_LOGIC;
  signal \w_strobes_reg_n_0_[2]\ : STD_LOGIC;
  signal \w_strobes_reg_n_0_[3]\ : STD_LOGIC;
  attribute SOFT_HLUTNM : string;
  attribute SOFT_HLUTNM of aw_pending_i_1 : label is "soft_lutpair3";
  attribute SOFT_HLUTNM of s_axi_arready_INST_0 : label is "soft_lutpair2";
  attribute SOFT_HLUTNM of s_axi_awready_INST_0 : label is "soft_lutpair1";
  attribute SOFT_HLUTNM of \s_axi_bresp[1]_i_5\ : label is "soft_lutpair0";
  attribute X_INTERFACE_INFO : string;
  attribute X_INTERFACE_INFO of \s_axi_bresp_reg[1]\ : label is "xilinx.com:interface:aximm:1.0 S_AXI BRESP";
  attribute SOFT_HLUTNM of s_axi_bvalid_i_2 : label is "soft_lutpair0";
  attribute X_INTERFACE_INFO of s_axi_bvalid_reg : label is "xilinx.com:interface:aximm:1.0 S_AXI BVALID";
  attribute X_INTERFACE_INFO of \s_axi_rdata_reg[0]\ : label is "xilinx.com:interface:aximm:1.0 S_AXI RDATA";
  attribute X_INTERFACE_INFO of \s_axi_rdata_reg[10]\ : label is "xilinx.com:interface:aximm:1.0 S_AXI RDATA";
  attribute X_INTERFACE_INFO of \s_axi_rdata_reg[11]\ : label is "xilinx.com:interface:aximm:1.0 S_AXI RDATA";
  attribute X_INTERFACE_INFO of \s_axi_rdata_reg[12]\ : label is "xilinx.com:interface:aximm:1.0 S_AXI RDATA";
  attribute X_INTERFACE_INFO of \s_axi_rdata_reg[13]\ : label is "xilinx.com:interface:aximm:1.0 S_AXI RDATA";
  attribute X_INTERFACE_INFO of \s_axi_rdata_reg[14]\ : label is "xilinx.com:interface:aximm:1.0 S_AXI RDATA";
  attribute X_INTERFACE_INFO of \s_axi_rdata_reg[15]\ : label is "xilinx.com:interface:aximm:1.0 S_AXI RDATA";
  attribute X_INTERFACE_INFO of \s_axi_rdata_reg[16]\ : label is "xilinx.com:interface:aximm:1.0 S_AXI RDATA";
  attribute X_INTERFACE_INFO of \s_axi_rdata_reg[17]\ : label is "xilinx.com:interface:aximm:1.0 S_AXI RDATA";
  attribute X_INTERFACE_INFO of \s_axi_rdata_reg[18]\ : label is "xilinx.com:interface:aximm:1.0 S_AXI RDATA";
  attribute X_INTERFACE_INFO of \s_axi_rdata_reg[19]\ : label is "xilinx.com:interface:aximm:1.0 S_AXI RDATA";
  attribute X_INTERFACE_INFO of \s_axi_rdata_reg[1]\ : label is "xilinx.com:interface:aximm:1.0 S_AXI RDATA";
  attribute X_INTERFACE_INFO of \s_axi_rdata_reg[20]\ : label is "xilinx.com:interface:aximm:1.0 S_AXI RDATA";
  attribute X_INTERFACE_INFO of \s_axi_rdata_reg[21]\ : label is "xilinx.com:interface:aximm:1.0 S_AXI RDATA";
  attribute X_INTERFACE_INFO of \s_axi_rdata_reg[22]\ : label is "xilinx.com:interface:aximm:1.0 S_AXI RDATA";
  attribute X_INTERFACE_INFO of \s_axi_rdata_reg[23]\ : label is "xilinx.com:interface:aximm:1.0 S_AXI RDATA";
  attribute X_INTERFACE_INFO of \s_axi_rdata_reg[24]\ : label is "xilinx.com:interface:aximm:1.0 S_AXI RDATA";
  attribute X_INTERFACE_INFO of \s_axi_rdata_reg[25]\ : label is "xilinx.com:interface:aximm:1.0 S_AXI RDATA";
  attribute X_INTERFACE_INFO of \s_axi_rdata_reg[26]\ : label is "xilinx.com:interface:aximm:1.0 S_AXI RDATA";
  attribute X_INTERFACE_INFO of \s_axi_rdata_reg[27]\ : label is "xilinx.com:interface:aximm:1.0 S_AXI RDATA";
  attribute X_INTERFACE_INFO of \s_axi_rdata_reg[28]\ : label is "xilinx.com:interface:aximm:1.0 S_AXI RDATA";
  attribute X_INTERFACE_INFO of \s_axi_rdata_reg[29]\ : label is "xilinx.com:interface:aximm:1.0 S_AXI RDATA";
  attribute X_INTERFACE_INFO of \s_axi_rdata_reg[2]\ : label is "xilinx.com:interface:aximm:1.0 S_AXI RDATA";
  attribute X_INTERFACE_INFO of \s_axi_rdata_reg[30]\ : label is "xilinx.com:interface:aximm:1.0 S_AXI RDATA";
  attribute X_INTERFACE_INFO of \s_axi_rdata_reg[31]\ : label is "xilinx.com:interface:aximm:1.0 S_AXI RDATA";
  attribute X_INTERFACE_INFO of \s_axi_rdata_reg[3]\ : label is "xilinx.com:interface:aximm:1.0 S_AXI RDATA";
  attribute X_INTERFACE_INFO of \s_axi_rdata_reg[4]\ : label is "xilinx.com:interface:aximm:1.0 S_AXI RDATA";
  attribute X_INTERFACE_INFO of \s_axi_rdata_reg[5]\ : label is "xilinx.com:interface:aximm:1.0 S_AXI RDATA";
  attribute X_INTERFACE_INFO of \s_axi_rdata_reg[6]\ : label is "xilinx.com:interface:aximm:1.0 S_AXI RDATA";
  attribute X_INTERFACE_INFO of \s_axi_rdata_reg[7]\ : label is "xilinx.com:interface:aximm:1.0 S_AXI RDATA";
  attribute X_INTERFACE_INFO of \s_axi_rdata_reg[8]\ : label is "xilinx.com:interface:aximm:1.0 S_AXI RDATA";
  attribute X_INTERFACE_INFO of \s_axi_rdata_reg[9]\ : label is "xilinx.com:interface:aximm:1.0 S_AXI RDATA";
  attribute X_INTERFACE_INFO of \s_axi_rresp_reg[1]\ : label is "xilinx.com:interface:aximm:1.0 S_AXI RRESP";
  attribute SOFT_HLUTNM of s_axi_rvalid_i_1 : label is "soft_lutpair2";
  attribute X_INTERFACE_INFO of s_axi_rvalid_reg : label is "xilinx.com:interface:aximm:1.0 S_AXI RVALID";
  attribute SOFT_HLUTNM of s_axi_wready_INST_0 : label is "soft_lutpair1";
  attribute SOFT_HLUTNM of w_pending_i_2 : label is "soft_lutpair3";
begin
  s_axi_bresp(0) <= \^s_axi_bresp\(0);
  s_axi_bvalid_reg_0 <= \^s_axi_bvalid_reg_0\;
  s_axi_rvalid_reg_0 <= \^s_axi_rvalid_reg_0\;
\aw_address[11]_i_1\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"04"
    )
        port map (
      I0 => aw_pending,
      I1 => s_axi_awvalid,
      I2 => \^s_axi_bvalid_reg_0\,
      O => aw_pending0
    );
\aw_address_reg[0]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => aw_pending0,
      D => s_axi_awaddr(0),
      Q => aw_address(0),
      R => p_0_in
    );
\aw_address_reg[10]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => aw_pending0,
      D => s_axi_awaddr(10),
      Q => aw_address(10),
      R => p_0_in
    );
\aw_address_reg[11]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => aw_pending0,
      D => s_axi_awaddr(11),
      Q => aw_address(11),
      R => p_0_in
    );
\aw_address_reg[1]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => aw_pending0,
      D => s_axi_awaddr(1),
      Q => aw_address(1),
      R => p_0_in
    );
\aw_address_reg[2]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => aw_pending0,
      D => s_axi_awaddr(2),
      Q => aw_address(2),
      R => p_0_in
    );
\aw_address_reg[3]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => aw_pending0,
      D => s_axi_awaddr(3),
      Q => aw_address(3),
      R => p_0_in
    );
\aw_address_reg[4]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => aw_pending0,
      D => s_axi_awaddr(4),
      Q => aw_address(4),
      R => p_0_in
    );
\aw_address_reg[5]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => aw_pending0,
      D => s_axi_awaddr(5),
      Q => aw_address(5),
      R => p_0_in
    );
\aw_address_reg[6]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => aw_pending0,
      D => s_axi_awaddr(6),
      Q => aw_address(6),
      R => p_0_in
    );
\aw_address_reg[7]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => aw_pending0,
      D => s_axi_awaddr(7),
      Q => aw_address(7),
      R => p_0_in
    );
\aw_address_reg[8]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => aw_pending0,
      D => s_axi_awaddr(8),
      Q => aw_address(8),
      R => p_0_in
    );
\aw_address_reg[9]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => aw_pending0,
      D => s_axi_awaddr(9),
      Q => aw_address(9),
      R => p_0_in
    );
aw_pending_i_1: unisim.vcomponents.LUT3
    generic map(
      INIT => X"F4"
    )
        port map (
      I0 => \^s_axi_bvalid_reg_0\,
      I1 => s_axi_awvalid,
      I2 => aw_pending,
      O => aw_pending_i_1_n_0
    );
aw_pending_reg: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => '1',
      D => aw_pending_i_1_n_0,
      Q => aw_pending,
      R => w_pending
    );
s_axi_arready_INST_0: unisim.vcomponents.LUT2
    generic map(
      INIT => X"2"
    )
        port map (
      I0 => s_axi_aresetn,
      I1 => \^s_axi_rvalid_reg_0\,
      O => s_axi_arready
    );
s_axi_awready_INST_0: unisim.vcomponents.LUT3
    generic map(
      INIT => X"04"
    )
        port map (
      I0 => \^s_axi_bvalid_reg_0\,
      I1 => s_axi_aresetn,
      I2 => aw_pending,
      O => s_axi_awready
    );
\s_axi_bresp[1]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FF000000FE00FE00"
    )
        port map (
      I0 => \s_axi_bresp[1]_i_2_n_0\,
      I1 => \s_axi_bresp[1]_i_3_n_0\,
      I2 => \s_axi_bresp[1]_i_4_n_0\,
      I3 => s_axi_aresetn,
      I4 => \^s_axi_bresp\(0),
      I5 => \s_axi_bresp[1]_i_5_n_0\,
      O => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_bresp[1]_i_2\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"FFFE"
    )
        port map (
      I0 => aw_address(9),
      I1 => aw_address(8),
      I2 => aw_address(11),
      I3 => aw_address(10),
      O => \s_axi_bresp[1]_i_2_n_0\
    );
\s_axi_bresp[1]_i_3\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"EFFF"
    )
        port map (
      I0 => aw_address(1),
      I1 => aw_address(0),
      I2 => aw_address(3),
      I3 => aw_address(2),
      O => \s_axi_bresp[1]_i_3_n_0\
    );
\s_axi_bresp[1]_i_4\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"FFFE"
    )
        port map (
      I0 => aw_address(5),
      I1 => aw_address(4),
      I2 => aw_address(7),
      I3 => aw_address(6),
      O => \s_axi_bresp[1]_i_4_n_0\
    );
\s_axi_bresp[1]_i_5\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"DF"
    )
        port map (
      I0 => w_pending_reg_n_0,
      I1 => \^s_axi_bvalid_reg_0\,
      I2 => aw_pending,
      O => \s_axi_bresp[1]_i_5_n_0\
    );
\s_axi_bresp_reg[1]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => '1',
      D => \s_axi_bresp[1]_i_1_n_0\,
      Q => \^s_axi_bresp\(0),
      R => '0'
    );
s_axi_bvalid_i_1: unisim.vcomponents.LUT1
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => s_axi_aresetn,
      O => p_0_in
    );
s_axi_bvalid_i_2: unisim.vcomponents.LUT4
    generic map(
      INIT => X"5C50"
    )
        port map (
      I0 => s_axi_bready,
      I1 => aw_pending,
      I2 => \^s_axi_bvalid_reg_0\,
      I3 => w_pending_reg_n_0,
      O => s_axi_bvalid_i_2_n_0
    );
s_axi_bvalid_reg: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => '1',
      D => s_axi_bvalid_i_2_n_0,
      Q => \^s_axi_bvalid_reg_0\,
      R => p_0_in
    );
\s_axi_rdata[0]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"00080003"
    )
        port map (
      I0 => scratch(0),
      I1 => s_axi_araddr(3),
      I2 => \s_axi_rdata[31]_i_3_n_0\,
      I3 => \s_axi_rdata[31]_i_4_n_0\,
      I4 => s_axi_araddr(2),
      O => \s_axi_rdata[0]_i_1_n_0\
    );
\s_axi_rdata[10]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"000000B0"
    )
        port map (
      I0 => scratch(10),
      I1 => s_axi_araddr(2),
      I2 => s_axi_araddr(3),
      I3 => \s_axi_rdata[31]_i_3_n_0\,
      I4 => \s_axi_rdata[31]_i_4_n_0\,
      O => \s_axi_rdata[10]_i_1_n_0\
    );
\s_axi_rdata[11]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"00080000"
    )
        port map (
      I0 => s_axi_araddr(2),
      I1 => s_axi_araddr(3),
      I2 => \s_axi_rdata[31]_i_3_n_0\,
      I3 => \s_axi_rdata[31]_i_4_n_0\,
      I4 => scratch(11),
      O => \s_axi_rdata[11]_i_1_n_0\
    );
\s_axi_rdata[12]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"00080003"
    )
        port map (
      I0 => scratch(12),
      I1 => s_axi_araddr(3),
      I2 => \s_axi_rdata[31]_i_3_n_0\,
      I3 => \s_axi_rdata[31]_i_4_n_0\,
      I4 => s_axi_araddr(2),
      O => \s_axi_rdata[12]_i_1_n_0\
    );
\s_axi_rdata[13]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"00080000"
    )
        port map (
      I0 => s_axi_araddr(2),
      I1 => s_axi_araddr(3),
      I2 => \s_axi_rdata[31]_i_3_n_0\,
      I3 => \s_axi_rdata[31]_i_4_n_0\,
      I4 => scratch(13),
      O => \s_axi_rdata[13]_i_1_n_0\
    );
\s_axi_rdata[14]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"00080003"
    )
        port map (
      I0 => scratch(14),
      I1 => s_axi_araddr(3),
      I2 => \s_axi_rdata[31]_i_3_n_0\,
      I3 => \s_axi_rdata[31]_i_4_n_0\,
      I4 => s_axi_araddr(2),
      O => \s_axi_rdata[14]_i_1_n_0\
    );
\s_axi_rdata[15]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"000000B0"
    )
        port map (
      I0 => scratch(15),
      I1 => s_axi_araddr(2),
      I2 => s_axi_araddr(3),
      I3 => \s_axi_rdata[31]_i_3_n_0\,
      I4 => \s_axi_rdata[31]_i_4_n_0\,
      O => \s_axi_rdata[15]_i_1_n_0\
    );
\s_axi_rdata[16]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"000F0007"
    )
        port map (
      I0 => s_axi_araddr(2),
      I1 => s_axi_araddr(3),
      I2 => \s_axi_rdata[31]_i_4_n_0\,
      I3 => \s_axi_rdata[31]_i_3_n_0\,
      I4 => scratch(16),
      O => \s_axi_rdata[16]_i_1_n_0\
    );
\s_axi_rdata[17]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"000000B0"
    )
        port map (
      I0 => scratch(17),
      I1 => s_axi_araddr(2),
      I2 => s_axi_araddr(3),
      I3 => \s_axi_rdata[31]_i_3_n_0\,
      I4 => \s_axi_rdata[31]_i_4_n_0\,
      O => \s_axi_rdata[17]_i_1_n_0\
    );
\s_axi_rdata[18]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"0000008F"
    )
        port map (
      I0 => scratch(18),
      I1 => s_axi_araddr(3),
      I2 => s_axi_araddr(2),
      I3 => \s_axi_rdata[31]_i_4_n_0\,
      I4 => \s_axi_rdata[31]_i_3_n_0\,
      O => \s_axi_rdata[18]_i_1_n_0\
    );
\s_axi_rdata[19]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"00080000"
    )
        port map (
      I0 => s_axi_araddr(2),
      I1 => s_axi_araddr(3),
      I2 => \s_axi_rdata[31]_i_3_n_0\,
      I3 => \s_axi_rdata[31]_i_4_n_0\,
      I4 => scratch(19),
      O => \s_axi_rdata[19]_i_1_n_0\
    );
\s_axi_rdata[1]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"00080000"
    )
        port map (
      I0 => s_axi_araddr(2),
      I1 => s_axi_araddr(3),
      I2 => \s_axi_rdata[31]_i_3_n_0\,
      I3 => \s_axi_rdata[31]_i_4_n_0\,
      I4 => scratch(1),
      O => \s_axi_rdata[1]_i_1_n_0\
    );
\s_axi_rdata[20]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"00080003"
    )
        port map (
      I0 => scratch(20),
      I1 => s_axi_araddr(3),
      I2 => \s_axi_rdata[31]_i_3_n_0\,
      I3 => \s_axi_rdata[31]_i_4_n_0\,
      I4 => s_axi_araddr(2),
      O => \s_axi_rdata[20]_i_1_n_0\
    );
\s_axi_rdata[21]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"00080000"
    )
        port map (
      I0 => s_axi_araddr(2),
      I1 => s_axi_araddr(3),
      I2 => \s_axi_rdata[31]_i_3_n_0\,
      I3 => \s_axi_rdata[31]_i_4_n_0\,
      I4 => scratch(21),
      O => \s_axi_rdata[21]_i_1_n_0\
    );
\s_axi_rdata[22]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"00080003"
    )
        port map (
      I0 => scratch(22),
      I1 => s_axi_araddr(3),
      I2 => \s_axi_rdata[31]_i_3_n_0\,
      I3 => \s_axi_rdata[31]_i_4_n_0\,
      I4 => s_axi_araddr(2),
      O => \s_axi_rdata[22]_i_1_n_0\
    );
\s_axi_rdata[23]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"00080000"
    )
        port map (
      I0 => s_axi_araddr(2),
      I1 => s_axi_araddr(3),
      I2 => \s_axi_rdata[31]_i_3_n_0\,
      I3 => \s_axi_rdata[31]_i_4_n_0\,
      I4 => scratch(23),
      O => \s_axi_rdata[23]_i_1_n_0\
    );
\s_axi_rdata[24]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"0000008F"
    )
        port map (
      I0 => scratch(24),
      I1 => s_axi_araddr(3),
      I2 => s_axi_araddr(2),
      I3 => \s_axi_rdata[31]_i_4_n_0\,
      I4 => \s_axi_rdata[31]_i_3_n_0\,
      O => \s_axi_rdata[24]_i_1_n_0\
    );
\s_axi_rdata[25]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"00080000"
    )
        port map (
      I0 => s_axi_araddr(2),
      I1 => s_axi_araddr(3),
      I2 => \s_axi_rdata[31]_i_3_n_0\,
      I3 => \s_axi_rdata[31]_i_4_n_0\,
      I4 => scratch(25),
      O => \s_axi_rdata[25]_i_1_n_0\
    );
\s_axi_rdata[26]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"000000B0"
    )
        port map (
      I0 => scratch(26),
      I1 => s_axi_araddr(2),
      I2 => s_axi_araddr(3),
      I3 => \s_axi_rdata[31]_i_3_n_0\,
      I4 => \s_axi_rdata[31]_i_4_n_0\,
      O => \s_axi_rdata[26]_i_1_n_0\
    );
\s_axi_rdata[27]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"00080000"
    )
        port map (
      I0 => s_axi_araddr(2),
      I1 => s_axi_araddr(3),
      I2 => \s_axi_rdata[31]_i_3_n_0\,
      I3 => \s_axi_rdata[31]_i_4_n_0\,
      I4 => scratch(27),
      O => \s_axi_rdata[27]_i_1_n_0\
    );
\s_axi_rdata[28]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"00080000"
    )
        port map (
      I0 => s_axi_araddr(2),
      I1 => s_axi_araddr(3),
      I2 => \s_axi_rdata[31]_i_3_n_0\,
      I3 => \s_axi_rdata[31]_i_4_n_0\,
      I4 => scratch(28),
      O => \s_axi_rdata[28]_i_1_n_0\
    );
\s_axi_rdata[29]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"000000B0"
    )
        port map (
      I0 => scratch(29),
      I1 => s_axi_araddr(2),
      I2 => s_axi_araddr(3),
      I3 => \s_axi_rdata[31]_i_3_n_0\,
      I4 => \s_axi_rdata[31]_i_4_n_0\,
      O => \s_axi_rdata[29]_i_1_n_0\
    );
\s_axi_rdata[2]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"00080000"
    )
        port map (
      I0 => s_axi_araddr(2),
      I1 => s_axi_araddr(3),
      I2 => \s_axi_rdata[31]_i_3_n_0\,
      I3 => \s_axi_rdata[31]_i_4_n_0\,
      I4 => scratch(2),
      O => \s_axi_rdata[2]_i_1_n_0\
    );
\s_axi_rdata[30]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"00080003"
    )
        port map (
      I0 => scratch(30),
      I1 => s_axi_araddr(3),
      I2 => \s_axi_rdata[31]_i_3_n_0\,
      I3 => \s_axi_rdata[31]_i_4_n_0\,
      I4 => s_axi_araddr(2),
      O => \s_axi_rdata[30]_i_1_n_0\
    );
\s_axi_rdata[31]_i_1\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"2"
    )
        port map (
      I0 => s_axi_arvalid,
      I1 => \^s_axi_rvalid_reg_0\,
      O => s_axi_rvalid01_out
    );
\s_axi_rdata[31]_i_2\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"000000B0"
    )
        port map (
      I0 => scratch(31),
      I1 => s_axi_araddr(2),
      I2 => s_axi_araddr(3),
      I3 => \s_axi_rdata[31]_i_3_n_0\,
      I4 => \s_axi_rdata[31]_i_4_n_0\,
      O => \s_axi_rdata[31]_i_2_n_0\
    );
\s_axi_rdata[31]_i_3\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"FFFE"
    )
        port map (
      I0 => s_axi_araddr(5),
      I1 => s_axi_araddr(4),
      I2 => s_axi_araddr(7),
      I3 => s_axi_araddr(6),
      O => \s_axi_rdata[31]_i_3_n_0\
    );
\s_axi_rdata[31]_i_4\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FFFFFFFFFFFFFFFE"
    )
        port map (
      I0 => s_axi_araddr(10),
      I1 => s_axi_araddr(11),
      I2 => s_axi_araddr(8),
      I3 => s_axi_araddr(9),
      I4 => s_axi_araddr(1),
      I5 => s_axi_araddr(0),
      O => \s_axi_rdata[31]_i_4_n_0\
    );
\s_axi_rdata[3]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"00080000"
    )
        port map (
      I0 => s_axi_araddr(2),
      I1 => s_axi_araddr(3),
      I2 => \s_axi_rdata[31]_i_3_n_0\,
      I3 => \s_axi_rdata[31]_i_4_n_0\,
      I4 => scratch(3),
      O => \s_axi_rdata[3]_i_1_n_0\
    );
\s_axi_rdata[4]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"000000B0"
    )
        port map (
      I0 => scratch(4),
      I1 => s_axi_araddr(2),
      I2 => s_axi_araddr(3),
      I3 => \s_axi_rdata[31]_i_3_n_0\,
      I4 => \s_axi_rdata[31]_i_4_n_0\,
      O => \s_axi_rdata[4]_i_1_n_0\
    );
\s_axi_rdata[5]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"00080000"
    )
        port map (
      I0 => s_axi_araddr(2),
      I1 => s_axi_araddr(3),
      I2 => \s_axi_rdata[31]_i_3_n_0\,
      I3 => \s_axi_rdata[31]_i_4_n_0\,
      I4 => scratch(5),
      O => \s_axi_rdata[5]_i_1_n_0\
    );
\s_axi_rdata[6]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"0000008F"
    )
        port map (
      I0 => scratch(6),
      I1 => s_axi_araddr(3),
      I2 => s_axi_araddr(2),
      I3 => \s_axi_rdata[31]_i_4_n_0\,
      I4 => \s_axi_rdata[31]_i_3_n_0\,
      O => \s_axi_rdata[6]_i_1_n_0\
    );
\s_axi_rdata[7]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"00080000"
    )
        port map (
      I0 => s_axi_araddr(2),
      I1 => s_axi_araddr(3),
      I2 => \s_axi_rdata[31]_i_3_n_0\,
      I3 => \s_axi_rdata[31]_i_4_n_0\,
      I4 => scratch(7),
      O => \s_axi_rdata[7]_i_1_n_0\
    );
\s_axi_rdata[8]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"00080000"
    )
        port map (
      I0 => s_axi_araddr(2),
      I1 => s_axi_araddr(3),
      I2 => \s_axi_rdata[31]_i_3_n_0\,
      I3 => \s_axi_rdata[31]_i_4_n_0\,
      I4 => scratch(8),
      O => \s_axi_rdata[8]_i_1_n_0\
    );
\s_axi_rdata[9]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"00080003"
    )
        port map (
      I0 => scratch(9),
      I1 => s_axi_araddr(3),
      I2 => \s_axi_rdata[31]_i_3_n_0\,
      I3 => \s_axi_rdata[31]_i_4_n_0\,
      I4 => s_axi_araddr(2),
      O => \s_axi_rdata[9]_i_1_n_0\
    );
\s_axi_rdata_reg[0]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => \s_axi_rdata[0]_i_1_n_0\,
      Q => s_axi_rdata(0),
      R => p_0_in
    );
\s_axi_rdata_reg[10]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => \s_axi_rdata[10]_i_1_n_0\,
      Q => s_axi_rdata(10),
      R => p_0_in
    );
\s_axi_rdata_reg[11]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => \s_axi_rdata[11]_i_1_n_0\,
      Q => s_axi_rdata(11),
      R => p_0_in
    );
\s_axi_rdata_reg[12]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => \s_axi_rdata[12]_i_1_n_0\,
      Q => s_axi_rdata(12),
      R => p_0_in
    );
\s_axi_rdata_reg[13]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => \s_axi_rdata[13]_i_1_n_0\,
      Q => s_axi_rdata(13),
      R => p_0_in
    );
\s_axi_rdata_reg[14]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => \s_axi_rdata[14]_i_1_n_0\,
      Q => s_axi_rdata(14),
      R => p_0_in
    );
\s_axi_rdata_reg[15]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => \s_axi_rdata[15]_i_1_n_0\,
      Q => s_axi_rdata(15),
      R => p_0_in
    );
\s_axi_rdata_reg[16]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => \s_axi_rdata[16]_i_1_n_0\,
      Q => s_axi_rdata(16),
      R => p_0_in
    );
\s_axi_rdata_reg[17]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => \s_axi_rdata[17]_i_1_n_0\,
      Q => s_axi_rdata(17),
      R => p_0_in
    );
\s_axi_rdata_reg[18]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => \s_axi_rdata[18]_i_1_n_0\,
      Q => s_axi_rdata(18),
      R => p_0_in
    );
\s_axi_rdata_reg[19]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => \s_axi_rdata[19]_i_1_n_0\,
      Q => s_axi_rdata(19),
      R => p_0_in
    );
\s_axi_rdata_reg[1]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => \s_axi_rdata[1]_i_1_n_0\,
      Q => s_axi_rdata(1),
      R => p_0_in
    );
\s_axi_rdata_reg[20]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => \s_axi_rdata[20]_i_1_n_0\,
      Q => s_axi_rdata(20),
      R => p_0_in
    );
\s_axi_rdata_reg[21]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => \s_axi_rdata[21]_i_1_n_0\,
      Q => s_axi_rdata(21),
      R => p_0_in
    );
\s_axi_rdata_reg[22]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => \s_axi_rdata[22]_i_1_n_0\,
      Q => s_axi_rdata(22),
      R => p_0_in
    );
\s_axi_rdata_reg[23]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => \s_axi_rdata[23]_i_1_n_0\,
      Q => s_axi_rdata(23),
      R => p_0_in
    );
\s_axi_rdata_reg[24]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => \s_axi_rdata[24]_i_1_n_0\,
      Q => s_axi_rdata(24),
      R => p_0_in
    );
\s_axi_rdata_reg[25]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => \s_axi_rdata[25]_i_1_n_0\,
      Q => s_axi_rdata(25),
      R => p_0_in
    );
\s_axi_rdata_reg[26]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => \s_axi_rdata[26]_i_1_n_0\,
      Q => s_axi_rdata(26),
      R => p_0_in
    );
\s_axi_rdata_reg[27]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => \s_axi_rdata[27]_i_1_n_0\,
      Q => s_axi_rdata(27),
      R => p_0_in
    );
\s_axi_rdata_reg[28]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => \s_axi_rdata[28]_i_1_n_0\,
      Q => s_axi_rdata(28),
      R => p_0_in
    );
\s_axi_rdata_reg[29]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => \s_axi_rdata[29]_i_1_n_0\,
      Q => s_axi_rdata(29),
      R => p_0_in
    );
\s_axi_rdata_reg[2]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => \s_axi_rdata[2]_i_1_n_0\,
      Q => s_axi_rdata(2),
      R => p_0_in
    );
\s_axi_rdata_reg[30]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => \s_axi_rdata[30]_i_1_n_0\,
      Q => s_axi_rdata(30),
      R => p_0_in
    );
\s_axi_rdata_reg[31]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => \s_axi_rdata[31]_i_2_n_0\,
      Q => s_axi_rdata(31),
      R => p_0_in
    );
\s_axi_rdata_reg[3]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => \s_axi_rdata[3]_i_1_n_0\,
      Q => s_axi_rdata(3),
      R => p_0_in
    );
\s_axi_rdata_reg[4]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => \s_axi_rdata[4]_i_1_n_0\,
      Q => s_axi_rdata(4),
      R => p_0_in
    );
\s_axi_rdata_reg[5]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => \s_axi_rdata[5]_i_1_n_0\,
      Q => s_axi_rdata(5),
      R => p_0_in
    );
\s_axi_rdata_reg[6]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => \s_axi_rdata[6]_i_1_n_0\,
      Q => s_axi_rdata(6),
      R => p_0_in
    );
\s_axi_rdata_reg[7]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => \s_axi_rdata[7]_i_1_n_0\,
      Q => s_axi_rdata(7),
      R => p_0_in
    );
\s_axi_rdata_reg[8]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => \s_axi_rdata[8]_i_1_n_0\,
      Q => s_axi_rdata(8),
      R => p_0_in
    );
\s_axi_rdata_reg[9]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => \s_axi_rdata[9]_i_1_n_0\,
      Q => s_axi_rdata(9),
      R => p_0_in
    );
\s_axi_rresp[1]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FFFFFFFE"
    )
        port map (
      I0 => \s_axi_rdata[31]_i_4_n_0\,
      I1 => s_axi_araddr(6),
      I2 => s_axi_araddr(7),
      I3 => s_axi_araddr(4),
      I4 => s_axi_araddr(5),
      O => \s_axi_rresp[1]_i_1_n_0\
    );
\s_axi_rresp_reg[1]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => \s_axi_rresp[1]_i_1_n_0\,
      Q => s_axi_rresp(0),
      R => p_0_in
    );
s_axi_rvalid_i_1: unisim.vcomponents.LUT3
    generic map(
      INIT => X"74"
    )
        port map (
      I0 => s_axi_rready,
      I1 => \^s_axi_rvalid_reg_0\,
      I2 => s_axi_arvalid,
      O => s_axi_rvalid_i_1_n_0
    );
s_axi_rvalid_reg: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => '1',
      D => s_axi_rvalid_i_1_n_0,
      Q => \^s_axi_rvalid_reg_0\,
      R => p_0_in
    );
s_axi_wready_INST_0: unisim.vcomponents.LUT3
    generic map(
      INIT => X"04"
    )
        port map (
      I0 => \^s_axi_bvalid_reg_0\,
      I1 => s_axi_aresetn,
      I2 => w_pending_reg_n_0,
      O => s_axi_wready
    );
\scratch[15]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"00000002"
    )
        port map (
      I0 => data00,
      I1 => \s_axi_bresp[1]_i_2_n_0\,
      I2 => \s_axi_bresp[1]_i_5_n_0\,
      I3 => \s_axi_bresp[1]_i_3_n_0\,
      I4 => \s_axi_bresp[1]_i_4_n_0\,
      O => p_1_in(15)
    );
\scratch[23]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"00000002"
    )
        port map (
      I0 => \w_strobes_reg_n_0_[2]\,
      I1 => \s_axi_bresp[1]_i_2_n_0\,
      I2 => \s_axi_bresp[1]_i_5_n_0\,
      I3 => \s_axi_bresp[1]_i_3_n_0\,
      I4 => \s_axi_bresp[1]_i_4_n_0\,
      O => p_1_in(23)
    );
\scratch[31]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"00000002"
    )
        port map (
      I0 => \w_strobes_reg_n_0_[3]\,
      I1 => \s_axi_bresp[1]_i_2_n_0\,
      I2 => \s_axi_bresp[1]_i_5_n_0\,
      I3 => \s_axi_bresp[1]_i_3_n_0\,
      I4 => \s_axi_bresp[1]_i_4_n_0\,
      O => p_1_in(31)
    );
\scratch[7]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"00000002"
    )
        port map (
      I0 => \w_strobes_reg_n_0_[0]\,
      I1 => \s_axi_bresp[1]_i_2_n_0\,
      I2 => \s_axi_bresp[1]_i_5_n_0\,
      I3 => \s_axi_bresp[1]_i_3_n_0\,
      I4 => \s_axi_bresp[1]_i_4_n_0\,
      O => p_1_in(7)
    );
\scratch_reg[0]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(7),
      D => w_data(0),
      Q => scratch(0),
      R => p_0_in
    );
\scratch_reg[10]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(15),
      D => w_data(10),
      Q => scratch(10),
      R => p_0_in
    );
\scratch_reg[11]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(15),
      D => w_data(11),
      Q => scratch(11),
      R => p_0_in
    );
\scratch_reg[12]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(15),
      D => w_data(12),
      Q => scratch(12),
      R => p_0_in
    );
\scratch_reg[13]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(15),
      D => w_data(13),
      Q => scratch(13),
      R => p_0_in
    );
\scratch_reg[14]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(15),
      D => w_data(14),
      Q => scratch(14),
      R => p_0_in
    );
\scratch_reg[15]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(15),
      D => w_data(15),
      Q => scratch(15),
      R => p_0_in
    );
\scratch_reg[16]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(23),
      D => w_data(16),
      Q => scratch(16),
      R => p_0_in
    );
\scratch_reg[17]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(23),
      D => w_data(17),
      Q => scratch(17),
      R => p_0_in
    );
\scratch_reg[18]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(23),
      D => w_data(18),
      Q => scratch(18),
      R => p_0_in
    );
\scratch_reg[19]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(23),
      D => w_data(19),
      Q => scratch(19),
      R => p_0_in
    );
\scratch_reg[1]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(7),
      D => w_data(1),
      Q => scratch(1),
      R => p_0_in
    );
\scratch_reg[20]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(23),
      D => w_data(20),
      Q => scratch(20),
      R => p_0_in
    );
\scratch_reg[21]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(23),
      D => w_data(21),
      Q => scratch(21),
      R => p_0_in
    );
\scratch_reg[22]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(23),
      D => w_data(22),
      Q => scratch(22),
      R => p_0_in
    );
\scratch_reg[23]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(23),
      D => w_data(23),
      Q => scratch(23),
      R => p_0_in
    );
\scratch_reg[24]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(31),
      D => w_data(24),
      Q => scratch(24),
      R => p_0_in
    );
\scratch_reg[25]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(31),
      D => w_data(25),
      Q => scratch(25),
      R => p_0_in
    );
\scratch_reg[26]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(31),
      D => w_data(26),
      Q => scratch(26),
      R => p_0_in
    );
\scratch_reg[27]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(31),
      D => w_data(27),
      Q => scratch(27),
      R => p_0_in
    );
\scratch_reg[28]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(31),
      D => w_data(28),
      Q => scratch(28),
      R => p_0_in
    );
\scratch_reg[29]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(31),
      D => w_data(29),
      Q => scratch(29),
      R => p_0_in
    );
\scratch_reg[2]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(7),
      D => w_data(2),
      Q => scratch(2),
      R => p_0_in
    );
\scratch_reg[30]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(31),
      D => w_data(30),
      Q => scratch(30),
      R => p_0_in
    );
\scratch_reg[31]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(31),
      D => w_data(31),
      Q => scratch(31),
      R => p_0_in
    );
\scratch_reg[3]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(7),
      D => w_data(3),
      Q => scratch(3),
      R => p_0_in
    );
\scratch_reg[4]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(7),
      D => w_data(4),
      Q => scratch(4),
      R => p_0_in
    );
\scratch_reg[5]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(7),
      D => w_data(5),
      Q => scratch(5),
      R => p_0_in
    );
\scratch_reg[6]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(7),
      D => w_data(6),
      Q => scratch(6),
      R => p_0_in
    );
\scratch_reg[7]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(7),
      D => w_data(7),
      Q => scratch(7),
      R => p_0_in
    );
\scratch_reg[8]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(15),
      D => w_data(8),
      Q => scratch(8),
      R => p_0_in
    );
\scratch_reg[9]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(15),
      D => w_data(9),
      Q => scratch(9),
      R => p_0_in
    );
\w_data_reg[0]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(0),
      Q => w_data(0),
      R => p_0_in
    );
\w_data_reg[10]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(10),
      Q => w_data(10),
      R => p_0_in
    );
\w_data_reg[11]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(11),
      Q => w_data(11),
      R => p_0_in
    );
\w_data_reg[12]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(12),
      Q => w_data(12),
      R => p_0_in
    );
\w_data_reg[13]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(13),
      Q => w_data(13),
      R => p_0_in
    );
\w_data_reg[14]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(14),
      Q => w_data(14),
      R => p_0_in
    );
\w_data_reg[15]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(15),
      Q => w_data(15),
      R => p_0_in
    );
\w_data_reg[16]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(16),
      Q => w_data(16),
      R => p_0_in
    );
\w_data_reg[17]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(17),
      Q => w_data(17),
      R => p_0_in
    );
\w_data_reg[18]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(18),
      Q => w_data(18),
      R => p_0_in
    );
\w_data_reg[19]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(19),
      Q => w_data(19),
      R => p_0_in
    );
\w_data_reg[1]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(1),
      Q => w_data(1),
      R => p_0_in
    );
\w_data_reg[20]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(20),
      Q => w_data(20),
      R => p_0_in
    );
\w_data_reg[21]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(21),
      Q => w_data(21),
      R => p_0_in
    );
\w_data_reg[22]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(22),
      Q => w_data(22),
      R => p_0_in
    );
\w_data_reg[23]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(23),
      Q => w_data(23),
      R => p_0_in
    );
\w_data_reg[24]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(24),
      Q => w_data(24),
      R => p_0_in
    );
\w_data_reg[25]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(25),
      Q => w_data(25),
      R => p_0_in
    );
\w_data_reg[26]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(26),
      Q => w_data(26),
      R => p_0_in
    );
\w_data_reg[27]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(27),
      Q => w_data(27),
      R => p_0_in
    );
\w_data_reg[28]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(28),
      Q => w_data(28),
      R => p_0_in
    );
\w_data_reg[29]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(29),
      Q => w_data(29),
      R => p_0_in
    );
\w_data_reg[2]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(2),
      Q => w_data(2),
      R => p_0_in
    );
\w_data_reg[30]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(30),
      Q => w_data(30),
      R => p_0_in
    );
\w_data_reg[31]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(31),
      Q => w_data(31),
      R => p_0_in
    );
\w_data_reg[3]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(3),
      Q => w_data(3),
      R => p_0_in
    );
\w_data_reg[4]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(4),
      Q => w_data(4),
      R => p_0_in
    );
\w_data_reg[5]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(5),
      Q => w_data(5),
      R => p_0_in
    );
\w_data_reg[6]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(6),
      Q => w_data(6),
      R => p_0_in
    );
\w_data_reg[7]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(7),
      Q => w_data(7),
      R => p_0_in
    );
\w_data_reg[8]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(8),
      Q => w_data(8),
      R => p_0_in
    );
\w_data_reg[9]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(9),
      Q => w_data(9),
      R => p_0_in
    );
w_pending_i_1: unisim.vcomponents.LUT4
    generic map(
      INIT => X"20FF"
    )
        port map (
      I0 => aw_pending,
      I1 => \^s_axi_bvalid_reg_0\,
      I2 => w_pending_reg_n_0,
      I3 => s_axi_aresetn,
      O => w_pending
    );
w_pending_i_2: unisim.vcomponents.LUT3
    generic map(
      INIT => X"F4"
    )
        port map (
      I0 => \^s_axi_bvalid_reg_0\,
      I1 => s_axi_wvalid,
      I2 => w_pending_reg_n_0,
      O => w_pending_i_2_n_0
    );
w_pending_reg: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => '1',
      D => w_pending_i_2_n_0,
      Q => w_pending_reg_n_0,
      R => w_pending
    );
\w_strobes[3]_i_1\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"04"
    )
        port map (
      I0 => w_pending_reg_n_0,
      I1 => s_axi_wvalid,
      I2 => \^s_axi_bvalid_reg_0\,
      O => w_pending0
    );
\w_strobes_reg[0]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wstrb(0),
      Q => \w_strobes_reg_n_0_[0]\,
      R => p_0_in
    );
\w_strobes_reg[1]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wstrb(1),
      Q => data00,
      R => p_0_in
    );
\w_strobes_reg[2]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wstrb(2),
      Q => \w_strobes_reg_n_0_[2]\,
      R => p_0_in
    );
\w_strobes_reg[3]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wstrb(3),
      Q => \w_strobes_reg_n_0_[3]\,
      R => p_0_in
    );
end STRUCTURE;
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
library UNISIM;
use UNISIM.VCOMPONENTS.ALL;
entity kv260_ispMipiRx_vcu_DP_aura_m3_regs_0_0 is
  port (
    s_axi_aclk : in STD_LOGIC;
    s_axi_aresetn : in STD_LOGIC;
    s_axi_awaddr : in STD_LOGIC_VECTOR ( 11 downto 0 );
    s_axi_awprot : in STD_LOGIC_VECTOR ( 2 downto 0 );
    s_axi_awvalid : in STD_LOGIC;
    s_axi_awready : out STD_LOGIC;
    s_axi_wdata : in STD_LOGIC_VECTOR ( 31 downto 0 );
    s_axi_wstrb : in STD_LOGIC_VECTOR ( 3 downto 0 );
    s_axi_wvalid : in STD_LOGIC;
    s_axi_wready : out STD_LOGIC;
    s_axi_bresp : out STD_LOGIC_VECTOR ( 1 downto 0 );
    s_axi_bvalid : out STD_LOGIC;
    s_axi_bready : in STD_LOGIC;
    s_axi_araddr : in STD_LOGIC_VECTOR ( 11 downto 0 );
    s_axi_arprot : in STD_LOGIC_VECTOR ( 2 downto 0 );
    s_axi_arvalid : in STD_LOGIC;
    s_axi_arready : out STD_LOGIC;
    s_axi_rdata : out STD_LOGIC_VECTOR ( 31 downto 0 );
    s_axi_rresp : out STD_LOGIC_VECTOR ( 1 downto 0 );
    s_axi_rvalid : out STD_LOGIC;
    s_axi_rready : in STD_LOGIC
  );
  attribute NotValidForBitStream : boolean;
  attribute NotValidForBitStream of kv260_ispMipiRx_vcu_DP_aura_m3_regs_0_0 : entity is true;
  attribute CHECK_LICENSE_TYPE : string;
  attribute CHECK_LICENSE_TYPE of kv260_ispMipiRx_vcu_DP_aura_m3_regs_0_0 : entity is "kv260_ispMipiRx_vcu_DP_aura_m3_regs_0_0,aura_m3_regs,{}";
  attribute DowngradeIPIdentifiedWarnings : string;
  attribute DowngradeIPIdentifiedWarnings of kv260_ispMipiRx_vcu_DP_aura_m3_regs_0_0 : entity is "yes";
  attribute IP_DEFINITION_SOURCE : string;
  attribute IP_DEFINITION_SOURCE of kv260_ispMipiRx_vcu_DP_aura_m3_regs_0_0 : entity is "package_project";
  attribute X_CORE_INFO : string;
  attribute X_CORE_INFO of kv260_ispMipiRx_vcu_DP_aura_m3_regs_0_0 : entity is "aura_m3_regs,Vivado 2022.2";
end kv260_ispMipiRx_vcu_DP_aura_m3_regs_0_0;

architecture STRUCTURE of kv260_ispMipiRx_vcu_DP_aura_m3_regs_0_0 is
  signal \<const0>\ : STD_LOGIC;
  signal \^s_axi_bresp\ : STD_LOGIC_VECTOR ( 1 to 1 );
  signal \^s_axi_rresp\ : STD_LOGIC_VECTOR ( 1 to 1 );
  attribute X_INTERFACE_INFO : string;
  attribute X_INTERFACE_INFO of s_axi_aclk : signal is "xilinx.com:signal:clock:1.0 s_axi_aclk CLK";
  attribute X_INTERFACE_PARAMETER : string;
  attribute X_INTERFACE_PARAMETER of s_axi_aclk : signal is "XIL_INTERFACENAME s_axi_aclk, ASSOCIATED_BUSIF S_AXI, ASSOCIATED_RESET s_axi_aresetn, FREQ_HZ 99999000, FREQ_TOLERANCE_HZ 0, PHASE 0.0, CLK_DOMAIN kv260_ispMipiRx_vcu_DP_clk_wiz_0_0_clk_200M, INSERT_VIP 0";
  attribute X_INTERFACE_INFO of s_axi_aresetn : signal is "xilinx.com:signal:reset:1.0 s_axi_aresetn RST";
  attribute X_INTERFACE_PARAMETER of s_axi_aresetn : signal is "XIL_INTERFACENAME s_axi_aresetn, POLARITY ACTIVE_LOW, INSERT_VIP 0";
  attribute X_INTERFACE_INFO of s_axi_arready : signal is "xilinx.com:interface:aximm:1.0 S_AXI ARREADY";
  attribute X_INTERFACE_INFO of s_axi_arvalid : signal is "xilinx.com:interface:aximm:1.0 S_AXI ARVALID";
  attribute X_INTERFACE_INFO of s_axi_awready : signal is "xilinx.com:interface:aximm:1.0 S_AXI AWREADY";
  attribute X_INTERFACE_INFO of s_axi_awvalid : signal is "xilinx.com:interface:aximm:1.0 S_AXI AWVALID";
  attribute X_INTERFACE_INFO of s_axi_bready : signal is "xilinx.com:interface:aximm:1.0 S_AXI BREADY";
  attribute X_INTERFACE_INFO of s_axi_bvalid : signal is "xilinx.com:interface:aximm:1.0 S_AXI BVALID";
  attribute X_INTERFACE_INFO of s_axi_rready : signal is "xilinx.com:interface:aximm:1.0 S_AXI RREADY";
  attribute X_INTERFACE_PARAMETER of s_axi_rready : signal is "XIL_INTERFACENAME S_AXI, PROTOCOL AXI4LITE, DATA_WIDTH 32, ADDR_WIDTH 12, READ_WRITE_MODE READ_WRITE, FREQ_HZ 99999000, ID_WIDTH 0, AWUSER_WIDTH 0, ARUSER_WIDTH 0, WUSER_WIDTH 0, RUSER_WIDTH 0, BUSER_WIDTH 0, HAS_BURST 0, HAS_LOCK 0, HAS_PROT 1, HAS_CACHE 0, HAS_QOS 0, HAS_REGION 0, HAS_WSTRB 1, HAS_BRESP 1, HAS_RRESP 1, SUPPORTS_NARROW_BURST 0, NUM_READ_OUTSTANDING 1, NUM_WRITE_OUTSTANDING 1, MAX_BURST_LENGTH 1, PHASE 0.0, CLK_DOMAIN kv260_ispMipiRx_vcu_DP_clk_wiz_0_0_clk_200M, NUM_READ_THREADS 1, NUM_WRITE_THREADS 1, RUSER_BITS_PER_BYTE 0, WUSER_BITS_PER_BYTE 0, INSERT_VIP 0";
  attribute X_INTERFACE_INFO of s_axi_rvalid : signal is "xilinx.com:interface:aximm:1.0 S_AXI RVALID";
  attribute X_INTERFACE_INFO of s_axi_wready : signal is "xilinx.com:interface:aximm:1.0 S_AXI WREADY";
  attribute X_INTERFACE_INFO of s_axi_wvalid : signal is "xilinx.com:interface:aximm:1.0 S_AXI WVALID";
  attribute X_INTERFACE_INFO of s_axi_araddr : signal is "xilinx.com:interface:aximm:1.0 S_AXI ARADDR";
  attribute X_INTERFACE_INFO of s_axi_arprot : signal is "xilinx.com:interface:aximm:1.0 S_AXI ARPROT";
  attribute X_INTERFACE_INFO of s_axi_awaddr : signal is "xilinx.com:interface:aximm:1.0 S_AXI AWADDR";
  attribute X_INTERFACE_PARAMETER of s_axi_awaddr : signal is "PROTOCOL AXI4LITE, DATA_WIDTH 32, ADDR_WIDTH 12, READ_WRITE_MODE READ_WRITE";
  attribute X_INTERFACE_INFO of s_axi_awprot : signal is "xilinx.com:interface:aximm:1.0 S_AXI AWPROT";
  attribute X_INTERFACE_INFO of s_axi_bresp : signal is "xilinx.com:interface:aximm:1.0 S_AXI BRESP";
  attribute X_INTERFACE_INFO of s_axi_rdata : signal is "xilinx.com:interface:aximm:1.0 S_AXI RDATA";
  attribute X_INTERFACE_INFO of s_axi_rresp : signal is "xilinx.com:interface:aximm:1.0 S_AXI RRESP";
  attribute X_INTERFACE_INFO of s_axi_wdata : signal is "xilinx.com:interface:aximm:1.0 S_AXI WDATA";
  attribute X_INTERFACE_INFO of s_axi_wstrb : signal is "xilinx.com:interface:aximm:1.0 S_AXI WSTRB";
begin
  s_axi_bresp(1) <= \^s_axi_bresp\(1);
  s_axi_bresp(0) <= \<const0>\;
  s_axi_rresp(1) <= \^s_axi_rresp\(1);
  s_axi_rresp(0) <= \<const0>\;
GND: unisim.vcomponents.GND
     port map (
      G => \<const0>\
    );
inst: entity work.kv260_ispMipiRx_vcu_DP_aura_m3_regs_0_0_aura_m3_regs
     port map (
      s_axi_aclk => s_axi_aclk,
      s_axi_araddr(11 downto 0) => s_axi_araddr(11 downto 0),
      s_axi_aresetn => s_axi_aresetn,
      s_axi_arready => s_axi_arready,
      s_axi_arvalid => s_axi_arvalid,
      s_axi_awaddr(11 downto 0) => s_axi_awaddr(11 downto 0),
      s_axi_awready => s_axi_awready,
      s_axi_awvalid => s_axi_awvalid,
      s_axi_bready => s_axi_bready,
      s_axi_bresp(0) => \^s_axi_bresp\(1),
      s_axi_bvalid_reg_0 => s_axi_bvalid,
      s_axi_rdata(31 downto 0) => s_axi_rdata(31 downto 0),
      s_axi_rready => s_axi_rready,
      s_axi_rresp(0) => \^s_axi_rresp\(1),
      s_axi_rvalid_reg_0 => s_axi_rvalid,
      s_axi_wdata(31 downto 0) => s_axi_wdata(31 downto 0),
      s_axi_wready => s_axi_wready,
      s_axi_wstrb(3 downto 0) => s_axi_wstrb(3 downto 0),
      s_axi_wvalid => s_axi_wvalid
    );
end STRUCTURE;
