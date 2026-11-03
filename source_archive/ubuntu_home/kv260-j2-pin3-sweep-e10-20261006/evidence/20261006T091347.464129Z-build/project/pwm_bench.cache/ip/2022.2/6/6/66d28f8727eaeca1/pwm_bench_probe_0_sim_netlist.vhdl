-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- --------------------------------------------------------------------------------
-- Tool Version: Vivado v.2022.2 (lin64) Build 3671981 Fri Oct 14 04:59:54 MDT 2022
-- Date        : Tue Oct  6 02:16:07 2026
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
    \w_data_reg[0]\ : out STD_LOGIC;
    \w_data_reg[30]\ : out STD_LOGIC;
    \aw_address_reg[1]\ : out STD_LOGIC;
    \w_data_reg[12]\ : out STD_LOGIC;
    \w_data_reg[21]\ : out STD_LOGIC;
    \aw_address_reg[9]\ : out STD_LOGIC;
    D : out STD_LOGIC_VECTOR ( 31 downto 0 );
    servo_pwm : out STD_LOGIC;
    \s_axi_bresp_reg[1]\ : out STD_LOGIC;
    s_axi_aclk : in STD_LOGIC;
    s_axi_aresetn : in STD_LOGIC;
    Q : in STD_LOGIC_VECTOR ( 11 downto 0 );
    \s_axi_bresp[1]_i_5\ : in STD_LOGIC_VECTOR ( 31 downto 0 );
    \s_axi_bresp[1]_i_9_0\ : in STD_LOGIC_VECTOR ( 3 downto 0 );
    \s_axi_bresp_reg[1]_0\ : in STD_LOGIC;
    \s_axi_bresp_reg[1]_1\ : in STD_LOGIC;
    aw_pending : in STD_LOGIC;
    \s_axi_rdata_reg[17]\ : in STD_LOGIC;
    s_axi_araddr : in STD_LOGIC_VECTOR ( 4 downto 0 );
    \s_axi_rdata_reg[17]_0\ : in STD_LOGIC;
    \s_axi_rdata_reg[31]\ : in STD_LOGIC_VECTOR ( 29 downto 0 );
    \s_axi_rdata_reg[17]_1\ : in STD_LOGIC;
    \s_axi_rdata_reg[2]\ : in STD_LOGIC;
    \s_axi_rdata_reg[2]_0\ : in STD_LOGIC;
    \s_axi_rdata_reg[2]_1\ : in STD_LOGIC;
    \s_axi_rdata_reg[2]_2\ : in STD_LOGIC;
    \s_axi_rdata_reg[3]\ : in STD_LOGIC;
    \s_axi_rdata_reg[3]_0\ : in STD_LOGIC;
    \s_axi_rdata_reg[3]_1\ : in STD_LOGIC;
    \s_axi_rdata_reg[5]\ : in STD_LOGIC;
    \s_axi_rdata_reg[6]\ : in STD_LOGIC;
    \s_axi_rdata_reg[6]_0\ : in STD_LOGIC;
    \s_axi_rdata_reg[6]_1\ : in STD_LOGIC;
    \s_axi_rdata_reg[15]\ : in STD_LOGIC;
    \s_axi_rdata_reg[15]_0\ : in STD_LOGIC;
    \s_axi_rdata_reg[19]\ : in STD_LOGIC;
    \s_axi_rdata_reg[18]\ : in STD_LOGIC;
    \s_axi_rdata_reg[12]\ : in STD_LOGIC;
    \s_axi_rdata_reg[12]_0\ : in STD_LOGIC;
    \s_axi_rdata_reg[5]_0\ : in STD_LOGIC;
    \s_axi_rdata_reg[1]\ : in STD_LOGIC;
    \s_axi_rdata_reg[14]\ : in STD_LOGIC;
    \s_axi_rdata_reg[4]\ : in STD_LOGIC;
    \s_axi_rdata_reg[4]_0\ : in STD_LOGIC;
    \s_axi_rdata_reg[4]_1\ : in STD_LOGIC;
    \s_axi_rdata_reg[1]_0\ : in STD_LOGIC;
    \s_axi_rdata_reg[25]\ : in STD_LOGIC;
    \s_axi_rdata_reg[26]\ : in STD_LOGIC;
    s_axi_bresp : in STD_LOGIC_VECTOR ( 0 to 0 );
    \s_axi_bresp_reg[1]_2\ : in STD_LOGIC;
    \s_axi_bresp_reg[1]_3\ : in STD_LOGIC
  );
end decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_pwm_burst;

architecture STRUCTURE of decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_pwm_burst is
  signal \^aw_address_reg[1]\ : STD_LOGIC;
  signal \^aw_address_reg[9]\ : STD_LOGIC;
  signal busy : STD_LOGIC;
  signal busy_i_1_n_0 : STD_LOGIC;
  signal data0 : STD_LOGIC_VECTOR ( 31 downto 1 );
  signal dwell_frame : STD_LOGIC_VECTOR ( 31 downto 0 );
  signal \dwell_frame[31]_i_10_n_0\ : STD_LOGIC;
  signal \dwell_frame[31]_i_11_n_0\ : STD_LOGIC;
  signal \dwell_frame[31]_i_12_n_0\ : STD_LOGIC;
  signal \dwell_frame[31]_i_13_n_0\ : STD_LOGIC;
  signal \dwell_frame[31]_i_14_n_0\ : STD_LOGIC;
  signal \dwell_frame[31]_i_15_n_0\ : STD_LOGIC;
  signal \dwell_frame[31]_i_16_n_0\ : STD_LOGIC;
  signal \dwell_frame[31]_i_17_n_0\ : STD_LOGIC;
  signal \dwell_frame[31]_i_18_n_0\ : STD_LOGIC;
  signal \dwell_frame[31]_i_19_n_0\ : STD_LOGIC;
  signal \dwell_frame[31]_i_1_n_0\ : STD_LOGIC;
  signal \dwell_frame[31]_i_20_n_0\ : STD_LOGIC;
  signal \dwell_frame[31]_i_21_n_0\ : STD_LOGIC;
  signal \dwell_frame[31]_i_2_n_0\ : STD_LOGIC;
  signal \dwell_frame[31]_i_4_n_0\ : STD_LOGIC;
  signal \dwell_frame[31]_i_5_n_0\ : STD_LOGIC;
  signal \dwell_frame[31]_i_6_n_0\ : STD_LOGIC;
  signal \dwell_frame[31]_i_7_n_0\ : STD_LOGIC;
  signal \dwell_frame[31]_i_8_n_0\ : STD_LOGIC;
  signal dwell_frame_0 : STD_LOGIC_VECTOR ( 31 downto 0 );
  signal \dwell_frame_reg[16]_i_2_n_0\ : STD_LOGIC;
  signal \dwell_frame_reg[16]_i_2_n_1\ : STD_LOGIC;
  signal \dwell_frame_reg[16]_i_2_n_2\ : STD_LOGIC;
  signal \dwell_frame_reg[16]_i_2_n_3\ : STD_LOGIC;
  signal \dwell_frame_reg[16]_i_2_n_4\ : STD_LOGIC;
  signal \dwell_frame_reg[16]_i_2_n_5\ : STD_LOGIC;
  signal \dwell_frame_reg[16]_i_2_n_6\ : STD_LOGIC;
  signal \dwell_frame_reg[16]_i_2_n_7\ : STD_LOGIC;
  signal \dwell_frame_reg[24]_i_2_n_0\ : STD_LOGIC;
  signal \dwell_frame_reg[24]_i_2_n_1\ : STD_LOGIC;
  signal \dwell_frame_reg[24]_i_2_n_2\ : STD_LOGIC;
  signal \dwell_frame_reg[24]_i_2_n_3\ : STD_LOGIC;
  signal \dwell_frame_reg[24]_i_2_n_4\ : STD_LOGIC;
  signal \dwell_frame_reg[24]_i_2_n_5\ : STD_LOGIC;
  signal \dwell_frame_reg[24]_i_2_n_6\ : STD_LOGIC;
  signal \dwell_frame_reg[24]_i_2_n_7\ : STD_LOGIC;
  signal \dwell_frame_reg[31]_i_9_n_2\ : STD_LOGIC;
  signal \dwell_frame_reg[31]_i_9_n_3\ : STD_LOGIC;
  signal \dwell_frame_reg[31]_i_9_n_4\ : STD_LOGIC;
  signal \dwell_frame_reg[31]_i_9_n_5\ : STD_LOGIC;
  signal \dwell_frame_reg[31]_i_9_n_6\ : STD_LOGIC;
  signal \dwell_frame_reg[31]_i_9_n_7\ : STD_LOGIC;
  signal \dwell_frame_reg[8]_i_2_n_0\ : STD_LOGIC;
  signal \dwell_frame_reg[8]_i_2_n_1\ : STD_LOGIC;
  signal \dwell_frame_reg[8]_i_2_n_2\ : STD_LOGIC;
  signal \dwell_frame_reg[8]_i_2_n_3\ : STD_LOGIC;
  signal \dwell_frame_reg[8]_i_2_n_4\ : STD_LOGIC;
  signal \dwell_frame_reg[8]_i_2_n_5\ : STD_LOGIC;
  signal \dwell_frame_reg[8]_i_2_n_6\ : STD_LOGIC;
  signal \dwell_frame_reg[8]_i_2_n_7\ : STD_LOGIC;
  signal \i__carry__0_i_10_n_0\ : STD_LOGIC;
  signal \i__carry__0_i_10_n_1\ : STD_LOGIC;
  signal \i__carry__0_i_10_n_2\ : STD_LOGIC;
  signal \i__carry__0_i_10_n_3\ : STD_LOGIC;
  signal \i__carry__0_i_10_n_4\ : STD_LOGIC;
  signal \i__carry__0_i_10_n_5\ : STD_LOGIC;
  signal \i__carry__0_i_10_n_6\ : STD_LOGIC;
  signal \i__carry__0_i_10_n_7\ : STD_LOGIC;
  signal \i__carry__0_i_11_n_2\ : STD_LOGIC;
  signal \i__carry__0_i_11_n_3\ : STD_LOGIC;
  signal \i__carry__0_i_11_n_4\ : STD_LOGIC;
  signal \i__carry__0_i_11_n_5\ : STD_LOGIC;
  signal \i__carry__0_i_11_n_6\ : STD_LOGIC;
  signal \i__carry__0_i_11_n_7\ : STD_LOGIC;
  signal \i__carry__0_i_1_n_0\ : STD_LOGIC;
  signal \i__carry__0_i_2_n_0\ : STD_LOGIC;
  signal \i__carry__0_i_3_n_0\ : STD_LOGIC;
  signal \i__carry__0_i_4_n_0\ : STD_LOGIC;
  signal \i__carry__0_i_5_n_0\ : STD_LOGIC;
  signal \i__carry__0_i_6_n_0\ : STD_LOGIC;
  signal \i__carry__0_i_7_n_0\ : STD_LOGIC;
  signal \i__carry__0_i_8_n_0\ : STD_LOGIC;
  signal \i__carry__0_i_9_n_0\ : STD_LOGIC;
  signal \i__carry_i_10_n_0\ : STD_LOGIC;
  signal \i__carry_i_11_n_0\ : STD_LOGIC;
  signal \i__carry_i_12_n_0\ : STD_LOGIC;
  signal \i__carry_i_13_n_0\ : STD_LOGIC;
  signal \i__carry_i_14_n_0\ : STD_LOGIC;
  signal \i__carry_i_15_n_0\ : STD_LOGIC;
  signal \i__carry_i_16_n_0\ : STD_LOGIC;
  signal \i__carry_i_16_n_1\ : STD_LOGIC;
  signal \i__carry_i_16_n_2\ : STD_LOGIC;
  signal \i__carry_i_16_n_3\ : STD_LOGIC;
  signal \i__carry_i_16_n_4\ : STD_LOGIC;
  signal \i__carry_i_16_n_5\ : STD_LOGIC;
  signal \i__carry_i_16_n_6\ : STD_LOGIC;
  signal \i__carry_i_16_n_7\ : STD_LOGIC;
  signal \i__carry_i_17_n_0\ : STD_LOGIC;
  signal \i__carry_i_17_n_1\ : STD_LOGIC;
  signal \i__carry_i_17_n_2\ : STD_LOGIC;
  signal \i__carry_i_17_n_3\ : STD_LOGIC;
  signal \i__carry_i_17_n_4\ : STD_LOGIC;
  signal \i__carry_i_17_n_5\ : STD_LOGIC;
  signal \i__carry_i_17_n_6\ : STD_LOGIC;
  signal \i__carry_i_17_n_7\ : STD_LOGIC;
  signal \i__carry_i_1_n_0\ : STD_LOGIC;
  signal \i__carry_i_2_n_0\ : STD_LOGIC;
  signal \i__carry_i_3_n_0\ : STD_LOGIC;
  signal \i__carry_i_4_n_0\ : STD_LOGIC;
  signal \i__carry_i_5_n_0\ : STD_LOGIC;
  signal \i__carry_i_6_n_0\ : STD_LOGIC;
  signal \i__carry_i_7_n_0\ : STD_LOGIC;
  signal \i__carry_i_8_n_0\ : STD_LOGIC;
  signal \i__carry_i_9_n_0\ : STD_LOGIC;
  signal p_0_in : STD_LOGIC_VECTOR ( 31 downto 0 );
  signal \phase[0]_i_1_n_0\ : STD_LOGIC;
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
  signal \pwm0_inferred__0/i__carry__0_n_0\ : STD_LOGIC;
  signal \pwm0_inferred__0/i__carry__0_n_1\ : STD_LOGIC;
  signal \pwm0_inferred__0/i__carry__0_n_2\ : STD_LOGIC;
  signal \pwm0_inferred__0/i__carry__0_n_3\ : STD_LOGIC;
  signal \pwm0_inferred__0/i__carry__0_n_4\ : STD_LOGIC;
  signal \pwm0_inferred__0/i__carry__0_n_5\ : STD_LOGIC;
  signal \pwm0_inferred__0/i__carry__0_n_6\ : STD_LOGIC;
  signal \pwm0_inferred__0/i__carry__0_n_7\ : STD_LOGIC;
  signal \pwm0_inferred__0/i__carry_n_0\ : STD_LOGIC;
  signal \pwm0_inferred__0/i__carry_n_1\ : STD_LOGIC;
  signal \pwm0_inferred__0/i__carry_n_2\ : STD_LOGIC;
  signal \pwm0_inferred__0/i__carry_n_3\ : STD_LOGIC;
  signal \pwm0_inferred__0/i__carry_n_4\ : STD_LOGIC;
  signal \pwm0_inferred__0/i__carry_n_5\ : STD_LOGIC;
  signal \pwm0_inferred__0/i__carry_n_6\ : STD_LOGIC;
  signal \pwm0_inferred__0/i__carry_n_7\ : STD_LOGIC;
  signal pwm_i_1_n_0 : STD_LOGIC;
  signal pwm_i_2_n_0 : STD_LOGIC;
  signal pwm_i_3_n_0 : STD_LOGIC;
  signal pwm_i_4_n_0 : STD_LOGIC;
  signal pwm_i_5_n_0 : STD_LOGIC;
  signal pwm_i_6_n_0 : STD_LOGIC;
  signal pwm_i_7_n_0 : STD_LOGIC;
  signal pwm_i_8_n_0 : STD_LOGIC;
  signal pwm_i_9_n_0 : STD_LOGIC;
  signal \s_axi_bresp[1]_i_12_n_0\ : STD_LOGIC;
  signal \s_axi_bresp[1]_i_13_n_0\ : STD_LOGIC;
  signal \s_axi_bresp[1]_i_14_n_0\ : STD_LOGIC;
  signal \s_axi_bresp[1]_i_15_n_0\ : STD_LOGIC;
  signal \s_axi_bresp[1]_i_16_n_0\ : STD_LOGIC;
  signal \s_axi_bresp[1]_i_3_n_0\ : STD_LOGIC;
  signal \s_axi_bresp[1]_i_6_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[0]_i_2_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[10]_i_2_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[17]_i_2_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[1]_i_2_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[3]_i_2_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[4]_i_4_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[5]_i_3_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[8]_i_2_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[9]_i_3_n_0\ : STD_LOGIC;
  signal select_high : STD_LOGIC;
  signal select_high_i_1_n_0 : STD_LOGIC;
  signal \^servo_pwm\ : STD_LOGIC;
  signal \^w_data_reg[0]\ : STD_LOGIC;
  signal \^w_data_reg[12]\ : STD_LOGIC;
  signal \^w_data_reg[21]\ : STD_LOGIC;
  signal \^w_data_reg[30]\ : STD_LOGIC;
  signal \NLW_dwell_frame_reg[31]_i_9_CO_UNCONNECTED\ : STD_LOGIC_VECTOR ( 7 downto 6 );
  signal \NLW_dwell_frame_reg[31]_i_9_O_UNCONNECTED\ : STD_LOGIC_VECTOR ( 7 to 7 );
  signal \NLW_i__carry__0_i_11_CO_UNCONNECTED\ : STD_LOGIC_VECTOR ( 7 downto 6 );
  signal \NLW_i__carry__0_i_11_O_UNCONNECTED\ : STD_LOGIC_VECTOR ( 7 to 7 );
  signal \NLW_phase_reg[24]_i_1_CO_UNCONNECTED\ : STD_LOGIC_VECTOR ( 7 to 7 );
  signal \NLW_pwm0_inferred__0/i__carry_O_UNCONNECTED\ : STD_LOGIC_VECTOR ( 7 downto 0 );
  signal \NLW_pwm0_inferred__0/i__carry__0_O_UNCONNECTED\ : STD_LOGIC_VECTOR ( 7 downto 0 );
  attribute SOFT_HLUTNM : string;
  attribute SOFT_HLUTNM of \dwell_frame[0]_i_1\ : label is "soft_lutpair2";
  attribute SOFT_HLUTNM of \dwell_frame[10]_i_1\ : label is "soft_lutpair9";
  attribute SOFT_HLUTNM of \dwell_frame[11]_i_1\ : label is "soft_lutpair10";
  attribute SOFT_HLUTNM of \dwell_frame[12]_i_1\ : label is "soft_lutpair10";
  attribute SOFT_HLUTNM of \dwell_frame[13]_i_1\ : label is "soft_lutpair11";
  attribute SOFT_HLUTNM of \dwell_frame[14]_i_1\ : label is "soft_lutpair11";
  attribute SOFT_HLUTNM of \dwell_frame[15]_i_1\ : label is "soft_lutpair12";
  attribute SOFT_HLUTNM of \dwell_frame[16]_i_1\ : label is "soft_lutpair12";
  attribute SOFT_HLUTNM of \dwell_frame[17]_i_1\ : label is "soft_lutpair13";
  attribute SOFT_HLUTNM of \dwell_frame[18]_i_1\ : label is "soft_lutpair13";
  attribute SOFT_HLUTNM of \dwell_frame[19]_i_1\ : label is "soft_lutpair14";
  attribute SOFT_HLUTNM of \dwell_frame[1]_i_1\ : label is "soft_lutpair5";
  attribute SOFT_HLUTNM of \dwell_frame[20]_i_1\ : label is "soft_lutpair14";
  attribute SOFT_HLUTNM of \dwell_frame[21]_i_1\ : label is "soft_lutpair15";
  attribute SOFT_HLUTNM of \dwell_frame[22]_i_1\ : label is "soft_lutpair15";
  attribute SOFT_HLUTNM of \dwell_frame[23]_i_1\ : label is "soft_lutpair16";
  attribute SOFT_HLUTNM of \dwell_frame[24]_i_1\ : label is "soft_lutpair16";
  attribute SOFT_HLUTNM of \dwell_frame[25]_i_1\ : label is "soft_lutpair17";
  attribute SOFT_HLUTNM of \dwell_frame[26]_i_1\ : label is "soft_lutpair17";
  attribute SOFT_HLUTNM of \dwell_frame[27]_i_1\ : label is "soft_lutpair18";
  attribute SOFT_HLUTNM of \dwell_frame[28]_i_1\ : label is "soft_lutpair18";
  attribute SOFT_HLUTNM of \dwell_frame[29]_i_1\ : label is "soft_lutpair19";
  attribute SOFT_HLUTNM of \dwell_frame[2]_i_1\ : label is "soft_lutpair5";
  attribute SOFT_HLUTNM of \dwell_frame[30]_i_1\ : label is "soft_lutpair19";
  attribute SOFT_HLUTNM of \dwell_frame[3]_i_1\ : label is "soft_lutpair6";
  attribute SOFT_HLUTNM of \dwell_frame[4]_i_1\ : label is "soft_lutpair6";
  attribute SOFT_HLUTNM of \dwell_frame[5]_i_1\ : label is "soft_lutpair7";
  attribute SOFT_HLUTNM of \dwell_frame[6]_i_1\ : label is "soft_lutpair7";
  attribute SOFT_HLUTNM of \dwell_frame[7]_i_1\ : label is "soft_lutpair8";
  attribute SOFT_HLUTNM of \dwell_frame[8]_i_1\ : label is "soft_lutpair8";
  attribute SOFT_HLUTNM of \dwell_frame[9]_i_1\ : label is "soft_lutpair9";
  attribute ADDER_THRESHOLD : integer;
  attribute ADDER_THRESHOLD of \dwell_frame_reg[16]_i_2\ : label is 35;
  attribute ADDER_THRESHOLD of \dwell_frame_reg[24]_i_2\ : label is 35;
  attribute ADDER_THRESHOLD of \dwell_frame_reg[31]_i_9\ : label is 35;
  attribute ADDER_THRESHOLD of \dwell_frame_reg[8]_i_2\ : label is 35;
  attribute ADDER_THRESHOLD of \i__carry__0_i_10\ : label is 35;
  attribute ADDER_THRESHOLD of \i__carry__0_i_11\ : label is 35;
  attribute ADDER_THRESHOLD of \i__carry_i_16\ : label is 35;
  attribute ADDER_THRESHOLD of \i__carry_i_17\ : label is 35;
  attribute ADDER_THRESHOLD of \phase_reg[0]_i_2\ : label is 16;
  attribute ADDER_THRESHOLD of \phase_reg[16]_i_1\ : label is 16;
  attribute ADDER_THRESHOLD of \phase_reg[24]_i_1\ : label is 16;
  attribute ADDER_THRESHOLD of \phase_reg[8]_i_1\ : label is 16;
  attribute COMPARATOR_THRESHOLD : integer;
  attribute COMPARATOR_THRESHOLD of \pwm0_inferred__0/i__carry\ : label is 11;
  attribute COMPARATOR_THRESHOLD of \pwm0_inferred__0/i__carry__0\ : label is 11;
  attribute SOFT_HLUTNM of pwm_i_4 : label is "soft_lutpair4";
  attribute SOFT_HLUTNM of pwm_i_6 : label is "soft_lutpair4";
  attribute SOFT_HLUTNM of pwm_i_8 : label is "soft_lutpair1";
  attribute SOFT_HLUTNM of pwm_i_9 : label is "soft_lutpair0";
  attribute SOFT_HLUTNM of \s_axi_bresp[1]_i_10\ : label is "soft_lutpair0";
  attribute SOFT_HLUTNM of \s_axi_bresp[1]_i_11\ : label is "soft_lutpair1";
  attribute SOFT_HLUTNM of \s_axi_rdata[0]_i_1\ : label is "soft_lutpair2";
  attribute SOFT_HLUTNM of \s_axi_rdata[4]_i_4\ : label is "soft_lutpair3";
  attribute SOFT_HLUTNM of \s_axi_rdata[9]_i_3\ : label is "soft_lutpair3";
