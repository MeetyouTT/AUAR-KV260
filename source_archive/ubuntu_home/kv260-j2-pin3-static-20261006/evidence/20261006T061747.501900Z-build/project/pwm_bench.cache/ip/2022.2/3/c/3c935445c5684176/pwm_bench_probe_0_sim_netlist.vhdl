-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- --------------------------------------------------------------------------------
-- Tool Version: Vivado v.2022.2 (lin64) Build 3671981 Fri Oct 14 04:59:54 MDT 2022
-- Date        : Mon Oct  5 23:20:36 2026
-- Host        : ghmd-MRA-XXX running 64-bit Ubuntu 20.04.4 LTS
-- Command     : write_vhdl -force -mode funcsim -rename_top decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix -prefix
--               decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_ pwm_bench_probe_0_sim_netlist.vhdl
-- Design      : pwm_bench_probe_0
-- Purpose     : This VHDL netlist is a functional simulation representation of the design and should not be modified or
--               synthesized. This netlist cannot be used for SDF annotated simulation.
-- Device      : xck26-sfvc784-2LV-c
-- --------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
library UNISIM;
use UNISIM.VCOMPONENTS.ALL;
entity decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_pwm_burst is
  port (
    servo_pwm : out STD_LOGIC;
    \aw_address_reg[10]\ : out STD_LOGIC;
    D : out STD_LOGIC_VECTOR ( 1 downto 0 );
    \aw_address_reg[5]\ : out STD_LOGIC;
    s_axi_aclk : in STD_LOGIC;
    s_axi_aresetn : in STD_LOGIC;
    s_axi_araddr : in STD_LOGIC_VECTOR ( 5 downto 0 );
    Q : in STD_LOGIC_VECTOR ( 1 downto 0 );
    \s_axi_bresp[1]_i_4_0\ : in STD_LOGIC_VECTOR ( 31 downto 0 );
    aw_pending : in STD_LOGIC;
    \s_axi_bresp[1]_i_4_1\ : in STD_LOGIC;
    \s_axi_bresp[1]_i_4_2\ : in STD_LOGIC;
    \scratch[31]_i_2\ : in STD_LOGIC_VECTOR ( 11 downto 0 );
    \s_axi_bresp[1]_i_14_0\ : in STD_LOGIC_VECTOR ( 3 downto 0 );
    \s_axi_rdata_reg[1]\ : in STD_LOGIC;
    \s_axi_rdata_reg[0]\ : in STD_LOGIC;
    \s_axi_bresp_reg[1]\ : in STD_LOGIC;
    p_5_in : in STD_LOGIC;
    s_axi_bresp : in STD_LOGIC_VECTOR ( 0 to 0 )
  );
end decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_pwm_burst;

architecture STRUCTURE of decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_pwm_burst is
  signal \^aw_address_reg[10]\ : STD_LOGIC;
  signal busy : STD_LOGIC;
  signal busy_i_1_n_0 : STD_LOGIC;
  signal \phase[0]_i_10_n_0\ : STD_LOGIC;
  signal \phase[0]_i_11_n_0\ : STD_LOGIC;
  signal \phase[0]_i_1_n_0\ : STD_LOGIC;
  signal \phase[0]_i_3_n_0\ : STD_LOGIC;
  signal \phase[0]_i_4_n_0\ : STD_LOGIC;
  signal \phase[0]_i_5_n_0\ : STD_LOGIC;
  signal \phase[0]_i_6_n_0\ : STD_LOGIC;
  signal \phase[0]_i_7_n_0\ : STD_LOGIC;
  signal \phase[0]_i_8_n_0\ : STD_LOGIC;
  signal \phase[0]_i_9_n_0\ : STD_LOGIC;
  signal phase_reg : STD_LOGIC_VECTOR ( 31 downto 0 );
  signal \phase_reg[0]_i_2_n_0\ : STD_LOGIC;
  signal \phase_reg[0]_i_2_n_1\ : STD_LOGIC;
  signal \phase_reg[0]_i_2_n_10\ : STD_LOGIC;
  signal \phase_reg[0]_i_2_n_11\ : STD_LOGIC;
  signal \phase_reg[0]_i_2_n_12\ : STD_LOGIC;
  signal \phase_reg[0]_i_2_n_13\ : STD_LOGIC;
  signal \phase_reg[0]_i_2_n_14\ : STD_LOGIC;
  signal \phase_reg[0]_i_2_n_15\ : STD_LOGIC;
  signal \phase_reg[0]_i_2_n_2\ : STD_LOGIC;
  signal \phase_reg[0]_i_2_n_3\ : STD_LOGIC;
  signal \phase_reg[0]_i_2_n_4\ : STD_LOGIC;
  signal \phase_reg[0]_i_2_n_5\ : STD_LOGIC;
  signal \phase_reg[0]_i_2_n_6\ : STD_LOGIC;
  signal \phase_reg[0]_i_2_n_7\ : STD_LOGIC;
  signal \phase_reg[0]_i_2_n_8\ : STD_LOGIC;
  signal \phase_reg[0]_i_2_n_9\ : STD_LOGIC;
  signal \phase_reg[16]_i_1_n_0\ : STD_LOGIC;
  signal \phase_reg[16]_i_1_n_1\ : STD_LOGIC;
  signal \phase_reg[16]_i_1_n_10\ : STD_LOGIC;
  signal \phase_reg[16]_i_1_n_11\ : STD_LOGIC;
  signal \phase_reg[16]_i_1_n_12\ : STD_LOGIC;
  signal \phase_reg[16]_i_1_n_13\ : STD_LOGIC;
  signal \phase_reg[16]_i_1_n_14\ : STD_LOGIC;
  signal \phase_reg[16]_i_1_n_15\ : STD_LOGIC;
  signal \phase_reg[16]_i_1_n_2\ : STD_LOGIC;
  signal \phase_reg[16]_i_1_n_3\ : STD_LOGIC;
  signal \phase_reg[16]_i_1_n_4\ : STD_LOGIC;
  signal \phase_reg[16]_i_1_n_5\ : STD_LOGIC;
  signal \phase_reg[16]_i_1_n_6\ : STD_LOGIC;
  signal \phase_reg[16]_i_1_n_7\ : STD_LOGIC;
  signal \phase_reg[16]_i_1_n_8\ : STD_LOGIC;
  signal \phase_reg[16]_i_1_n_9\ : STD_LOGIC;
  signal \phase_reg[24]_i_1_n_1\ : STD_LOGIC;
  signal \phase_reg[24]_i_1_n_10\ : STD_LOGIC;
  signal \phase_reg[24]_i_1_n_11\ : STD_LOGIC;
  signal \phase_reg[24]_i_1_n_12\ : STD_LOGIC;
  signal \phase_reg[24]_i_1_n_13\ : STD_LOGIC;
  signal \phase_reg[24]_i_1_n_14\ : STD_LOGIC;
  signal \phase_reg[24]_i_1_n_15\ : STD_LOGIC;
  signal \phase_reg[24]_i_1_n_2\ : STD_LOGIC;
  signal \phase_reg[24]_i_1_n_3\ : STD_LOGIC;
  signal \phase_reg[24]_i_1_n_4\ : STD_LOGIC;
  signal \phase_reg[24]_i_1_n_5\ : STD_LOGIC;
  signal \phase_reg[24]_i_1_n_6\ : STD_LOGIC;
  signal \phase_reg[24]_i_1_n_7\ : STD_LOGIC;
  signal \phase_reg[24]_i_1_n_8\ : STD_LOGIC;
  signal \phase_reg[24]_i_1_n_9\ : STD_LOGIC;
  signal \phase_reg[8]_i_1_n_0\ : STD_LOGIC;
  signal \phase_reg[8]_i_1_n_1\ : STD_LOGIC;
  signal \phase_reg[8]_i_1_n_10\ : STD_LOGIC;
  signal \phase_reg[8]_i_1_n_11\ : STD_LOGIC;
  signal \phase_reg[8]_i_1_n_12\ : STD_LOGIC;
  signal \phase_reg[8]_i_1_n_13\ : STD_LOGIC;
  signal \phase_reg[8]_i_1_n_14\ : STD_LOGIC;
  signal \phase_reg[8]_i_1_n_15\ : STD_LOGIC;
  signal \phase_reg[8]_i_1_n_2\ : STD_LOGIC;
  signal \phase_reg[8]_i_1_n_3\ : STD_LOGIC;
  signal \phase_reg[8]_i_1_n_4\ : STD_LOGIC;
  signal \phase_reg[8]_i_1_n_5\ : STD_LOGIC;
  signal \phase_reg[8]_i_1_n_6\ : STD_LOGIC;
  signal \phase_reg[8]_i_1_n_7\ : STD_LOGIC;
  signal \phase_reg[8]_i_1_n_8\ : STD_LOGIC;
  signal \phase_reg[8]_i_1_n_9\ : STD_LOGIC;
  signal pwm1 : STD_LOGIC_VECTOR ( 32 downto 2 );
  signal pwm_i_10_n_0 : STD_LOGIC;
  signal pwm_i_11_n_0 : STD_LOGIC;
  signal pwm_i_13_n_0 : STD_LOGIC;
  signal pwm_i_15_n_0 : STD_LOGIC;
  signal pwm_i_16_n_0 : STD_LOGIC;
  signal pwm_i_1_n_0 : STD_LOGIC;
  signal pwm_i_2_n_0 : STD_LOGIC;
  signal pwm_i_3_n_0 : STD_LOGIC;
  signal pwm_i_4_n_0 : STD_LOGIC;
  signal pwm_i_6_n_0 : STD_LOGIC;
  signal pwm_i_7_n_0 : STD_LOGIC;
  signal pwm_i_8_n_0 : STD_LOGIC;
  signal pwm_reg_i_12_n_2 : STD_LOGIC;
  signal pwm_reg_i_12_n_3 : STD_LOGIC;
  signal pwm_reg_i_12_n_4 : STD_LOGIC;
  signal pwm_reg_i_12_n_5 : STD_LOGIC;
  signal pwm_reg_i_12_n_6 : STD_LOGIC;
  signal pwm_reg_i_12_n_7 : STD_LOGIC;
  signal pwm_reg_i_14_n_0 : STD_LOGIC;
  signal pwm_reg_i_14_n_1 : STD_LOGIC;
  signal pwm_reg_i_14_n_2 : STD_LOGIC;
  signal pwm_reg_i_14_n_3 : STD_LOGIC;
  signal pwm_reg_i_14_n_4 : STD_LOGIC;
  signal pwm_reg_i_14_n_5 : STD_LOGIC;
  signal pwm_reg_i_14_n_6 : STD_LOGIC;
  signal pwm_reg_i_14_n_7 : STD_LOGIC;
  signal pwm_reg_i_5_n_0 : STD_LOGIC;
  signal pwm_reg_i_5_n_1 : STD_LOGIC;
  signal pwm_reg_i_5_n_2 : STD_LOGIC;
  signal pwm_reg_i_5_n_3 : STD_LOGIC;
  signal pwm_reg_i_5_n_4 : STD_LOGIC;
  signal pwm_reg_i_5_n_5 : STD_LOGIC;
  signal pwm_reg_i_5_n_6 : STD_LOGIC;
  signal pwm_reg_i_5_n_7 : STD_LOGIC;
  signal pwm_reg_i_9_n_0 : STD_LOGIC;
  signal pwm_reg_i_9_n_1 : STD_LOGIC;
  signal pwm_reg_i_9_n_2 : STD_LOGIC;
  signal pwm_reg_i_9_n_3 : STD_LOGIC;
  signal pwm_reg_i_9_n_4 : STD_LOGIC;
  signal pwm_reg_i_9_n_5 : STD_LOGIC;
  signal pwm_reg_i_9_n_6 : STD_LOGIC;
  signal pwm_reg_i_9_n_7 : STD_LOGIC;
  signal \s_axi_bresp[1]_i_10_n_0\ : STD_LOGIC;
  signal \s_axi_bresp[1]_i_11_n_0\ : STD_LOGIC;
  signal \s_axi_bresp[1]_i_14_n_0\ : STD_LOGIC;
  signal \s_axi_bresp[1]_i_15_n_0\ : STD_LOGIC;
  signal \s_axi_bresp[1]_i_16_n_0\ : STD_LOGIC;
  signal \s_axi_bresp[1]_i_17_n_0\ : STD_LOGIC;
  signal \s_axi_bresp[1]_i_18_n_0\ : STD_LOGIC;
  signal \s_axi_bresp[1]_i_19_n_0\ : STD_LOGIC;
  signal \s_axi_bresp[1]_i_20_n_0\ : STD_LOGIC;
  signal \s_axi_bresp[1]_i_3_n_0\ : STD_LOGIC;
  signal \s_axi_bresp[1]_i_7_n_0\ : STD_LOGIC;
  signal \s_axi_bresp[1]_i_8_n_0\ : STD_LOGIC;
  signal \s_axi_bresp[1]_i_9_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[0]_i_2_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[1]_i_3_n_0\ : STD_LOGIC;
  signal \^servo_pwm\ : STD_LOGIC;
  signal start : STD_LOGIC;
  signal \NLW_phase_reg[24]_i_1_CO_UNCONNECTED\ : STD_LOGIC_VECTOR ( 7 to 7 );
  signal NLW_pwm_reg_i_12_CO_UNCONNECTED : STD_LOGIC_VECTOR ( 6 to 6 );
  signal NLW_pwm_reg_i_12_O_UNCONNECTED : STD_LOGIC_VECTOR ( 7 to 7 );
  signal NLW_pwm_reg_i_14_O_UNCONNECTED : STD_LOGIC_VECTOR ( 0 to 0 );
  attribute ADDER_THRESHOLD : integer;
  attribute ADDER_THRESHOLD of \phase_reg[0]_i_2\ : label is 16;
  attribute ADDER_THRESHOLD of \phase_reg[16]_i_1\ : label is 16;
  attribute ADDER_THRESHOLD of \phase_reg[24]_i_1\ : label is 16;
  attribute ADDER_THRESHOLD of \phase_reg[8]_i_1\ : label is 16;
  attribute SOFT_HLUTNM : string;
  attribute SOFT_HLUTNM of \s_axi_bresp[1]_i_3\ : label is "soft_lutpair0";
  attribute SOFT_HLUTNM of \s_axi_bresp[1]_i_4\ : label is "soft_lutpair0";
