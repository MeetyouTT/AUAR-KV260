-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- --------------------------------------------------------------------------------
-- Tool Version: Vivado v.2022.2 (lin64) Build 3671981 Fri Oct 14 04:59:54 MDT 2022
-- Date        : Thu Oct  8 02:17:50 2026
-- Host        : ghmd-MRA-XXX running 64-bit Ubuntu 20.04.4 LTS
-- Command     : write_vhdl -force -mode funcsim -rename_top kv260_ispMipiRx_vcu_DP_audio_ss_0_0 -prefix
--               kv260_ispMipiRx_vcu_DP_audio_ss_0_0_ kv260_ispMipiRx_vcu_DP_audio_ss_0_0_sim_netlist.vhdl
-- Design      : kv260_ispMipiRx_vcu_DP_audio_ss_0_0
-- Purpose     : This VHDL netlist is a functional simulation representation of the design and should not be modified or
--               synthesized. This netlist cannot be used for SDF annotated simulation.
-- Device      : xck26-sfvc784-2LV-c
-- --------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
library UNISIM;
use UNISIM.VCOMPONENTS.ALL;
entity kv260_ispMipiRx_vcu_DP_audio_ss_0_0_aura_audio_decerr is
  port (
    bvalid_reg_0 : out STD_LOGIC;
    s_axi_ctrl_i2s_rx_rvalid : out STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_ctrl_i2s_rx_wready : out STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_ctrl_i2s_rx_awready : out STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_ctrl_i2s_rx_arready : out STD_LOGIC_VECTOR ( 0 to 0 );
    ACLK : in STD_LOGIC;
    ARESETN : in STD_LOGIC;
    s_axi_ctrl_i2s_rx_bready : in STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_ctrl_i2s_rx_arvalid : in STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_ctrl_i2s_rx_rready : in STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_ctrl_i2s_rx_wvalid : in STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_ctrl_i2s_rx_awvalid : in STD_LOGIC_VECTOR ( 0 to 0 )
  );
end kv260_ispMipiRx_vcu_DP_audio_ss_0_0_aura_audio_decerr;

architecture STRUCTURE of kv260_ispMipiRx_vcu_DP_audio_ss_0_0_aura_audio_decerr is
  signal aw_pending : STD_LOGIC;
  signal aw_pending_i_1_n_0 : STD_LOGIC;
  signal bvalid_i_1_n_0 : STD_LOGIC;
  signal \^bvalid_reg_0\ : STD_LOGIC;
  signal rvalid_i_1_n_0 : STD_LOGIC;
  signal \^s_axi_ctrl_i2s_rx_rvalid\ : STD_LOGIC_VECTOR ( 0 to 0 );
  signal w_pending_i_1_n_0 : STD_LOGIC;
  signal w_pending_i_2_n_0 : STD_LOGIC;
  signal w_pending_reg_n_0 : STD_LOGIC;
  attribute SOFT_HLUTNM : string;
  attribute SOFT_HLUTNM of aw_pending_i_1 : label is "soft_lutpair2";
  attribute SOFT_HLUTNM of bvalid_i_1 : label is "soft_lutpair0";
  attribute SOFT_HLUTNM of rvalid_i_1 : label is "soft_lutpair1";
  attribute SOFT_HLUTNM of \s_axi_ctrl_i2s_rx_arready[0]_INST_0\ : label is "soft_lutpair1";
  attribute SOFT_HLUTNM of \s_axi_ctrl_i2s_rx_awready[0]_INST_0\ : label is "soft_lutpair2";
  attribute SOFT_HLUTNM of \s_axi_ctrl_i2s_rx_wready[0]_INST_0\ : label is "soft_lutpair0";
begin
  bvalid_reg_0 <= \^bvalid_reg_0\;
  s_axi_ctrl_i2s_rx_rvalid(0) <= \^s_axi_ctrl_i2s_rx_rvalid\(0);
aw_pending_i_1: unisim.vcomponents.LUT3
    generic map(
      INIT => X"F2"
    )
        port map (
      I0 => s_axi_ctrl_i2s_rx_awvalid(0),
      I1 => \^bvalid_reg_0\,
      I2 => aw_pending,
      O => aw_pending_i_1_n_0
    );
aw_pending_reg: unisim.vcomponents.FDRE
     port map (
      C => ACLK,
      CE => '1',
      D => aw_pending_i_1_n_0,
      Q => aw_pending,
      R => w_pending_i_1_n_0
    );
bvalid_i_1: unisim.vcomponents.LUT5
    generic map(
      INIT => X"00F08080"
    )
        port map (
      I0 => aw_pending,
      I1 => w_pending_reg_n_0,
      I2 => ARESETN,
      I3 => s_axi_ctrl_i2s_rx_bready(0),
      I4 => \^bvalid_reg_0\,
      O => bvalid_i_1_n_0
    );
bvalid_reg: unisim.vcomponents.FDRE
     port map (
      C => ACLK,
      CE => '1',
      D => bvalid_i_1_n_0,
      Q => \^bvalid_reg_0\,
      R => '0'
    );
rvalid_i_1: unisim.vcomponents.LUT4
    generic map(
      INIT => X"0C88"
    )
        port map (
      I0 => s_axi_ctrl_i2s_rx_arvalid(0),
      I1 => ARESETN,
      I2 => s_axi_ctrl_i2s_rx_rready(0),
      I3 => \^s_axi_ctrl_i2s_rx_rvalid\(0),
      O => rvalid_i_1_n_0
    );
rvalid_reg: unisim.vcomponents.FDRE
     port map (
      C => ACLK,
      CE => '1',
      D => rvalid_i_1_n_0,
      Q => \^s_axi_ctrl_i2s_rx_rvalid\(0),
      R => '0'
    );
\s_axi_ctrl_i2s_rx_arready[0]_INST_0\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"2"
    )
        port map (
      I0 => ARESETN,
      I1 => \^s_axi_ctrl_i2s_rx_rvalid\(0),
      O => s_axi_ctrl_i2s_rx_arready(0)
    );
\s_axi_ctrl_i2s_rx_awready[0]_INST_0\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"04"
    )
        port map (
      I0 => \^bvalid_reg_0\,
      I1 => ARESETN,
      I2 => aw_pending,
      O => s_axi_ctrl_i2s_rx_awready(0)
    );
\s_axi_ctrl_i2s_rx_wready[0]_INST_0\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"04"
    )
        port map (
      I0 => \^bvalid_reg_0\,
      I1 => ARESETN,
      I2 => w_pending_reg_n_0,
      O => s_axi_ctrl_i2s_rx_wready(0)
    );
w_pending_i_1: unisim.vcomponents.LUT4
    generic map(
      INIT => X"20FF"
    )
        port map (
      I0 => w_pending_reg_n_0,
      I1 => \^bvalid_reg_0\,
      I2 => aw_pending,
      I3 => ARESETN,
      O => w_pending_i_1_n_0
    );
w_pending_i_2: unisim.vcomponents.LUT3
    generic map(
      INIT => X"F2"
    )
        port map (
      I0 => s_axi_ctrl_i2s_rx_wvalid(0),
      I1 => \^bvalid_reg_0\,
      I2 => w_pending_reg_n_0,
      O => w_pending_i_2_n_0
    );
w_pending_reg: unisim.vcomponents.FDRE
     port map (
      C => ACLK,
      CE => '1',
      D => w_pending_i_2_n_0,
      Q => w_pending_reg_n_0,
      R => w_pending_i_1_n_0
    );
end STRUCTURE;
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
library UNISIM;
use UNISIM.VCOMPONENTS.ALL;
entity kv260_ispMipiRx_vcu_DP_audio_ss_0_0_aura_audio_decerr_0 is
  port (
    bvalid_reg_0 : out STD_LOGIC;
    s_axi_ctrl_i2s_tx_rvalid : out STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_ctrl_i2s_tx_wready : out STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_ctrl_i2s_tx_awready : out STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_ctrl_i2s_tx_arready : out STD_LOGIC_VECTOR ( 0 to 0 );
    ACLK : in STD_LOGIC;
    ARESETN : in STD_LOGIC;
    s_axi_ctrl_i2s_tx_bready : in STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_ctrl_i2s_tx_arvalid : in STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_ctrl_i2s_tx_rready : in STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_ctrl_i2s_tx_wvalid : in STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_ctrl_i2s_tx_awvalid : in STD_LOGIC_VECTOR ( 0 to 0 )
  );
  attribute ORIG_REF_NAME : string;
  attribute ORIG_REF_NAME of kv260_ispMipiRx_vcu_DP_audio_ss_0_0_aura_audio_decerr_0 : entity is "aura_audio_decerr";
end kv260_ispMipiRx_vcu_DP_audio_ss_0_0_aura_audio_decerr_0;