begin
  \aw_address_reg[1]\ <= \^aw_address_reg[1]\;
  \aw_address_reg[9]\ <= \^aw_address_reg[9]\;
  servo_pwm <= \^servo_pwm\;
  \w_data_reg[0]\ <= \^w_data_reg[0]\;
  \w_data_reg[12]\ <= \^w_data_reg[12]\;
  \w_data_reg[21]\ <= \^w_data_reg[21]\;
  \w_data_reg[30]\ <= \^w_data_reg[30]\;
busy_i_1: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FFFFFFFF00000004"
    )
        port map (
      I0 => pwm_i_5_n_0,
      I1 => \s_axi_bresp[1]_i_5\(1),
      I2 => \s_axi_bresp[1]_i_5\(11),
      I3 => \s_axi_bresp[1]_i_5\(9),
      I4 => \s_axi_bresp[1]_i_5\(10),
      I5 => busy,
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
\dwell_frame[0]_i_1\: unisim.vcomponents.LUT1
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => dwell_frame(0),
      O => dwell_frame_0(0)
    );
\dwell_frame[10]_i_1\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"8"
    )
        port map (
      I0 => \dwell_frame[31]_i_8_n_0\,
      I1 => data0(10),
      O => dwell_frame_0(10)
    );
\dwell_frame[11]_i_1\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"8"
    )
        port map (
      I0 => \dwell_frame[31]_i_8_n_0\,
      I1 => data0(11),
      O => dwell_frame_0(11)
    );
\dwell_frame[12]_i_1\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"8"
    )
        port map (
      I0 => \dwell_frame[31]_i_8_n_0\,
      I1 => data0(12),
      O => dwell_frame_0(12)
    );
\dwell_frame[13]_i_1\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"8"
    )
        port map (
      I0 => \dwell_frame[31]_i_8_n_0\,
      I1 => data0(13),
      O => dwell_frame_0(13)
    );
\dwell_frame[14]_i_1\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"8"
    )
        port map (
      I0 => \dwell_frame[31]_i_8_n_0\,
      I1 => data0(14),
      O => dwell_frame_0(14)
    );
\dwell_frame[15]_i_1\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"8"
    )
        port map (
      I0 => \dwell_frame[31]_i_8_n_0\,
      I1 => data0(15),
      O => dwell_frame_0(15)
    );
\dwell_frame[16]_i_1\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"8"
    )
        port map (
      I0 => \dwell_frame[31]_i_8_n_0\,
      I1 => data0(16),
      O => dwell_frame_0(16)
    );
\dwell_frame[17]_i_1\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"8"
    )
        port map (
      I0 => \dwell_frame[31]_i_8_n_0\,
      I1 => data0(17),
      O => dwell_frame_0(17)
    );
\dwell_frame[18]_i_1\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"8"
    )
        port map (
      I0 => \dwell_frame[31]_i_8_n_0\,
      I1 => data0(18),
      O => dwell_frame_0(18)
    );
\dwell_frame[19]_i_1\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"8"
    )
        port map (
      I0 => \dwell_frame[31]_i_8_n_0\,
      I1 => data0(19),
      O => dwell_frame_0(19)
    );
\dwell_frame[1]_i_1\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"8"
    )
        port map (
      I0 => \dwell_frame[31]_i_8_n_0\,
      I1 => data0(1),
      O => dwell_frame_0(1)
    );
\dwell_frame[20]_i_1\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"8"
    )
        port map (
      I0 => \dwell_frame[31]_i_8_n_0\,
      I1 => data0(20),
      O => dwell_frame_0(20)
    );
\dwell_frame[21]_i_1\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"8"
    )
        port map (
      I0 => \dwell_frame[31]_i_8_n_0\,
      I1 => data0(21),
      O => dwell_frame_0(21)
    );
\dwell_frame[22]_i_1\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"8"
    )
        port map (
      I0 => \dwell_frame[31]_i_8_n_0\,
      I1 => data0(22),
      O => dwell_frame_0(22)
    );
\dwell_frame[23]_i_1\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"8"
    )
        port map (
      I0 => \dwell_frame[31]_i_8_n_0\,
      I1 => data0(23),
      O => dwell_frame_0(23)
    );
\dwell_frame[24]_i_1\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"8"
    )
        port map (
      I0 => \dwell_frame[31]_i_8_n_0\,
      I1 => data0(24),
      O => dwell_frame_0(24)
    );
\dwell_frame[25]_i_1\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"8"
    )
        port map (
      I0 => \dwell_frame[31]_i_8_n_0\,
      I1 => data0(25),
      O => dwell_frame_0(25)
    );
\dwell_frame[26]_i_1\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"8"
    )
        port map (
      I0 => \dwell_frame[31]_i_8_n_0\,
      I1 => data0(26),
      O => dwell_frame_0(26)
    );
\dwell_frame[27]_i_1\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"8"
    )
        port map (
      I0 => \dwell_frame[31]_i_8_n_0\,
      I1 => data0(27),
      O => dwell_frame_0(27)
    );
\dwell_frame[28]_i_1\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"8"
    )
        port map (
      I0 => \dwell_frame[31]_i_8_n_0\,
      I1 => data0(28),
      O => dwell_frame_0(28)
    );
\dwell_frame[29]_i_1\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"8"
    )
        port map (
      I0 => \dwell_frame[31]_i_8_n_0\,
      I1 => data0(29),
      O => dwell_frame_0(29)
    );
\dwell_frame[2]_i_1\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"8"
    )
        port map (
      I0 => \dwell_frame[31]_i_8_n_0\,
      I1 => data0(2),
      O => dwell_frame_0(2)
    );
\dwell_frame[30]_i_1\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"8"
    )
        port map (
      I0 => \dwell_frame[31]_i_8_n_0\,
      I1 => data0(30),
      O => dwell_frame_0(30)
    );
\dwell_frame[31]_i_1\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"7F"
    )
        port map (
      I0 => s_axi_aresetn,
      I1 => busy,
      I2 => pwm_i_3_n_0,
      O => \dwell_frame[31]_i_1_n_0\
    );
\dwell_frame[31]_i_10\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"0400"
    )
        port map (
      I0 => phase_reg(7),
      I1 => phase_reg(6),
      I2 => phase_reg(4),
      I3 => phase_reg(5),
      O => \dwell_frame[31]_i_10_n_0\
    );
\dwell_frame[31]_i_11\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"0004"
    )
        port map (
      I0 => phase_reg(14),
      I1 => phase_reg(15),
      I2 => phase_reg(13),
      I3 => phase_reg(12),
      O => \dwell_frame[31]_i_11_n_0\
    );
\dwell_frame[31]_i_12\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"0100"
    )
        port map (
      I0 => phase_reg(23),
      I1 => phase_reg(22),
      I2 => phase_reg(21),
      I3 => phase_reg(20),
      O => \dwell_frame[31]_i_12_n_0\
    );
\dwell_frame[31]_i_13\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"0001"
    )
        port map (
      I0 => phase_reg(31),
      I1 => phase_reg(30),
      I2 => phase_reg(29),
      I3 => phase_reg(28),
      O => \dwell_frame[31]_i_13_n_0\
    );
\dwell_frame[31]_i_14\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FFFFFFFE"
    )
        port map (
      I0 => dwell_frame(10),
      I1 => dwell_frame(11),
      I2 => dwell_frame(8),
      I3 => dwell_frame(9),
      I4 => \dwell_frame[31]_i_18_n_0\,
      O => \dwell_frame[31]_i_14_n_0\
    );
\dwell_frame[31]_i_15\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FFFFFEFF"
    )
        port map (
      I0 => dwell_frame(2),
      I1 => dwell_frame(3),
      I2 => dwell_frame(1),
      I3 => dwell_frame(0),
      I4 => \dwell_frame[31]_i_19_n_0\,
      O => \dwell_frame[31]_i_15_n_0\
    );