begin
  \aw_address_reg[10]\ <= \^aw_address_reg[10]\;
  servo_pwm <= \^servo_pwm\;
busy_i_1: unisim.vcomponents.LUT2
    generic map(
      INIT => X"E"
    )
        port map (
      I0 => start,
      I1 => busy,
      O => busy_i_1_n_0
    );
busy_reg: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => '1',
      D => busy_i_1_n_0,
      Q => busy,
      R => pwm_i_1_n_0
    );
\phase[0]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FFFF0004FFFFFFFF"
    )
        port map (
      I0 => \phase[0]_i_3_n_0\,
      I1 => \phase[0]_i_4_n_0\,
      I2 => \phase[0]_i_5_n_0\,
      I3 => \phase[0]_i_6_n_0\,
      I4 => pwm_i_1_n_0,
      I5 => busy,
      O => \phase[0]_i_1_n_0\
    );
\phase[0]_i_10\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"FFEF"
    )
        port map (
      I0 => phase_reg(2),
      I1 => phase_reg(6),
      I2 => phase_reg(10),
      I3 => phase_reg(16),
      O => \phase[0]_i_10_n_0\
    );
\phase[0]_i_11\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"DFFF"
    )
        port map (
      I0 => phase_reg(3),
      I1 => phase_reg(14),
      I2 => phase_reg(19),
      I3 => phase_reg(15),
      O => \phase[0]_i_11_n_0\
    );
\phase[0]_i_3\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FFFFFEFF"
    )
        port map (
      I0 => phase_reg(21),
      I1 => phase_reg(27),
      I2 => phase_reg(28),
      I3 => phase_reg(9),
      I4 => \phase[0]_i_8_n_0\,
      O => \phase[0]_i_3_n_0\
    );
\phase[0]_i_4\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"00000001"
    )
        port map (
      I0 => phase_reg(24),
      I1 => phase_reg(29),
      I2 => phase_reg(5),
      I3 => phase_reg(30),
      I4 => \phase[0]_i_9_n_0\,
      O => \phase[0]_i_4_n_0\
    );
\phase[0]_i_5\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FFFFFBFF"
    )
        port map (
      I0 => phase_reg(7),
      I1 => phase_reg(12),
      I2 => phase_reg(17),
      I3 => phase_reg(0),
      I4 => \phase[0]_i_10_n_0\,
      O => \phase[0]_i_5_n_0\
    );
\phase[0]_i_6\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FFFFFEFF"
    )
        port map (
      I0 => phase_reg(22),
      I1 => phase_reg(25),
      I2 => phase_reg(31),
      I3 => phase_reg(1),
      I4 => \phase[0]_i_11_n_0\,
      O => \phase[0]_i_6_n_0\
    );
\phase[0]_i_7\: unisim.vcomponents.LUT1
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => phase_reg(0),
      O => \phase[0]_i_7_n_0\
    );
\phase[0]_i_8\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"FFFE"
    )
        port map (
      I0 => phase_reg(26),
      I1 => phase_reg(13),
      I2 => phase_reg(8),
      I3 => phase_reg(18),
      O => \phase[0]_i_8_n_0\
    );
\phase[0]_i_9\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"DFFF"
    )
        port map (
      I0 => phase_reg(23),
      I1 => phase_reg(11),
      I2 => phase_reg(20),
      I3 => phase_reg(4),
      O => \phase[0]_i_9_n_0\
    );
\phase_reg[0]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => '1',
      D => \phase_reg[0]_i_2_n_15\,
      Q => phase_reg(0),
      R => \phase[0]_i_1_n_0\
    );
\phase_reg[0]_i_2\: unisim.vcomponents.CARRY8
     port map (
      CI => '0',
      CI_TOP => '0',
      CO(7) => \phase_reg[0]_i_2_n_0\,
      CO(6) => \phase_reg[0]_i_2_n_1\,
      CO(5) => \phase_reg[0]_i_2_n_2\,
      CO(4) => \phase_reg[0]_i_2_n_3\,
      CO(3) => \phase_reg[0]_i_2_n_4\,
      CO(2) => \phase_reg[0]_i_2_n_5\,
      CO(1) => \phase_reg[0]_i_2_n_6\,
      CO(0) => \phase_reg[0]_i_2_n_7\,
      DI(7 downto 0) => B"00000001",
      O(7) => \phase_reg[0]_i_2_n_8\,
      O(6) => \phase_reg[0]_i_2_n_9\,
      O(5) => \phase_reg[0]_i_2_n_10\,
      O(4) => \phase_reg[0]_i_2_n_11\,
      O(3) => \phase_reg[0]_i_2_n_12\,
      O(2) => \phase_reg[0]_i_2_n_13\,
      O(1) => \phase_reg[0]_i_2_n_14\,
      O(0) => \phase_reg[0]_i_2_n_15\,
      S(7 downto 1) => phase_reg(7 downto 1),
      S(0) => \phase[0]_i_7_n_0\
    );
\phase_reg[10]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => '1',
      D => \phase_reg[8]_i_1_n_13\,
      Q => phase_reg(10),
      R => \phase[0]_i_1_n_0\
    );
\phase_reg[11]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => '1',
      D => \phase_reg[8]_i_1_n_12\,
      Q => phase_reg(11),
      R => \phase[0]_i_1_n_0\
    );
\phase_reg[12]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => '1',
      D => \phase_reg[8]_i_1_n_11\,
      Q => phase_reg(12),
      R => \phase[0]_i_1_n_0\
    );
\phase_reg[13]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => '1',
      D => \phase_reg[8]_i_1_n_10\,
      Q => phase_reg(13),
      R => \phase[0]_i_1_n_0\
    );
\phase_reg[14]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => '1',
      D => \phase_reg[8]_i_1_n_9\,
      Q => phase_reg(14),
      R => \phase[0]_i_1_n_0\
    );
\phase_reg[15]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => '1',
      D => \phase_reg[8]_i_1_n_8\,
      Q => phase_reg(15),
      R => \phase[0]_i_1_n_0\
    );
\phase_reg[16]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => '1',
      D => \phase_reg[16]_i_1_n_15\,
      Q => phase_reg(16),
      R => \phase[0]_i_1_n_0\
    );