architecture STRUCTURE of kv260_ispMipiRx_vcu_DP_audio_ss_0_0_aura_audio_decerr_0 is
  signal aw_pending : STD_LOGIC;
  signal \aw_pending_i_1__0_n_0\ : STD_LOGIC;
  signal \bvalid_i_1__0_n_0\ : STD_LOGIC;
  signal \^bvalid_reg_0\ : STD_LOGIC;
  signal \rvalid_i_1__0_n_0\ : STD_LOGIC;
  signal \^s_axi_ctrl_i2s_tx_rvalid\ : STD_LOGIC_VECTOR ( 0 to 0 );
  signal \w_pending_i_1__0_n_0\ : STD_LOGIC;
  signal \w_pending_i_2__0_n_0\ : STD_LOGIC;
  signal w_pending_reg_n_0 : STD_LOGIC;
  attribute SOFT_HLUTNM : string;
  attribute SOFT_HLUTNM of \aw_pending_i_1__0\ : label is "soft_lutpair5";
  attribute SOFT_HLUTNM of \bvalid_i_1__0\ : label is "soft_lutpair3";
  attribute SOFT_HLUTNM of \rvalid_i_1__0\ : label is "soft_lutpair4";
  attribute SOFT_HLUTNM of \s_axi_ctrl_i2s_tx_arready[0]_INST_0\ : label is "soft_lutpair4";
  attribute SOFT_HLUTNM of \s_axi_ctrl_i2s_tx_awready[0]_INST_0\ : label is "soft_lutpair5";
  attribute SOFT_HLUTNM of \s_axi_ctrl_i2s_tx_wready[0]_INST_0\ : label is "soft_lutpair3";
begin
  bvalid_reg_0 <= \^bvalid_reg_0\;
  s_axi_ctrl_i2s_tx_rvalid(0) <= \^s_axi_ctrl_i2s_tx_rvalid\(0);
\aw_pending_i_1__0\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"F2"
    )
        port map (
      I0 => s_axi_ctrl_i2s_tx_awvalid(0),
      I1 => \^bvalid_reg_0\,
      I2 => aw_pending,
      O => \aw_pending_i_1__0_n_0\
    );
aw_pending_reg: unisim.vcomponents.FDRE
     port map (
      C => ACLK,
      CE => '1',
      D => \aw_pending_i_1__0_n_0\,
      Q => aw_pending,
      R => \w_pending_i_1__0_n_0\
    );
\bvalid_i_1__0\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"00F08080"
    )
        port map (
      I0 => aw_pending,
      I1 => w_pending_reg_n_0,
      I2 => ARESETN,
      I3 => s_axi_ctrl_i2s_tx_bready(0),
      I4 => \^bvalid_reg_0\,
      O => \bvalid_i_1__0_n_0\
    );
bvalid_reg: unisim.vcomponents.FDRE
     port map (
      C => ACLK,
      CE => '1',
      D => \bvalid_i_1__0_n_0\,
      Q => \^bvalid_reg_0\,
      R => '0'
    );
\rvalid_i_1__0\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"0C88"
    )
        port map (
      I0 => s_axi_ctrl_i2s_tx_arvalid(0),
      I1 => ARESETN,
      I2 => s_axi_ctrl_i2s_tx_rready(0),
      I3 => \^s_axi_ctrl_i2s_tx_rvalid\(0),
      O => \rvalid_i_1__0_n_0\
    );
rvalid_reg: unisim.vcomponents.FDRE
     port map (
      C => ACLK,
      CE => '1',
      D => \rvalid_i_1__0_n_0\,
      Q => \^s_axi_ctrl_i2s_tx_rvalid\(0),
      R => '0'
    );
\s_axi_ctrl_i2s_tx_arready[0]_INST_0\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"2"
    )
        port map (
      I0 => ARESETN,
      I1 => \^s_axi_ctrl_i2s_tx_rvalid\(0),
      O => s_axi_ctrl_i2s_tx_arready(0)
    );
\s_axi_ctrl_i2s_tx_awready[0]_INST_0\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"04"
    )
        port map (
      I0 => \^bvalid_reg_0\,
      I1 => ARESETN,
      I2 => aw_pending,
      O => s_axi_ctrl_i2s_tx_awready(0)
    );
\s_axi_ctrl_i2s_tx_wready[0]_INST_0\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"04"
    )
        port map (
      I0 => \^bvalid_reg_0\,
      I1 => ARESETN,
      I2 => w_pending_reg_n_0,
      O => s_axi_ctrl_i2s_tx_wready(0)
    );
\w_pending_i_1__0\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"20FF"
    )
        port map (
      I0 => w_pending_reg_n_0,
      I1 => \^bvalid_reg_0\,
      I2 => aw_pending,
      I3 => ARESETN,
      O => \w_pending_i_1__0_n_0\
    );
\w_pending_i_2__0\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"F2"
    )
        port map (
      I0 => s_axi_ctrl_i2s_tx_wvalid(0),
      I1 => \^bvalid_reg_0\,
      I2 => w_pending_reg_n_0,
      O => \w_pending_i_2__0_n_0\
    );
w_pending_reg: unisim.vcomponents.FDRE
     port map (
      C => ACLK,
      CE => '1',
      D => \w_pending_i_2__0_n_0\,
      Q => w_pending_reg_n_0,
      R => \w_pending_i_1__0_n_0\
    );
end STRUCTURE;
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
library UNISIM;
use UNISIM.VCOMPONENTS.ALL;
entity kv260_ispMipiRx_vcu_DP_audio_ss_0_0_aura_audio_decerr_1 is
  port (
    bvalid_reg_0 : out STD_LOGIC;
    s_axi_lite_audio_fmt_rvalid : out STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_lite_audio_fmt_wready : out STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_lite_audio_fmt_awready : out STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_lite_audio_fmt_arready : out STD_LOGIC_VECTOR ( 0 to 0 );
    ACLK : in STD_LOGIC;
    ARESETN : in STD_LOGIC;
    s_axi_lite_audio_fmt_bready : in STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_lite_audio_fmt_arvalid : in STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_lite_audio_fmt_rready : in STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_lite_audio_fmt_wvalid : in STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_lite_audio_fmt_awvalid : in STD_LOGIC_VECTOR ( 0 to 0 )
  );
  attribute ORIG_REF_NAME : string;
  attribute ORIG_REF_NAME of kv260_ispMipiRx_vcu_DP_audio_ss_0_0_aura_audio_decerr_1 : entity is "aura_audio_decerr";
end kv260_ispMipiRx_vcu_DP_audio_ss_0_0_aura_audio_decerr_1;

architecture STRUCTURE of kv260_ispMipiRx_vcu_DP_audio_ss_0_0_aura_audio_decerr_1 is
  signal aw_pending : STD_LOGIC;
  signal \aw_pending_i_1__1_n_0\ : STD_LOGIC;
  signal \bvalid_i_1__1_n_0\ : STD_LOGIC;
  signal \^bvalid_reg_0\ : STD_LOGIC;
  signal \rvalid_i_1__1_n_0\ : STD_LOGIC;
  signal \^s_axi_lite_audio_fmt_rvalid\ : STD_LOGIC_VECTOR ( 0 to 0 );
  signal \w_pending_i_1__1_n_0\ : STD_LOGIC;
  signal \w_pending_i_2__1_n_0\ : STD_LOGIC;
  signal w_pending_reg_n_0 : STD_LOGIC;
  attribute SOFT_HLUTNM : string;
  attribute SOFT_HLUTNM of \aw_pending_i_1__1\ : label is "soft_lutpair8";
  attribute SOFT_HLUTNM of \bvalid_i_1__1\ : label is "soft_lutpair6";
  attribute SOFT_HLUTNM of \rvalid_i_1__1\ : label is "soft_lutpair7";
  attribute SOFT_HLUTNM of \s_axi_lite_audio_fmt_arready[0]_INST_0\ : label is "soft_lutpair7";
  attribute SOFT_HLUTNM of \s_axi_lite_audio_fmt_awready[0]_INST_0\ : label is "soft_lutpair8";
  attribute SOFT_HLUTNM of \s_axi_lite_audio_fmt_wready[0]_INST_0\ : label is "soft_lutpair6";
begin
  bvalid_reg_0 <= \^bvalid_reg_0\;
  s_axi_lite_audio_fmt_rvalid(0) <= \^s_axi_lite_audio_fmt_rvalid\(0);
\aw_pending_i_1__1\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"F2"
    )
        port map (
      I0 => s_axi_lite_audio_fmt_awvalid(0),
      I1 => \^bvalid_reg_0\,
      I2 => aw_pending,
      O => \aw_pending_i_1__1_n_0\
    );
aw_pending_reg: unisim.vcomponents.FDRE
     port map (
      C => ACLK,
      CE => '1',
      D => \aw_pending_i_1__1_n_0\,
      Q => aw_pending,
      R => \w_pending_i_1__1_n_0\
    );
\bvalid_i_1__1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"00F08080"
    )
        port map (
      I0 => aw_pending,
      I1 => w_pending_reg_n_0,
      I2 => ARESETN,
      I3 => s_axi_lite_audio_fmt_bready(0),
      I4 => \^bvalid_reg_0\,
      O => \bvalid_i_1__1_n_0\
    );
bvalid_reg: unisim.vcomponents.FDRE
     port map (
      C => ACLK,
      CE => '1',
      D => \bvalid_i_1__1_n_0\,
      Q => \^bvalid_reg_0\,
      R => '0'
    );
\rvalid_i_1__1\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"0C88"
    )
        port map (
      I0 => s_axi_lite_audio_fmt_arvalid(0),
      I1 => ARESETN,
      I2 => s_axi_lite_audio_fmt_rready(0),
      I3 => \^s_axi_lite_audio_fmt_rvalid\(0),
      O => \rvalid_i_1__1_n_0\
    );
rvalid_reg: unisim.vcomponents.FDRE
     port map (
      C => ACLK,
      CE => '1',
      D => \rvalid_i_1__1_n_0\,
      Q => \^s_axi_lite_audio_fmt_rvalid\(0),
      R => '0'
    );