\dwell_frame[31]_i_16\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FFFFFFFE"
    )
        port map (
      I0 => dwell_frame(26),
      I1 => dwell_frame(27),
      I2 => dwell_frame(24),
      I3 => dwell_frame(25),
      I4 => \dwell_frame[31]_i_20_n_0\,
      O => \dwell_frame[31]_i_16_n_0\
    );
\dwell_frame[31]_i_17\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FFFFFFFE"
    )
        port map (
      I0 => dwell_frame(18),
      I1 => dwell_frame(19),
      I2 => dwell_frame(16),
      I3 => dwell_frame(17),
      I4 => \dwell_frame[31]_i_21_n_0\,
      O => \dwell_frame[31]_i_17_n_0\
    );
\dwell_frame[31]_i_18\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"FFFE"
    )
        port map (
      I0 => dwell_frame(13),
      I1 => dwell_frame(12),
      I2 => dwell_frame(15),
      I3 => dwell_frame(14),
      O => \dwell_frame[31]_i_18_n_0\
    );
\dwell_frame[31]_i_19\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"FFF7"
    )
        port map (
      I0 => dwell_frame(5),
      I1 => dwell_frame(4),
      I2 => dwell_frame(7),
      I3 => dwell_frame(6),
      O => \dwell_frame[31]_i_19_n_0\
    );
\dwell_frame[31]_i_2\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"8000"
    )
        port map (
      I0 => \dwell_frame[31]_i_4_n_0\,
      I1 => \dwell_frame[31]_i_5_n_0\,
      I2 => \dwell_frame[31]_i_6_n_0\,
      I3 => \dwell_frame[31]_i_7_n_0\,
      O => \dwell_frame[31]_i_2_n_0\
    );
\dwell_frame[31]_i_20\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"FFFE"
    )
        port map (
      I0 => dwell_frame(29),
      I1 => dwell_frame(28),
      I2 => dwell_frame(31),
      I3 => dwell_frame(30),
      O => \dwell_frame[31]_i_20_n_0\
    );
\dwell_frame[31]_i_21\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"FFFE"
    )
        port map (
      I0 => dwell_frame(21),
      I1 => dwell_frame(20),
      I2 => dwell_frame(23),
      I3 => dwell_frame(22),
      O => \dwell_frame[31]_i_21_n_0\
    );
\dwell_frame[31]_i_3\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"8"
    )
        port map (
      I0 => \dwell_frame[31]_i_8_n_0\,
      I1 => data0(31),
      O => dwell_frame_0(31)
    );
\dwell_frame[31]_i_4\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"00800000"
    )
        port map (
      I0 => phase_reg(0),
      I1 => phase_reg(1),
      I2 => phase_reg(3),
      I3 => phase_reg(2),
      I4 => \dwell_frame[31]_i_10_n_0\,
      O => \dwell_frame[31]_i_4_n_0\
    );
\dwell_frame[31]_i_5\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"00100000"
    )
        port map (
      I0 => phase_reg(8),
      I1 => phase_reg(9),
      I2 => phase_reg(10),
      I3 => phase_reg(11),
      I4 => \dwell_frame[31]_i_11_n_0\,
      O => \dwell_frame[31]_i_5_n_0\
    );
\dwell_frame[31]_i_6\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"20000000"
    )
        port map (
      I0 => phase_reg(17),
      I1 => phase_reg(16),
      I2 => phase_reg(18),
      I3 => phase_reg(19),
      I4 => \dwell_frame[31]_i_12_n_0\,
      O => \dwell_frame[31]_i_6_n_0\
    );
\dwell_frame[31]_i_7\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"00010000"
    )
        port map (
      I0 => phase_reg(24),
      I1 => phase_reg(25),
      I2 => phase_reg(26),
      I3 => phase_reg(27),
      I4 => \dwell_frame[31]_i_13_n_0\,
      O => \dwell_frame[31]_i_7_n_0\
    );
\dwell_frame[31]_i_8\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"FFFE"
    )
        port map (
      I0 => \dwell_frame[31]_i_14_n_0\,
      I1 => \dwell_frame[31]_i_15_n_0\,
      I2 => \dwell_frame[31]_i_16_n_0\,
      I3 => \dwell_frame[31]_i_17_n_0\,
      O => \dwell_frame[31]_i_8_n_0\
    );
\dwell_frame[3]_i_1\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"8"
    )
        port map (
      I0 => \dwell_frame[31]_i_8_n_0\,
      I1 => data0(3),
      O => dwell_frame_0(3)
    );
\dwell_frame[4]_i_1\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"8"
    )
        port map (
      I0 => \dwell_frame[31]_i_8_n_0\,
      I1 => data0(4),
      O => dwell_frame_0(4)
    );
\dwell_frame[5]_i_1\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"8"
    )
        port map (
      I0 => \dwell_frame[31]_i_8_n_0\,
      I1 => data0(5),
      O => dwell_frame_0(5)
    );
\dwell_frame[6]_i_1\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"8"
    )
        port map (
      I0 => \dwell_frame[31]_i_8_n_0\,
      I1 => data0(6),
      O => dwell_frame_0(6)
    );
\dwell_frame[7]_i_1\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"8"
    )
        port map (
      I0 => \dwell_frame[31]_i_8_n_0\,
      I1 => data0(7),
      O => dwell_frame_0(7)
    );
\dwell_frame[8]_i_1\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"8"
    )
        port map (
      I0 => \dwell_frame[31]_i_8_n_0\,
      I1 => data0(8),
      O => dwell_frame_0(8)
    );
\dwell_frame[9]_i_1\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"8"
    )
        port map (
      I0 => \dwell_frame[31]_i_8_n_0\,
      I1 => data0(9),
      O => dwell_frame_0(9)
    );
\dwell_frame_reg[0]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \dwell_frame[31]_i_2_n_0\,
      D => dwell_frame_0(0),
      Q => dwell_frame(0),
      R => \dwell_frame[31]_i_1_n_0\
    );
\dwell_frame_reg[10]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \dwell_frame[31]_i_2_n_0\,
      D => dwell_frame_0(10),
      Q => dwell_frame(10),
      R => \dwell_frame[31]_i_1_n_0\
    );
\dwell_frame_reg[11]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \dwell_frame[31]_i_2_n_0\,
      D => dwell_frame_0(11),
      Q => dwell_frame(11),
      R => \dwell_frame[31]_i_1_n_0\
    );
\dwell_frame_reg[12]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \dwell_frame[31]_i_2_n_0\,
      D => dwell_frame_0(12),
      Q => dwell_frame(12),
      R => \dwell_frame[31]_i_1_n_0\
    );
\dwell_frame_reg[13]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \dwell_frame[31]_i_2_n_0\,
      D => dwell_frame_0(13),
      Q => dwell_frame(13),
      R => \dwell_frame[31]_i_1_n_0\
    );
\dwell_frame_reg[14]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \dwell_frame[31]_i_2_n_0\,
      D => dwell_frame_0(14),
      Q => dwell_frame(14),
      R => \dwell_frame[31]_i_1_n_0\
    );
\dwell_frame_reg[15]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \dwell_frame[31]_i_2_n_0\,
      D => dwell_frame_0(15),
      Q => dwell_frame(15),
      R => \dwell_frame[31]_i_1_n_0\
    );
\dwell_frame_reg[16]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \dwell_frame[31]_i_2_n_0\,
      D => dwell_frame_0(16),
      Q => dwell_frame(16),
      R => \dwell_frame[31]_i_1_n_0\
    );
\dwell_frame_reg[16]_i_2\: unisim.vcomponents.CARRY8
     port map (
      CI => \dwell_frame_reg[8]_i_2_n_0\,
      CI_TOP => '0',
      CO(7) => \dwell_frame_reg[16]_i_2_n_0\,
      CO(6) => \dwell_frame_reg[16]_i_2_n_1\,
      CO(5) => \dwell_frame_reg[16]_i_2_n_2\,
      CO(4) => \dwell_frame_reg[16]_i_2_n_3\,
      CO(3) => \dwell_frame_reg[16]_i_2_n_4\,
      CO(2) => \dwell_frame_reg[16]_i_2_n_5\,
      CO(1) => \dwell_frame_reg[16]_i_2_n_6\,
      CO(0) => \dwell_frame_reg[16]_i_2_n_7\,
      DI(7 downto 0) => B"00000000",
      O(7 downto 0) => data0(16 downto 9),
      S(7 downto 0) => dwell_frame(16 downto 9)
    );
\dwell_frame_reg[17]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \dwell_frame[31]_i_2_n_0\,
      D => dwell_frame_0(17),
      Q => dwell_frame(17),
      R => \dwell_frame[31]_i_1_n_0\
    );
\dwell_frame_reg[18]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \dwell_frame[31]_i_2_n_0\,
      D => dwell_frame_0(18),
      Q => dwell_frame(18),
      R => \dwell_frame[31]_i_1_n_0\
    );
\dwell_frame_reg[19]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \dwell_frame[31]_i_2_n_0\,
      D => dwell_frame_0(19),
      Q => dwell_frame(19),
      R => \dwell_frame[31]_i_1_n_0\
    );
\dwell_frame_reg[1]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \dwell_frame[31]_i_2_n_0\,
      D => dwell_frame_0(1),
      Q => dwell_frame(1),
      R => \dwell_frame[31]_i_1_n_0\
    );
\dwell_frame_reg[20]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \dwell_frame[31]_i_2_n_0\,
      D => dwell_frame_0(20),
      Q => dwell_frame(20),
      R => \dwell_frame[31]_i_1_n_0\
    );
\dwell_frame_reg[21]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \dwell_frame[31]_i_2_n_0\,
      D => dwell_frame_0(21),
      Q => dwell_frame(21),
      R => \dwell_frame[31]_i_1_n_0\
    );
\dwell_frame_reg[22]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \dwell_frame[31]_i_2_n_0\,
      D => dwell_frame_0(22),
      Q => dwell_frame(22),
      R => \dwell_frame[31]_i_1_n_0\
    );
\dwell_frame_reg[23]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \dwell_frame[31]_i_2_n_0\,
      D => dwell_frame_0(23),
      Q => dwell_frame(23),
      R => \dwell_frame[31]_i_1_n_0\
    );
\dwell_frame_reg[24]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \dwell_frame[31]_i_2_n_0\,
      D => dwell_frame_0(24),
      Q => dwell_frame(24),
      R => \dwell_frame[31]_i_1_n_0\
    );
\dwell_frame_reg[24]_i_2\: unisim.vcomponents.CARRY8
     port map (
      CI => \dwell_frame_reg[16]_i_2_n_0\,
      CI_TOP => '0',
      CO(7) => \dwell_frame_reg[24]_i_2_n_0\,
      CO(6) => \dwell_frame_reg[24]_i_2_n_1\,
      CO(5) => \dwell_frame_reg[24]_i_2_n_2\,
      CO(4) => \dwell_frame_reg[24]_i_2_n_3\,
      CO(3) => \dwell_frame_reg[24]_i_2_n_4\,
      CO(2) => \dwell_frame_reg[24]_i_2_n_5\,
      CO(1) => \dwell_frame_reg[24]_i_2_n_6\,
      CO(0) => \dwell_frame_reg[24]_i_2_n_7\,
      DI(7 downto 0) => B"00000000",
      O(7 downto 0) => data0(24 downto 17),
      S(7 downto 0) => dwell_frame(24 downto 17)
    );
\dwell_frame_reg[25]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \dwell_frame[31]_i_2_n_0\,
      D => dwell_frame_0(25),
      Q => dwell_frame(25),
      R => \dwell_frame[31]_i_1_n_0\
    );
\dwell_frame_reg[26]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \dwell_frame[31]_i_2_n_0\,
      D => dwell_frame_0(26),
      Q => dwell_frame(26),
      R => \dwell_frame[31]_i_1_n_0\
    );
\dwell_frame_reg[27]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \dwell_frame[31]_i_2_n_0\,
      D => dwell_frame_0(27),
      Q => dwell_frame(27),
      R => \dwell_frame[31]_i_1_n_0\
    );
\dwell_frame_reg[28]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \dwell_frame[31]_i_2_n_0\,
      D => dwell_frame_0(28),
      Q => dwell_frame(28),
      R => \dwell_frame[31]_i_1_n_0\
    );
\dwell_frame_reg[29]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \dwell_frame[31]_i_2_n_0\,
      D => dwell_frame_0(29),
      Q => dwell_frame(29),
      R => \dwell_frame[31]_i_1_n_0\
    );
\dwell_frame_reg[2]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \dwell_frame[31]_i_2_n_0\,
      D => dwell_frame_0(2),
      Q => dwell_frame(2),
      R => \dwell_frame[31]_i_1_n_0\
    );
\dwell_frame_reg[30]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \dwell_frame[31]_i_2_n_0\,
      D => dwell_frame_0(30),
      Q => dwell_frame(30),
      R => \dwell_frame[31]_i_1_n_0\
    );
\dwell_frame_reg[31]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \dwell_frame[31]_i_2_n_0\,
      D => dwell_frame_0(31),
      Q => dwell_frame(31),
      R => \dwell_frame[31]_i_1_n_0\
    );
\dwell_frame_reg[31]_i_9\: unisim.vcomponents.CARRY8
     port map (
      CI => \dwell_frame_reg[24]_i_2_n_0\,
      CI_TOP => '0',
      CO(7 downto 6) => \NLW_dwell_frame_reg[31]_i_9_CO_UNCONNECTED\(7 downto 6),
      CO(5) => \dwell_frame_reg[31]_i_9_n_2\,
      CO(4) => \dwell_frame_reg[31]_i_9_n_3\,
      CO(3) => \dwell_frame_reg[31]_i_9_n_4\,
      CO(2) => \dwell_frame_reg[31]_i_9_n_5\,
      CO(1) => \dwell_frame_reg[31]_i_9_n_6\,
      CO(0) => \dwell_frame_reg[31]_i_9_n_7\,
      DI(7 downto 0) => B"00000000",
      O(7) => \NLW_dwell_frame_reg[31]_i_9_O_UNCONNECTED\(7),
      O(6 downto 0) => data0(31 downto 25),
      S(7) => '0',
      S(6 downto 0) => dwell_frame(31 downto 25)
    );
\dwell_frame_reg[3]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \dwell_frame[31]_i_2_n_0\,
      D => dwell_frame_0(3),
      Q => dwell_frame(3),
      R => \dwell_frame[31]_i_1_n_0\
    );
\dwell_frame_reg[4]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \dwell_frame[31]_i_2_n_0\,
      D => dwell_frame_0(4),
      Q => dwell_frame(4),
      R => \dwell_frame[31]_i_1_n_0\
    );
\dwell_frame_reg[5]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \dwell_frame[31]_i_2_n_0\,
      D => dwell_frame_0(5),
      Q => dwell_frame(5),
      R => \dwell_frame[31]_i_1_n_0\
    );
\dwell_frame_reg[6]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \dwell_frame[31]_i_2_n_0\,
      D => dwell_frame_0(6),
      Q => dwell_frame(6),
      R => \dwell_frame[31]_i_1_n_0\
    );
\dwell_frame_reg[7]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \dwell_frame[31]_i_2_n_0\,
      D => dwell_frame_0(7),
      Q => dwell_frame(7),
      R => \dwell_frame[31]_i_1_n_0\
    );
\dwell_frame_reg[8]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \dwell_frame[31]_i_2_n_0\,
      D => dwell_frame_0(8),
      Q => dwell_frame(8),
      R => \dwell_frame[31]_i_1_n_0\
    );
\dwell_frame_reg[8]_i_2\: unisim.vcomponents.CARRY8
     port map (
      CI => dwell_frame(0),
      CI_TOP => '0',
      CO(7) => \dwell_frame_reg[8]_i_2_n_0\,
      CO(6) => \dwell_frame_reg[8]_i_2_n_1\,
      CO(5) => \dwell_frame_reg[8]_i_2_n_2\,
      CO(4) => \dwell_frame_reg[8]_i_2_n_3\,
      CO(3) => \dwell_frame_reg[8]_i_2_n_4\,
      CO(2) => \dwell_frame_reg[8]_i_2_n_5\,
      CO(1) => \dwell_frame_reg[8]_i_2_n_6\,
      CO(0) => \dwell_frame_reg[8]_i_2_n_7\,
      DI(7 downto 0) => B"00000000",
      O(7 downto 0) => data0(8 downto 1),
      S(7 downto 0) => dwell_frame(8 downto 1)
    );