\phase_reg[16]_i_1\: unisim.vcomponents.CARRY8
     port map (
      CI => \phase_reg[8]_i_1_n_0\,
      CI_TOP => '0',
      CO(7) => \phase_reg[16]_i_1_n_0\,
      CO(6) => \phase_reg[16]_i_1_n_1\,
      CO(5) => \phase_reg[16]_i_1_n_2\,
      CO(4) => \phase_reg[16]_i_1_n_3\,
      CO(3) => \phase_reg[16]_i_1_n_4\,
      CO(2) => \phase_reg[16]_i_1_n_5\,
      CO(1) => \phase_reg[16]_i_1_n_6\,
      CO(0) => \phase_reg[16]_i_1_n_7\,
      DI(7 downto 0) => B"00000000",
      O(7) => \phase_reg[16]_i_1_n_8\,
      O(6) => \phase_reg[16]_i_1_n_9\,
      O(5) => \phase_reg[16]_i_1_n_10\,
      O(4) => \phase_reg[16]_i_1_n_11\,
      O(3) => \phase_reg[16]_i_1_n_12\,
      O(2) => \phase_reg[16]_i_1_n_13\,
      O(1) => \phase_reg[16]_i_1_n_14\,
      O(0) => \phase_reg[16]_i_1_n_15\,
      S(7 downto 0) => phase_reg(23 downto 16)
    );
\phase_reg[17]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => '1',
      D => \phase_reg[16]_i_1_n_14\,
      Q => phase_reg(17),
      R => \phase[0]_i_1_n_0\
    );
\phase_reg[18]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => '1',
      D => \phase_reg[16]_i_1_n_13\,
      Q => phase_reg(18),
      R => \phase[0]_i_1_n_0\
    );
\phase_reg[19]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => '1',
      D => \phase_reg[16]_i_1_n_12\,
      Q => phase_reg(19),
      R => \phase[0]_i_1_n_0\
    );
\phase_reg[1]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => '1',
      D => \phase_reg[0]_i_2_n_14\,
      Q => phase_reg(1),
      R => \phase[0]_i_1_n_0\
    );
\phase_reg[20]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => '1',
      D => \phase_reg[16]_i_1_n_11\,
      Q => phase_reg(20),
      R => \phase[0]_i_1_n_0\
    );
\phase_reg[21]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => '1',
      D => \phase_reg[16]_i_1_n_10\,
      Q => phase_reg(21),
      R => \phase[0]_i_1_n_0\
    );
\phase_reg[22]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => '1',
      D => \phase_reg[16]_i_1_n_9\,
      Q => phase_reg(22),
      R => \phase[0]_i_1_n_0\
    );
\phase_reg[23]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => '1',
      D => \phase_reg[16]_i_1_n_8\,
      Q => phase_reg(23),
      R => \phase[0]_i_1_n_0\
    );
\phase_reg[24]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => '1',
      D => \phase_reg[24]_i_1_n_15\,
      Q => phase_reg(24),
      R => \phase[0]_i_1_n_0\
    );
\phase_reg[24]_i_1\: unisim.vcomponents.CARRY8
     port map (
      CI => \phase_reg[16]_i_1_n_0\,
      CI_TOP => '0',
      CO(7) => \NLW_phase_reg[24]_i_1_CO_UNCONNECTED\(7),
      CO(6) => \phase_reg[24]_i_1_n_1\,
      CO(5) => \phase_reg[24]_i_1_n_2\,
      CO(4) => \phase_reg[24]_i_1_n_3\,
      CO(3) => \phase_reg[24]_i_1_n_4\,
      CO(2) => \phase_reg[24]_i_1_n_5\,
      CO(1) => \phase_reg[24]_i_1_n_6\,
      CO(0) => \phase_reg[24]_i_1_n_7\,
      DI(7 downto 0) => B"00000000",
      O(7) => \phase_reg[24]_i_1_n_8\,
      O(6) => \phase_reg[24]_i_1_n_9\,
      O(5) => \phase_reg[24]_i_1_n_10\,
      O(4) => \phase_reg[24]_i_1_n_11\,
      O(3) => \phase_reg[24]_i_1_n_12\,
      O(2) => \phase_reg[24]_i_1_n_13\,
      O(1) => \phase_reg[24]_i_1_n_14\,
      O(0) => \phase_reg[24]_i_1_n_15\,
      S(7 downto 0) => phase_reg(31 downto 24)
    );
\phase_reg[25]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => '1',
      D => \phase_reg[24]_i_1_n_14\,
      Q => phase_reg(25),
      R => \phase[0]_i_1_n_0\
    );
\phase_reg[26]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => '1',
      D => \phase_reg[24]_i_1_n_13\,
      Q => phase_reg(26),
      R => \phase[0]_i_1_n_0\
    );
\phase_reg[27]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => '1',
      D => \phase_reg[24]_i_1_n_12\,
      Q => phase_reg(27),
      R => \phase[0]_i_1_n_0\
    );
\phase_reg[28]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => '1',
      D => \phase_reg[24]_i_1_n_11\,
      Q => phase_reg(28),
      R => \phase[0]_i_1_n_0\
    );
\phase_reg[29]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => '1',
      D => \phase_reg[24]_i_1_n_10\,
      Q => phase_reg(29),
      R => \phase[0]_i_1_n_0\
    );
\phase_reg[2]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => '1',
      D => \phase_reg[0]_i_2_n_13\,
      Q => phase_reg(2),
      R => \phase[0]_i_1_n_0\
    );
\phase_reg[30]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => '1',
      D => \phase_reg[24]_i_1_n_9\,
      Q => phase_reg(30),
      R => \phase[0]_i_1_n_0\
    );
\phase_reg[31]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => '1',
      D => \phase_reg[24]_i_1_n_8\,
      Q => phase_reg(31),
      R => \phase[0]_i_1_n_0\
    );
\phase_reg[3]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => '1',
      D => \phase_reg[0]_i_2_n_12\,
      Q => phase_reg(3),
      R => \phase[0]_i_1_n_0\
    );
\phase_reg[4]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => '1',
      D => \phase_reg[0]_i_2_n_11\,
      Q => phase_reg(4),
      R => \phase[0]_i_1_n_0\
    );
\phase_reg[5]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => '1',
      D => \phase_reg[0]_i_2_n_10\,
      Q => phase_reg(5),
      R => \phase[0]_i_1_n_0\
    );
\phase_reg[6]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => '1',
      D => \phase_reg[0]_i_2_n_9\,
      Q => phase_reg(6),
      R => \phase[0]_i_1_n_0\
    );
\phase_reg[7]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => '1',
      D => \phase_reg[0]_i_2_n_8\,
      Q => phase_reg(7),
      R => \phase[0]_i_1_n_0\
    );
\phase_reg[8]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => '1',
      D => \phase_reg[8]_i_1_n_15\,
      Q => phase_reg(8),
      R => \phase[0]_i_1_n_0\
    );
\phase_reg[8]_i_1\: unisim.vcomponents.CARRY8
     port map (
      CI => \phase_reg[0]_i_2_n_0\,
      CI_TOP => '0',
      CO(7) => \phase_reg[8]_i_1_n_0\,
      CO(6) => \phase_reg[8]_i_1_n_1\,
      CO(5) => \phase_reg[8]_i_1_n_2\,
      CO(4) => \phase_reg[8]_i_1_n_3\,
      CO(3) => \phase_reg[8]_i_1_n_4\,
      CO(2) => \phase_reg[8]_i_1_n_5\,
      CO(1) => \phase_reg[8]_i_1_n_6\,
      CO(0) => \phase_reg[8]_i_1_n_7\,
      DI(7 downto 0) => B"00000000",
      O(7) => \phase_reg[8]_i_1_n_8\,
      O(6) => \phase_reg[8]_i_1_n_9\,
      O(5) => \phase_reg[8]_i_1_n_10\,
      O(4) => \phase_reg[8]_i_1_n_11\,
      O(3) => \phase_reg[8]_i_1_n_12\,
      O(2) => \phase_reg[8]_i_1_n_13\,
      O(1) => \phase_reg[8]_i_1_n_14\,
      O(0) => \phase_reg[8]_i_1_n_15\,
      S(7 downto 0) => phase_reg(15 downto 8)
    );
\phase_reg[9]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => '1',
      D => \phase_reg[8]_i_1_n_14\,
      Q => phase_reg(9),
      R => \phase[0]_i_1_n_0\
    );
pwm_i_1: unisim.vcomponents.LUT2
    generic map(
      INIT => X"B"
    )
        port map (
      I0 => \s_axi_bresp[1]_i_3_n_0\,
      I1 => s_axi_aresetn,
      O => pwm_i_1_n_0
    );
pwm_i_10: unisim.vcomponents.LUT6
    generic map(
      INIT => X"5555555557FFFFFF"
    )
        port map (
      I0 => pwm1(12),
      I1 => pwm_i_15_n_0,
      I2 => pwm_i_16_n_0,
      I3 => pwm1(9),
      I4 => pwm1(10),
      I5 => pwm1(11),
      O => pwm_i_10_n_0
    );
pwm_i_11: unisim.vcomponents.LUT2
    generic map(
      INIT => X"7"
    )
        port map (
      I0 => pwm1(20),
      I1 => pwm1(19),
      O => pwm_i_11_n_0
    );
pwm_i_13: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FFFFFFFFFFFFFFFE"
    )
        port map (
      I0 => pwm1(26),
      I1 => pwm1(30),
      I2 => pwm1(31),
      I3 => pwm1(25),
      I4 => pwm1(27),
      I5 => pwm1(24),
      O => pwm_i_13_n_0
    );
pwm_i_15: unisim.vcomponents.LUT4
    generic map(
      INIT => X"FFFE"
    )
        port map (
      I0 => pwm1(5),
      I1 => pwm1(8),
      I2 => pwm1(6),
      I3 => pwm1(7),
      O => pwm_i_15_n_0
    );
pwm_i_16: unisim.vcomponents.LUT3
    generic map(
      INIT => X"80"
    )
        port map (
      I0 => pwm1(4),
      I1 => pwm1(2),
      I2 => pwm1(3),
      O => pwm_i_16_n_0
    );
pwm_i_2: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FFFFFFFFFFFF004F"
    )
        port map (
      I0 => pwm_i_3_n_0,
      I1 => pwm_i_4_n_0,
      I2 => pwm1(23),
      I3 => pwm_i_6_n_0,
      I4 => start,
      I5 => pwm_i_7_n_0,
      O => pwm_i_2_n_0
    );
pwm_i_3: unisim.vcomponents.LUT2
    generic map(
      INIT => X"E"
    )
        port map (
      I0 => pwm1(22),
      I1 => pwm1(21),
      O => pwm_i_3_n_0
    );
pwm_i_4: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FFFFFFFF11111151"
    )
        port map (
      I0 => pwm_i_8_n_0,
      I1 => pwm1(15),
      I2 => pwm_i_10_n_0,
      I3 => pwm1(14),
      I4 => pwm1(13),
      I5 => pwm_i_11_n_0,
      O => pwm_i_4_n_0
    );