\s_axi_lite_audio_fmt_arready[0]_INST_0\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"2"
    )
        port map (
      I0 => ARESETN,
      I1 => \^s_axi_lite_audio_fmt_rvalid\(0),
      O => s_axi_lite_audio_fmt_arready(0)
    );
\s_axi_lite_audio_fmt_awready[0]_INST_0\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"04"
    )
        port map (
      I0 => \^bvalid_reg_0\,
      I1 => ARESETN,
      I2 => aw_pending,
      O => s_axi_lite_audio_fmt_awready(0)
    );
\s_axi_lite_audio_fmt_wready[0]_INST_0\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"04"
    )
        port map (
      I0 => \^bvalid_reg_0\,
      I1 => ARESETN,
      I2 => w_pending_reg_n_0,
      O => s_axi_lite_audio_fmt_wready(0)
    );
\w_pending_i_1__1\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"20FF"
    )
        port map (
      I0 => w_pending_reg_n_0,
      I1 => \^bvalid_reg_0\,
      I2 => aw_pending,
      I3 => ARESETN,
      O => \w_pending_i_1__1_n_0\
    );
\w_pending_i_2__1\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"F2"
    )
        port map (
      I0 => s_axi_lite_audio_fmt_wvalid(0),
      I1 => \^bvalid_reg_0\,
      I2 => w_pending_reg_n_0,
      O => \w_pending_i_2__1_n_0\
    );
w_pending_reg: unisim.vcomponents.FDRE
     port map (
      C => ACLK,
      CE => '1',
      D => \w_pending_i_2__1_n_0\,
      Q => w_pending_reg_n_0,
      R => \w_pending_i_1__1_n_0\
    );
end STRUCTURE;
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
library UNISIM;
use UNISIM.VCOMPONENTS.ALL;
entity kv260_ispMipiRx_vcu_DP_audio_ss_0_0_aura_disabled_audio is
  port (
    bvalid_reg : out STD_LOGIC;
    bvalid_reg_0 : out STD_LOGIC;
    bvalid_reg_1 : out STD_LOGIC;
    s_axi_ctrl_i2s_rx_wready : out STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_ctrl_i2s_rx_awready : out STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_ctrl_i2s_rx_rvalid : out STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_ctrl_i2s_rx_arready : out STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_ctrl_i2s_tx_wready : out STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_ctrl_i2s_tx_awready : out STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_ctrl_i2s_tx_rvalid : out STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_ctrl_i2s_tx_arready : out STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_lite_audio_fmt_wready : out STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_lite_audio_fmt_awready : out STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_lite_audio_fmt_rvalid : out STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_lite_audio_fmt_arready : out STD_LOGIC_VECTOR ( 0 to 0 );
    ARESETN : in STD_LOGIC;
    s_axi_ctrl_i2s_rx_bready : in STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_ctrl_i2s_rx_arvalid : in STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_ctrl_i2s_rx_rready : in STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_ctrl_i2s_tx_bready : in STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_ctrl_i2s_tx_arvalid : in STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_ctrl_i2s_tx_rready : in STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_lite_audio_fmt_bready : in STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_lite_audio_fmt_arvalid : in STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_lite_audio_fmt_rready : in STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_ctrl_i2s_rx_wvalid : in STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_ctrl_i2s_rx_awvalid : in STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_ctrl_i2s_tx_wvalid : in STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_ctrl_i2s_tx_awvalid : in STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_lite_audio_fmt_wvalid : in STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_lite_audio_fmt_awvalid : in STD_LOGIC_VECTOR ( 0 to 0 );
    ACLK : in STD_LOGIC
  );
end kv260_ispMipiRx_vcu_DP_audio_ss_0_0_aura_disabled_audio;

architecture STRUCTURE of kv260_ispMipiRx_vcu_DP_audio_ss_0_0_aura_disabled_audio is
begin
s_axi_ctrl_i2s_rx_stub: entity work.kv260_ispMipiRx_vcu_DP_audio_ss_0_0_aura_audio_decerr
     port map (
      ACLK => ACLK,
      ARESETN => ARESETN,
      bvalid_reg_0 => bvalid_reg,
      s_axi_ctrl_i2s_rx_arready(0) => s_axi_ctrl_i2s_rx_arready(0),
      s_axi_ctrl_i2s_rx_arvalid(0) => s_axi_ctrl_i2s_rx_arvalid(0),
      s_axi_ctrl_i2s_rx_awready(0) => s_axi_ctrl_i2s_rx_awready(0),
      s_axi_ctrl_i2s_rx_awvalid(0) => s_axi_ctrl_i2s_rx_awvalid(0),
      s_axi_ctrl_i2s_rx_bready(0) => s_axi_ctrl_i2s_rx_bready(0),
      s_axi_ctrl_i2s_rx_rready(0) => s_axi_ctrl_i2s_rx_rready(0),
      s_axi_ctrl_i2s_rx_rvalid(0) => s_axi_ctrl_i2s_rx_rvalid(0),
      s_axi_ctrl_i2s_rx_wready(0) => s_axi_ctrl_i2s_rx_wready(0),
      s_axi_ctrl_i2s_rx_wvalid(0) => s_axi_ctrl_i2s_rx_wvalid(0)
    );
s_axi_ctrl_i2s_tx_stub: entity work.kv260_ispMipiRx_vcu_DP_audio_ss_0_0_aura_audio_decerr_0
     port map (
      ACLK => ACLK,
      ARESETN => ARESETN,
      bvalid_reg_0 => bvalid_reg_0,
      s_axi_ctrl_i2s_tx_arready(0) => s_axi_ctrl_i2s_tx_arready(0),
      s_axi_ctrl_i2s_tx_arvalid(0) => s_axi_ctrl_i2s_tx_arvalid(0),
      s_axi_ctrl_i2s_tx_awready(0) => s_axi_ctrl_i2s_tx_awready(0),
      s_axi_ctrl_i2s_tx_awvalid(0) => s_axi_ctrl_i2s_tx_awvalid(0),
      s_axi_ctrl_i2s_tx_bready(0) => s_axi_ctrl_i2s_tx_bready(0),
      s_axi_ctrl_i2s_tx_rready(0) => s_axi_ctrl_i2s_tx_rready(0),
      s_axi_ctrl_i2s_tx_rvalid(0) => s_axi_ctrl_i2s_tx_rvalid(0),
      s_axi_ctrl_i2s_tx_wready(0) => s_axi_ctrl_i2s_tx_wready(0),
      s_axi_ctrl_i2s_tx_wvalid(0) => s_axi_ctrl_i2s_tx_wvalid(0)
    );
s_axi_lite_audio_fmt_stub: entity work.kv260_ispMipiRx_vcu_DP_audio_ss_0_0_aura_audio_decerr_1
     port map (
      ACLK => ACLK,
      ARESETN => ARESETN,
      bvalid_reg_0 => bvalid_reg_1,
      s_axi_lite_audio_fmt_arready(0) => s_axi_lite_audio_fmt_arready(0),
      s_axi_lite_audio_fmt_arvalid(0) => s_axi_lite_audio_fmt_arvalid(0),
      s_axi_lite_audio_fmt_awready(0) => s_axi_lite_audio_fmt_awready(0),
      s_axi_lite_audio_fmt_awvalid(0) => s_axi_lite_audio_fmt_awvalid(0),
      s_axi_lite_audio_fmt_bready(0) => s_axi_lite_audio_fmt_bready(0),
      s_axi_lite_audio_fmt_rready(0) => s_axi_lite_audio_fmt_rready(0),
      s_axi_lite_audio_fmt_rvalid(0) => s_axi_lite_audio_fmt_rvalid(0),
      s_axi_lite_audio_fmt_wready(0) => s_axi_lite_audio_fmt_wready(0),
      s_axi_lite_audio_fmt_wvalid(0) => s_axi_lite_audio_fmt_wvalid(0)
    );