\dwell_frame_reg[9]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \dwell_frame[31]_i_2_n_0\,
      D => dwell_frame_0(9),
      Q => dwell_frame(9),
      R => \dwell_frame[31]_i_1_n_0\
    );
\i__carry__0_i_1\: unisim.vcomponents.LUT1
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => p_0_in(17),
      O => \i__carry__0_i_1_n_0\
    );
\i__carry__0_i_10\: unisim.vcomponents.CARRY8
     port map (
      CI => \i__carry_i_16_n_0\,
      CI_TOP => '0',
      CO(7) => \i__carry__0_i_10_n_0\,
      CO(6) => \i__carry__0_i_10_n_1\,
      CO(5) => \i__carry__0_i_10_n_2\,
      CO(4) => \i__carry__0_i_10_n_3\,
      CO(3) => \i__carry__0_i_10_n_4\,
      CO(2) => \i__carry__0_i_10_n_5\,
      CO(1) => \i__carry__0_i_10_n_6\,
      CO(0) => \i__carry__0_i_10_n_7\,
      DI(7 downto 0) => B"00000000",
      O(7 downto 0) => p_0_in(24 downto 17),
      S(7 downto 0) => phase_reg(24 downto 17)
    );
\i__carry__0_i_11\: unisim.vcomponents.CARRY8
     port map (
      CI => \i__carry__0_i_10_n_0\,
      CI_TOP => '0',
      CO(7 downto 6) => \NLW_i__carry__0_i_11_CO_UNCONNECTED\(7 downto 6),
      CO(5) => \i__carry__0_i_11_n_2\,
      CO(4) => \i__carry__0_i_11_n_3\,
      CO(3) => \i__carry__0_i_11_n_4\,
      CO(2) => \i__carry__0_i_11_n_5\,
      CO(1) => \i__carry__0_i_11_n_6\,
      CO(0) => \i__carry__0_i_11_n_7\,
      DI(7 downto 0) => B"00000000",
      O(7) => \NLW_i__carry__0_i_11_O_UNCONNECTED\(7),
      O(6 downto 0) => p_0_in(31 downto 25),
      S(7) => '0',
      S(6 downto 0) => phase_reg(31 downto 25)
    );
\i__carry__0_i_2\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => p_0_in(30),
      I1 => p_0_in(31),
      O => \i__carry__0_i_2_n_0\
    );
\i__carry__0_i_3\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => p_0_in(28),
      I1 => p_0_in(29),
      O => \i__carry__0_i_3_n_0\
    );
\i__carry__0_i_4\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => p_0_in(26),
      I1 => p_0_in(27),
      O => \i__carry__0_i_4_n_0\
    );
\i__carry__0_i_5\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => p_0_in(24),
      I1 => p_0_in(25),
      O => \i__carry__0_i_5_n_0\
    );
\i__carry__0_i_6\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => p_0_in(22),
      I1 => p_0_in(23),
      O => \i__carry__0_i_6_n_0\
    );
\i__carry__0_i_7\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => p_0_in(20),
      I1 => p_0_in(21),
      O => \i__carry__0_i_7_n_0\
    );
\i__carry__0_i_8\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => p_0_in(18),
      I1 => p_0_in(19),
      O => \i__carry__0_i_8_n_0\
    );
\i__carry__0_i_9\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"2"
    )
        port map (
      I0 => p_0_in(17),
      I1 => p_0_in(16),
      O => \i__carry__0_i_9_n_0\
    );
\i__carry_i_1\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"10"
    )
        port map (
      I0 => p_0_in(15),
      I1 => p_0_in(14),
      I2 => select_high,
      O => \i__carry_i_1_n_0\
    );
\i__carry_i_10\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => p_0_in(10),
      I1 => p_0_in(11),
      O => \i__carry_i_10_n_0\
    );
\i__carry_i_11\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"12"
    )
        port map (
      I0 => select_high,
      I1 => p_0_in(8),
      I2 => p_0_in(9),
      O => \i__carry_i_11_n_0\
    );
\i__carry_i_12\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"8"
    )
        port map (
      I0 => p_0_in(6),
      I1 => p_0_in(7),
      O => \i__carry_i_12_n_0\
    );
\i__carry_i_13\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"84"
    )
        port map (
      I0 => select_high,
      I1 => p_0_in(4),
      I2 => p_0_in(5),
      O => \i__carry_i_13_n_0\
    );
\i__carry_i_14\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"8"
    )
        port map (
      I0 => p_0_in(2),
      I1 => p_0_in(3),
      O => \i__carry_i_14_n_0\
    );
\i__carry_i_15\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"84"
    )
        port map (
      I0 => select_high,
      I1 => p_0_in(1),
      I2 => phase_reg(0),
      O => \i__carry_i_15_n_0\
    );
\i__carry_i_16\: unisim.vcomponents.CARRY8
     port map (
      CI => \i__carry_i_17_n_0\,
      CI_TOP => '0',
      CO(7) => \i__carry_i_16_n_0\,
      CO(6) => \i__carry_i_16_n_1\,
      CO(5) => \i__carry_i_16_n_2\,
      CO(4) => \i__carry_i_16_n_3\,
      CO(3) => \i__carry_i_16_n_4\,
      CO(2) => \i__carry_i_16_n_5\,
      CO(1) => \i__carry_i_16_n_6\,
      CO(0) => \i__carry_i_16_n_7\,
      DI(7 downto 0) => B"00000000",
      O(7 downto 0) => p_0_in(16 downto 9),
      S(7 downto 0) => phase_reg(16 downto 9)
    );
\i__carry_i_17\: unisim.vcomponents.CARRY8
     port map (
      CI => phase_reg(0),
      CI_TOP => '0',
      CO(7) => \i__carry_i_17_n_0\,
      CO(6) => \i__carry_i_17_n_1\,
      CO(5) => \i__carry_i_17_n_2\,
      CO(4) => \i__carry_i_17_n_3\,
      CO(3) => \i__carry_i_17_n_4\,
      CO(2) => \i__carry_i_17_n_5\,
      CO(1) => \i__carry_i_17_n_6\,
      CO(0) => \i__carry_i_17_n_7\,
      DI(7 downto 0) => B"00000000",
      O(7 downto 0) => p_0_in(8 downto 1),
      S(7 downto 0) => phase_reg(8 downto 1)
    );
\i__carry_i_2\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"4F"
    )
        port map (
      I0 => p_0_in(12),
      I1 => select_high,
      I2 => p_0_in(13),
      O => \i__carry_i_2_n_0\
    );
\i__carry_i_3\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => p_0_in(9),
      I1 => select_high,
      O => \i__carry_i_3_n_0\
    );
\i__carry_i_4\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"7"
    )
        port map (
      I0 => p_0_in(6),
      I1 => p_0_in(7),
      O => \i__carry_i_4_n_0\
    );
\i__carry_i_5\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"2B"
    )
        port map (
      I0 => select_high,
      I1 => p_0_in(5),
      I2 => p_0_in(4),
      O => \i__carry_i_5_n_0\
    );
\i__carry_i_6\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"7"
    )
        port map (
      I0 => p_0_in(2),
      I1 => p_0_in(3),
      O => \i__carry_i_6_n_0\
    );
\i__carry_i_7\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"4F"
    )
        port map (
      I0 => select_high,
      I1 => phase_reg(0),
      I2 => p_0_in(1),
      O => \i__carry_i_7_n_0\
    );
\i__carry_i_8\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"09"
    )
        port map (
      I0 => select_high,
      I1 => p_0_in(14),
      I2 => p_0_in(15),
      O => \i__carry_i_8_n_0\
    );
\i__carry_i_9\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"84"
    )
        port map (
      I0 => select_high,
      I1 => p_0_in(13),
      I2 => p_0_in(12),
      O => \i__carry_i_9_n_0\
    );
\phase[0]_i_1\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"F7FF"
    )
        port map (
      I0 => busy,
      I1 => s_axi_aresetn,
      I2 => \dwell_frame[31]_i_2_n_0\,
      I3 => pwm_i_3_n_0,
      O => \phase[0]_i_1_n_0\
    );
\phase[0]_i_3\: unisim.vcomponents.LUT1
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => phase_reg(0),
      O => p_0_in(0)
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
      S(0) => p_0_in(0)
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
\pwm0_inferred__0/i__carry\: unisim.vcomponents.CARRY8
     port map (
      CI => '0',
      CI_TOP => '0',
      CO(7) => \pwm0_inferred__0/i__carry_n_0\,
      CO(6) => \pwm0_inferred__0/i__carry_n_1\,
      CO(5) => \pwm0_inferred__0/i__carry_n_2\,
      CO(4) => \pwm0_inferred__0/i__carry_n_3\,
      CO(3) => \pwm0_inferred__0/i__carry_n_4\,
      CO(2) => \pwm0_inferred__0/i__carry_n_5\,
      CO(1) => \pwm0_inferred__0/i__carry_n_6\,
      CO(0) => \pwm0_inferred__0/i__carry_n_7\,
      DI(7) => \i__carry_i_1_n_0\,
      DI(6) => \i__carry_i_2_n_0\,
      DI(5) => '0',
      DI(4) => \i__carry_i_3_n_0\,
      DI(3) => \i__carry_i_4_n_0\,
      DI(2) => \i__carry_i_5_n_0\,
      DI(1) => \i__carry_i_6_n_0\,
      DI(0) => \i__carry_i_7_n_0\,
      O(7 downto 0) => \NLW_pwm0_inferred__0/i__carry_O_UNCONNECTED\(7 downto 0),
      S(7) => \i__carry_i_8_n_0\,
      S(6) => \i__carry_i_9_n_0\,
      S(5) => \i__carry_i_10_n_0\,
      S(4) => \i__carry_i_11_n_0\,
      S(3) => \i__carry_i_12_n_0\,
      S(2) => \i__carry_i_13_n_0\,
      S(1) => \i__carry_i_14_n_0\,
      S(0) => \i__carry_i_15_n_0\
    );
\pwm0_inferred__0/i__carry__0\: unisim.vcomponents.CARRY8
     port map (
      CI => \pwm0_inferred__0/i__carry_n_0\,
      CI_TOP => '0',
      CO(7) => \pwm0_inferred__0/i__carry__0_n_0\,
      CO(6) => \pwm0_inferred__0/i__carry__0_n_1\,
      CO(5) => \pwm0_inferred__0/i__carry__0_n_2\,
      CO(4) => \pwm0_inferred__0/i__carry__0_n_3\,
      CO(3) => \pwm0_inferred__0/i__carry__0_n_4\,
      CO(2) => \pwm0_inferred__0/i__carry__0_n_5\,
      CO(1) => \pwm0_inferred__0/i__carry__0_n_6\,
      CO(0) => \pwm0_inferred__0/i__carry__0_n_7\,
      DI(7 downto 1) => B"0000000",
      DI(0) => \i__carry__0_i_1_n_0\,
      O(7 downto 0) => \NLW_pwm0_inferred__0/i__carry__0_O_UNCONNECTED\(7 downto 0),
      S(7) => \i__carry__0_i_2_n_0\,
      S(6) => \i__carry__0_i_3_n_0\,
      S(5) => \i__carry__0_i_4_n_0\,
      S(4) => \i__carry__0_i_5_n_0\,
      S(3) => \i__carry__0_i_6_n_0\,
      S(2) => \i__carry__0_i_7_n_0\,
      S(1) => \i__carry__0_i_8_n_0\,
      S(0) => \i__carry__0_i_9_n_0\
    );
pwm_i_1: unisim.vcomponents.LUT2
    generic map(
      INIT => X"7"
    )
        port map (
      I0 => pwm_i_3_n_0,
      I1 => s_axi_aresetn,
      O => pwm_i_1_n_0
    );
pwm_i_2: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FFFF0404FF040404"
    )
        port map (
      I0 => pwm_i_4_n_0,
      I1 => \s_axi_bresp[1]_i_5\(1),
      I2 => pwm_i_5_n_0,
      I3 => \pwm0_inferred__0/i__carry__0_n_0\,
      I4 => busy,
      I5 => \dwell_frame[31]_i_2_n_0\,
      O => pwm_i_2_n_0
    );
pwm_i_3: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FFFFFFFFFFFFFFFE"
    )
        port map (
      I0 => pwm_i_6_n_0,
      I1 => \^w_data_reg[0]\,
      I2 => \^w_data_reg[30]\,
      I3 => pwm_i_7_n_0,
      I4 => \^aw_address_reg[1]\,
      I5 => Q(3),
      O => pwm_i_3_n_0
    );
pwm_i_4: unisim.vcomponents.LUT4
    generic map(
      INIT => X"FFFE"
    )
        port map (
      I0 => \s_axi_bresp[1]_i_5\(10),
      I1 => \s_axi_bresp[1]_i_5\(9),
      I2 => busy,
      I3 => \s_axi_bresp[1]_i_5\(11),
      O => pwm_i_4_n_0
    );
pwm_i_5: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FFFFFFFFFFFFFFFE"
    )
        port map (
      I0 => Q(3),
      I1 => \^aw_address_reg[1]\,
      I2 => \^w_data_reg[12]\,
      I3 => \^w_data_reg[21]\,
      I4 => \^w_data_reg[30]\,
      I5 => \^w_data_reg[0]\,
      O => pwm_i_5_n_0
    );
pwm_i_6: unisim.vcomponents.LUT4
    generic map(
      INIT => X"FF7F"
    )
        port map (
      I0 => \s_axi_bresp[1]_i_5\(9),
      I1 => \s_axi_bresp[1]_i_5\(10),
      I2 => \s_axi_bresp[1]_i_5\(11),
      I3 => \s_axi_bresp[1]_i_5\(1),
      O => pwm_i_6_n_0
    );
pwm_i_7: unisim.vcomponents.LUT4
    generic map(
      INIT => X"FFFE"
    )
        port map (
      I0 => \s_axi_bresp[1]_i_16_n_0\,
      I1 => pwm_i_8_n_0,
      I2 => \s_axi_bresp[1]_i_15_n_0\,
      I3 => pwm_i_9_n_0,
      O => pwm_i_7_n_0
    );
pwm_i_8: unisim.vcomponents.LUT4
    generic map(
      INIT => X"FFFD"
    )
        port map (
      I0 => \s_axi_bresp[1]_i_5\(8),
      I1 => \s_axi_bresp[1]_i_5\(7),
      I2 => \s_axi_bresp[1]_i_5\(13),
      I3 => \s_axi_bresp[1]_i_5\(12),
      O => pwm_i_8_n_0
    );
pwm_i_9: unisim.vcomponents.LUT4
    generic map(
      INIT => X"FFDF"
    )
        port map (
      I0 => \s_axi_bresp[1]_i_5\(18),
      I1 => \s_axi_bresp[1]_i_5\(19),
      I2 => \s_axi_bresp[1]_i_5\(20),
      I3 => \s_axi_bresp[1]_i_5\(21),
      O => pwm_i_9_n_0
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
\s_axi_bresp[1]_i_10\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FFFFFBFF"
    )
        port map (
      I0 => \s_axi_bresp[1]_i_5\(21),
      I1 => \s_axi_bresp[1]_i_5\(20),
      I2 => \s_axi_bresp[1]_i_5\(19),
      I3 => \s_axi_bresp[1]_i_5\(18),
      I4 => \s_axi_bresp[1]_i_15_n_0\,
      O => \^w_data_reg[21]\
    );