pwm_i_6: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FFFFFEFF"
    )
        port map (
      I0 => pwm1(32),
      I1 => pwm1(28),
      I2 => pwm1(29),
      I3 => busy,
      I4 => pwm_i_13_n_0,
      O => pwm_i_6_n_0
    );
pwm_i_7: unisim.vcomponents.LUT5
    generic map(
      INIT => X"00040000"
    )
        port map (
      I0 => \phase[0]_i_3_n_0\,
      I1 => \phase[0]_i_4_n_0\,
      I2 => \phase[0]_i_5_n_0\,
      I3 => \phase[0]_i_6_n_0\,
      I4 => busy,
      O => pwm_i_7_n_0
    );
pwm_i_8: unisim.vcomponents.LUT3
    generic map(
      INIT => X"FE"
    )
        port map (
      I0 => pwm1(18),
      I1 => pwm1(16),
      I2 => pwm1(17),
      O => pwm_i_8_n_0
    );
pwm_reg: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => '1',
      D => pwm_i_2_n_0,
      Q => \^servo_pwm\,
      R => pwm_i_1_n_0
    );
pwm_reg_i_12: unisim.vcomponents.CARRY8
     port map (
      CI => pwm_reg_i_5_n_0,
      CI_TOP => '0',
      CO(7) => pwm1(32),
      CO(6) => NLW_pwm_reg_i_12_CO_UNCONNECTED(6),
      CO(5) => pwm_reg_i_12_n_2,
      CO(4) => pwm_reg_i_12_n_3,
      CO(3) => pwm_reg_i_12_n_4,
      CO(2) => pwm_reg_i_12_n_5,
      CO(1) => pwm_reg_i_12_n_6,
      CO(0) => pwm_reg_i_12_n_7,
      DI(7 downto 0) => B"00000000",
      O(7) => NLW_pwm_reg_i_12_O_UNCONNECTED(7),
      O(6 downto 0) => pwm1(31 downto 25),
      S(7) => '1',
      S(6 downto 0) => phase_reg(31 downto 25)
    );
pwm_reg_i_14: unisim.vcomponents.CARRY8
     port map (
      CI => phase_reg(0),
      CI_TOP => '0',
      CO(7) => pwm_reg_i_14_n_0,
      CO(6) => pwm_reg_i_14_n_1,
      CO(5) => pwm_reg_i_14_n_2,
      CO(4) => pwm_reg_i_14_n_3,
      CO(3) => pwm_reg_i_14_n_4,
      CO(2) => pwm_reg_i_14_n_5,
      CO(1) => pwm_reg_i_14_n_6,
      CO(0) => pwm_reg_i_14_n_7,
      DI(7 downto 0) => B"00000000",
      O(7 downto 1) => pwm1(8 downto 2),
      O(0) => NLW_pwm_reg_i_14_O_UNCONNECTED(0),
      S(7 downto 0) => phase_reg(8 downto 1)
    );
pwm_reg_i_5: unisim.vcomponents.CARRY8
     port map (
      CI => pwm_reg_i_9_n_0,
      CI_TOP => '0',
      CO(7) => pwm_reg_i_5_n_0,
      CO(6) => pwm_reg_i_5_n_1,
      CO(5) => pwm_reg_i_5_n_2,
      CO(4) => pwm_reg_i_5_n_3,
      CO(3) => pwm_reg_i_5_n_4,
      CO(2) => pwm_reg_i_5_n_5,
      CO(1) => pwm_reg_i_5_n_6,
      CO(0) => pwm_reg_i_5_n_7,
      DI(7 downto 0) => B"00000000",
      O(7 downto 0) => pwm1(24 downto 17),
      S(7 downto 0) => phase_reg(24 downto 17)
    );
pwm_reg_i_9: unisim.vcomponents.CARRY8
     port map (
      CI => pwm_reg_i_14_n_0,
      CI_TOP => '0',
      CO(7) => pwm_reg_i_9_n_0,
      CO(6) => pwm_reg_i_9_n_1,
      CO(5) => pwm_reg_i_9_n_2,
      CO(4) => pwm_reg_i_9_n_3,
      CO(3) => pwm_reg_i_9_n_4,
      CO(2) => pwm_reg_i_9_n_5,
      CO(1) => pwm_reg_i_9_n_6,
      CO(0) => pwm_reg_i_9_n_7,
      DI(7 downto 0) => B"00000000",
      O(7 downto 0) => pwm1(16 downto 9),
      S(7 downto 0) => phase_reg(16 downto 9)
    );
\s_axi_bresp[1]_i_10\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FFFDFFFFFFFFFFFF"
    )
        port map (
      I0 => \s_axi_bresp[1]_i_4_0\(28),
      I1 => \s_axi_bresp[1]_i_4_0\(2),
      I2 => \s_axi_bresp[1]_i_4_0\(19),
      I3 => \s_axi_bresp[1]_i_4_0\(31),
      I4 => \s_axi_bresp[1]_i_4_0\(8),
      I5 => \s_axi_bresp[1]_i_4_0\(4),
      O => \s_axi_bresp[1]_i_10_n_0\
    );
\s_axi_bresp[1]_i_11\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FFFFFFFFFFFFFFEF"
    )
        port map (
      I0 => \s_axi_bresp[1]_i_4_0\(9),
      I1 => \s_axi_bresp[1]_i_4_0\(11),
      I2 => \s_axi_bresp[1]_i_4_0\(1),
      I3 => busy,
      I4 => \s_axi_bresp[1]_i_4_0\(10),
      I5 => \s_axi_bresp[1]_i_17_n_0\,
      O => \s_axi_bresp[1]_i_11_n_0\
    );
\s_axi_bresp[1]_i_12\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FFFFFFFFFFFFFFFE"
    )
        port map (
      I0 => \scratch[31]_i_2\(10),
      I1 => \scratch[31]_i_2\(11),
      I2 => \scratch[31]_i_2\(8),
      I3 => \scratch[31]_i_2\(9),
      I4 => \scratch[31]_i_2\(6),
      I5 => \scratch[31]_i_2\(7),
      O => \^aw_address_reg[10]\
    );
\s_axi_bresp[1]_i_14\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FFFFFBFF"
    )
        port map (
      I0 => \scratch[31]_i_2\(1),
      I1 => \s_axi_bresp[1]_i_14_0\(1),
      I2 => \scratch[31]_i_2\(5),
      I3 => \s_axi_bresp[1]_i_14_0\(2),
      I4 => \s_axi_bresp[1]_i_18_n_0\,
      O => \s_axi_bresp[1]_i_14_n_0\
    );
\s_axi_bresp[1]_i_15\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FFFFFFFFFFFFFFFE"
    )
        port map (
      I0 => \s_axi_bresp[1]_i_19_n_0\,
      I1 => \s_axi_bresp[1]_i_20_n_0\,
      I2 => \s_axi_bresp[1]_i_4_0\(17),
      I3 => \s_axi_bresp[1]_i_4_0\(16),
      I4 => \s_axi_bresp[1]_i_4_0\(7),
      I5 => \s_axi_bresp[1]_i_4_0\(29),
      O => \s_axi_bresp[1]_i_15_n_0\
    );
\s_axi_bresp[1]_i_16\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"FFDF"
    )
        port map (
      I0 => \s_axi_bresp[1]_i_4_0\(6),
      I1 => \s_axi_bresp[1]_i_4_0\(27),
      I2 => \s_axi_bresp[1]_i_4_0\(20),
      I3 => \s_axi_bresp[1]_i_4_0\(26),
      O => \s_axi_bresp[1]_i_16_n_0\
    );
\s_axi_bresp[1]_i_17\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"7"
    )
        port map (
      I0 => \s_axi_bresp[1]_i_4_0\(18),
      I1 => \s_axi_bresp[1]_i_4_0\(22),
      O => \s_axi_bresp[1]_i_17_n_0\
    );
\s_axi_bresp[1]_i_18\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"FFDF"
    )
        port map (
      I0 => \s_axi_bresp[1]_i_14_0\(0),
      I1 => \scratch[31]_i_2\(0),
      I2 => \s_axi_bresp[1]_i_14_0\(3),
      I3 => \scratch[31]_i_2\(2),
      O => \s_axi_bresp[1]_i_18_n_0\
    );
\s_axi_bresp[1]_i_19\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FFFFFFFFFFFFFDFF"
    )
        port map (
      I0 => \scratch[31]_i_2\(4),
      I1 => \scratch[31]_i_2\(3),
      I2 => \s_axi_bresp[1]_i_4_0\(21),
      I3 => \s_axi_bresp[1]_i_4_0\(25),
      I4 => \s_axi_bresp[1]_i_4_0\(13),
      I5 => \s_axi_bresp[1]_i_4_0\(23),
      O => \s_axi_bresp[1]_i_19_n_0\
    );
\s_axi_bresp[1]_i_2\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FF01FFFFFF010000"
    )
        port map (
      I0 => \scratch[31]_i_2\(5),
      I1 => \s_axi_bresp[1]_i_3_n_0\,
      I2 => start,
      I3 => \s_axi_bresp_reg[1]\,
      I4 => p_5_in,
      I5 => s_axi_bresp(0),
      O => \aw_address_reg[5]\
    );
\s_axi_bresp[1]_i_20\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"FFFD"
    )
        port map (
      I0 => \s_axi_bresp[1]_i_4_0\(24),
      I1 => \s_axi_bresp[1]_i_4_0\(0),
      I2 => \s_axi_bresp[1]_i_4_0\(3),
      I3 => \s_axi_bresp[1]_i_4_0\(5),
      O => \s_axi_bresp[1]_i_20_n_0\
    );
\s_axi_bresp[1]_i_3\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"0002"
    )
        port map (
      I0 => \s_axi_bresp[1]_i_7_n_0\,
      I1 => \s_axi_bresp[1]_i_8_n_0\,
      I2 => \s_axi_bresp[1]_i_9_n_0\,
      I3 => \s_axi_bresp[1]_i_10_n_0\,
      O => \s_axi_bresp[1]_i_3_n_0\
    );
\s_axi_bresp[1]_i_4\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"0002"
    )
        port map (
      I0 => \s_axi_bresp[1]_i_7_n_0\,
      I1 => \s_axi_bresp[1]_i_9_n_0\,
      I2 => \s_axi_bresp[1]_i_11_n_0\,
      I3 => \s_axi_bresp[1]_i_10_n_0\,
      O => start
    );