end STRUCTURE;
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
library UNISIM;
use UNISIM.VCOMPONENTS.ALL;
entity kv260_ispMipiRx_vcu_DP_audio_ss_0_0 is
  port (
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
  attribute NotValidForBitStream : boolean;
  attribute NotValidForBitStream of kv260_ispMipiRx_vcu_DP_audio_ss_0_0 : entity is true;
  attribute CHECK_LICENSE_TYPE : string;
  attribute CHECK_LICENSE_TYPE of kv260_ispMipiRx_vcu_DP_audio_ss_0_0 : entity is "kv260_ispMipiRx_vcu_DP_audio_ss_0_0,aura_disabled_audio,{}";
  attribute DowngradeIPIdentifiedWarnings : string;
  attribute DowngradeIPIdentifiedWarnings of kv260_ispMipiRx_vcu_DP_audio_ss_0_0 : entity is "yes";
  attribute IP_DEFINITION_SOURCE : string;
  attribute IP_DEFINITION_SOURCE of kv260_ispMipiRx_vcu_DP_audio_ss_0_0 : entity is "package_project";
  attribute X_CORE_INFO : string;
  attribute X_CORE_INFO of kv260_ispMipiRx_vcu_DP_audio_ss_0_0 : entity is "aura_disabled_audio,Vivado 2022.2";
end kv260_ispMipiRx_vcu_DP_audio_ss_0_0;

architecture STRUCTURE of kv260_ispMipiRx_vcu_DP_audio_ss_0_0 is
  signal \<const0>\ : STD_LOGIC;
  signal \<const1>\ : STD_LOGIC;
  attribute X_INTERFACE_INFO : string;
  attribute X_INTERFACE_INFO of ACLK : signal is "xilinx.com:signal:clock:1.0 ACLK CLK";
  attribute X_INTERFACE_PARAMETER : string;
  attribute X_INTERFACE_PARAMETER of ACLK : signal is "XIL_INTERFACENAME ACLK, ASSOCIATED_BUSIF s_axi_ctrl_i2s_rx:s_axi_ctrl_i2s_tx:s_axi_lite_audio_fmt, ASSOCIATED_RESET ARESETN, FREQ_HZ 99999000, FREQ_TOLERANCE_HZ 0, PHASE 0.0, CLK_DOMAIN kv260_ispMipiRx_vcu_DP_clk_wiz_0_0_clk_200M, INSERT_VIP 0";
  attribute X_INTERFACE_INFO of ARESETN : signal is "xilinx.com:signal:reset:1.0 ARESETN RST";
  attribute X_INTERFACE_PARAMETER of ARESETN : signal is "XIL_INTERFACENAME ARESETN, POLARITY ACTIVE_LOW, INSERT_VIP 0";
  attribute X_INTERFACE_INFO of m_axi_aclk : signal is "xilinx.com:signal:clock:1.0 m_axi_aclk CLK";
  attribute X_INTERFACE_PARAMETER of m_axi_aclk : signal is "XIL_INTERFACENAME m_axi_aclk, ASSOCIATED_RESET m_axi_aresetn, ASSOCIATED_BUSIF m_axi_mm2s_audio:m_axi_s2mm_audio, FREQ_HZ 299997000, FREQ_TOLERANCE_HZ 0, PHASE 0.0, CLK_DOMAIN kv260_ispMipiRx_vcu_DP_clk_wiz_0_0_clk_200M, INSERT_VIP 0";
  attribute X_INTERFACE_INFO of m_axi_aresetn : signal is "xilinx.com:signal:reset:1.0 m_axi_aresetn RST";
  attribute X_INTERFACE_PARAMETER of m_axi_aresetn : signal is "XIL_INTERFACENAME m_axi_aresetn, POLARITY ACTIVE_LOW, INSERT_VIP 0";
  attribute X_INTERFACE_INFO of m_axi_mm2s_audio_arready : signal is "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio ARREADY";
  attribute X_INTERFACE_INFO of m_axi_mm2s_audio_arvalid : signal is "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio ARVALID";
  attribute X_INTERFACE_INFO of m_axi_mm2s_audio_rlast : signal is "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio RLAST";
  attribute X_INTERFACE_INFO of m_axi_mm2s_audio_rready : signal is "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio RREADY";
  attribute X_INTERFACE_INFO of m_axi_mm2s_audio_rvalid : signal is "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio RVALID";
  attribute X_INTERFACE_PARAMETER of m_axi_mm2s_audio_rvalid : signal is "XIL_INTERFACENAME m_axi_mm2s_audio, PROTOCOL AXI4, READ_WRITE_MODE READ_ONLY, DATA_WIDTH 32, FREQ_HZ 299997000, ID_WIDTH 0, ADDR_WIDTH 64, AWUSER_WIDTH 0, ARUSER_WIDTH 4, WUSER_WIDTH 0, RUSER_WIDTH 0, BUSER_WIDTH 0, HAS_BURST 1, HAS_LOCK 1, HAS_PROT 1, HAS_CACHE 1, HAS_QOS 1, HAS_REGION 1, HAS_WSTRB 0, HAS_BRESP 0, HAS_RRESP 1, SUPPORTS_NARROW_BURST 1, NUM_READ_OUTSTANDING 2, NUM_WRITE_OUTSTANDING 2, MAX_BURST_LENGTH 256, PHASE 0.0, CLK_DOMAIN kv260_ispMipiRx_vcu_DP_clk_wiz_0_0_clk_200M, NUM_READ_THREADS 1, NUM_WRITE_THREADS 1, RUSER_BITS_PER_BYTE 0, WUSER_BITS_PER_BYTE 0, INSERT_VIP 0";
  attribute X_INTERFACE_INFO of m_axi_s2mm_audio_awready : signal is "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio AWREADY";
  attribute X_INTERFACE_INFO of m_axi_s2mm_audio_awvalid : signal is "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio AWVALID";
  attribute X_INTERFACE_INFO of m_axi_s2mm_audio_bready : signal is "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio BREADY";
  attribute X_INTERFACE_INFO of m_axi_s2mm_audio_bvalid : signal is "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio BVALID";
  attribute X_INTERFACE_INFO of m_axi_s2mm_audio_wlast : signal is "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio WLAST";
  attribute X_INTERFACE_INFO of m_axi_s2mm_audio_wready : signal is "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio WREADY";
  attribute X_INTERFACE_INFO of m_axi_s2mm_audio_wvalid : signal is "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio WVALID";
  attribute X_INTERFACE_PARAMETER of m_axi_s2mm_audio_wvalid : signal is "XIL_INTERFACENAME m_axi_s2mm_audio, PROTOCOL AXI4, READ_WRITE_MODE WRITE_ONLY, DATA_WIDTH 32, FREQ_HZ 299997000, ID_WIDTH 0, ADDR_WIDTH 64, AWUSER_WIDTH 4, ARUSER_WIDTH 0, WUSER_WIDTH 0, RUSER_WIDTH 0, BUSER_WIDTH 0, HAS_BURST 1, HAS_LOCK 1, HAS_PROT 1, HAS_CACHE 1, HAS_QOS 1, HAS_REGION 1, HAS_WSTRB 1, HAS_BRESP 1, HAS_RRESP 0, SUPPORTS_NARROW_BURST 1, NUM_READ_OUTSTANDING 2, NUM_WRITE_OUTSTANDING 2, MAX_BURST_LENGTH 256, PHASE 0.0, CLK_DOMAIN kv260_ispMipiRx_vcu_DP_clk_wiz_0_0_clk_200M, NUM_READ_THREADS 1, NUM_WRITE_THREADS 1, RUSER_BITS_PER_BYTE 0, WUSER_BITS_PER_BYTE 0, INSERT_VIP 0";
  attribute X_INTERFACE_INFO of m_axi_mm2s_audio_araddr : signal is "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio ARADDR";
  attribute X_INTERFACE_INFO of m_axi_mm2s_audio_arburst : signal is "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio ARBURST";
  attribute X_INTERFACE_INFO of m_axi_mm2s_audio_arcache : signal is "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio ARCACHE";
  attribute X_INTERFACE_INFO of m_axi_mm2s_audio_arlen : signal is "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio ARLEN";
  attribute X_INTERFACE_INFO of m_axi_mm2s_audio_arlock : signal is "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio ARLOCK";
  attribute X_INTERFACE_INFO of m_axi_mm2s_audio_arprot : signal is "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio ARPROT";
  attribute X_INTERFACE_INFO of m_axi_mm2s_audio_arqos : signal is "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio ARQOS";
  attribute X_INTERFACE_INFO of m_axi_mm2s_audio_arregion : signal is "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio ARREGION";
  attribute X_INTERFACE_INFO of m_axi_mm2s_audio_arsize : signal is "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio ARSIZE";
  attribute X_INTERFACE_INFO of m_axi_mm2s_audio_aruser : signal is "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio ARUSER";
  attribute X_INTERFACE_INFO of m_axi_mm2s_audio_rdata : signal is "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio RDATA";
  attribute X_INTERFACE_INFO of m_axi_mm2s_audio_rresp : signal is "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio RRESP";
  attribute X_INTERFACE_INFO of m_axi_s2mm_audio_awaddr : signal is "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio AWADDR";
  attribute X_INTERFACE_INFO of m_axi_s2mm_audio_awburst : signal is "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio AWBURST";
  attribute X_INTERFACE_INFO of m_axi_s2mm_audio_awcache : signal is "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio AWCACHE";
  attribute X_INTERFACE_INFO of m_axi_s2mm_audio_awlen : signal is "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio AWLEN";
  attribute X_INTERFACE_INFO of m_axi_s2mm_audio_awlock : signal is "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio AWLOCK";
  attribute X_INTERFACE_INFO of m_axi_s2mm_audio_awprot : signal is "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio AWPROT";
  attribute X_INTERFACE_INFO of m_axi_s2mm_audio_awqos : signal is "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio AWQOS";
  attribute X_INTERFACE_INFO of m_axi_s2mm_audio_awregion : signal is "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio AWREGION";
  attribute X_INTERFACE_INFO of m_axi_s2mm_audio_awsize : signal is "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio AWSIZE";
  attribute X_INTERFACE_INFO of m_axi_s2mm_audio_awuser : signal is "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio AWUSER";
  attribute X_INTERFACE_INFO of m_axi_s2mm_audio_bresp : signal is "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio BRESP";
  attribute X_INTERFACE_INFO of m_axi_s2mm_audio_wdata : signal is "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio WDATA";
  attribute X_INTERFACE_INFO of m_axi_s2mm_audio_wstrb : signal is "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio WSTRB";
  attribute X_INTERFACE_INFO of peripheral_aresetn : signal is "xilinx.com:signal:reset:1.0 peripheral_aresetn RST";
  attribute X_INTERFACE_PARAMETER of peripheral_aresetn : signal is "XIL_INTERFACENAME peripheral_aresetn, POLARITY ACTIVE_LOW, INSERT_VIP 0";
  attribute X_INTERFACE_INFO of s_axi_ctrl_i2s_rx_araddr : signal is "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx ARADDR";
  attribute X_INTERFACE_PARAMETER of s_axi_ctrl_i2s_rx_araddr : signal is "PROTOCOL AXI4LITE, READ_WRITE_MODE READ_WRITE";
  attribute X_INTERFACE_INFO of s_axi_ctrl_i2s_rx_arready : signal is "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx ARREADY";
  attribute X_INTERFACE_INFO of s_axi_ctrl_i2s_rx_arvalid : signal is "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx ARVALID";
  attribute X_INTERFACE_INFO of s_axi_ctrl_i2s_rx_awaddr : signal is "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx AWADDR";
  attribute X_INTERFACE_INFO of s_axi_ctrl_i2s_rx_awready : signal is "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx AWREADY";
  attribute X_INTERFACE_INFO of s_axi_ctrl_i2s_rx_awvalid : signal is "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx AWVALID";
  attribute X_INTERFACE_INFO of s_axi_ctrl_i2s_rx_bready : signal is "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx BREADY";
  attribute X_INTERFACE_INFO of s_axi_ctrl_i2s_rx_bresp : signal is "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx BRESP";
  attribute X_INTERFACE_INFO of s_axi_ctrl_i2s_rx_bvalid : signal is "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx BVALID";
  attribute X_INTERFACE_INFO of s_axi_ctrl_i2s_rx_rdata : signal is "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx RDATA";
  attribute X_INTERFACE_INFO of s_axi_ctrl_i2s_rx_rready : signal is "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx RREADY";
  attribute X_INTERFACE_INFO of s_axi_ctrl_i2s_rx_rresp : signal is "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx RRESP";
  attribute X_INTERFACE_INFO of s_axi_ctrl_i2s_rx_rvalid : signal is "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx RVALID";
  attribute X_INTERFACE_INFO of s_axi_ctrl_i2s_rx_wdata : signal is "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx WDATA";
  attribute X_INTERFACE_INFO of s_axi_ctrl_i2s_rx_wready : signal is "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx WREADY";
  attribute X_INTERFACE_INFO of s_axi_ctrl_i2s_rx_wvalid : signal is "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx WVALID";
  attribute X_INTERFACE_PARAMETER of s_axi_ctrl_i2s_rx_wvalid : signal is "XIL_INTERFACENAME s_axi_ctrl_i2s_rx, PROTOCOL AXI4LITE, READ_WRITE_MODE READ_WRITE, DATA_WIDTH 32, FREQ_HZ 99999000, ID_WIDTH 0, ADDR_WIDTH 40, AWUSER_WIDTH 0, ARUSER_WIDTH 0, WUSER_WIDTH 0, RUSER_WIDTH 0, BUSER_WIDTH 0, HAS_BURST 0, HAS_LOCK 0, HAS_PROT 0, HAS_CACHE 0, HAS_QOS 0, HAS_REGION 0, HAS_WSTRB 0, HAS_BRESP 1, HAS_RRESP 1, SUPPORTS_NARROW_BURST 0, NUM_READ_OUTSTANDING 1, NUM_WRITE_OUTSTANDING 1, MAX_BURST_LENGTH 1, PHASE 0.0, CLK_DOMAIN kv260_ispMipiRx_vcu_DP_clk_wiz_0_0_clk_200M, NUM_READ_THREADS 1, NUM_WRITE_THREADS 1, RUSER_BITS_PER_BYTE 0, WUSER_BITS_PER_BYTE 0, INSERT_VIP 0";
  attribute X_INTERFACE_INFO of s_axi_ctrl_i2s_tx_araddr : signal is "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx ARADDR";
  attribute X_INTERFACE_PARAMETER of s_axi_ctrl_i2s_tx_araddr : signal is "PROTOCOL AXI4LITE, READ_WRITE_MODE READ_WRITE";
  attribute X_INTERFACE_INFO of s_axi_ctrl_i2s_tx_arready : signal is "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx ARREADY";
  attribute X_INTERFACE_INFO of s_axi_ctrl_i2s_tx_arvalid : signal is "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx ARVALID";
  attribute X_INTERFACE_INFO of s_axi_ctrl_i2s_tx_awaddr : signal is "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx AWADDR";
  attribute X_INTERFACE_INFO of s_axi_ctrl_i2s_tx_awready : signal is "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx AWREADY";
  attribute X_INTERFACE_INFO of s_axi_ctrl_i2s_tx_awvalid : signal is "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx AWVALID";
  attribute X_INTERFACE_INFO of s_axi_ctrl_i2s_tx_bready : signal is "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx BREADY";
  attribute X_INTERFACE_INFO of s_axi_ctrl_i2s_tx_bresp : signal is "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx BRESP";
  attribute X_INTERFACE_INFO of s_axi_ctrl_i2s_tx_bvalid : signal is "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx BVALID";
  attribute X_INTERFACE_INFO of s_axi_ctrl_i2s_tx_rdata : signal is "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx RDATA";
  attribute X_INTERFACE_INFO of s_axi_ctrl_i2s_tx_rready : signal is "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx RREADY";
  attribute X_INTERFACE_INFO of s_axi_ctrl_i2s_tx_rresp : signal is "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx RRESP";
  attribute X_INTERFACE_INFO of s_axi_ctrl_i2s_tx_rvalid : signal is "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx RVALID";
  attribute X_INTERFACE_INFO of s_axi_ctrl_i2s_tx_wdata : signal is "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx WDATA";
  attribute X_INTERFACE_INFO of s_axi_ctrl_i2s_tx_wready : signal is "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx WREADY";
  attribute X_INTERFACE_INFO of s_axi_ctrl_i2s_tx_wvalid : signal is "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx WVALID";
  attribute X_INTERFACE_PARAMETER of s_axi_ctrl_i2s_tx_wvalid : signal is "XIL_INTERFACENAME s_axi_ctrl_i2s_tx, PROTOCOL AXI4LITE, READ_WRITE_MODE READ_WRITE, DATA_WIDTH 32, FREQ_HZ 99999000, ID_WIDTH 0, ADDR_WIDTH 40, AWUSER_WIDTH 0, ARUSER_WIDTH 0, WUSER_WIDTH 0, RUSER_WIDTH 0, BUSER_WIDTH 0, HAS_BURST 0, HAS_LOCK 0, HAS_PROT 0, HAS_CACHE 0, HAS_QOS 0, HAS_REGION 0, HAS_WSTRB 0, HAS_BRESP 1, HAS_RRESP 1, SUPPORTS_NARROW_BURST 0, NUM_READ_OUTSTANDING 1, NUM_WRITE_OUTSTANDING 1, MAX_BURST_LENGTH 1, PHASE 0.0, CLK_DOMAIN kv260_ispMipiRx_vcu_DP_clk_wiz_0_0_clk_200M, NUM_READ_THREADS 1, NUM_WRITE_THREADS 1, RUSER_BITS_PER_BYTE 0, WUSER_BITS_PER_BYTE 0, INSERT_VIP 0";
  attribute X_INTERFACE_INFO of s_axi_lite_audio_fmt_araddr : signal is "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt ARADDR";
  attribute X_INTERFACE_PARAMETER of s_axi_lite_audio_fmt_araddr : signal is "PROTOCOL AXI4LITE, READ_WRITE_MODE READ_WRITE";
  attribute X_INTERFACE_INFO of s_axi_lite_audio_fmt_arready : signal is "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt ARREADY";
  attribute X_INTERFACE_INFO of s_axi_lite_audio_fmt_arvalid : signal is "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt ARVALID";
  attribute X_INTERFACE_INFO of s_axi_lite_audio_fmt_awaddr : signal is "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt AWADDR";
  attribute X_INTERFACE_INFO of s_axi_lite_audio_fmt_awready : signal is "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt AWREADY";
  attribute X_INTERFACE_INFO of s_axi_lite_audio_fmt_awvalid : signal is "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt AWVALID";
  attribute X_INTERFACE_INFO of s_axi_lite_audio_fmt_bready : signal is "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt BREADY";
  attribute X_INTERFACE_INFO of s_axi_lite_audio_fmt_bresp : signal is "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt BRESP";
  attribute X_INTERFACE_INFO of s_axi_lite_audio_fmt_bvalid : signal is "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt BVALID";
  attribute X_INTERFACE_INFO of s_axi_lite_audio_fmt_rdata : signal is "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt RDATA";
  attribute X_INTERFACE_INFO of s_axi_lite_audio_fmt_rready : signal is "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt RREADY";
  attribute X_INTERFACE_INFO of s_axi_lite_audio_fmt_rresp : signal is "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt RRESP";
  attribute X_INTERFACE_INFO of s_axi_lite_audio_fmt_rvalid : signal is "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt RVALID";
  attribute X_INTERFACE_INFO of s_axi_lite_audio_fmt_wdata : signal is "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt WDATA";
  attribute X_INTERFACE_INFO of s_axi_lite_audio_fmt_wready : signal is "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt WREADY";
  attribute X_INTERFACE_INFO of s_axi_lite_audio_fmt_wvalid : signal is "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt WVALID";
  attribute X_INTERFACE_PARAMETER of s_axi_lite_audio_fmt_wvalid : signal is "XIL_INTERFACENAME s_axi_lite_audio_fmt, PROTOCOL AXI4LITE, READ_WRITE_MODE READ_WRITE, DATA_WIDTH 32, FREQ_HZ 99999000, ID_WIDTH 0, ADDR_WIDTH 40, AWUSER_WIDTH 0, ARUSER_WIDTH 0, WUSER_WIDTH 0, RUSER_WIDTH 0, BUSER_WIDTH 0, HAS_BURST 0, HAS_LOCK 0, HAS_PROT 0, HAS_CACHE 0, HAS_QOS 0, HAS_REGION 0, HAS_WSTRB 0, HAS_BRESP 1, HAS_RRESP 1, SUPPORTS_NARROW_BURST 0, NUM_READ_OUTSTANDING 1, NUM_WRITE_OUTSTANDING 1, MAX_BURST_LENGTH 1, PHASE 0.0, CLK_DOMAIN kv260_ispMipiRx_vcu_DP_clk_wiz_0_0_clk_200M, NUM_READ_THREADS 1, NUM_WRITE_THREADS 1, RUSER_BITS_PER_BYTE 0, WUSER_BITS_PER_BYTE 0, INSERT_VIP 0";
begin
  clk_out_audio <= \<const0>\;
  irq_i2s_rx <= \<const0>\;
  irq_i2s_tx <= \<const0>\;
  irq_mm2s_audio <= \<const0>\;
  irq_s2mm_audio <= \<const0>\;
  lrclk_rx <= \<const0>\;
  lrclk_tx <= \<const0>\;
  m_axi_mm2s_audio_araddr(63) <= \<const0>\;
  m_axi_mm2s_audio_araddr(62) <= \<const0>\;
  m_axi_mm2s_audio_araddr(61) <= \<const0>\;
  m_axi_mm2s_audio_araddr(60) <= \<const0>\;
  m_axi_mm2s_audio_araddr(59) <= \<const0>\;
  m_axi_mm2s_audio_araddr(58) <= \<const0>\;
  m_axi_mm2s_audio_araddr(57) <= \<const0>\;
  m_axi_mm2s_audio_araddr(56) <= \<const0>\;
  m_axi_mm2s_audio_araddr(55) <= \<const0>\;
  m_axi_mm2s_audio_araddr(54) <= \<const0>\;
  m_axi_mm2s_audio_araddr(53) <= \<const0>\;
  m_axi_mm2s_audio_araddr(52) <= \<const0>\;
  m_axi_mm2s_audio_araddr(51) <= \<const0>\;
  m_axi_mm2s_audio_araddr(50) <= \<const0>\;
  m_axi_mm2s_audio_araddr(49) <= \<const0>\;
  m_axi_mm2s_audio_araddr(48) <= \<const0>\;
  m_axi_mm2s_audio_araddr(47) <= \<const0>\;
  m_axi_mm2s_audio_araddr(46) <= \<const0>\;
  m_axi_mm2s_audio_araddr(45) <= \<const0>\;
  m_axi_mm2s_audio_araddr(44) <= \<const0>\;
  m_axi_mm2s_audio_araddr(43) <= \<const0>\;
  m_axi_mm2s_audio_araddr(42) <= \<const0>\;
  m_axi_mm2s_audio_araddr(41) <= \<const0>\;
  m_axi_mm2s_audio_araddr(40) <= \<const0>\;
  m_axi_mm2s_audio_araddr(39) <= \<const0>\;
  m_axi_mm2s_audio_araddr(38) <= \<const0>\;
  m_axi_mm2s_audio_araddr(37) <= \<const0>\;
  m_axi_mm2s_audio_araddr(36) <= \<const0>\;
  m_axi_mm2s_audio_araddr(35) <= \<const0>\;
  m_axi_mm2s_audio_araddr(34) <= \<const0>\;
  m_axi_mm2s_audio_araddr(33) <= \<const0>\;
  m_axi_mm2s_audio_araddr(32) <= \<const0>\;
  m_axi_mm2s_audio_araddr(31) <= \<const0>\;
  m_axi_mm2s_audio_araddr(30) <= \<const0>\;
  m_axi_mm2s_audio_araddr(29) <= \<const0>\;
  m_axi_mm2s_audio_araddr(28) <= \<const0>\;
  m_axi_mm2s_audio_araddr(27) <= \<const0>\;
  m_axi_mm2s_audio_araddr(26) <= \<const0>\;
  m_axi_mm2s_audio_araddr(25) <= \<const0>\;
  m_axi_mm2s_audio_araddr(24) <= \<const0>\;
  m_axi_mm2s_audio_araddr(23) <= \<const0>\;
  m_axi_mm2s_audio_araddr(22) <= \<const0>\;
  m_axi_mm2s_audio_araddr(21) <= \<const0>\;
  m_axi_mm2s_audio_araddr(20) <= \<const0>\;
  m_axi_mm2s_audio_araddr(19) <= \<const0>\;
  m_axi_mm2s_audio_araddr(18) <= \<const0>\;
  m_axi_mm2s_audio_araddr(17) <= \<const0>\;
  m_axi_mm2s_audio_araddr(16) <= \<const0>\;
  m_axi_mm2s_audio_araddr(15) <= \<const0>\;
  m_axi_mm2s_audio_araddr(14) <= \<const0>\;
  m_axi_mm2s_audio_araddr(13) <= \<const0>\;
  m_axi_mm2s_audio_araddr(12) <= \<const0>\;
  m_axi_mm2s_audio_araddr(11) <= \<const0>\;
  m_axi_mm2s_audio_araddr(10) <= \<const0>\;
  m_axi_mm2s_audio_araddr(9) <= \<const0>\;
  m_axi_mm2s_audio_araddr(8) <= \<const0>\;
  m_axi_mm2s_audio_araddr(7) <= \<const0>\;
  m_axi_mm2s_audio_araddr(6) <= \<const0>\;
  m_axi_mm2s_audio_araddr(5) <= \<const0>\;
  m_axi_mm2s_audio_araddr(4) <= \<const0>\;
  m_axi_mm2s_audio_araddr(3) <= \<const0>\;
  m_axi_mm2s_audio_araddr(2) <= \<const0>\;
  m_axi_mm2s_audio_araddr(1) <= \<const0>\;
  m_axi_mm2s_audio_araddr(0) <= \<const0>\;
  m_axi_mm2s_audio_arburst(1) <= \<const0>\;
  m_axi_mm2s_audio_arburst(0) <= \<const0>\;
  m_axi_mm2s_audio_arcache(3) <= \<const0>\;
  m_axi_mm2s_audio_arcache(2) <= \<const0>\;
  m_axi_mm2s_audio_arcache(1) <= \<const0>\;
  m_axi_mm2s_audio_arcache(0) <= \<const0>\;
  m_axi_mm2s_audio_arlen(7) <= \<const0>\;
  m_axi_mm2s_audio_arlen(6) <= \<const0>\;
  m_axi_mm2s_audio_arlen(5) <= \<const0>\;
  m_axi_mm2s_audio_arlen(4) <= \<const0>\;
  m_axi_mm2s_audio_arlen(3) <= \<const0>\;
  m_axi_mm2s_audio_arlen(2) <= \<const0>\;
  m_axi_mm2s_audio_arlen(1) <= \<const0>\;
  m_axi_mm2s_audio_arlen(0) <= \<const0>\;
  m_axi_mm2s_audio_arlock(0) <= \<const0>\;
  m_axi_mm2s_audio_arprot(2) <= \<const0>\;
  m_axi_mm2s_audio_arprot(1) <= \<const0>\;
  m_axi_mm2s_audio_arprot(0) <= \<const0>\;
  m_axi_mm2s_audio_arqos(3) <= \<const0>\;
  m_axi_mm2s_audio_arqos(2) <= \<const0>\;
  m_axi_mm2s_audio_arqos(1) <= \<const0>\;
  m_axi_mm2s_audio_arqos(0) <= \<const0>\;
  m_axi_mm2s_audio_arregion(3) <= \<const0>\;
  m_axi_mm2s_audio_arregion(2) <= \<const0>\;
  m_axi_mm2s_audio_arregion(1) <= \<const0>\;
  m_axi_mm2s_audio_arregion(0) <= \<const0>\;
  m_axi_mm2s_audio_arsize(2) <= \<const0>\;
  m_axi_mm2s_audio_arsize(1) <= \<const0>\;
  m_axi_mm2s_audio_arsize(0) <= \<const0>\;
  m_axi_mm2s_audio_aruser(3) <= \<const0>\;
  m_axi_mm2s_audio_aruser(2) <= \<const0>\;
  m_axi_mm2s_audio_aruser(1) <= \<const0>\;
  m_axi_mm2s_audio_aruser(0) <= \<const0>\;
  m_axi_mm2s_audio_arvalid <= \<const0>\;
  m_axi_mm2s_audio_rready <= \<const0>\;
  m_axi_s2mm_audio_awaddr(63) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(62) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(61) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(60) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(59) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(58) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(57) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(56) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(55) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(54) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(53) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(52) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(51) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(50) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(49) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(48) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(47) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(46) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(45) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(44) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(43) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(42) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(41) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(40) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(39) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(38) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(37) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(36) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(35) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(34) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(33) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(32) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(31) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(30) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(29) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(28) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(27) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(26) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(25) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(24) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(23) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(22) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(21) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(20) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(19) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(18) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(17) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(16) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(15) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(14) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(13) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(12) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(11) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(10) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(9) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(8) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(7) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(6) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(5) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(4) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(3) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(2) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(1) <= \<const0>\;
  m_axi_s2mm_audio_awaddr(0) <= \<const0>\;
  m_axi_s2mm_audio_awburst(1) <= \<const0>\;
  m_axi_s2mm_audio_awburst(0) <= \<const0>\;
  m_axi_s2mm_audio_awcache(3) <= \<const0>\;
  m_axi_s2mm_audio_awcache(2) <= \<const0>\;
  m_axi_s2mm_audio_awcache(1) <= \<const0>\;
  m_axi_s2mm_audio_awcache(0) <= \<const0>\;
  m_axi_s2mm_audio_awlen(7) <= \<const0>\;
  m_axi_s2mm_audio_awlen(6) <= \<const0>\;
  m_axi_s2mm_audio_awlen(5) <= \<const0>\;
  m_axi_s2mm_audio_awlen(4) <= \<const0>\;
  m_axi_s2mm_audio_awlen(3) <= \<const0>\;
  m_axi_s2mm_audio_awlen(2) <= \<const0>\;
  m_axi_s2mm_audio_awlen(1) <= \<const0>\;
  m_axi_s2mm_audio_awlen(0) <= \<const0>\;
  m_axi_s2mm_audio_awlock(0) <= \<const0>\;
  m_axi_s2mm_audio_awprot(2) <= \<const0>\;
  m_axi_s2mm_audio_awprot(1) <= \<const0>\;
  m_axi_s2mm_audio_awprot(0) <= \<const0>\;
  m_axi_s2mm_audio_awqos(3) <= \<const0>\;
  m_axi_s2mm_audio_awqos(2) <= \<const0>\;
  m_axi_s2mm_audio_awqos(1) <= \<const0>\;
  m_axi_s2mm_audio_awqos(0) <= \<const0>\;
  m_axi_s2mm_audio_awregion(3) <= \<const0>\;
  m_axi_s2mm_audio_awregion(2) <= \<const0>\;
  m_axi_s2mm_audio_awregion(1) <= \<const0>\;
  m_axi_s2mm_audio_awregion(0) <= \<const0>\;
  m_axi_s2mm_audio_awsize(2) <= \<const0>\;
  m_axi_s2mm_audio_awsize(1) <= \<const0>\;
  m_axi_s2mm_audio_awsize(0) <= \<const0>\;
  m_axi_s2mm_audio_awuser(3) <= \<const0>\;
  m_axi_s2mm_audio_awuser(2) <= \<const0>\;
  m_axi_s2mm_audio_awuser(1) <= \<const0>\;
  m_axi_s2mm_audio_awuser(0) <= \<const0>\;
  m_axi_s2mm_audio_awvalid <= \<const0>\;
  m_axi_s2mm_audio_bready <= \<const0>\;
  m_axi_s2mm_audio_wdata(31) <= \<const0>\;
  m_axi_s2mm_audio_wdata(30) <= \<const0>\;
  m_axi_s2mm_audio_wdata(29) <= \<const0>\;
  m_axi_s2mm_audio_wdata(28) <= \<const0>\;
  m_axi_s2mm_audio_wdata(27) <= \<const0>\;
  m_axi_s2mm_audio_wdata(26) <= \<const0>\;
  m_axi_s2mm_audio_wdata(25) <= \<const0>\;
  m_axi_s2mm_audio_wdata(24) <= \<const0>\;
  m_axi_s2mm_audio_wdata(23) <= \<const0>\;
  m_axi_s2mm_audio_wdata(22) <= \<const0>\;
  m_axi_s2mm_audio_wdata(21) <= \<const0>\;
  m_axi_s2mm_audio_wdata(20) <= \<const0>\;
  m_axi_s2mm_audio_wdata(19) <= \<const0>\;
  m_axi_s2mm_audio_wdata(18) <= \<const0>\;
  m_axi_s2mm_audio_wdata(17) <= \<const0>\;
  m_axi_s2mm_audio_wdata(16) <= \<const0>\;
  m_axi_s2mm_audio_wdata(15) <= \<const0>\;
  m_axi_s2mm_audio_wdata(14) <= \<const0>\;
  m_axi_s2mm_audio_wdata(13) <= \<const0>\;
  m_axi_s2mm_audio_wdata(12) <= \<const0>\;
  m_axi_s2mm_audio_wdata(11) <= \<const0>\;
  m_axi_s2mm_audio_wdata(10) <= \<const0>\;
  m_axi_s2mm_audio_wdata(9) <= \<const0>\;
  m_axi_s2mm_audio_wdata(8) <= \<const0>\;
  m_axi_s2mm_audio_wdata(7) <= \<const0>\;
  m_axi_s2mm_audio_wdata(6) <= \<const0>\;
  m_axi_s2mm_audio_wdata(5) <= \<const0>\;
  m_axi_s2mm_audio_wdata(4) <= \<const0>\;
  m_axi_s2mm_audio_wdata(3) <= \<const0>\;
  m_axi_s2mm_audio_wdata(2) <= \<const0>\;
  m_axi_s2mm_audio_wdata(1) <= \<const0>\;
  m_axi_s2mm_audio_wdata(0) <= \<const0>\;
  m_axi_s2mm_audio_wlast <= \<const0>\;
  m_axi_s2mm_audio_wstrb(3) <= \<const0>\;
  m_axi_s2mm_audio_wstrb(2) <= \<const0>\;
  m_axi_s2mm_audio_wstrb(1) <= \<const0>\;
  m_axi_s2mm_audio_wstrb(0) <= \<const0>\;
  m_axi_s2mm_audio_wvalid <= \<const0>\;
  mclk_out_rx <= \<const0>\;
  mclk_out_tx <= \<const0>\;
  peripheral_aresetn(0) <= \<const0>\;
  s_axi_ctrl_i2s_rx_bresp(1) <= \<const1>\;
  s_axi_ctrl_i2s_rx_bresp(0) <= \<const1>\;
  s_axi_ctrl_i2s_rx_rdata(31) <= \<const0>\;
  s_axi_ctrl_i2s_rx_rdata(30) <= \<const0>\;
  s_axi_ctrl_i2s_rx_rdata(29) <= \<const0>\;
  s_axi_ctrl_i2s_rx_rdata(28) <= \<const0>\;
  s_axi_ctrl_i2s_rx_rdata(27) <= \<const0>\;
  s_axi_ctrl_i2s_rx_rdata(26) <= \<const0>\;
  s_axi_ctrl_i2s_rx_rdata(25) <= \<const0>\;
  s_axi_ctrl_i2s_rx_rdata(24) <= \<const0>\;
  s_axi_ctrl_i2s_rx_rdata(23) <= \<const0>\;
  s_axi_ctrl_i2s_rx_rdata(22) <= \<const0>\;
  s_axi_ctrl_i2s_rx_rdata(21) <= \<const0>\;
  s_axi_ctrl_i2s_rx_rdata(20) <= \<const0>\;
  s_axi_ctrl_i2s_rx_rdata(19) <= \<const0>\;
  s_axi_ctrl_i2s_rx_rdata(18) <= \<const0>\;
  s_axi_ctrl_i2s_rx_rdata(17) <= \<const0>\;
  s_axi_ctrl_i2s_rx_rdata(16) <= \<const0>\;
  s_axi_ctrl_i2s_rx_rdata(15) <= \<const0>\;
  s_axi_ctrl_i2s_rx_rdata(14) <= \<const0>\;
  s_axi_ctrl_i2s_rx_rdata(13) <= \<const0>\;
  s_axi_ctrl_i2s_rx_rdata(12) <= \<const0>\;
  s_axi_ctrl_i2s_rx_rdata(11) <= \<const0>\;
  s_axi_ctrl_i2s_rx_rdata(10) <= \<const0>\;
  s_axi_ctrl_i2s_rx_rdata(9) <= \<const0>\;
  s_axi_ctrl_i2s_rx_rdata(8) <= \<const0>\;
  s_axi_ctrl_i2s_rx_rdata(7) <= \<const0>\;
  s_axi_ctrl_i2s_rx_rdata(6) <= \<const0>\;
  s_axi_ctrl_i2s_rx_rdata(5) <= \<const0>\;
  s_axi_ctrl_i2s_rx_rdata(4) <= \<const0>\;
  s_axi_ctrl_i2s_rx_rdata(3) <= \<const0>\;
  s_axi_ctrl_i2s_rx_rdata(2) <= \<const0>\;
  s_axi_ctrl_i2s_rx_rdata(1) <= \<const0>\;
  s_axi_ctrl_i2s_rx_rdata(0) <= \<const0>\;
  s_axi_ctrl_i2s_rx_rresp(1) <= \<const1>\;
  s_axi_ctrl_i2s_rx_rresp(0) <= \<const1>\;
  s_axi_ctrl_i2s_tx_bresp(1) <= \<const1>\;
  s_axi_ctrl_i2s_tx_bresp(0) <= \<const1>\;
  s_axi_ctrl_i2s_tx_rdata(31) <= \<const0>\;
  s_axi_ctrl_i2s_tx_rdata(30) <= \<const0>\;
  s_axi_ctrl_i2s_tx_rdata(29) <= \<const0>\;
  s_axi_ctrl_i2s_tx_rdata(28) <= \<const0>\;
  s_axi_ctrl_i2s_tx_rdata(27) <= \<const0>\;
  s_axi_ctrl_i2s_tx_rdata(26) <= \<const0>\;
  s_axi_ctrl_i2s_tx_rdata(25) <= \<const0>\;
  s_axi_ctrl_i2s_tx_rdata(24) <= \<const0>\;
  s_axi_ctrl_i2s_tx_rdata(23) <= \<const0>\;
  s_axi_ctrl_i2s_tx_rdata(22) <= \<const0>\;
  s_axi_ctrl_i2s_tx_rdata(21) <= \<const0>\;
  s_axi_ctrl_i2s_tx_rdata(20) <= \<const0>\;
  s_axi_ctrl_i2s_tx_rdata(19) <= \<const0>\;
  s_axi_ctrl_i2s_tx_rdata(18) <= \<const0>\;
  s_axi_ctrl_i2s_tx_rdata(17) <= \<const0>\;
  s_axi_ctrl_i2s_tx_rdata(16) <= \<const0>\;
  s_axi_ctrl_i2s_tx_rdata(15) <= \<const0>\;
  s_axi_ctrl_i2s_tx_rdata(14) <= \<const0>\;
  s_axi_ctrl_i2s_tx_rdata(13) <= \<const0>\;
  s_axi_ctrl_i2s_tx_rdata(12) <= \<const0>\;
  s_axi_ctrl_i2s_tx_rdata(11) <= \<const0>\;
  s_axi_ctrl_i2s_tx_rdata(10) <= \<const0>\;
  s_axi_ctrl_i2s_tx_rdata(9) <= \<const0>\;
  s_axi_ctrl_i2s_tx_rdata(8) <= \<const0>\;
  s_axi_ctrl_i2s_tx_rdata(7) <= \<const0>\;
  s_axi_ctrl_i2s_tx_rdata(6) <= \<const0>\;
  s_axi_ctrl_i2s_tx_rdata(5) <= \<const0>\;
  s_axi_ctrl_i2s_tx_rdata(4) <= \<const0>\;
  s_axi_ctrl_i2s_tx_rdata(3) <= \<const0>\;
  s_axi_ctrl_i2s_tx_rdata(2) <= \<const0>\;
  s_axi_ctrl_i2s_tx_rdata(1) <= \<const0>\;
  s_axi_ctrl_i2s_tx_rdata(0) <= \<const0>\;
  s_axi_ctrl_i2s_tx_rresp(1) <= \<const1>\;
  s_axi_ctrl_i2s_tx_rresp(0) <= \<const1>\;
  s_axi_lite_audio_fmt_bresp(1) <= \<const1>\;
  s_axi_lite_audio_fmt_bresp(0) <= \<const1>\;
  s_axi_lite_audio_fmt_rdata(31) <= \<const0>\;
  s_axi_lite_audio_fmt_rdata(30) <= \<const0>\;
  s_axi_lite_audio_fmt_rdata(29) <= \<const0>\;
  s_axi_lite_audio_fmt_rdata(28) <= \<const0>\;
  s_axi_lite_audio_fmt_rdata(27) <= \<const0>\;
  s_axi_lite_audio_fmt_rdata(26) <= \<const0>\;
  s_axi_lite_audio_fmt_rdata(25) <= \<const0>\;
  s_axi_lite_audio_fmt_rdata(24) <= \<const0>\;
  s_axi_lite_audio_fmt_rdata(23) <= \<const0>\;
  s_axi_lite_audio_fmt_rdata(22) <= \<const0>\;
  s_axi_lite_audio_fmt_rdata(21) <= \<const0>\;
  s_axi_lite_audio_fmt_rdata(20) <= \<const0>\;
  s_axi_lite_audio_fmt_rdata(19) <= \<const0>\;
  s_axi_lite_audio_fmt_rdata(18) <= \<const0>\;
  s_axi_lite_audio_fmt_rdata(17) <= \<const0>\;
  s_axi_lite_audio_fmt_rdata(16) <= \<const0>\;
  s_axi_lite_audio_fmt_rdata(15) <= \<const0>\;
  s_axi_lite_audio_fmt_rdata(14) <= \<const0>\;
  s_axi_lite_audio_fmt_rdata(13) <= \<const0>\;
  s_axi_lite_audio_fmt_rdata(12) <= \<const0>\;
  s_axi_lite_audio_fmt_rdata(11) <= \<const0>\;
  s_axi_lite_audio_fmt_rdata(10) <= \<const0>\;
  s_axi_lite_audio_fmt_rdata(9) <= \<const0>\;
  s_axi_lite_audio_fmt_rdata(8) <= \<const0>\;
  s_axi_lite_audio_fmt_rdata(7) <= \<const0>\;
  s_axi_lite_audio_fmt_rdata(6) <= \<const0>\;
  s_axi_lite_audio_fmt_rdata(5) <= \<const0>\;
  s_axi_lite_audio_fmt_rdata(4) <= \<const0>\;
  s_axi_lite_audio_fmt_rdata(3) <= \<const0>\;
  s_axi_lite_audio_fmt_rdata(2) <= \<const0>\;
  s_axi_lite_audio_fmt_rdata(1) <= \<const0>\;
  s_axi_lite_audio_fmt_rdata(0) <= \<const0>\;
  s_axi_lite_audio_fmt_rresp(1) <= \<const1>\;
  s_axi_lite_audio_fmt_rresp(0) <= \<const1>\;
  sclk_rx <= \<const0>\;
  sclk_tx <= \<const0>\;
  sdata_tx <= \<const0>\;
GND: unisim.vcomponents.GND
     port map (
      G => \<const0>\
    );
VCC: unisim.vcomponents.VCC
     port map (
      P => \<const1>\
    );
inst: entity work.kv260_ispMipiRx_vcu_DP_audio_ss_0_0_aura_disabled_audio
     port map (
      ACLK => ACLK,
      ARESETN => ARESETN,
      bvalid_reg => s_axi_ctrl_i2s_rx_bvalid(0),
      bvalid_reg_0 => s_axi_ctrl_i2s_tx_bvalid(0),
      bvalid_reg_1 => s_axi_lite_audio_fmt_bvalid(0),
      s_axi_ctrl_i2s_rx_arready(0) => s_axi_ctrl_i2s_rx_arready(0),
      s_axi_ctrl_i2s_rx_arvalid(0) => s_axi_ctrl_i2s_rx_arvalid(0),
      s_axi_ctrl_i2s_rx_awready(0) => s_axi_ctrl_i2s_rx_awready(0),
      s_axi_ctrl_i2s_rx_awvalid(0) => s_axi_ctrl_i2s_rx_awvalid(0),
      s_axi_ctrl_i2s_rx_bready(0) => s_axi_ctrl_i2s_rx_bready(0),
      s_axi_ctrl_i2s_rx_rready(0) => s_axi_ctrl_i2s_rx_rready(0),
      s_axi_ctrl_i2s_rx_rvalid(0) => s_axi_ctrl_i2s_rx_rvalid(0),
      s_axi_ctrl_i2s_rx_wready(0) => s_axi_ctrl_i2s_rx_wready(0),
      s_axi_ctrl_i2s_rx_wvalid(0) => s_axi_ctrl_i2s_rx_wvalid(0),
      s_axi_ctrl_i2s_tx_arready(0) => s_axi_ctrl_i2s_tx_arready(0),
      s_axi_ctrl_i2s_tx_arvalid(0) => s_axi_ctrl_i2s_tx_arvalid(0),
      s_axi_ctrl_i2s_tx_awready(0) => s_axi_ctrl_i2s_tx_awready(0),
      s_axi_ctrl_i2s_tx_awvalid(0) => s_axi_ctrl_i2s_tx_awvalid(0),
      s_axi_ctrl_i2s_tx_bready(0) => s_axi_ctrl_i2s_tx_bready(0),
      s_axi_ctrl_i2s_tx_rready(0) => s_axi_ctrl_i2s_tx_rready(0),
      s_axi_ctrl_i2s_tx_rvalid(0) => s_axi_ctrl_i2s_tx_rvalid(0),
      s_axi_ctrl_i2s_tx_wready(0) => s_axi_ctrl_i2s_tx_wready(0),
      s_axi_ctrl_i2s_tx_wvalid(0) => s_axi_ctrl_i2s_tx_wvalid(0),
      s_axi_lite_audio_fmt_arready(0) => s_axi_lite_audio_fmt_arready(0),
      s_axi_lite_audio_fmt_arvalid(0) => s_axi_lite_audio_fmt_arvalid(0),
      s_axi_lite_audio_fmt_awready(0) => s_axi_lite_audio_fmt_awready(0),
      s_axi_lite_audio_fmt_awvalid(0) => s_axi_lite_audio_fmt_awvalid(0),
      s_axi_lite_audio_fmt_bready(0) => s_axi_lite_audio_fmt_bready(0),
      s_axi_lite_audio_fmt_rready(0) => s_axi_lite_audio_fmt_rready(0),
      s_axi_lite_audio_fmt_rvalid(0) => s_axi_lite_audio_fmt_rvalid(0),
      s_axi_lite_audio_fmt_wready(0) => s_axi_lite_audio_fmt_wready(0),
      s_axi_lite_audio_fmt_wvalid(0) => s_axi_lite_audio_fmt_wvalid(0)
    );
end STRUCTURE;