\s_axi_bresp[1]_i_11\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FFFFFEFF"
    )
        port map (
      I0 => \s_axi_bresp[1]_i_5\(12),
      I1 => \s_axi_bresp[1]_i_5\(13),
      I2 => \s_axi_bresp[1]_i_5\(7),
      I3 => \s_axi_bresp[1]_i_5\(8),
      I4 => \s_axi_bresp[1]_i_16_n_0\,
      O => \^w_data_reg[12]\
    );
\s_axi_bresp[1]_i_12\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"FFDF"
    )
        port map (
      I0 => \s_axi_bresp[1]_i_5\(4),
      I1 => \s_axi_bresp[1]_i_5\(3),
      I2 => \s_axi_bresp[1]_i_5\(6),
      I3 => \s_axi_bresp[1]_i_5\(5),
      O => \s_axi_bresp[1]_i_12_n_0\
    );
\s_axi_bresp[1]_i_13\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"FFEF"
    )
        port map (
      I0 => \s_axi_bresp[1]_i_5\(27),
      I1 => \s_axi_bresp[1]_i_5\(26),
      I2 => \s_axi_bresp[1]_i_5\(28),
      I3 => \s_axi_bresp[1]_i_5\(29),
      O => \s_axi_bresp[1]_i_13_n_0\
    );
\s_axi_bresp[1]_i_14\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"FF7F"
    )
        port map (
      I0 => \s_axi_bresp[1]_i_9_0\(2),
      I1 => \s_axi_bresp[1]_i_9_0\(1),
      I2 => \s_axi_bresp[1]_i_9_0\(3),
      I3 => Q(2),
      O => \s_axi_bresp[1]_i_14_n_0\
    );
\s_axi_bresp[1]_i_15\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"DFFF"
    )
        port map (
      I0 => \s_axi_bresp[1]_i_5\(22),
      I1 => \s_axi_bresp[1]_i_5\(23),
      I2 => \s_axi_bresp[1]_i_5\(25),
      I3 => \s_axi_bresp[1]_i_5\(24),
      O => \s_axi_bresp[1]_i_15_n_0\
    );
\s_axi_bresp[1]_i_16\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"FFFD"
    )
        port map (
      I0 => \s_axi_bresp[1]_i_5\(14),
      I1 => \s_axi_bresp[1]_i_5\(15),
      I2 => \s_axi_bresp[1]_i_5\(17),
      I3 => \s_axi_bresp[1]_i_5\(16),
      O => \s_axi_bresp[1]_i_16_n_0\
    );
\s_axi_bresp[1]_i_2\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"BBBBBBBBB8B8BBB8"
    )
        port map (
      I0 => s_axi_bresp(0),
      I1 => \s_axi_bresp[1]_i_3_n_0\,
      I2 => \s_axi_bresp_reg[1]_2\,
      I3 => \s_axi_bresp_reg[1]_3\,
      I4 => Q(3),
      I5 => \s_axi_bresp[1]_i_6_n_0\,
      O => \s_axi_bresp_reg[1]\
    );
\s_axi_bresp[1]_i_3\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"DF"
    )
        port map (
      I0 => \s_axi_bresp_reg[1]_0\,
      I1 => \s_axi_bresp_reg[1]_1\,
      I2 => aw_pending,
      O => \s_axi_bresp[1]_i_3_n_0\
    );
\s_axi_bresp[1]_i_6\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"00000000FFFE77FF"
    )
        port map (
      I0 => \s_axi_bresp[1]_i_5\(10),
      I1 => \s_axi_bresp[1]_i_5\(9),
      I2 => busy,
      I3 => \s_axi_bresp[1]_i_5\(11),
      I4 => \s_axi_bresp[1]_i_5\(1),
      I5 => Q(3),
      O => \s_axi_bresp[1]_i_6_n_0\
    );
\s_axi_bresp[1]_i_8\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FFFFFEFF"
    )
        port map (
      I0 => \s_axi_bresp[1]_i_5\(0),
      I1 => \s_axi_bresp[1]_i_5\(2),
      I2 => Q(5),
      I3 => Q(4),
      I4 => \s_axi_bresp[1]_i_12_n_0\,
      O => \^w_data_reg[0]\
    );
\s_axi_bresp[1]_i_9\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FFFFFFDF"
    )
        port map (
      I0 => \s_axi_bresp[1]_i_5\(30),
      I1 => \s_axi_bresp[1]_i_5\(31),
      I2 => \s_axi_bresp[1]_i_9_0\(0),
      I3 => \s_axi_bresp[1]_i_13_n_0\,
      I4 => \s_axi_bresp[1]_i_14_n_0\,
      O => \^w_data_reg[30]\
    );
\s_axi_rdata[0]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FFEAEAEA"
    )
        port map (
      I0 => \s_axi_rdata[0]_i_2_n_0\,
      I1 => \s_axi_rdata_reg[15]\,
      I2 => \s_axi_rdata_reg[31]\(0),
      I3 => dwell_frame(0),
      I4 => \s_axi_rdata_reg[2]\,
      O => D(0)
    );
\s_axi_rdata[0]_i_2\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"000030B000300000"
    )
        port map (
      I0 => busy,
      I1 => s_axi_araddr(0),
      I2 => \s_axi_rdata_reg[6]_1\,
      I3 => s_axi_araddr(2),
      I4 => s_axi_araddr(3),
      I5 => s_axi_araddr(1),
      O => \s_axi_rdata[0]_i_2_n_0\
    );
\s_axi_rdata[10]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"AAFAAAAAAAFAEABA"
    )
        port map (
      I0 => \s_axi_rdata[10]_i_2_n_0\,
      I1 => s_axi_araddr(2),
      I2 => \s_axi_rdata_reg[6]_1\,
      I3 => s_axi_araddr(0),
      I4 => s_axi_araddr(3),
      I5 => s_axi_araddr(1),
      O => D(10)
    );
\s_axi_rdata[10]_i_2\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"C808000000000000"
    )
        port map (
      I0 => \s_axi_rdata_reg[31]\(8),
      I1 => \s_axi_rdata_reg[6]_1\,
      I2 => s_axi_araddr(2),
      I3 => dwell_frame(10),
      I4 => s_axi_araddr(3),
      I5 => s_axi_araddr(1),
      O => \s_axi_rdata[10]_i_2_n_0\
    );
\s_axi_rdata[11]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FFEAEAEA"
    )
        port map (
      I0 => \s_axi_rdata_reg[14]\,
      I1 => \s_axi_rdata_reg[15]\,
      I2 => \s_axi_rdata_reg[31]\(9),
      I3 => dwell_frame(11),
      I4 => \s_axi_rdata_reg[2]\,
      O => D(11)
    );
\s_axi_rdata[12]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FFFFFFFFFFEAEAEA"
    )
        port map (
      I0 => \s_axi_rdata_reg[12]\,
      I1 => dwell_frame(12),
      I2 => \s_axi_rdata_reg[2]\,
      I3 => \s_axi_rdata_reg[31]\(10),
      I4 => \s_axi_rdata_reg[15]\,
      I5 => \s_axi_rdata_reg[12]_0\,
      O => D(12)
    );
\s_axi_rdata[13]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FFEAEAEA"
    )
        port map (
      I0 => \s_axi_rdata_reg[3]\,
      I1 => \s_axi_rdata_reg[15]\,
      I2 => \s_axi_rdata_reg[31]\(11),
      I3 => dwell_frame(13),
      I4 => \s_axi_rdata_reg[2]\,
      O => D(13)
    );
\s_axi_rdata[14]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FFFFFFFFFFFFF888"
    )
        port map (
      I0 => \s_axi_rdata_reg[15]\,
      I1 => \s_axi_rdata_reg[31]\(12),
      I2 => \s_axi_rdata_reg[2]\,
      I3 => dwell_frame(14),
      I4 => \s_axi_rdata_reg[14]\,
      I5 => \s_axi_rdata_reg[17]\,
      O => D(14)
    );
\s_axi_rdata[15]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FFFFFFFFFFFFF888"
    )
        port map (
      I0 => \s_axi_rdata_reg[2]\,
      I1 => dwell_frame(15),
      I2 => \s_axi_rdata_reg[31]\(13),
      I3 => \s_axi_rdata_reg[15]\,
      I4 => \s_axi_rdata_reg[15]_0\,
      I5 => \s_axi_rdata_reg[2]_1\,
      O => D(15)
    );
\s_axi_rdata[16]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FFEAEAEA"
    )
        port map (
      I0 => \s_axi_rdata_reg[14]\,
      I1 => \s_axi_rdata_reg[15]\,
      I2 => \s_axi_rdata_reg[31]\(14),
      I3 => dwell_frame(16),
      I4 => \s_axi_rdata_reg[2]\,
      O => D(16)
    );
\s_axi_rdata[17]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"EEEEEEEEFEEEEEEE"
    )
        port map (
      I0 => \s_axi_rdata[17]_i_2_n_0\,
      I1 => \s_axi_rdata_reg[17]\,
      I2 => s_axi_araddr(2),
      I3 => \s_axi_rdata_reg[17]_0\,
      I4 => s_axi_araddr(1),
      I5 => s_axi_araddr(3),
      O => D(17)
    );
\s_axi_rdata[17]_i_2\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"C00F0000A00F0000"
    )
        port map (
      I0 => \s_axi_rdata_reg[31]\(15),
      I1 => dwell_frame(17),
      I2 => s_axi_araddr(1),
      I3 => s_axi_araddr(3),
      I4 => \s_axi_rdata_reg[17]_1\,
      I5 => s_axi_araddr(2),
      O => \s_axi_rdata[17]_i_2_n_0\
    );
\s_axi_rdata[18]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FFFFF888"
    )
        port map (
      I0 => \s_axi_rdata_reg[15]\,
      I1 => \s_axi_rdata_reg[31]\(16),
      I2 => \s_axi_rdata_reg[2]\,
      I3 => dwell_frame(18),
      I4 => \s_axi_rdata_reg[18]\,
      O => D(18)
    );
\s_axi_rdata[19]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FFFFFFFFFFFFF888"
    )
        port map (
      I0 => \s_axi_rdata_reg[2]\,
      I1 => dwell_frame(19),
      I2 => \s_axi_rdata_reg[31]\(17),
      I3 => \s_axi_rdata_reg[15]\,
      I4 => \s_axi_rdata_reg[19]\,
      I5 => \s_axi_rdata_reg[2]_1\,
      O => D(19)
    );
\s_axi_rdata[1]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FFFFFFFEFFFEFFFE"
    )
        port map (
      I0 => \s_axi_rdata_reg[2]_0\,
      I1 => \s_axi_rdata[1]_i_2_n_0\,
      I2 => \s_axi_rdata_reg[12]\,
      I3 => \s_axi_rdata_reg[1]\,
      I4 => \s_axi_rdata_reg[31]\(1),
      I5 => \s_axi_rdata_reg[15]\,
      O => D(1)
    );
\s_axi_rdata[1]_i_2\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"88888888F0000000"
    )
        port map (
      I0 => \s_axi_rdata_reg[4]_0\,
      I1 => dwell_frame(1),
      I2 => \s_axi_rdata_reg[1]_0\,
      I3 => \^servo_pwm\,
      I4 => s_axi_araddr(1),
      I5 => s_axi_araddr(3),
      O => \s_axi_rdata[1]_i_2_n_0\
    );
\s_axi_rdata[20]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FFFFF888"
    )
        port map (
      I0 => \s_axi_rdata_reg[15]\,
      I1 => \s_axi_rdata_reg[31]\(18),
      I2 => \s_axi_rdata_reg[2]\,
      I3 => dwell_frame(20),
      I4 => \s_axi_rdata_reg[18]\,
      O => D(20)
    );
\s_axi_rdata[21]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FFEAEAEA"
    )
        port map (
      I0 => \s_axi_rdata_reg[12]_0\,
      I1 => \s_axi_rdata_reg[15]\,
      I2 => \s_axi_rdata_reg[31]\(19),
      I3 => dwell_frame(21),
      I4 => \s_axi_rdata_reg[2]\,
      O => D(21)
    );
\s_axi_rdata[22]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FFEAEAEA"
    )
        port map (
      I0 => \s_axi_rdata_reg[14]\,
      I1 => \s_axi_rdata_reg[15]\,
      I2 => \s_axi_rdata_reg[31]\(20),
      I3 => dwell_frame(22),
      I4 => \s_axi_rdata_reg[2]\,
      O => D(22)
    );
\s_axi_rdata[23]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FFEAEAEA"
    )
        port map (
      I0 => \s_axi_rdata_reg[12]_0\,
      I1 => \s_axi_rdata_reg[15]\,
      I2 => \s_axi_rdata_reg[31]\(21),
      I3 => dwell_frame(23),
      I4 => \s_axi_rdata_reg[2]\,
      O => D(23)
    );
\s_axi_rdata[24]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FFEAEAEA"
    )
        port map (
      I0 => \s_axi_rdata_reg[12]_0\,
      I1 => \s_axi_rdata_reg[15]\,
      I2 => \s_axi_rdata_reg[31]\(22),
      I3 => dwell_frame(24),
      I4 => \s_axi_rdata_reg[2]\,
      O => D(24)
    );
\s_axi_rdata[25]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FFFFF222F222F222"
    )
        port map (
      I0 => \s_axi_rdata_reg[3]_0\,
      I1 => \s_axi_rdata_reg[25]\,
      I2 => \s_axi_rdata_reg[15]\,
      I3 => \s_axi_rdata_reg[31]\(23),
      I4 => dwell_frame(25),
      I5 => \s_axi_rdata_reg[2]\,
      O => D(25)
    );
\s_axi_rdata[26]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FFFFF888F888F888"
    )
        port map (
      I0 => \s_axi_rdata_reg[26]\,
      I1 => \s_axi_rdata_reg[3]_0\,
      I2 => \s_axi_rdata_reg[15]\,
      I3 => \s_axi_rdata_reg[31]\(24),
      I4 => dwell_frame(26),
      I5 => \s_axi_rdata_reg[2]\,
      O => D(26)
    );
\s_axi_rdata[27]_i_1\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"F888"
    )
        port map (
      I0 => dwell_frame(27),
      I1 => \s_axi_rdata_reg[2]\,
      I2 => \s_axi_rdata_reg[31]\(25),
      I3 => \s_axi_rdata_reg[15]\,
      O => D(27)
    );
\s_axi_rdata[28]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FFFFF222F222F222"
    )
        port map (
      I0 => \s_axi_rdata_reg[3]_0\,
      I1 => s_axi_araddr(3),
      I2 => \s_axi_rdata_reg[15]\,
      I3 => \s_axi_rdata_reg[31]\(26),
      I4 => dwell_frame(28),
      I5 => \s_axi_rdata_reg[2]\,
      O => D(28)
    );
\s_axi_rdata[29]_i_1\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"F888"
    )
        port map (
      I0 => dwell_frame(29),
      I1 => \s_axi_rdata_reg[2]\,
      I2 => \s_axi_rdata_reg[31]\(27),
      I3 => \s_axi_rdata_reg[15]\,
      O => D(29)
    );
\s_axi_rdata[2]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FFFFFFFFFFFFFFF8"
    )
        port map (
      I0 => \s_axi_rdata_reg[2]\,
      I1 => dwell_frame(2),
      I2 => \s_axi_rdata_reg[2]_0\,
      I3 => \s_axi_rdata_reg[2]_1\,
      I4 => \s_axi_rdata_reg[17]\,
      I5 => \s_axi_rdata_reg[2]_2\,
      O => D(2)
    );
\s_axi_rdata[30]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FFFFF222F222F222"
    )
        port map (
      I0 => \s_axi_rdata_reg[3]_0\,
      I1 => s_axi_araddr(3),
      I2 => \s_axi_rdata_reg[15]\,
      I3 => \s_axi_rdata_reg[31]\(28),
      I4 => dwell_frame(30),
      I5 => \s_axi_rdata_reg[2]\,
      O => D(30)
    );