\s_axi_bresp[1]_i_7\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0000000000000040"
    )
        port map (
      I0 => \s_axi_bresp[1]_i_14_n_0\,
      I1 => aw_pending,
      I2 => \s_axi_bresp[1]_i_4_1\,
      I3 => \s_axi_bresp[1]_i_4_2\,
      I4 => \s_axi_bresp[1]_i_15_n_0\,
      I5 => \^aw_address_reg[10]\,
      O => \s_axi_bresp[1]_i_7_n_0\
    );
\s_axi_bresp[1]_i_8\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"F7FFFFFFFFFFFFFF"
    )
        port map (
      I0 => \s_axi_bresp[1]_i_4_0\(22),
      I1 => \s_axi_bresp[1]_i_4_0\(18),
      I2 => \s_axi_bresp[1]_i_4_0\(1),
      I3 => \s_axi_bresp[1]_i_4_0\(11),
      I4 => \s_axi_bresp[1]_i_4_0\(10),
      I5 => \s_axi_bresp[1]_i_4_0\(9),
      O => \s_axi_bresp[1]_i_8_n_0\
    );
\s_axi_bresp[1]_i_9\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FFFFEFFF"
    )
        port map (
      I0 => \s_axi_bresp[1]_i_4_0\(12),
      I1 => \s_axi_bresp[1]_i_4_0\(15),
      I2 => \s_axi_bresp[1]_i_4_0\(14),
      I3 => \s_axi_bresp[1]_i_4_0\(30),
      I4 => \s_axi_bresp[1]_i_16_n_0\,
      O => \s_axi_bresp[1]_i_9_n_0\
    );
\s_axi_rdata[0]_i_1\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"2"
    )
        port map (
      I0 => \s_axi_rdata_reg[0]\,
      I1 => \s_axi_rdata[0]_i_2_n_0\,
      O => D(0)
    );
\s_axi_rdata[0]_i_2\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"F5F3FFFFFFFFF0FF"
    )
        port map (
      I0 => Q(0),
      I1 => busy,
      I2 => s_axi_araddr(4),
      I3 => s_axi_araddr(5),
      I4 => s_axi_araddr(3),
      I5 => s_axi_araddr(2),
      O => \s_axi_rdata[0]_i_2_n_0\
    );
\s_axi_rdata[1]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0002000000000000"
    )
        port map (
      I0 => \s_axi_rdata_reg[1]\,
      I1 => \s_axi_rdata[1]_i_3_n_0\,
      I2 => s_axi_araddr(0),
      I3 => s_axi_araddr(1),
      I4 => s_axi_araddr(2),
      I5 => s_axi_araddr(3),
      O => D(1)
    );
\s_axi_rdata[1]_i_3\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"ABFB"
    )
        port map (
      I0 => s_axi_araddr(4),
      I1 => \^servo_pwm\,
      I2 => s_axi_araddr(5),
      I3 => Q(1),
      O => \s_axi_rdata[1]_i_3_n_0\
    );
end STRUCTURE;
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
library UNISIM;
use UNISIM.VCOMPONENTS.ALL;
entity decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_aura_pwm_probe is
  port (
    s_axi_bvalid_reg_0 : out STD_LOGIC;
    servo_pwm : out STD_LOGIC;
    s_axi_rdata : out STD_LOGIC_VECTOR ( 31 downto 0 );
    s_axi_rresp : out STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_wready : out STD_LOGIC;
    s_axi_awready : out STD_LOGIC;
    s_axi_arready : out STD_LOGIC;
    s_axi_rvalid_reg_0 : out STD_LOGIC;
    s_axi_bresp : out STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_aresetn : in STD_LOGIC;
    s_axi_araddr : in STD_LOGIC_VECTOR ( 11 downto 0 );
    s_axi_aclk : in STD_LOGIC;
    s_axi_awaddr : in STD_LOGIC_VECTOR ( 11 downto 0 );
    s_axi_wdata : in STD_LOGIC_VECTOR ( 31 downto 0 );
    s_axi_wstrb : in STD_LOGIC_VECTOR ( 3 downto 0 );
    s_axi_awvalid : in STD_LOGIC;
    s_axi_wvalid : in STD_LOGIC;
    s_axi_arvalid : in STD_LOGIC;
    s_axi_bready : in STD_LOGIC;
    s_axi_rready : in STD_LOGIC
  );
end decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_aura_pwm_probe;

architecture STRUCTURE of decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_aura_pwm_probe is
  signal aw_address : STD_LOGIC_VECTOR ( 11 downto 0 );
  signal aw_pending : STD_LOGIC;
  signal aw_pending0 : STD_LOGIC;
  signal aw_pending_i_1_n_0 : STD_LOGIC;
  signal burst_n_1 : STD_LOGIC;
  signal burst_n_2 : STD_LOGIC;
  signal burst_n_3 : STD_LOGIC;
  signal burst_n_4 : STD_LOGIC;
  signal p_0_in : STD_LOGIC;
  signal p_0_in_1 : STD_LOGIC;
  signal p_1_in : STD_LOGIC_VECTOR ( 31 downto 7 );
  signal p_1_in_0 : STD_LOGIC;
  signal p_2_in : STD_LOGIC;
  signal p_5_in : STD_LOGIC;
  signal \^s_axi_bresp\ : STD_LOGIC_VECTOR ( 0 to 0 );
  signal \s_axi_bresp[1]_i_13_n_0\ : STD_LOGIC;
  signal \s_axi_bresp[1]_i_5_n_0\ : STD_LOGIC;
  signal s_axi_bvalid_i_1_n_0 : STD_LOGIC;
  signal \^s_axi_bvalid_reg_0\ : STD_LOGIC;
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
  signal \s_axi_rdata[1]_i_2_n_0\ : STD_LOGIC;
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
  signal \scratch[31]_i_2_n_0\ : STD_LOGIC;
  signal \scratch[31]_i_3_n_0\ : STD_LOGIC;
  signal w_data : STD_LOGIC_VECTOR ( 31 downto 0 );
  signal w_pending0 : STD_LOGIC;
  signal w_pending_i_1_n_0 : STD_LOGIC;
  signal w_pending_i_2_n_0 : STD_LOGIC;
  signal w_pending_reg_n_0 : STD_LOGIC;
  signal \w_strobes_reg_n_0_[3]\ : STD_LOGIC;
  attribute SOFT_HLUTNM : string;
  attribute SOFT_HLUTNM of aw_pending_i_1 : label is "soft_lutpair4";
  attribute SOFT_HLUTNM of s_axi_arready_INST_0 : label is "soft_lutpair3";
  attribute SOFT_HLUTNM of s_axi_awready_INST_0 : label is "soft_lutpair2";
  attribute SOFT_HLUTNM of \s_axi_bresp[1]_i_6\ : label is "soft_lutpair1";
  attribute X_INTERFACE_INFO : string;
  attribute X_INTERFACE_INFO of \s_axi_bresp_reg[1]\ : label is "xilinx.com:interface:aximm:1.0 S_AXI BRESP";
  attribute SOFT_HLUTNM of s_axi_bvalid_i_1 : label is "soft_lutpair1";
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
  attribute SOFT_HLUTNM of s_axi_rvalid_i_1 : label is "soft_lutpair3";
  attribute X_INTERFACE_INFO of s_axi_rvalid_reg : label is "xilinx.com:interface:aximm:1.0 S_AXI RVALID";
  attribute SOFT_HLUTNM of s_axi_wready_INST_0 : label is "soft_lutpair2";
  attribute SOFT_HLUTNM of w_pending_i_2 : label is "soft_lutpair4";
begin
  s_axi_bresp(0) <= \^s_axi_bresp\(0);
  s_axi_bvalid_reg_0 <= \^s_axi_bvalid_reg_0\;
  s_axi_rvalid_reg_0 <= \^s_axi_rvalid_reg_0\;
\aw_address[11]_i_1\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"02"
    )
        port map (
      I0 => s_axi_awvalid,
      I1 => \^s_axi_bvalid_reg_0\,
      I2 => aw_pending,
      O => aw_pending0
    );
\aw_address_reg[0]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => aw_pending0,
      D => s_axi_awaddr(0),
      Q => aw_address(0),
      R => p_0_in
    );
\aw_address_reg[10]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => aw_pending0,
      D => s_axi_awaddr(10),
      Q => aw_address(10),
      R => p_0_in
    );
\aw_address_reg[11]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => aw_pending0,
      D => s_axi_awaddr(11),
      Q => aw_address(11),
      R => p_0_in
    );
\aw_address_reg[1]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => aw_pending0,
      D => s_axi_awaddr(1),
      Q => aw_address(1),
      R => p_0_in
    );
\aw_address_reg[2]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => aw_pending0,
      D => s_axi_awaddr(2),
      Q => aw_address(2),
      R => p_0_in
    );
\aw_address_reg[3]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => aw_pending0,
      D => s_axi_awaddr(3),
      Q => aw_address(3),
      R => p_0_in
    );
\aw_address_reg[4]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => aw_pending0,
      D => s_axi_awaddr(4),
      Q => aw_address(4),
      R => p_0_in
    );
\aw_address_reg[5]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => aw_pending0,
      D => s_axi_awaddr(5),
      Q => aw_address(5),
      R => p_0_in
    );
\aw_address_reg[6]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => aw_pending0,
      D => s_axi_awaddr(6),
      Q => aw_address(6),
      R => p_0_in
    );
\aw_address_reg[7]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => aw_pending0,
      D => s_axi_awaddr(7),
      Q => aw_address(7),
      R => p_0_in
    );
\aw_address_reg[8]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => aw_pending0,
      D => s_axi_awaddr(8),
      Q => aw_address(8),
      R => p_0_in
    );
\aw_address_reg[9]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
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
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => '1',
      D => aw_pending_i_1_n_0,
      Q => aw_pending,
      R => w_pending_i_1_n_0
    );
burst: entity work.decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_pwm_burst
     port map (
      D(1) => burst_n_2,
      D(0) => burst_n_3,
      Q(1 downto 0) => scratch(1 downto 0),
      \aw_address_reg[10]\ => burst_n_1,
      \aw_address_reg[5]\ => burst_n_4,
      aw_pending => aw_pending,
      p_5_in => p_5_in,
      s_axi_aclk => s_axi_aclk,
      s_axi_araddr(5 downto 0) => s_axi_araddr(5 downto 0),
      s_axi_aresetn => s_axi_aresetn,
      s_axi_bresp(0) => \^s_axi_bresp\(0),
      \s_axi_bresp[1]_i_14_0\(3) => \w_strobes_reg_n_0_[3]\,
      \s_axi_bresp[1]_i_14_0\(2) => p_2_in,
      \s_axi_bresp[1]_i_14_0\(1) => p_1_in_0,
      \s_axi_bresp[1]_i_14_0\(0) => p_0_in_1,
      \s_axi_bresp[1]_i_4_0\(31 downto 0) => w_data(31 downto 0),
      \s_axi_bresp[1]_i_4_1\ => w_pending_reg_n_0,
      \s_axi_bresp[1]_i_4_2\ => \^s_axi_bvalid_reg_0\,
      \s_axi_bresp_reg[1]\ => \s_axi_bresp[1]_i_5_n_0\,
      \s_axi_rdata_reg[0]\ => \s_axi_rdata[31]_i_3_n_0\,
      \s_axi_rdata_reg[1]\ => \s_axi_rdata[1]_i_2_n_0\,
      \scratch[31]_i_2\(11 downto 0) => aw_address(11 downto 0),
      servo_pwm => servo_pwm
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
      I0 => aw_pending,
      I1 => s_axi_aresetn,
      I2 => \^s_axi_bvalid_reg_0\,
      O => s_axi_awready
    );
\s_axi_bresp[1]_i_1\: unisim.vcomponents.LUT1
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => s_axi_aresetn,
      O => p_0_in
    );
\s_axi_bresp[1]_i_13\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"E"
    )
        port map (
      I0 => aw_address(1),
      I1 => aw_address(0),
      O => \s_axi_bresp[1]_i_13_n_0\
    );
\s_axi_bresp[1]_i_5\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FFFFEFFEEFFFEFFE"
    )
        port map (
      I0 => burst_n_1,
      I1 => \s_axi_bresp[1]_i_13_n_0\,
      I2 => aw_address(3),
      I3 => aw_address(2),
      I4 => aw_address(5),
      I5 => aw_address(4),
      O => \s_axi_bresp[1]_i_5_n_0\
    );
\s_axi_bresp[1]_i_6\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"08"
    )
        port map (
      I0 => aw_pending,
      I1 => w_pending_reg_n_0,
      I2 => \^s_axi_bvalid_reg_0\,
      O => p_5_in
    );
\s_axi_bresp_reg[1]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => '1',
      D => burst_n_4,
      Q => \^s_axi_bresp\(0),
      R => p_0_in
    );
s_axi_bvalid_i_1: unisim.vcomponents.LUT4
    generic map(
      INIT => X"7444"
    )
        port map (
      I0 => s_axi_bready,
      I1 => \^s_axi_bvalid_reg_0\,
      I2 => w_pending_reg_n_0,
      I3 => aw_pending,
      O => s_axi_bvalid_i_1_n_0
    );
s_axi_bvalid_reg: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => '1',
      D => s_axi_bvalid_i_1_n_0,
      Q => \^s_axi_bvalid_reg_0\,
      R => p_0_in
    );
\s_axi_rdata[10]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"000A00A08000AA0A"
    )
        port map (
      I0 => \s_axi_rdata[31]_i_3_n_0\,
      I1 => scratch(10),
      I2 => s_axi_araddr(3),
      I3 => s_axi_araddr(5),
      I4 => s_axi_araddr(2),
      I5 => s_axi_araddr(4),
      O => \s_axi_rdata[10]_i_1_n_0\
    );
\s_axi_rdata[11]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"00800000000A00AA"
    )
        port map (
      I0 => \s_axi_rdata[31]_i_3_n_0\,
      I1 => scratch(11),
      I2 => s_axi_araddr(5),
      I3 => s_axi_araddr(4),
      I4 => s_axi_araddr(3),
      I5 => s_axi_araddr(2),
      O => \s_axi_rdata[11]_i_1_n_0\
    );
\s_axi_rdata[12]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0822002220082008"
    )
        port map (
      I0 => \s_axi_rdata[31]_i_3_n_0\,
      I1 => s_axi_araddr(5),
      I2 => s_axi_araddr(4),
      I3 => s_axi_araddr(2),
      I4 => scratch(12),
      I5 => s_axi_araddr(3),
      O => \s_axi_rdata[12]_i_1_n_0\
    );
\s_axi_rdata[13]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0800000800000008"
    )
        port map (
      I0 => s_axi_araddr(3),
      I1 => \s_axi_rdata[31]_i_3_n_0\,
      I2 => s_axi_araddr(4),
      I3 => s_axi_araddr(2),
      I4 => s_axi_araddr(5),
      I5 => scratch(13),
      O => \s_axi_rdata[13]_i_1_n_0\
    );
\s_axi_rdata[14]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"00800000000A00AA"
    )
        port map (
      I0 => \s_axi_rdata[31]_i_3_n_0\,
      I1 => scratch(14),
      I2 => s_axi_araddr(5),
      I3 => s_axi_araddr(4),
      I4 => s_axi_araddr(3),
      I5 => s_axi_araddr(2),
      O => \s_axi_rdata[14]_i_1_n_0\
    );
\s_axi_rdata[15]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0A02020220802080"
    )
        port map (
      I0 => \s_axi_rdata[31]_i_3_n_0\,
      I1 => s_axi_araddr(2),
      I2 => s_axi_araddr(4),
      I3 => s_axi_araddr(3),
      I4 => scratch(15),
      I5 => s_axi_araddr(5),
      O => \s_axi_rdata[15]_i_1_n_0\
    );
\s_axi_rdata[16]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"00000000A22A222A"
    )
        port map (
      I0 => \s_axi_rdata[31]_i_3_n_0\,
      I1 => s_axi_araddr(2),
      I2 => s_axi_araddr(3),
      I3 => s_axi_araddr(5),
      I4 => scratch(16),
      I5 => s_axi_araddr(4),
      O => \s_axi_rdata[16]_i_1_n_0\
    );
\s_axi_rdata[17]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"008000000000000A"
    )
        port map (
      I0 => \s_axi_rdata[31]_i_3_n_0\,
      I1 => scratch(17),
      I2 => s_axi_araddr(5),
      I3 => s_axi_araddr(4),
      I4 => s_axi_araddr(3),
      I5 => s_axi_araddr(2),
      O => \s_axi_rdata[17]_i_1_n_0\
    );
\s_axi_rdata[18]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"2002020200020202"
    )
        port map (
      I0 => \s_axi_rdata[31]_i_3_n_0\,
      I1 => s_axi_araddr(4),
      I2 => s_axi_araddr(2),
      I3 => s_axi_araddr(5),
      I4 => s_axi_araddr(3),
      I5 => scratch(18),
      O => \s_axi_rdata[18]_i_1_n_0\
    );
\s_axi_rdata[19]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"00800A000A0A0000"
    )
        port map (
      I0 => \s_axi_rdata[31]_i_3_n_0\,
      I1 => scratch(19),
      I2 => s_axi_araddr(5),
      I3 => s_axi_araddr(4),
      I4 => s_axi_araddr(3),
      I5 => s_axi_araddr(2),
      O => \s_axi_rdata[19]_i_1_n_0\
    );
\s_axi_rdata[1]_i_2\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0000000000000001"
    )
        port map (
      I0 => s_axi_araddr(10),
      I1 => s_axi_araddr(9),
      I2 => s_axi_araddr(6),
      I3 => s_axi_araddr(11),
      I4 => s_axi_araddr(7),
      I5 => s_axi_araddr(8),
      O => \s_axi_rdata[1]_i_2_n_0\
    );
\s_axi_rdata[20]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"2002088200020882"
    )
        port map (
      I0 => \s_axi_rdata[31]_i_3_n_0\,
      I1 => s_axi_araddr(4),
      I2 => s_axi_araddr(2),
      I3 => s_axi_araddr(3),
      I4 => s_axi_araddr(5),
      I5 => scratch(20),
      O => \s_axi_rdata[20]_i_1_n_0\
    );
\s_axi_rdata[21]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"2002020000020200"
    )
        port map (
      I0 => \s_axi_rdata[31]_i_3_n_0\,
      I1 => s_axi_araddr(4),
      I2 => s_axi_araddr(2),
      I3 => s_axi_araddr(5),
      I4 => s_axi_araddr(3),
      I5 => scratch(21),
      O => \s_axi_rdata[21]_i_1_n_0\
    );
\s_axi_rdata[22]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"00800000000000AA"
    )
        port map (
      I0 => \s_axi_rdata[31]_i_3_n_0\,
      I1 => scratch(22),
      I2 => s_axi_araddr(5),
      I3 => s_axi_araddr(4),
      I4 => s_axi_araddr(3),
      I5 => s_axi_araddr(2),
      O => \s_axi_rdata[22]_i_1_n_0\
    );
\s_axi_rdata[23]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0822002220082008"
    )
        port map (
      I0 => \s_axi_rdata[31]_i_3_n_0\,
      I1 => s_axi_araddr(5),
      I2 => s_axi_araddr(4),
      I3 => s_axi_araddr(2),
      I4 => scratch(23),
      I5 => s_axi_araddr(3),
      O => \s_axi_rdata[23]_i_1_n_0\
    );
\s_axi_rdata[24]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"2002020000020200"
    )
        port map (
      I0 => \s_axi_rdata[31]_i_3_n_0\,
      I1 => s_axi_araddr(4),
      I2 => s_axi_araddr(2),
      I3 => s_axi_araddr(5),
      I4 => s_axi_araddr(3),
      I5 => scratch(24),
      O => \s_axi_rdata[24]_i_1_n_0\
    );
\s_axi_rdata[25]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0800000800000008"
    )
        port map (
      I0 => s_axi_araddr(3),
      I1 => \s_axi_rdata[31]_i_3_n_0\,
      I2 => s_axi_araddr(4),
      I3 => s_axi_araddr(2),
      I4 => s_axi_araddr(5),
      I5 => scratch(25),
      O => \s_axi_rdata[25]_i_1_n_0\
    );
\s_axi_rdata[26]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0000000080080008"
    )
        port map (
      I0 => s_axi_araddr(5),
      I1 => \s_axi_rdata[31]_i_3_n_0\,
      I2 => s_axi_araddr(2),
      I3 => s_axi_araddr(3),
      I4 => scratch(26),
      I5 => s_axi_araddr(4),
      O => \s_axi_rdata[26]_i_1_n_0\
    );
\s_axi_rdata[27]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0800000000080008"
    )
        port map (
      I0 => s_axi_araddr(3),
      I1 => \s_axi_rdata[31]_i_3_n_0\,
      I2 => s_axi_araddr(4),
      I3 => s_axi_araddr(5),
      I4 => scratch(27),
      I5 => s_axi_araddr(2),
      O => \s_axi_rdata[27]_i_1_n_0\
    );