\s_axi_rdata[31]_i_2\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"F888"
    )
        port map (
      I0 => dwell_frame(31),
      I1 => \s_axi_rdata_reg[2]\,
      I2 => \s_axi_rdata_reg[31]\(29),
      I3 => \s_axi_rdata_reg[15]\,
      O => D(31)
    );
\s_axi_rdata[3]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FFFFFFEAFFEAFFEA"
    )
        port map (
      I0 => \s_axi_rdata[3]_i_2_n_0\,
      I1 => \s_axi_rdata_reg[2]\,
      I2 => dwell_frame(3),
      I3 => \s_axi_rdata_reg[3]\,
      I4 => \s_axi_rdata_reg[3]_0\,
      I5 => s_axi_araddr(3),
      O => D(3)
    );
\s_axi_rdata[3]_i_2\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FFFFBAAABAAABAAA"
    )
        port map (
      I0 => \s_axi_rdata_reg[2]_1\,
      I1 => select_high,
      I2 => s_axi_araddr(1),
      I3 => \s_axi_rdata_reg[3]_1\,
      I4 => \s_axi_rdata_reg[31]\(2),
      I5 => \s_axi_rdata_reg[5]\,
      O => \s_axi_rdata[3]_i_2_n_0\
    );
\s_axi_rdata[4]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FFFFFFFFFFFFEAAA"
    )
        port map (
      I0 => \s_axi_rdata_reg[4]\,
      I1 => \s_axi_rdata_reg[4]_0\,
      I2 => dwell_frame(4),
      I3 => s_axi_araddr(3),
      I4 => \s_axi_rdata[4]_i_4_n_0\,
      I5 => \s_axi_rdata_reg[4]_1\,
      O => D(4)
    );
\s_axi_rdata[4]_i_4\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"4000"
    )
        port map (
      I0 => select_high,
      I1 => s_axi_araddr(1),
      I2 => s_axi_araddr(2),
      I3 => \s_axi_rdata_reg[17]_0\,
      O => \s_axi_rdata[4]_i_4_n_0\
    );
\s_axi_rdata[5]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FFFFFFFFFFFFF888"
    )
        port map (
      I0 => s_axi_araddr(4),
      I1 => \s_axi_rdata_reg[17]\,
      I2 => \s_axi_rdata_reg[31]\(3),
      I3 => \s_axi_rdata_reg[5]\,
      I4 => \s_axi_rdata[5]_i_3_n_0\,
      I5 => \s_axi_rdata_reg[5]_0\,
      O => D(5)
    );
\s_axi_rdata[5]_i_3\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"88008800F8008800"
    )
        port map (
      I0 => \s_axi_rdata_reg[4]_0\,
      I1 => dwell_frame(5),
      I2 => \s_axi_rdata_reg[17]_0\,
      I3 => s_axi_araddr(3),
      I4 => s_axi_araddr(1),
      I5 => select_high,
      O => \s_axi_rdata[5]_i_3_n_0\
    );
\s_axi_rdata[6]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"BABBAAAABAAAAAAA"
    )
        port map (
      I0 => \s_axi_rdata_reg[6]\,
      I1 => \s_axi_rdata_reg[6]_0\,
      I2 => dwell_frame(6),
      I3 => s_axi_araddr(2),
      I4 => \s_axi_rdata_reg[6]_1\,
      I5 => \s_axi_rdata_reg[31]\(4),
      O => D(6)
    );
\s_axi_rdata[7]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FFEAEAEA"
    )
        port map (
      I0 => \s_axi_rdata_reg[3]\,
      I1 => \s_axi_rdata_reg[15]\,
      I2 => \s_axi_rdata_reg[31]\(5),
      I3 => dwell_frame(7),
      I4 => \s_axi_rdata_reg[2]\,
      O => D(7)
    );
\s_axi_rdata[8]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FFEAEAEAFFEAFFEA"
    )
        port map (
      I0 => \s_axi_rdata[8]_i_2_n_0\,
      I1 => \s_axi_rdata_reg[2]\,
      I2 => dwell_frame(8),
      I3 => \s_axi_rdata_reg[3]_0\,
      I4 => s_axi_araddr(3),
      I5 => s_axi_araddr(1),
      O => D(8)
    );
\s_axi_rdata[8]_i_2\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"00002020000020F0"
    )
        port map (
      I0 => \s_axi_rdata_reg[31]\(6),
      I1 => s_axi_araddr(2),
      I2 => \s_axi_rdata_reg[6]_1\,
      I3 => s_axi_araddr(0),
      I4 => \s_axi_rdata_reg[6]_0\,
      I5 => select_high,
      O => \s_axi_rdata[8]_i_2_n_0\
    );
\s_axi_rdata[9]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FFFFFFFFFFEAEAEA"
    )
        port map (
      I0 => \s_axi_rdata_reg[2]_0\,
      I1 => \s_axi_rdata_reg[2]\,
      I2 => dwell_frame(9),
      I3 => \s_axi_rdata_reg[15]\,
      I4 => \s_axi_rdata_reg[31]\(7),
      I5 => \s_axi_rdata[9]_i_3_n_0\,
      O => D(9)
    );
\s_axi_rdata[9]_i_3\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"C0004000"
    )
        port map (
      I0 => s_axi_araddr(1),
      I1 => \s_axi_rdata_reg[17]_0\,
      I2 => s_axi_araddr(2),
      I3 => s_axi_araddr(3),
      I4 => select_high,
      O => \s_axi_rdata[9]_i_3_n_0\
    );
\scratch[31]_i_2\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FFFFFFFFFFFFFFFE"
    )
        port map (
      I0 => \^aw_address_reg[9]\,
      I1 => Q(1),
      I2 => Q(0),
      I3 => Q(7),
      I4 => Q(6),
      I5 => \s_axi_bresp[1]_i_3_n_0\,
      O => \^aw_address_reg[1]\
    );
\scratch[31]_i_3\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"FFFE"
    )
        port map (
      I0 => Q(9),
      I1 => Q(8),
      I2 => Q(11),
      I3 => Q(10),
      O => \^aw_address_reg[9]\
    );
select_high_i_1: unisim.vcomponents.LUT6
    generic map(
      INIT => X"8000808000800000"
    )
        port map (
      I0 => pwm_i_3_n_0,
      I1 => busy,
      I2 => s_axi_aresetn,
      I3 => \dwell_frame[31]_i_8_n_0\,
      I4 => \dwell_frame[31]_i_2_n_0\,
      I5 => select_high,
      O => select_high_i_1_n_0
    );
select_high_reg: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => '1',
      D => select_high_i_1_n_0,
      Q => select_high,
      R => '0'
    );
end STRUCTURE;
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
library UNISIM;
use UNISIM.VCOMPONENTS.ALL;
entity decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_aura_pwm_probe is
  port (
    servo_pwm : out STD_LOGIC;
    s_axi_rdata : out STD_LOGIC_VECTOR ( 31 downto 0 );
    s_axi_rresp : out STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_bvalid_reg_0 : out STD_LOGIC;
    s_axi_wready : out STD_LOGIC;
    s_axi_awready : out STD_LOGIC;
    s_axi_arready : out STD_LOGIC;
    s_axi_rvalid_reg_0 : out STD_LOGIC;
    s_axi_bresp : out STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_aclk : in STD_LOGIC;
    s_axi_awaddr : in STD_LOGIC_VECTOR ( 11 downto 0 );
    s_axi_wdata : in STD_LOGIC_VECTOR ( 31 downto 0 );
    s_axi_wstrb : in STD_LOGIC_VECTOR ( 3 downto 0 );
    s_axi_aresetn : in STD_LOGIC;
    s_axi_araddr : in STD_LOGIC_VECTOR ( 11 downto 0 );
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
  signal burst_n_0 : STD_LOGIC;
  signal burst_n_1 : STD_LOGIC;
  signal burst_n_10 : STD_LOGIC;
  signal burst_n_11 : STD_LOGIC;
  signal burst_n_12 : STD_LOGIC;
  signal burst_n_13 : STD_LOGIC;
  signal burst_n_14 : STD_LOGIC;
  signal burst_n_15 : STD_LOGIC;
  signal burst_n_16 : STD_LOGIC;
  signal burst_n_17 : STD_LOGIC;
  signal burst_n_18 : STD_LOGIC;
  signal burst_n_19 : STD_LOGIC;
  signal burst_n_2 : STD_LOGIC;
  signal burst_n_20 : STD_LOGIC;
  signal burst_n_21 : STD_LOGIC;
  signal burst_n_22 : STD_LOGIC;
  signal burst_n_23 : STD_LOGIC;
  signal burst_n_24 : STD_LOGIC;
  signal burst_n_25 : STD_LOGIC;
  signal burst_n_26 : STD_LOGIC;
  signal burst_n_27 : STD_LOGIC;
  signal burst_n_28 : STD_LOGIC;
  signal burst_n_29 : STD_LOGIC;
  signal burst_n_3 : STD_LOGIC;
  signal burst_n_30 : STD_LOGIC;
  signal burst_n_31 : STD_LOGIC;
  signal burst_n_32 : STD_LOGIC;
  signal burst_n_33 : STD_LOGIC;
  signal burst_n_34 : STD_LOGIC;
  signal burst_n_35 : STD_LOGIC;
  signal burst_n_36 : STD_LOGIC;
  signal burst_n_37 : STD_LOGIC;
  signal burst_n_39 : STD_LOGIC;
  signal burst_n_4 : STD_LOGIC;
  signal burst_n_5 : STD_LOGIC;
  signal burst_n_6 : STD_LOGIC;
  signal burst_n_7 : STD_LOGIC;
  signal burst_n_8 : STD_LOGIC;
  signal burst_n_9 : STD_LOGIC;
  signal p_0_in_0 : STD_LOGIC;
  signal p_1_in : STD_LOGIC;
  signal p_2_in : STD_LOGIC;
  signal \^s_axi_bresp\ : STD_LOGIC_VECTOR ( 0 to 0 );
  signal \s_axi_bresp[1]_i_1_n_0\ : STD_LOGIC;
  signal \s_axi_bresp[1]_i_4_n_0\ : STD_LOGIC;
  signal \s_axi_bresp[1]_i_5_n_0\ : STD_LOGIC;
  signal \s_axi_bresp[1]_i_7_n_0\ : STD_LOGIC;
  signal s_axi_bvalid_i_1_n_0 : STD_LOGIC;
  signal \^s_axi_bvalid_reg_0\ : STD_LOGIC;
  signal \s_axi_rdata[10]_i_3_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[12]_i_2_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[13]_i_2_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[15]_i_2_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[17]_i_3_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[17]_i_4_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[17]_i_5_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[19]_i_2_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[19]_i_3_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[19]_i_4_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[1]_i_3_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[1]_i_4_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[20]_i_2_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[22]_i_2_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[24]_i_2_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[25]_i_2_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[26]_i_2_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[2]_i_2_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[30]_i_2_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[31]_i_3_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[31]_i_4_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[31]_i_5_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[31]_i_6_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[3]_i_3_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[4]_i_2_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[4]_i_3_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[4]_i_5_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[5]_i_2_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[5]_i_4_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[6]_i_2_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[6]_i_3_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[9]_i_2_n_0\ : STD_LOGIC;
  signal \s_axi_rresp[1]_i_1_n_0\ : STD_LOGIC;
  signal \s_axi_rresp[1]_i_2_n_0\ : STD_LOGIC;
  signal s_axi_rvalid01_out : STD_LOGIC;
  signal s_axi_rvalid_i_1_n_0 : STD_LOGIC;
  signal \^s_axi_rvalid_reg_0\ : STD_LOGIC;
  signal scratch : STD_LOGIC_VECTOR ( 31 downto 0 );
  signal \scratch[15]_i_1_n_0\ : STD_LOGIC;
  signal \scratch[23]_i_1_n_0\ : STD_LOGIC;
  signal \scratch[31]_i_1_n_0\ : STD_LOGIC;
  signal \scratch[7]_i_1_n_0\ : STD_LOGIC;
  signal w_data : STD_LOGIC_VECTOR ( 31 downto 0 );
  signal w_pending : STD_LOGIC;
  signal w_pending0 : STD_LOGIC;
  signal w_pending_i_2_n_0 : STD_LOGIC;
  signal w_pending_reg_n_0 : STD_LOGIC;
  signal \w_strobes_reg_n_0_[3]\ : STD_LOGIC;
  attribute SOFT_HLUTNM : string;
  attribute SOFT_HLUTNM of s_axi_arready_INST_0 : label is "soft_lutpair30";
  attribute SOFT_HLUTNM of s_axi_awready_INST_0 : label is "soft_lutpair27";
  attribute X_INTERFACE_INFO : string;
  attribute X_INTERFACE_INFO of \s_axi_bresp_reg[1]\ : label is "xilinx.com:interface:aximm:1.0 S_AXI BRESP";
  attribute SOFT_HLUTNM of s_axi_bvalid_i_1 : label is "soft_lutpair27";
  attribute X_INTERFACE_INFO of s_axi_bvalid_reg : label is "xilinx.com:interface:aximm:1.0 S_AXI BVALID";
  attribute SOFT_HLUTNM of \s_axi_rdata[10]_i_3\ : label is "soft_lutpair24";
  attribute SOFT_HLUTNM of \s_axi_rdata[15]_i_2\ : label is "soft_lutpair26";
  attribute SOFT_HLUTNM of \s_axi_rdata[17]_i_3\ : label is "soft_lutpair21";
  attribute SOFT_HLUTNM of \s_axi_rdata[19]_i_2\ : label is "soft_lutpair26";
  attribute SOFT_HLUTNM of \s_axi_rdata[19]_i_4\ : label is "soft_lutpair21";
  attribute SOFT_HLUTNM of \s_axi_rdata[1]_i_3\ : label is "soft_lutpair20";
  attribute SOFT_HLUTNM of \s_axi_rdata[20]_i_2\ : label is "soft_lutpair20";
  attribute SOFT_HLUTNM of \s_axi_rdata[22]_i_2\ : label is "soft_lutpair25";
  attribute SOFT_HLUTNM of \s_axi_rdata[24]_i_2\ : label is "soft_lutpair25";
  attribute SOFT_HLUTNM of \s_axi_rdata[25]_i_2\ : label is "soft_lutpair31";
  attribute SOFT_HLUTNM of \s_axi_rdata[26]_i_2\ : label is "soft_lutpair31";
  attribute SOFT_HLUTNM of \s_axi_rdata[31]_i_3\ : label is "soft_lutpair23";
  attribute SOFT_HLUTNM of \s_axi_rdata[3]_i_3\ : label is "soft_lutpair22";
  attribute SOFT_HLUTNM of \s_axi_rdata[4]_i_3\ : label is "soft_lutpair22";
  attribute SOFT_HLUTNM of \s_axi_rdata[5]_i_4\ : label is "soft_lutpair23";
  attribute SOFT_HLUTNM of \s_axi_rdata[6]_i_3\ : label is "soft_lutpair29";
  attribute SOFT_HLUTNM of \s_axi_rdata[9]_i_2\ : label is "soft_lutpair29";
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
  attribute SOFT_HLUTNM of \s_axi_rresp[1]_i_2\ : label is "soft_lutpair24";
  attribute X_INTERFACE_INFO of \s_axi_rresp_reg[1]\ : label is "xilinx.com:interface:aximm:1.0 S_AXI RRESP";
  attribute SOFT_HLUTNM of s_axi_rvalid_i_1 : label is "soft_lutpair30";
  attribute X_INTERFACE_INFO of s_axi_rvalid_reg : label is "xilinx.com:interface:aximm:1.0 S_AXI RVALID";
  attribute SOFT_HLUTNM of s_axi_wready_INST_0 : label is "soft_lutpair28";
  attribute SOFT_HLUTNM of w_pending_i_2 : label is "soft_lutpair28";
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
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => aw_pending0,
      D => s_axi_awaddr(0),
      Q => aw_address(0),
      R => \s_axi_bresp[1]_i_1_n_0\
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
      R => \s_axi_bresp[1]_i_1_n_0\
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
      R => \s_axi_bresp[1]_i_1_n_0\
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
      R => \s_axi_bresp[1]_i_1_n_0\
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
      R => \s_axi_bresp[1]_i_1_n_0\
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
      R => \s_axi_bresp[1]_i_1_n_0\
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
      R => \s_axi_bresp[1]_i_1_n_0\
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
      R => \s_axi_bresp[1]_i_1_n_0\
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
      R => \s_axi_bresp[1]_i_1_n_0\
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
      R => \s_axi_bresp[1]_i_1_n_0\
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
      R => \s_axi_bresp[1]_i_1_n_0\
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
      R => \s_axi_bresp[1]_i_1_n_0\
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
      R => w_pending
    );