\s_axi_rdata[28]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"008000000000000A"
    )
        port map (
      I0 => \s_axi_rdata[31]_i_3_n_0\,
      I1 => scratch(28),
      I2 => s_axi_araddr(5),
      I3 => s_axi_araddr(4),
      I4 => s_axi_araddr(3),
      I5 => s_axi_araddr(2),
      O => \s_axi_rdata[28]_i_1_n_0\
    );
\s_axi_rdata[29]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0800000000000000"
    )
        port map (
      I0 => scratch(29),
      I1 => \s_axi_rdata[31]_i_3_n_0\,
      I2 => s_axi_araddr(4),
      I3 => s_axi_araddr(5),
      I4 => s_axi_araddr(3),
      I5 => s_axi_araddr(2),
      O => \s_axi_rdata[29]_i_1_n_0\
    );
\s_axi_rdata[2]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"000080002828A2A2"
    )
        port map (
      I0 => \s_axi_rdata[31]_i_3_n_0\,
      I1 => s_axi_araddr(2),
      I2 => s_axi_araddr(3),
      I3 => scratch(2),
      I4 => s_axi_araddr(4),
      I5 => s_axi_araddr(5),
      O => \s_axi_rdata[2]_i_1_n_0\
    );
\s_axi_rdata[30]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"008000000000000A"
    )
        port map (
      I0 => \s_axi_rdata[31]_i_3_n_0\,
      I1 => scratch(30),
      I2 => s_axi_araddr(5),
      I3 => s_axi_araddr(4),
      I4 => s_axi_araddr(3),
      I5 => s_axi_araddr(2),
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
\s_axi_rdata[31]_i_2\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0800000000000000"
    )
        port map (
      I0 => scratch(31),
      I1 => \s_axi_rdata[31]_i_3_n_0\,
      I2 => s_axi_araddr(4),
      I3 => s_axi_araddr(5),
      I4 => s_axi_araddr(3),
      I5 => s_axi_araddr(2),
      O => \s_axi_rdata[31]_i_2_n_0\
    );
\s_axi_rdata[31]_i_3\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"10"
    )
        port map (
      I0 => s_axi_araddr(0),
      I1 => s_axi_araddr(1),
      I2 => \s_axi_rdata[1]_i_2_n_0\,
      O => \s_axi_rdata[31]_i_3_n_0\
    );
\s_axi_rdata[3]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0822002220082008"
    )
        port map (
      I0 => \s_axi_rdata[31]_i_3_n_0\,
      I1 => s_axi_araddr(5),
      I2 => s_axi_araddr(4),
      I3 => s_axi_araddr(2),
      I4 => scratch(3),
      I5 => s_axi_araddr(3),
      O => \s_axi_rdata[3]_i_1_n_0\
    );
\s_axi_rdata[4]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"000A00A080000A0A"
    )
        port map (
      I0 => \s_axi_rdata[31]_i_3_n_0\,
      I1 => scratch(4),
      I2 => s_axi_araddr(3),
      I3 => s_axi_araddr(5),
      I4 => s_axi_araddr(2),
      I5 => s_axi_araddr(4),
      O => \s_axi_rdata[4]_i_1_n_0\
    );
\s_axi_rdata[5]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0080000000880088"
    )
        port map (
      I0 => s_axi_araddr(3),
      I1 => \s_axi_rdata[31]_i_3_n_0\,
      I2 => scratch(5),
      I3 => s_axi_araddr(4),
      I4 => s_axi_araddr(5),
      I5 => s_axi_araddr(2),
      O => \s_axi_rdata[5]_i_1_n_0\
    );
\s_axi_rdata[6]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"008000000000000A"
    )
        port map (
      I0 => \s_axi_rdata[31]_i_3_n_0\,
      I1 => scratch(6),
      I2 => s_axi_araddr(5),
      I3 => s_axi_araddr(4),
      I4 => s_axi_araddr(3),
      I5 => s_axi_araddr(2),
      O => \s_axi_rdata[6]_i_1_n_0\
    );
\s_axi_rdata[7]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0080000000880088"
    )
        port map (
      I0 => s_axi_araddr(3),
      I1 => \s_axi_rdata[31]_i_3_n_0\,
      I2 => scratch(7),
      I3 => s_axi_araddr(4),
      I4 => s_axi_araddr(5),
      I5 => s_axi_araddr(2),
      O => \s_axi_rdata[7]_i_1_n_0\
    );
\s_axi_rdata[8]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"00800000000A00AA"
    )
        port map (
      I0 => \s_axi_rdata[31]_i_3_n_0\,
      I1 => scratch(8),
      I2 => s_axi_araddr(5),
      I3 => s_axi_araddr(4),
      I4 => s_axi_araddr(3),
      I5 => s_axi_araddr(2),
      O => \s_axi_rdata[8]_i_1_n_0\
    );
\s_axi_rdata[9]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0A00020020802080"
    )
        port map (
      I0 => \s_axi_rdata[31]_i_3_n_0\,
      I1 => s_axi_araddr(2),
      I2 => s_axi_araddr(4),
      I3 => s_axi_araddr(3),
      I4 => scratch(9),
      I5 => s_axi_araddr(5),
      O => \s_axi_rdata[9]_i_1_n_0\
    );
\s_axi_rdata_reg[0]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_3,
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
      D => burst_n_2,
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
      INIT => X"F100FFFF"
    )
        port map (
      I0 => s_axi_araddr(3),
      I1 => s_axi_araddr(2),
      I2 => s_axi_araddr(5),
      I3 => s_axi_araddr(4),
      I4 => \s_axi_rdata[31]_i_3_n_0\,
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
      INIT => X"3A"
    )
        port map (
      I0 => s_axi_arvalid,
      I1 => s_axi_rready,
      I2 => \^s_axi_rvalid_reg_0\,
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
      I0 => w_pending_reg_n_0,
      I1 => s_axi_aresetn,
      I2 => \^s_axi_bvalid_reg_0\,
      O => s_axi_wready
    );
\scratch[15]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0000000800000000"
    )
        port map (
      I0 => \scratch[31]_i_2_n_0\,
      I1 => p_1_in_0,
      I2 => aw_address(0),
      I3 => aw_address(1),
      I4 => aw_address(4),
      I5 => aw_address(3),
      O => p_1_in(15)
    );
\scratch[23]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0000000800000000"
    )
        port map (
      I0 => \scratch[31]_i_2_n_0\,
      I1 => p_2_in,
      I2 => aw_address(0),
      I3 => aw_address(1),
      I4 => aw_address(4),
      I5 => aw_address(3),
      O => p_1_in(23)
    );
\scratch[31]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0000000800000000"
    )
        port map (
      I0 => \scratch[31]_i_2_n_0\,
      I1 => \w_strobes_reg_n_0_[3]\,
      I2 => aw_address(0),
      I3 => aw_address(1),
      I4 => aw_address(4),
      I5 => aw_address(3),
      O => p_1_in(31)
    );
\scratch[31]_i_2\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"11111000"
    )
        port map (
      I0 => burst_n_1,
      I1 => \scratch[31]_i_3_n_0\,
      I2 => aw_address(3),
      I3 => aw_address(2),
      I4 => aw_address(4),
      O => \scratch[31]_i_2_n_0\
    );
\scratch[31]_i_3\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FF45FFFFFFFFFFFF"
    )
        port map (
      I0 => aw_address(1),
      I1 => aw_address(0),
      I2 => aw_address(5),
      I3 => \^s_axi_bvalid_reg_0\,
      I4 => w_pending_reg_n_0,
      I5 => aw_pending,
      O => \scratch[31]_i_3_n_0\
    );
\scratch[7]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0000000800000000"
    )
        port map (
      I0 => \scratch[31]_i_2_n_0\,
      I1 => p_0_in_1,
      I2 => aw_address(0),
      I3 => aw_address(1),
      I4 => aw_address(4),
      I5 => aw_address(3),
      O => p_1_in(7)
    );
\scratch_reg[0]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => p_1_in(7),
      D => w_data(0),
      Q => scratch(0),
      R => p_0_in
    );
\scratch_reg[10]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => p_1_in(15),
      D => w_data(10),
      Q => scratch(10),
      R => p_0_in
    );
\scratch_reg[11]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => p_1_in(15),
      D => w_data(11),
      Q => scratch(11),
      R => p_0_in
    );
\scratch_reg[12]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => p_1_in(15),
      D => w_data(12),
      Q => scratch(12),
      R => p_0_in
    );
\scratch_reg[13]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => p_1_in(15),
      D => w_data(13),
      Q => scratch(13),
      R => p_0_in
    );
\scratch_reg[14]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => p_1_in(15),
      D => w_data(14),
      Q => scratch(14),
      R => p_0_in
    );
\scratch_reg[15]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => p_1_in(15),
      D => w_data(15),
      Q => scratch(15),
      R => p_0_in
    );
\scratch_reg[16]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => p_1_in(23),
      D => w_data(16),
      Q => scratch(16),
      R => p_0_in
    );
\scratch_reg[17]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => p_1_in(23),
      D => w_data(17),
      Q => scratch(17),
      R => p_0_in
    );
\scratch_reg[18]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => p_1_in(23),
      D => w_data(18),
      Q => scratch(18),
      R => p_0_in
    );
\scratch_reg[19]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => p_1_in(23),
      D => w_data(19),
      Q => scratch(19),
      R => p_0_in
    );
\scratch_reg[1]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => p_1_in(7),
      D => w_data(1),
      Q => scratch(1),
      R => p_0_in
    );
\scratch_reg[20]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => p_1_in(23),
      D => w_data(20),
      Q => scratch(20),
      R => p_0_in
    );
\scratch_reg[21]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => p_1_in(23),
      D => w_data(21),
      Q => scratch(21),
      R => p_0_in
    );
\scratch_reg[22]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => p_1_in(23),
      D => w_data(22),
      Q => scratch(22),
      R => p_0_in
    );
\scratch_reg[23]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => p_1_in(23),
      D => w_data(23),
      Q => scratch(23),
      R => p_0_in
    );
\scratch_reg[24]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => p_1_in(31),
      D => w_data(24),
      Q => scratch(24),
      R => p_0_in
    );
\scratch_reg[25]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => p_1_in(31),
      D => w_data(25),
      Q => scratch(25),
      R => p_0_in
    );
\scratch_reg[26]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => p_1_in(31),
      D => w_data(26),
      Q => scratch(26),
      R => p_0_in
    );