burst: entity work.decalper_eb_ot_sdeen_pot_pi_dehcac_xnilix_pwm_burst
     port map (
      D(31) => burst_n_6,
      D(30) => burst_n_7,
      D(29) => burst_n_8,
      D(28) => burst_n_9,
      D(27) => burst_n_10,
      D(26) => burst_n_11,
      D(25) => burst_n_12,
      D(24) => burst_n_13,
      D(23) => burst_n_14,
      D(22) => burst_n_15,
      D(21) => burst_n_16,
      D(20) => burst_n_17,
      D(19) => burst_n_18,
      D(18) => burst_n_19,
      D(17) => burst_n_20,
      D(16) => burst_n_21,
      D(15) => burst_n_22,
      D(14) => burst_n_23,
      D(13) => burst_n_24,
      D(12) => burst_n_25,
      D(11) => burst_n_26,
      D(10) => burst_n_27,
      D(9) => burst_n_28,
      D(8) => burst_n_29,
      D(7) => burst_n_30,
      D(6) => burst_n_31,
      D(5) => burst_n_32,
      D(4) => burst_n_33,
      D(3) => burst_n_34,
      D(2) => burst_n_35,
      D(1) => burst_n_36,
      D(0) => burst_n_37,
      Q(11 downto 0) => aw_address(11 downto 0),
      \aw_address_reg[1]\ => burst_n_2,
      \aw_address_reg[9]\ => burst_n_5,
      aw_pending => aw_pending,
      s_axi_aclk => s_axi_aclk,
      s_axi_araddr(4 downto 0) => s_axi_araddr(6 downto 2),
      s_axi_aresetn => s_axi_aresetn,
      s_axi_bresp(0) => \^s_axi_bresp\(0),
      \s_axi_bresp[1]_i_5\(31 downto 0) => w_data(31 downto 0),
      \s_axi_bresp[1]_i_9_0\(3) => \w_strobes_reg_n_0_[3]\,
      \s_axi_bresp[1]_i_9_0\(2) => p_2_in,
      \s_axi_bresp[1]_i_9_0\(1) => p_1_in,
      \s_axi_bresp[1]_i_9_0\(0) => p_0_in_0,
      \s_axi_bresp_reg[1]\ => burst_n_39,
      \s_axi_bresp_reg[1]_0\ => w_pending_reg_n_0,
      \s_axi_bresp_reg[1]_1\ => \^s_axi_bvalid_reg_0\,
      \s_axi_bresp_reg[1]_2\ => \s_axi_bresp[1]_i_4_n_0\,
      \s_axi_bresp_reg[1]_3\ => \s_axi_bresp[1]_i_5_n_0\,
      \s_axi_rdata_reg[12]\ => \s_axi_rdata[12]_i_2_n_0\,
      \s_axi_rdata_reg[12]_0\ => \s_axi_rdata[24]_i_2_n_0\,
      \s_axi_rdata_reg[14]\ => \s_axi_rdata[22]_i_2_n_0\,
      \s_axi_rdata_reg[15]\ => \s_axi_rdata[31]_i_4_n_0\,
      \s_axi_rdata_reg[15]_0\ => \s_axi_rdata[15]_i_2_n_0\,
      \s_axi_rdata_reg[17]\ => \s_axi_rdata[17]_i_3_n_0\,
      \s_axi_rdata_reg[17]_0\ => \s_axi_rdata[17]_i_4_n_0\,
      \s_axi_rdata_reg[17]_1\ => \s_axi_rdata[17]_i_5_n_0\,
      \s_axi_rdata_reg[18]\ => \s_axi_rdata[20]_i_2_n_0\,
      \s_axi_rdata_reg[19]\ => \s_axi_rdata[19]_i_2_n_0\,
      \s_axi_rdata_reg[1]\ => \s_axi_rdata[1]_i_3_n_0\,
      \s_axi_rdata_reg[1]_0\ => \s_axi_rdata[1]_i_4_n_0\,
      \s_axi_rdata_reg[25]\ => \s_axi_rdata[25]_i_2_n_0\,
      \s_axi_rdata_reg[26]\ => \s_axi_rdata[26]_i_2_n_0\,
      \s_axi_rdata_reg[2]\ => \s_axi_rdata[31]_i_3_n_0\,
      \s_axi_rdata_reg[2]_0\ => \s_axi_rdata[9]_i_2_n_0\,
      \s_axi_rdata_reg[2]_1\ => \s_axi_rdata[19]_i_3_n_0\,
      \s_axi_rdata_reg[2]_2\ => \s_axi_rdata[2]_i_2_n_0\,
      \s_axi_rdata_reg[31]\(29 downto 3) => scratch(31 downto 5),
      \s_axi_rdata_reg[31]\(2) => scratch(3),
      \s_axi_rdata_reg[31]\(1 downto 0) => scratch(1 downto 0),
      \s_axi_rdata_reg[3]\ => \s_axi_rdata[13]_i_2_n_0\,
      \s_axi_rdata_reg[3]_0\ => \s_axi_rdata[30]_i_2_n_0\,
      \s_axi_rdata_reg[3]_1\ => \s_axi_rdata[3]_i_3_n_0\,
      \s_axi_rdata_reg[4]\ => \s_axi_rdata[4]_i_2_n_0\,
      \s_axi_rdata_reg[4]_0\ => \s_axi_rdata[4]_i_3_n_0\,
      \s_axi_rdata_reg[4]_1\ => \s_axi_rdata[4]_i_5_n_0\,
      \s_axi_rdata_reg[5]\ => \s_axi_rdata[5]_i_2_n_0\,
      \s_axi_rdata_reg[5]_0\ => \s_axi_rdata[5]_i_4_n_0\,
      \s_axi_rdata_reg[6]\ => \s_axi_rdata[6]_i_2_n_0\,
      \s_axi_rdata_reg[6]_0\ => \s_axi_rdata[6]_i_3_n_0\,
      \s_axi_rdata_reg[6]_1\ => \s_axi_rdata[10]_i_3_n_0\,
      servo_pwm => servo_pwm,
      \w_data_reg[0]\ => burst_n_0,
      \w_data_reg[12]\ => burst_n_3,
      \w_data_reg[21]\ => burst_n_4,
      \w_data_reg[30]\ => burst_n_1
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
\s_axi_bresp[1]_i_1\: unisim.vcomponents.LUT1
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => s_axi_aresetn,
      O => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_bresp[1]_i_4\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FFFFA2AA"
    )
        port map (
      I0 => aw_address(3),
      I1 => aw_address(5),
      I2 => aw_address(4),
      I3 => aw_address(2),
      I4 => \s_axi_bresp[1]_i_7_n_0\,
      O => \s_axi_bresp[1]_i_4_n_0\
    );
\s_axi_bresp[1]_i_5\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"FFFE"
    )
        port map (
      I0 => burst_n_0,
      I1 => burst_n_1,
      I2 => burst_n_4,
      I3 => burst_n_3,
      O => \s_axi_bresp[1]_i_5_n_0\
    );
\s_axi_bresp[1]_i_7\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FFFFFFFE"
    )
        port map (
      I0 => aw_address(6),
      I1 => aw_address(7),
      I2 => aw_address(0),
      I3 => aw_address(1),
      I4 => burst_n_5,
      O => \s_axi_bresp[1]_i_7_n_0\
    );
\s_axi_bresp_reg[1]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => '1',
      D => burst_n_39,
      Q => \^s_axi_bresp\(0),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
s_axi_bvalid_i_1: unisim.vcomponents.LUT4
    generic map(
      INIT => X"5C50"
    )
        port map (
      I0 => s_axi_bready,
      I1 => aw_pending,
      I2 => \^s_axi_bvalid_reg_0\,
      I3 => w_pending_reg_n_0,
      O => s_axi_bvalid_i_1_n_0
    );
s_axi_bvalid_reg: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => '1',
      D => s_axi_bvalid_i_1_n_0,
      Q => \^s_axi_bvalid_reg_0\,
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata[10]_i_3\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"00000001"
    )
        port map (
      I0 => s_axi_araddr(11),
      I1 => s_axi_araddr(10),
      I2 => s_axi_araddr(0),
      I3 => \s_axi_rdata[31]_i_5_n_0\,
      I4 => s_axi_araddr(6),
      O => \s_axi_rdata[10]_i_3_n_0\
    );
\s_axi_rdata[12]_i_2\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0000000100000000"
    )
        port map (
      I0 => \s_axi_rresp[1]_i_2_n_0\,
      I1 => s_axi_araddr(2),
      I2 => s_axi_araddr(3),
      I3 => s_axi_araddr(5),
      I4 => s_axi_araddr(4),
      I5 => s_axi_araddr(6),
      O => \s_axi_rdata[12]_i_2_n_0\
    );
\s_axi_rdata[13]_i_2\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0000000000000402"
    )
        port map (
      I0 => s_axi_araddr(6),
      I1 => s_axi_araddr(4),
      I2 => s_axi_araddr(5),
      I3 => s_axi_araddr(3),
      I4 => s_axi_araddr(2),
      I5 => \s_axi_rresp[1]_i_2_n_0\,
      O => \s_axi_rdata[13]_i_2_n_0\
    );
\s_axi_rdata[15]_i_2\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"0400"
    )
        port map (
      I0 => s_axi_araddr(3),
      I1 => s_axi_araddr(5),
      I2 => s_axi_araddr(4),
      I3 => \s_axi_rdata[17]_i_4_n_0\,
      O => \s_axi_rdata[15]_i_2_n_0\
    );
\s_axi_rdata[17]_i_3\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"00000001"
    )
        port map (
      I0 => s_axi_araddr(4),
      I1 => s_axi_araddr(5),
      I2 => s_axi_araddr(3),
      I3 => s_axi_araddr(2),
      I4 => \s_axi_rresp[1]_i_2_n_0\,
      O => \s_axi_rdata[17]_i_3_n_0\
    );
\s_axi_rdata[17]_i_4\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0000000000000001"
    )
        port map (
      I0 => s_axi_araddr(6),
      I1 => \s_axi_rdata[31]_i_5_n_0\,
      I2 => s_axi_araddr(0),
      I3 => s_axi_araddr(10),
      I4 => s_axi_araddr(11),
      I5 => s_axi_araddr(2),
      O => \s_axi_rdata[17]_i_4_n_0\
    );
\s_axi_rdata[17]_i_5\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0000000100000000"
    )
        port map (
      I0 => s_axi_araddr(6),
      I1 => \s_axi_rdata[31]_i_5_n_0\,
      I2 => s_axi_araddr(0),
      I3 => s_axi_araddr(10),
      I4 => s_axi_araddr(11),
      I5 => s_axi_araddr(2),
      O => \s_axi_rdata[17]_i_5_n_0\
    );
\s_axi_rdata[19]_i_2\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"0040"
    )
        port map (
      I0 => s_axi_araddr(4),
      I1 => \s_axi_rdata[17]_i_4_n_0\,
      I2 => s_axi_araddr(3),
      I3 => s_axi_araddr(5),
      O => \s_axi_rdata[19]_i_2_n_0\
    );
\s_axi_rdata[19]_i_3\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0000000000020000"
    )
        port map (
      I0 => s_axi_araddr(4),
      I1 => s_axi_araddr(6),
      I2 => \s_axi_rdata[31]_i_5_n_0\,
      I3 => \s_axi_rdata[31]_i_6_n_0\,
      I4 => s_axi_araddr(2),
      I5 => \s_axi_rdata[19]_i_4_n_0\,
      O => \s_axi_rdata[19]_i_3_n_0\
    );
\s_axi_rdata[19]_i_4\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"E"
    )
        port map (
      I0 => s_axi_araddr(3),
      I1 => s_axi_araddr(5),
      O => \s_axi_rdata[19]_i_4_n_0\
    );
\s_axi_rdata[1]_i_3\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"40000000"
    )
        port map (
      I0 => s_axi_araddr(3),
      I1 => s_axi_araddr(5),
      I2 => s_axi_araddr(4),
      I3 => \s_axi_rdata[10]_i_3_n_0\,
      I4 => s_axi_araddr(2),
      O => \s_axi_rdata[1]_i_3_n_0\
    );
\s_axi_rdata[1]_i_4\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0000000000000001"
    )
        port map (
      I0 => s_axi_araddr(6),
      I1 => \s_axi_rdata[31]_i_5_n_0\,
      I2 => s_axi_araddr(0),
      I3 => s_axi_araddr(10),
      I4 => s_axi_araddr(11),
      I5 => s_axi_araddr(4),
      O => \s_axi_rdata[1]_i_4_n_0\
    );
\s_axi_rdata[20]_i_2\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"10000700"
    )
        port map (
      I0 => s_axi_araddr(3),
      I1 => s_axi_araddr(5),
      I2 => s_axi_araddr(2),
      I3 => \s_axi_rdata[10]_i_3_n_0\,
      I4 => s_axi_araddr(4),
      O => \s_axi_rdata[20]_i_2_n_0\
    );
\s_axi_rdata[22]_i_2\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"0444"
    )
        port map (
      I0 => s_axi_araddr(4),
      I1 => \s_axi_rdata[17]_i_4_n_0\,
      I2 => s_axi_araddr(5),
      I3 => s_axi_araddr(3),
      O => \s_axi_rdata[22]_i_2_n_0\
    );
\s_axi_rdata[24]_i_2\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"0600"
    )
        port map (
      I0 => s_axi_araddr(5),
      I1 => s_axi_araddr(3),
      I2 => s_axi_araddr(4),
      I3 => \s_axi_rdata[17]_i_4_n_0\,
      O => \s_axi_rdata[24]_i_2_n_0\
    );
\s_axi_rdata[25]_i_2\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"B"
    )
        port map (
      I0 => s_axi_araddr(5),
      I1 => s_axi_araddr(3),
      O => \s_axi_rdata[25]_i_2_n_0\
    );
\s_axi_rdata[26]_i_2\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"2"
    )
        port map (
      I0 => s_axi_araddr(5),
      I1 => s_axi_araddr(3),
      O => \s_axi_rdata[26]_i_2_n_0\
    );
\s_axi_rdata[2]_i_2\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"00C4000000440000"
    )
        port map (
      I0 => s_axi_araddr(5),
      I1 => \s_axi_rdata[10]_i_3_n_0\,
      I2 => s_axi_araddr(2),
      I3 => s_axi_araddr(4),
      I4 => s_axi_araddr(3),
      I5 => scratch(2),
      O => \s_axi_rdata[2]_i_2_n_0\
    );
\s_axi_rdata[30]_i_2\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"2"
    )
        port map (
      I0 => \s_axi_rdata[17]_i_4_n_0\,
      I1 => s_axi_araddr(4),
      O => \s_axi_rdata[30]_i_2_n_0\
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
\s_axi_rdata[31]_i_3\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"80000000"
    )
        port map (
      I0 => s_axi_araddr(3),
      I1 => s_axi_araddr(5),
      I2 => \s_axi_rdata[10]_i_3_n_0\,
      I3 => s_axi_araddr(2),
      I4 => s_axi_araddr(4),
      O => \s_axi_rdata[31]_i_3_n_0\
    );
\s_axi_rdata[31]_i_4\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0000000000010000"
    )
        port map (
      I0 => \s_axi_rdata[6]_i_3_n_0\,
      I1 => s_axi_araddr(6),
      I2 => \s_axi_rdata[31]_i_5_n_0\,
      I3 => \s_axi_rdata[31]_i_6_n_0\,
      I4 => s_axi_araddr(2),
      I5 => s_axi_araddr(4),
      O => \s_axi_rdata[31]_i_4_n_0\
    );
\s_axi_rdata[31]_i_5\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"FFFE"
    )
        port map (
      I0 => s_axi_araddr(7),
      I1 => s_axi_araddr(1),
      I2 => s_axi_araddr(9),
      I3 => s_axi_araddr(8),
      O => \s_axi_rdata[31]_i_5_n_0\
    );
\s_axi_rdata[31]_i_6\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"FE"
    )
        port map (
      I0 => s_axi_araddr(11),
      I1 => s_axi_araddr(10),
      I2 => s_axi_araddr(0),
      O => \s_axi_rdata[31]_i_6_n_0\
    );
\s_axi_rdata[3]_i_3\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"00010000"
    )
        port map (
      I0 => s_axi_araddr(2),
      I1 => \s_axi_rdata[31]_i_6_n_0\,
      I2 => \s_axi_rdata[31]_i_5_n_0\,
      I3 => s_axi_araddr(6),
      I4 => s_axi_araddr(4),
      O => \s_axi_rdata[3]_i_3_n_0\
    );
\s_axi_rdata[4]_i_2\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0000010000000003"
    )
        port map (
      I0 => s_axi_araddr(6),
      I1 => \s_axi_rresp[1]_i_2_n_0\,
      I2 => s_axi_araddr(2),
      I3 => s_axi_araddr(3),
      I4 => s_axi_araddr(5),
      I5 => s_axi_araddr(4),
      O => \s_axi_rdata[4]_i_2_n_0\
    );
\s_axi_rdata[4]_i_3\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"00020000"
    )
        port map (
      I0 => s_axi_araddr(2),
      I1 => \s_axi_rdata[31]_i_6_n_0\,
      I2 => \s_axi_rdata[31]_i_5_n_0\,
      I3 => s_axi_araddr(6),
      I4 => s_axi_araddr(4),
      O => \s_axi_rdata[4]_i_3_n_0\
    );
\s_axi_rdata[4]_i_5\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"00B00000C0300000"
    )
        port map (
      I0 => scratch(4),
      I1 => s_axi_araddr(2),
      I2 => \s_axi_rdata[10]_i_3_n_0\,
      I3 => s_axi_araddr(4),
      I4 => s_axi_araddr(5),
      I5 => s_axi_araddr(3),
      O => \s_axi_rdata[4]_i_5_n_0\
    );
\s_axi_rdata[5]_i_2\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0001000000000000"
    )
        port map (
      I0 => s_axi_araddr(4),
      I1 => \s_axi_rdata[31]_i_6_n_0\,
      I2 => \s_axi_rdata[31]_i_5_n_0\,
      I3 => s_axi_araddr(6),
      I4 => s_axi_araddr(5),
      I5 => s_axi_araddr(3),
      O => \s_axi_rdata[5]_i_2_n_0\
    );
\s_axi_rdata[5]_i_4\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"4020"
    )
        port map (
      I0 => s_axi_araddr(3),
      I1 => s_axi_araddr(2),
      I2 => \s_axi_rdata[10]_i_3_n_0\,
      I3 => s_axi_araddr(4),
      O => \s_axi_rdata[5]_i_4_n_0\
    );
\s_axi_rdata[6]_i_2\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0003000300020205"
    )
        port map (
      I0 => s_axi_araddr(4),
      I1 => s_axi_araddr(6),
      I2 => \s_axi_rresp[1]_i_2_n_0\,
      I3 => s_axi_araddr(2),
      I4 => s_axi_araddr(5),
      I5 => s_axi_araddr(3),
      O => \s_axi_rdata[6]_i_2_n_0\
    );
\s_axi_rdata[6]_i_3\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"7"
    )
        port map (
      I0 => s_axi_araddr(3),
      I1 => s_axi_araddr(5),
      O => \s_axi_rdata[6]_i_3_n_0\
    );
\s_axi_rdata[9]_i_2\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"08"
    )
        port map (
      I0 => \s_axi_rdata[17]_i_4_n_0\,
      I1 => s_axi_araddr(3),
      I2 => s_axi_araddr(5),
      O => \s_axi_rdata[9]_i_2_n_0\
    );
\s_axi_rdata_reg[0]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_37,
      Q => s_axi_rdata(0),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[10]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_27,
      Q => s_axi_rdata(10),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[11]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_26,
      Q => s_axi_rdata(11),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[12]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_25,
      Q => s_axi_rdata(12),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[13]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_24,
      Q => s_axi_rdata(13),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[14]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_23,
      Q => s_axi_rdata(14),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[15]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_22,
      Q => s_axi_rdata(15),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[16]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_21,
      Q => s_axi_rdata(16),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[17]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_20,
      Q => s_axi_rdata(17),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[18]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_19,
      Q => s_axi_rdata(18),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[19]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_18,
      Q => s_axi_rdata(19),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[1]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_36,
      Q => s_axi_rdata(1),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[20]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_17,
      Q => s_axi_rdata(20),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[21]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_16,
      Q => s_axi_rdata(21),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[22]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_15,
      Q => s_axi_rdata(22),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[23]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_14,
      Q => s_axi_rdata(23),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[24]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_13,
      Q => s_axi_rdata(24),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[25]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_12,
      Q => s_axi_rdata(25),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[26]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_11,
      Q => s_axi_rdata(26),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[27]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_10,
      Q => s_axi_rdata(27),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[28]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_9,
      Q => s_axi_rdata(28),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[29]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_8,
      Q => s_axi_rdata(29),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[2]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_35,
      Q => s_axi_rdata(2),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[30]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_7,
      Q => s_axi_rdata(30),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[31]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_6,
      Q => s_axi_rdata(31),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[3]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_34,
      Q => s_axi_rdata(3),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[4]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_33,
      Q => s_axi_rdata(4),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[5]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_32,
      Q => s_axi_rdata(5),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[6]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_31,
      Q => s_axi_rdata(6),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[7]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_30,
      Q => s_axi_rdata(7),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[8]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_29,
      Q => s_axi_rdata(8),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[9]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_28,
      Q => s_axi_rdata(9),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rresp[1]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"EEEEEEEFEEEEEEEA"
    )
        port map (
      I0 => \s_axi_rresp[1]_i_2_n_0\,
      I1 => s_axi_araddr(6),
      I2 => s_axi_araddr(5),
      I3 => s_axi_araddr(3),
      I4 => s_axi_araddr(2),
      I5 => s_axi_araddr(4),
      O => \s_axi_rresp[1]_i_1_n_0\
    );
\s_axi_rresp[1]_i_2\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"FFFE"
    )
        port map (
      I0 => \s_axi_rdata[31]_i_5_n_0\,
      I1 => s_axi_araddr(0),
      I2 => s_axi_araddr(10),
      I3 => s_axi_araddr(11),
      O => \s_axi_rresp[1]_i_2_n_0\
    );
\s_axi_rresp_reg[1]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => \s_axi_rresp[1]_i_1_n_0\,
      Q => s_axi_rresp(0),
      R => \s_axi_bresp[1]_i_1_n_0\
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
      R => \s_axi_bresp[1]_i_1_n_0\
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
\scratch[15]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0000200000000000"
    )
        port map (
      I0 => aw_address(5),
      I1 => aw_address(4),
      I2 => aw_address(2),
      I3 => aw_address(3),
      I4 => burst_n_2,
      I5 => p_1_in,
      O => \scratch[15]_i_1_n_0\
    );
\scratch[23]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0000200000000000"
    )
        port map (
      I0 => aw_address(5),
      I1 => aw_address(4),
      I2 => aw_address(2),
      I3 => aw_address(3),
      I4 => burst_n_2,
      I5 => p_2_in,
      O => \scratch[23]_i_1_n_0\
    );
\scratch[31]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0000200000000000"
    )
        port map (
      I0 => aw_address(5),
      I1 => aw_address(4),
      I2 => aw_address(2),
      I3 => aw_address(3),
      I4 => burst_n_2,
      I5 => \w_strobes_reg_n_0_[3]\,
      O => \scratch[31]_i_1_n_0\
    );
\scratch[7]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0000200000000000"
    )
        port map (
      I0 => aw_address(5),
      I1 => aw_address(4),
      I2 => aw_address(2),
      I3 => aw_address(3),
      I4 => burst_n_2,
      I5 => p_0_in_0,
      O => \scratch[7]_i_1_n_0\
    );
\scratch_reg[0]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \scratch[7]_i_1_n_0\,
      D => w_data(0),
      Q => scratch(0),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\scratch_reg[10]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \scratch[15]_i_1_n_0\,
      D => w_data(10),
      Q => scratch(10),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\scratch_reg[11]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \scratch[15]_i_1_n_0\,
      D => w_data(11),
      Q => scratch(11),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\scratch_reg[12]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \scratch[15]_i_1_n_0\,
      D => w_data(12),
      Q => scratch(12),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\scratch_reg[13]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \scratch[15]_i_1_n_0\,
      D => w_data(13),
      Q => scratch(13),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\scratch_reg[14]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \scratch[15]_i_1_n_0\,
      D => w_data(14),
      Q => scratch(14),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\scratch_reg[15]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \scratch[15]_i_1_n_0\,
      D => w_data(15),
      Q => scratch(15),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\scratch_reg[16]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \scratch[23]_i_1_n_0\,
      D => w_data(16),
      Q => scratch(16),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\scratch_reg[17]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \scratch[23]_i_1_n_0\,
      D => w_data(17),
      Q => scratch(17),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\scratch_reg[18]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \scratch[23]_i_1_n_0\,
      D => w_data(18),
      Q => scratch(18),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\scratch_reg[19]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \scratch[23]_i_1_n_0\,
      D => w_data(19),
      Q => scratch(19),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\scratch_reg[1]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \scratch[7]_i_1_n_0\,
      D => w_data(1),
      Q => scratch(1),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\scratch_reg[20]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \scratch[23]_i_1_n_0\,
      D => w_data(20),
      Q => scratch(20),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\scratch_reg[21]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \scratch[23]_i_1_n_0\,
      D => w_data(21),
      Q => scratch(21),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\scratch_reg[22]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \scratch[23]_i_1_n_0\,
      D => w_data(22),
      Q => scratch(22),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\scratch_reg[23]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \scratch[23]_i_1_n_0\,
      D => w_data(23),
      Q => scratch(23),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\scratch_reg[24]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \scratch[31]_i_1_n_0\,
      D => w_data(24),
      Q => scratch(24),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\scratch_reg[25]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \scratch[31]_i_1_n_0\,
      D => w_data(25),
      Q => scratch(25),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\scratch_reg[26]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \scratch[31]_i_1_n_0\,
      D => w_data(26),
      Q => scratch(26),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\scratch_reg[27]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \scratch[31]_i_1_n_0\,
      D => w_data(27),
      Q => scratch(27),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\scratch_reg[28]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \scratch[31]_i_1_n_0\,
      D => w_data(28),
      Q => scratch(28),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\scratch_reg[29]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \scratch[31]_i_1_n_0\,
      D => w_data(29),
      Q => scratch(29),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\scratch_reg[2]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \scratch[7]_i_1_n_0\,
      D => w_data(2),
      Q => scratch(2),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\scratch_reg[30]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \scratch[31]_i_1_n_0\,
      D => w_data(30),
      Q => scratch(30),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\scratch_reg[31]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \scratch[31]_i_1_n_0\,
      D => w_data(31),
      Q => scratch(31),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\scratch_reg[3]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \scratch[7]_i_1_n_0\,
      D => w_data(3),
      Q => scratch(3),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\scratch_reg[4]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \scratch[7]_i_1_n_0\,
      D => w_data(4),
      Q => scratch(4),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\scratch_reg[5]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \scratch[7]_i_1_n_0\,
      D => w_data(5),
      Q => scratch(5),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\scratch_reg[6]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \scratch[7]_i_1_n_0\,
      D => w_data(6),
      Q => scratch(6),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\scratch_reg[7]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \scratch[7]_i_1_n_0\,
      D => w_data(7),
      Q => scratch(7),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\scratch_reg[8]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \scratch[15]_i_1_n_0\,
      D => w_data(8),
      Q => scratch(8),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\scratch_reg[9]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \scratch[15]_i_1_n_0\,
      D => w_data(9),
      Q => scratch(9),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\w_data[31]_i_1\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"04"
    )
        port map (
      I0 => w_pending_reg_n_0,
      I1 => s_axi_wvalid,
      I2 => \^s_axi_bvalid_reg_0\,
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
      R => \s_axi_bresp[1]_i_1_n_0\
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
      R => \s_axi_bresp[1]_i_1_n_0\
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
      R => \s_axi_bresp[1]_i_1_n_0\
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
      R => \s_axi_bresp[1]_i_1_n_0\
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
      R => \s_axi_bresp[1]_i_1_n_0\
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
      R => \s_axi_bresp[1]_i_1_n_0\
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
      R => \s_axi_bresp[1]_i_1_n_0\
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
      R => \s_axi_bresp[1]_i_1_n_0\
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
      R => \s_axi_bresp[1]_i_1_n_0\
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
      R => \s_axi_bresp[1]_i_1_n_0\
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
      R => \s_axi_bresp[1]_i_1_n_0\
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
      R => \s_axi_bresp[1]_i_1_n_0\
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
      R => \s_axi_bresp[1]_i_1_n_0\
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
      R => \s_axi_bresp[1]_i_1_n_0\
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
      R => \s_axi_bresp[1]_i_1_n_0\
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
      R => \s_axi_bresp[1]_i_1_n_0\
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
      R => \s_axi_bresp[1]_i_1_n_0\
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
      R => \s_axi_bresp[1]_i_1_n_0\
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
      R => \s_axi_bresp[1]_i_1_n_0\
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
      R => \s_axi_bresp[1]_i_1_n_0\
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
      R => \s_axi_bresp[1]_i_1_n_0\
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
      R => \s_axi_bresp[1]_i_1_n_0\
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
      R => \s_axi_bresp[1]_i_1_n_0\
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
      R => \s_axi_bresp[1]_i_1_n_0\
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
      R => \s_axi_bresp[1]_i_1_n_0\
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
      R => \s_axi_bresp[1]_i_1_n_0\
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
      R => \s_axi_bresp[1]_i_1_n_0\
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
      R => \s_axi_bresp[1]_i_1_n_0\
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
      R => \s_axi_bresp[1]_i_1_n_0\
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
      R => \s_axi_bresp[1]_i_1_n_0\
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
      R => \s_axi_bresp[1]_i_1_n_0\
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
      R => \s_axi_bresp[1]_i_1_n_0\
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
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => '1',
      D => w_pending_i_2_n_0,
      Q => w_pending_reg_n_0,
      R => w_pending
    );
\w_strobes_reg[0]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wstrb(0),
      Q => p_0_in_0,
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\w_strobes_reg[1]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => w_pending0,
      D => s_axi_wstrb(1),
      Q => p_1_in,
      R => \s_axi_bresp[1]_i_1_n_0\
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
      R => \s_axi_bresp[1]_i_1_n_0\
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
      R => \s_axi_bresp[1]_i_1_n_0\
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