\scratch_reg[27]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => p_1_in(31),
      D => w_data(27),
      Q => scratch(27),
      R => p_0_in
    );
\scratch_reg[28]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => p_1_in(31),
      D => w_data(28),
      Q => scratch(28),
      R => p_0_in
    );
\scratch_reg[29]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => p_1_in(31),
      D => w_data(29),
      Q => scratch(29),
      R => p_0_in
    );
\scratch_reg[2]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => p_1_in(7),
      D => w_data(2),
      Q => scratch(2),
      R => p_0_in
    );
\scratch_reg[30]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => p_1_in(31),
      D => w_data(30),
      Q => scratch(30),
      R => p_0_in
    );
\scratch_reg[31]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => p_1_in(31),
      D => w_data(31),
      Q => scratch(31),
      R => p_0_in
    );
\scratch_reg[3]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => p_1_in(7),
      D => w_data(3),
      Q => scratch(3),
      R => p_0_in
    );
\scratch_reg[4]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => p_1_in(7),
      D => w_data(4),
      Q => scratch(4),
      R => p_0_in
    );
\scratch_reg[5]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => p_1_in(7),
      D => w_data(5),
      Q => scratch(5),
      R => p_0_in
    );
\scratch_reg[6]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => p_1_in(7),
      D => w_data(6),
      Q => scratch(6),
      R => p_0_in
    );
\scratch_reg[7]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => p_1_in(7),
      D => w_data(7),
      Q => scratch(7),
      R => p_0_in
    );
\scratch_reg[8]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => p_1_in(15),
      D => w_data(8),
      Q => scratch(8),
      R => p_0_in
    );
\scratch_reg[9]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => p_1_in(15),
      D => w_data(9),
      Q => scratch(9),
      R => p_0_in
    );
\w_data[31]_i_1\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"02"
    )
        port map (
      I0 => s_axi_wvalid,
      I1 => \^s_axi_bvalid_reg_0\,
      I2 => w_pending_reg_n_0,
      O => w_pending0
    );
\w_data_reg[0]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(0),
      Q => w_data(0),
      R => p_0_in
    );
\w_data_reg[10]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(10),
      Q => w_data(10),
      R => p_0_in
    );
\w_data_reg[11]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(11),
      Q => w_data(11),
      R => p_0_in
    );
\w_data_reg[12]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(12),
      Q => w_data(12),
      R => p_0_in
    );
\w_data_reg[13]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(13),
      Q => w_data(13),
      R => p_0_in
    );
\w_data_reg[14]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(14),
      Q => w_data(14),
      R => p_0_in
    );
\w_data_reg[15]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(15),
      Q => w_data(15),
      R => p_0_in
    );
\w_data_reg[16]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(16),
      Q => w_data(16),
      R => p_0_in
    );
\w_data_reg[17]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(17),
      Q => w_data(17),
      R => p_0_in
    );
\w_data_reg[18]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(18),
      Q => w_data(18),
      R => p_0_in
    );
\w_data_reg[19]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(19),
      Q => w_data(19),
      R => p_0_in
    );
\w_data_reg[1]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(1),
      Q => w_data(1),
      R => p_0_in
    );
\w_data_reg[20]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(20),
      Q => w_data(20),
      R => p_0_in
    );
\w_data_reg[21]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(21),
      Q => w_data(21),
      R => p_0_in
    );
\w_data_reg[22]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(22),
      Q => w_data(22),
      R => p_0_in
    );
\w_data_reg[23]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(23),
      Q => w_data(23),
      R => p_0_in
    );
\w_data_reg[24]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(24),
      Q => w_data(24),
      R => p_0_in
    );
\w_data_reg[25]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(25),
      Q => w_data(25),
      R => p_0_in
    );
\w_data_reg[26]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(26),
      Q => w_data(26),
      R => p_0_in
    );
\w_data_reg[27]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(27),
      Q => w_data(27),
      R => p_0_in
    );
\w_data_reg[28]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(28),
      Q => w_data(28),
      R => p_0_in
    );
\w_data_reg[29]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(29),
      Q => w_data(29),
      R => p_0_in
    );
\w_data_reg[2]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(2),
      Q => w_data(2),
      R => p_0_in
    );
\w_data_reg[30]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(30),
      Q => w_data(30),
      R => p_0_in
    );
\w_data_reg[31]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(31),
      Q => w_data(31),
      R => p_0_in
    );
\w_data_reg[3]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(3),
      Q => w_data(3),
      R => p_0_in
    );
\w_data_reg[4]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(4),
      Q => w_data(4),
      R => p_0_in
    );
\w_data_reg[5]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(5),
      Q => w_data(5),
      R => p_0_in
    );
\w_data_reg[6]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(6),
      Q => w_data(6),
      R => p_0_in
    );
\w_data_reg[7]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(7),
      Q => w_data(7),
      R => p_0_in
    );
\w_data_reg[8]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(8),
      Q => w_data(8),
      R => p_0_in
    );
\w_data_reg[9]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wdata(9),
      Q => w_data(9),
      R => p_0_in
    );
w_pending_i_1: unisim.vcomponents.LUT4
    generic map(
      INIT => X"40FF"
    )
        port map (
      I0 => \^s_axi_bvalid_reg_0\,
      I1 => w_pending_reg_n_0,
      I2 => aw_pending,
      I3 => s_axi_aresetn,
      O => w_pending_i_1_n_0
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
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => '1',
      D => w_pending_i_2_n_0,
      Q => w_pending_reg_n_0,
      R => w_pending_i_1_n_0
    );
\w_strobes_reg[0]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wstrb(0),
      Q => p_0_in_1,
      R => p_0_in
    );
\w_strobes_reg[1]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wstrb(1),
      Q => p_1_in_0,
      R => p_0_in
    );
\w_strobes_reg[2]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wstrb(2),
      Q => p_2_in,
      R => p_0_in
    );
\w_strobes_reg[3]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
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
entity decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix is
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
    s_axi_rready : in STD_LOGIC;
    servo_pwm : out STD_LOGIC
  );
  attribute NotValidForBitStream : boolean;
  attribute NotValidForBitStream of decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix : entity is true;
  attribute CHECK_LICENSE_TYPE : string;
  attribute CHECK_LICENSE_TYPE of decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix : entity is "pwm_bench_probe_0,aura_pwm_probe,{}";
  attribute DowngradeIPIdentifiedWarnings : string;
  attribute DowngradeIPIdentifiedWarnings of decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix : entity is "yes";
  attribute IP_DEFINITION_SOURCE : string;
  attribute IP_DEFINITION_SOURCE of decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix : entity is "package_project";
  attribute X_CORE_INFO : string;
  attribute X_CORE_INFO of decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix : entity is "aura_pwm_probe,Vivado 2022.2";
end decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix;

architecture STRUCTURE of decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix is
  signal \<const0>\ : STD_LOGIC;
  signal \^s_axi_bresp\ : STD_LOGIC_VECTOR ( 1 to 1 );
  signal \^s_axi_rresp\ : STD_LOGIC_VECTOR ( 1 to 1 );
  attribute X_INTERFACE_INFO : string;
  attribute X_INTERFACE_INFO of s_axi_aclk : signal is "xilinx.com:signal:clock:1.0 s_axi_aclk CLK";
  attribute X_INTERFACE_PARAMETER : string;
  attribute X_INTERFACE_PARAMETER of s_axi_aclk : signal is "XIL_INTERFACENAME s_axi_aclk, ASSOCIATED_BUSIF S_AXI, ASSOCIATED_RESET s_axi_aresetn, FREQ_HZ 99999001, FREQ_TOLERANCE_HZ 0, PHASE 0.0, CLK_DOMAIN pwm_bench_PS_0_0_pl_clk0, INSERT_VIP 0";
  attribute X_INTERFACE_INFO of s_axi_aresetn : signal is "xilinx.com:signal:reset:1.0 s_axi_aresetn RST";
  attribute X_INTERFACE_PARAMETER of s_axi_aresetn : signal is "XIL_INTERFACENAME s_axi_aresetn, POLARITY ACTIVE_LOW, INSERT_VIP 0";
  attribute X_INTERFACE_INFO of s_axi_arready : signal is "xilinx.com:interface:aximm:1.0 S_AXI ARREADY";
  attribute X_INTERFACE_INFO of s_axi_arvalid : signal is "xilinx.com:interface:aximm:1.0 S_AXI ARVALID";
  attribute X_INTERFACE_INFO of s_axi_awready : signal is "xilinx.com:interface:aximm:1.0 S_AXI AWREADY";
  attribute X_INTERFACE_INFO of s_axi_awvalid : signal is "xilinx.com:interface:aximm:1.0 S_AXI AWVALID";
  attribute X_INTERFACE_INFO of s_axi_bready : signal is "xilinx.com:interface:aximm:1.0 S_AXI BREADY";
  attribute X_INTERFACE_INFO of s_axi_bvalid : signal is "xilinx.com:interface:aximm:1.0 S_AXI BVALID";
  attribute X_INTERFACE_INFO of s_axi_rready : signal is "xilinx.com:interface:aximm:1.0 S_AXI RREADY";
  attribute X_INTERFACE_PARAMETER of s_axi_rready : signal is "XIL_INTERFACENAME S_AXI, PROTOCOL AXI4LITE, DATA_WIDTH 32, ADDR_WIDTH 12, READ_WRITE_MODE READ_WRITE, FREQ_HZ 99999001, ID_WIDTH 0, AWUSER_WIDTH 0, ARUSER_WIDTH 0, WUSER_WIDTH 0, RUSER_WIDTH 0, BUSER_WIDTH 0, HAS_BURST 0, HAS_LOCK 0, HAS_PROT 1, HAS_CACHE 0, HAS_QOS 0, HAS_REGION 0, HAS_WSTRB 1, HAS_BRESP 1, HAS_RRESP 1, SUPPORTS_NARROW_BURST 0, NUM_READ_OUTSTANDING 1, NUM_WRITE_OUTSTANDING 1, MAX_BURST_LENGTH 1, PHASE 0.0, CLK_DOMAIN pwm_bench_PS_0_0_pl_clk0, NUM_READ_THREADS 4, NUM_WRITE_THREADS 4, RUSER_BITS_PER_BYTE 0, WUSER_BITS_PER_BYTE 0, INSERT_VIP 0";
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
inst: entity work.decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_aura_pwm_probe
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
      s_axi_wvalid => s_axi_wvalid,
      servo_pwm => servo_pwm
    );
end STRUCTURE;
