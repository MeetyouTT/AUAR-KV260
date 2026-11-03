-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- --------------------------------------------------------------------------------
-- Tool Version: Vivado v.2022.2 (lin64) Build 3671981 Fri Oct 14 04:59:54 MDT 2022
-- Date        : Sun Oct  4 20:57:15 2026
-- Host        : ghmd-MRA-XXX running 64-bit Ubuntu 20.04.4 LTS
-- Command     : write_vhdl -force -mode funcsim
--               /home/ghmd/kv260-j2-pwm-20261004/evidence/20261005T035504.065314Z-build/project/pwm_bench.gen/sources_1/bd/pwm_bench/ip/pwm_bench_probe_0/pwm_bench_probe_0_sim_netlist.vhdl
-- Design      : pwm_bench_probe_0
-- Purpose     : This VHDL netlist is a functional simulation representation of the design and should not be modified or
--               synthesized. This netlist cannot be used for SDF annotated simulation.
-- Device      : xck26-sfvc784-2LV-c
-- --------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
library UNISIM;
use UNISIM.VCOMPONENTS.ALL;
entity pwm_bench_probe_0_pwm_burst is
  port (
    servo_pwm : out STD_LOGIC;
    \aw_address_reg[10]\ : out STD_LOGIC;
    D : out STD_LOGIC_VECTOR ( 31 downto 0 );
    \s_axi_bresp_reg[1]\ : out STD_LOGIC;
    s_axi_aclk : in STD_LOGIC;
    s_axi_aresetn : in STD_LOGIC;
    s_axi_araddr : in STD_LOGIC_VECTOR ( 3 downto 0 );
    Q : in STD_LOGIC_VECTOR ( 31 downto 0 );
    \s_axi_bresp[1]_i_10_0\ : in STD_LOGIC_VECTOR ( 31 downto 0 );
    \s_axi_bresp[1]_i_5_0\ : in STD_LOGIC;
    aw_pending : in STD_LOGIC;
    \s_axi_bresp[1]_i_5_1\ : in STD_LOGIC;
    \s_axi_bresp[1]_i_7_0\ : in STD_LOGIC_VECTOR ( 3 downto 0 );
    \scratch[31]_i_2\ : in STD_LOGIC_VECTOR ( 11 downto 0 );
    \s_axi_rdata_reg[7]\ : in STD_LOGIC;
    \s_axi_rdata_reg[8]\ : in STD_LOGIC;
    \s_axi_rdata_reg[25]\ : in STD_LOGIC;
    \s_axi_rdata_reg[0]\ : in STD_LOGIC;
    \s_axi_rdata_reg[0]_0\ : in STD_LOGIC;
    \s_axi_rdata_reg[1]\ : in STD_LOGIC;
    \s_axi_rdata_reg[22]\ : in STD_LOGIC;
    \s_axi_rdata_reg[22]_0\ : in STD_LOGIC;
    \s_axi_rdata_reg[23]\ : in STD_LOGIC;
    \s_axi_rdata_reg[28]\ : in STD_LOGIC;
    \s_axi_rdata_reg[13]\ : in STD_LOGIC;
    s_axi_bresp : in STD_LOGIC_VECTOR ( 0 to 0 );
    \s_axi_bresp_reg[1]_0\ : in STD_LOGIC;
    \s_axi_bresp_reg[1]_1\ : in STD_LOGIC
  );
  attribute ORIG_REF_NAME : string;
  attribute ORIG_REF_NAME of pwm_bench_probe_0_pwm_burst : entity is "pwm_burst";
end pwm_bench_probe_0_pwm_burst;

architecture STRUCTURE of pwm_bench_probe_0_pwm_burst is
  signal \^aw_address_reg[10]\ : STD_LOGIC;
  signal busy : STD_LOGIC;
  signal busy3_out : STD_LOGIC;
  signal busy_i_1_n_0 : STD_LOGIC;
  signal data0 : STD_LOGIC_VECTOR ( 31 downto 1 );
  signal \frames_left0_carry__0_i_1_n_0\ : STD_LOGIC;
  signal \frames_left0_carry__0_i_2_n_0\ : STD_LOGIC;
  signal \frames_left0_carry__0_i_3_n_0\ : STD_LOGIC;
  signal \frames_left0_carry__0_i_4_n_0\ : STD_LOGIC;
  signal \frames_left0_carry__0_i_5_n_0\ : STD_LOGIC;
  signal \frames_left0_carry__0_i_6_n_0\ : STD_LOGIC;
  signal \frames_left0_carry__0_i_7_n_0\ : STD_LOGIC;
  signal \frames_left0_carry__0_i_8_n_0\ : STD_LOGIC;
  signal \frames_left0_carry__0_n_0\ : STD_LOGIC;
  signal \frames_left0_carry__0_n_1\ : STD_LOGIC;
  signal \frames_left0_carry__0_n_2\ : STD_LOGIC;
  signal \frames_left0_carry__0_n_3\ : STD_LOGIC;
  signal \frames_left0_carry__0_n_4\ : STD_LOGIC;
  signal \frames_left0_carry__0_n_5\ : STD_LOGIC;
  signal \frames_left0_carry__0_n_6\ : STD_LOGIC;
  signal \frames_left0_carry__0_n_7\ : STD_LOGIC;
  signal \frames_left0_carry__1_i_1_n_0\ : STD_LOGIC;
  signal \frames_left0_carry__1_i_2_n_0\ : STD_LOGIC;
  signal \frames_left0_carry__1_i_3_n_0\ : STD_LOGIC;
  signal \frames_left0_carry__1_i_4_n_0\ : STD_LOGIC;
  signal \frames_left0_carry__1_i_5_n_0\ : STD_LOGIC;
  signal \frames_left0_carry__1_i_6_n_0\ : STD_LOGIC;
  signal \frames_left0_carry__1_i_7_n_0\ : STD_LOGIC;
  signal \frames_left0_carry__1_i_8_n_0\ : STD_LOGIC;
  signal \frames_left0_carry__1_n_0\ : STD_LOGIC;
  signal \frames_left0_carry__1_n_1\ : STD_LOGIC;
  signal \frames_left0_carry__1_n_2\ : STD_LOGIC;
  signal \frames_left0_carry__1_n_3\ : STD_LOGIC;
  signal \frames_left0_carry__1_n_4\ : STD_LOGIC;
  signal \frames_left0_carry__1_n_5\ : STD_LOGIC;
  signal \frames_left0_carry__1_n_6\ : STD_LOGIC;
  signal \frames_left0_carry__1_n_7\ : STD_LOGIC;
  signal \frames_left0_carry__2_i_1_n_0\ : STD_LOGIC;
  signal \frames_left0_carry__2_i_2_n_0\ : STD_LOGIC;
  signal \frames_left0_carry__2_i_3_n_0\ : STD_LOGIC;
  signal \frames_left0_carry__2_i_4_n_0\ : STD_LOGIC;
  signal \frames_left0_carry__2_i_5_n_0\ : STD_LOGIC;
  signal \frames_left0_carry__2_i_6_n_0\ : STD_LOGIC;
  signal \frames_left0_carry__2_i_7_n_0\ : STD_LOGIC;
  signal \frames_left0_carry__2_n_2\ : STD_LOGIC;
  signal \frames_left0_carry__2_n_3\ : STD_LOGIC;
  signal \frames_left0_carry__2_n_4\ : STD_LOGIC;
  signal \frames_left0_carry__2_n_5\ : STD_LOGIC;
  signal \frames_left0_carry__2_n_6\ : STD_LOGIC;
  signal \frames_left0_carry__2_n_7\ : STD_LOGIC;
  signal frames_left0_carry_i_1_n_0 : STD_LOGIC;
  signal frames_left0_carry_i_2_n_0 : STD_LOGIC;
  signal frames_left0_carry_i_3_n_0 : STD_LOGIC;
  signal frames_left0_carry_i_4_n_0 : STD_LOGIC;
  signal frames_left0_carry_i_5_n_0 : STD_LOGIC;
  signal frames_left0_carry_i_6_n_0 : STD_LOGIC;
  signal frames_left0_carry_i_7_n_0 : STD_LOGIC;
  signal frames_left0_carry_i_8_n_0 : STD_LOGIC;
  signal frames_left0_carry_n_0 : STD_LOGIC;
  signal frames_left0_carry_n_1 : STD_LOGIC;
  signal frames_left0_carry_n_2 : STD_LOGIC;
  signal frames_left0_carry_n_3 : STD_LOGIC;
  signal frames_left0_carry_n_4 : STD_LOGIC;
  signal frames_left0_carry_n_5 : STD_LOGIC;
  signal frames_left0_carry_n_6 : STD_LOGIC;
  signal frames_left0_carry_n_7 : STD_LOGIC;
  signal \frames_left[31]_i_1_n_0\ : STD_LOGIC;
  signal \frames_left[31]_i_2_n_0\ : STD_LOGIC;
  signal \frames_left[5]_i_1_n_0\ : STD_LOGIC;
  signal \frames_left[5]_i_2_n_0\ : STD_LOGIC;
  signal \frames_left_reg_n_0_[0]\ : STD_LOGIC;
  signal \frames_left_reg_n_0_[10]\ : STD_LOGIC;
  signal \frames_left_reg_n_0_[11]\ : STD_LOGIC;
  signal \frames_left_reg_n_0_[12]\ : STD_LOGIC;
  signal \frames_left_reg_n_0_[13]\ : STD_LOGIC;
  signal \frames_left_reg_n_0_[14]\ : STD_LOGIC;
  signal \frames_left_reg_n_0_[15]\ : STD_LOGIC;
  signal \frames_left_reg_n_0_[16]\ : STD_LOGIC;
  signal \frames_left_reg_n_0_[17]\ : STD_LOGIC;
  signal \frames_left_reg_n_0_[18]\ : STD_LOGIC;
  signal \frames_left_reg_n_0_[19]\ : STD_LOGIC;
  signal \frames_left_reg_n_0_[1]\ : STD_LOGIC;
  signal \frames_left_reg_n_0_[20]\ : STD_LOGIC;
  signal \frames_left_reg_n_0_[21]\ : STD_LOGIC;
  signal \frames_left_reg_n_0_[22]\ : STD_LOGIC;
  signal \frames_left_reg_n_0_[23]\ : STD_LOGIC;
  signal \frames_left_reg_n_0_[24]\ : STD_LOGIC;
  signal \frames_left_reg_n_0_[25]\ : STD_LOGIC;
  signal \frames_left_reg_n_0_[26]\ : STD_LOGIC;
  signal \frames_left_reg_n_0_[27]\ : STD_LOGIC;
  signal \frames_left_reg_n_0_[28]\ : STD_LOGIC;
  signal \frames_left_reg_n_0_[29]\ : STD_LOGIC;
  signal \frames_left_reg_n_0_[2]\ : STD_LOGIC;
  signal \frames_left_reg_n_0_[30]\ : STD_LOGIC;
  signal \frames_left_reg_n_0_[31]\ : STD_LOGIC;
  signal \frames_left_reg_n_0_[3]\ : STD_LOGIC;
  signal \frames_left_reg_n_0_[4]\ : STD_LOGIC;
  signal \frames_left_reg_n_0_[5]\ : STD_LOGIC;
  signal \frames_left_reg_n_0_[6]\ : STD_LOGIC;
  signal \frames_left_reg_n_0_[7]\ : STD_LOGIC;
  signal \frames_left_reg_n_0_[8]\ : STD_LOGIC;
  signal \frames_left_reg_n_0_[9]\ : STD_LOGIC;
  signal p_1_in : STD_LOGIC_VECTOR ( 31 downto 0 );
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
  signal pwm1 : STD_LOGIC_VECTOR ( 32 downto 0 );
  signal pwm_i_10_n_0 : STD_LOGIC;
  signal pwm_i_11_n_0 : STD_LOGIC;
  signal pwm_i_12_n_0 : STD_LOGIC;
  signal pwm_i_14_n_0 : STD_LOGIC;
  signal pwm_i_16_n_0 : STD_LOGIC;
  signal pwm_i_17_n_0 : STD_LOGIC;
  signal pwm_i_18_n_0 : STD_LOGIC;
  signal pwm_i_19_n_0 : STD_LOGIC;
  signal pwm_i_1_n_0 : STD_LOGIC;
  signal pwm_i_20_n_0 : STD_LOGIC;
  signal pwm_i_21_n_0 : STD_LOGIC;
  signal pwm_i_22_n_0 : STD_LOGIC;
  signal pwm_i_23_n_0 : STD_LOGIC;
  signal pwm_i_24_n_0 : STD_LOGIC;
  signal pwm_i_26_n_0 : STD_LOGIC;
  signal pwm_i_27_n_0 : STD_LOGIC;
  signal pwm_i_28_n_0 : STD_LOGIC;
  signal pwm_i_29_n_0 : STD_LOGIC;
  signal pwm_i_2_n_0 : STD_LOGIC;
  signal pwm_i_30_n_0 : STD_LOGIC;
  signal pwm_i_31_n_0 : STD_LOGIC;
  signal pwm_i_32_n_0 : STD_LOGIC;
  signal pwm_i_3_n_0 : STD_LOGIC;
  signal pwm_i_4_n_0 : STD_LOGIC;
  signal pwm_i_5_n_0 : STD_LOGIC;
  signal pwm_i_6_n_0 : STD_LOGIC;
  signal pwm_i_7_n_0 : STD_LOGIC;
  signal pwm_i_8_n_0 : STD_LOGIC;
  signal pwm_i_9_n_0 : STD_LOGIC;
  signal pwm_reg_i_13_n_0 : STD_LOGIC;
  signal pwm_reg_i_13_n_1 : STD_LOGIC;
  signal pwm_reg_i_13_n_2 : STD_LOGIC;
  signal pwm_reg_i_13_n_3 : STD_LOGIC;
  signal pwm_reg_i_13_n_4 : STD_LOGIC;
  signal pwm_reg_i_13_n_5 : STD_LOGIC;
  signal pwm_reg_i_13_n_6 : STD_LOGIC;
  signal pwm_reg_i_13_n_7 : STD_LOGIC;
  signal pwm_reg_i_15_n_0 : STD_LOGIC;
  signal pwm_reg_i_15_n_1 : STD_LOGIC;
  signal pwm_reg_i_15_n_2 : STD_LOGIC;
  signal pwm_reg_i_15_n_3 : STD_LOGIC;
  signal pwm_reg_i_15_n_4 : STD_LOGIC;
  signal pwm_reg_i_15_n_5 : STD_LOGIC;
  signal pwm_reg_i_15_n_6 : STD_LOGIC;
  signal pwm_reg_i_15_n_7 : STD_LOGIC;
  signal pwm_reg_i_25_n_0 : STD_LOGIC;
  signal pwm_reg_i_25_n_1 : STD_LOGIC;
  signal pwm_reg_i_25_n_2 : STD_LOGIC;
  signal pwm_reg_i_25_n_3 : STD_LOGIC;
  signal pwm_reg_i_25_n_4 : STD_LOGIC;
  signal pwm_reg_i_25_n_5 : STD_LOGIC;
  signal pwm_reg_i_25_n_6 : STD_LOGIC;
  signal pwm_reg_i_25_n_7 : STD_LOGIC;
  signal pwm_reg_i_33_n_2 : STD_LOGIC;
  signal pwm_reg_i_33_n_3 : STD_LOGIC;
  signal pwm_reg_i_33_n_4 : STD_LOGIC;
  signal pwm_reg_i_33_n_5 : STD_LOGIC;
  signal pwm_reg_i_33_n_6 : STD_LOGIC;
  signal pwm_reg_i_33_n_7 : STD_LOGIC;
  signal \s_axi_bresp[1]_i_10_n_0\ : STD_LOGIC;
  signal \s_axi_bresp[1]_i_13_n_0\ : STD_LOGIC;
  signal \s_axi_bresp[1]_i_14_n_0\ : STD_LOGIC;
  signal \s_axi_bresp[1]_i_15_n_0\ : STD_LOGIC;
  signal \s_axi_bresp[1]_i_16_n_0\ : STD_LOGIC;
  signal \s_axi_bresp[1]_i_17_n_0\ : STD_LOGIC;
  signal \s_axi_bresp[1]_i_18_n_0\ : STD_LOGIC;
  signal \s_axi_bresp[1]_i_19_n_0\ : STD_LOGIC;
  signal \s_axi_bresp[1]_i_20_n_0\ : STD_LOGIC;
  signal \s_axi_bresp[1]_i_4_n_0\ : STD_LOGIC;
  signal \s_axi_bresp[1]_i_7_n_0\ : STD_LOGIC;
  signal \s_axi_bresp[1]_i_8_n_0\ : STD_LOGIC;
  signal \s_axi_bresp[1]_i_9_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[0]_i_3_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[10]_i_2_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[11]_i_2_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[12]_i_2_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[14]_i_2_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[15]_i_2_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[16]_i_2_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[17]_i_2_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[18]_i_2_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[19]_i_2_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[1]_i_2_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[20]_i_2_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[21]_i_2_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[26]_i_2_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[2]_i_2_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[3]_i_2_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[4]_i_2_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[5]_i_2_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[6]_i_2_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[8]_i_2_n_0\ : STD_LOGIC;
  signal \^servo_pwm\ : STD_LOGIC;
  signal \NLW_frames_left0_carry__2_CO_UNCONNECTED\ : STD_LOGIC_VECTOR ( 7 downto 6 );
  signal \NLW_frames_left0_carry__2_O_UNCONNECTED\ : STD_LOGIC_VECTOR ( 7 to 7 );
  signal \NLW_phase_reg[24]_i_1_CO_UNCONNECTED\ : STD_LOGIC_VECTOR ( 7 to 7 );
  signal NLW_pwm_reg_i_33_CO_UNCONNECTED : STD_LOGIC_VECTOR ( 6 to 6 );
  signal NLW_pwm_reg_i_33_O_UNCONNECTED : STD_LOGIC_VECTOR ( 7 to 7 );
  attribute ADDER_THRESHOLD : integer;
  attribute ADDER_THRESHOLD of frames_left0_carry : label is 35;
  attribute ADDER_THRESHOLD of \frames_left0_carry__0\ : label is 35;
  attribute ADDER_THRESHOLD of \frames_left0_carry__1\ : label is 35;
  attribute ADDER_THRESHOLD of \frames_left0_carry__2\ : label is 35;
  attribute SOFT_HLUTNM : string;
  attribute SOFT_HLUTNM of \frames_left[0]_i_1\ : label is "soft_lutpair1";
  attribute SOFT_HLUTNM of \frames_left[10]_i_1\ : label is "soft_lutpair12";
  attribute SOFT_HLUTNM of \frames_left[11]_i_1\ : label is "soft_lutpair12";
  attribute SOFT_HLUTNM of \frames_left[12]_i_1\ : label is "soft_lutpair11";
  attribute SOFT_HLUTNM of \frames_left[13]_i_1\ : label is "soft_lutpair11";
  attribute SOFT_HLUTNM of \frames_left[14]_i_1\ : label is "soft_lutpair10";
  attribute SOFT_HLUTNM of \frames_left[15]_i_1\ : label is "soft_lutpair10";
  attribute SOFT_HLUTNM of \frames_left[16]_i_1\ : label is "soft_lutpair9";
  attribute SOFT_HLUTNM of \frames_left[17]_i_1\ : label is "soft_lutpair9";
  attribute SOFT_HLUTNM of \frames_left[18]_i_1\ : label is "soft_lutpair8";
  attribute SOFT_HLUTNM of \frames_left[19]_i_1\ : label is "soft_lutpair8";
  attribute SOFT_HLUTNM of \frames_left[1]_i_1\ : label is "soft_lutpair0";
  attribute SOFT_HLUTNM of \frames_left[20]_i_1\ : label is "soft_lutpair7";
  attribute SOFT_HLUTNM of \frames_left[21]_i_1\ : label is "soft_lutpair7";
  attribute SOFT_HLUTNM of \frames_left[22]_i_1\ : label is "soft_lutpair6";
  attribute SOFT_HLUTNM of \frames_left[23]_i_1\ : label is "soft_lutpair6";
  attribute SOFT_HLUTNM of \frames_left[24]_i_1\ : label is "soft_lutpair5";
  attribute SOFT_HLUTNM of \frames_left[25]_i_1\ : label is "soft_lutpair5";
  attribute SOFT_HLUTNM of \frames_left[26]_i_1\ : label is "soft_lutpair4";
  attribute SOFT_HLUTNM of \frames_left[27]_i_1\ : label is "soft_lutpair4";
  attribute SOFT_HLUTNM of \frames_left[28]_i_1\ : label is "soft_lutpair3";
  attribute SOFT_HLUTNM of \frames_left[29]_i_1\ : label is "soft_lutpair3";
  attribute SOFT_HLUTNM of \frames_left[2]_i_1\ : label is "soft_lutpair15";
  attribute SOFT_HLUTNM of \frames_left[30]_i_1\ : label is "soft_lutpair2";
  attribute SOFT_HLUTNM of \frames_left[31]_i_3\ : label is "soft_lutpair2";
  attribute SOFT_HLUTNM of \frames_left[3]_i_1\ : label is "soft_lutpair15";
  attribute SOFT_HLUTNM of \frames_left[4]_i_1\ : label is "soft_lutpair0";
  attribute SOFT_HLUTNM of \frames_left[6]_i_1\ : label is "soft_lutpair14";
  attribute SOFT_HLUTNM of \frames_left[7]_i_1\ : label is "soft_lutpair14";
  attribute SOFT_HLUTNM of \frames_left[8]_i_1\ : label is "soft_lutpair13";
  attribute SOFT_HLUTNM of \frames_left[9]_i_1\ : label is "soft_lutpair13";
  attribute ADDER_THRESHOLD of \phase_reg[0]_i_2\ : label is 16;
  attribute ADDER_THRESHOLD of \phase_reg[16]_i_1\ : label is 16;
  attribute ADDER_THRESHOLD of \phase_reg[24]_i_1\ : label is 16;
  attribute ADDER_THRESHOLD of \phase_reg[8]_i_1\ : label is 16;
  attribute SOFT_HLUTNM of pwm_i_24 : label is "soft_lutpair1";
  attribute SOFT_HLUTNM of \s_axi_rdata[10]_i_1\ : label is "soft_lutpair18";
  attribute SOFT_HLUTNM of \s_axi_rdata[12]_i_1\ : label is "soft_lutpair19";
  attribute SOFT_HLUTNM of \s_axi_rdata[15]_i_1\ : label is "soft_lutpair19";
  attribute SOFT_HLUTNM of \s_axi_rdata[16]_i_1\ : label is "soft_lutpair20";
  attribute SOFT_HLUTNM of \s_axi_rdata[17]_i_1\ : label is "soft_lutpair20";
  attribute SOFT_HLUTNM of \s_axi_rdata[18]_i_1\ : label is "soft_lutpair21";
  attribute SOFT_HLUTNM of \s_axi_rdata[19]_i_1\ : label is "soft_lutpair21";
  attribute SOFT_HLUTNM of \s_axi_rdata[20]_i_1\ : label is "soft_lutpair22";
  attribute SOFT_HLUTNM of \s_axi_rdata[21]_i_1\ : label is "soft_lutpair22";
  attribute SOFT_HLUTNM of \s_axi_rdata[2]_i_1\ : label is "soft_lutpair16";
  attribute SOFT_HLUTNM of \s_axi_rdata[3]_i_1\ : label is "soft_lutpair16";
  attribute SOFT_HLUTNM of \s_axi_rdata[4]_i_1\ : label is "soft_lutpair17";
  attribute SOFT_HLUTNM of \s_axi_rdata[5]_i_1\ : label is "soft_lutpair17";
  attribute SOFT_HLUTNM of \s_axi_rdata[6]_i_1\ : label is "soft_lutpair18";
begin
  \aw_address_reg[10]\ <= \^aw_address_reg[10]\;
  servo_pwm <= \^servo_pwm\;
busy_i_1: unisim.vcomponents.LUT5
    generic map(
      INIT => X"0000FFA8"
    )
        port map (
      I0 => busy,
      I1 => pwm_i_2_n_0,
      I2 => pwm_i_3_n_0,
      I3 => busy3_out,
      I4 => \frames_left[5]_i_1_n_0\,
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
      R => '0'
    );
frames_left0_carry: unisim.vcomponents.CARRY8
     port map (
      CI => \frames_left_reg_n_0_[0]\,
      CI_TOP => '0',
      CO(7) => frames_left0_carry_n_0,
      CO(6) => frames_left0_carry_n_1,
      CO(5) => frames_left0_carry_n_2,
      CO(4) => frames_left0_carry_n_3,
      CO(3) => frames_left0_carry_n_4,
      CO(2) => frames_left0_carry_n_5,
      CO(1) => frames_left0_carry_n_6,
      CO(0) => frames_left0_carry_n_7,
      DI(7) => \frames_left_reg_n_0_[8]\,
      DI(6) => \frames_left_reg_n_0_[7]\,
      DI(5) => \frames_left_reg_n_0_[6]\,
      DI(4) => \frames_left_reg_n_0_[5]\,
      DI(3) => \frames_left_reg_n_0_[4]\,
      DI(2) => \frames_left_reg_n_0_[3]\,
      DI(1) => \frames_left_reg_n_0_[2]\,
      DI(0) => \frames_left_reg_n_0_[1]\,
      O(7 downto 0) => data0(8 downto 1),
      S(7) => frames_left0_carry_i_1_n_0,
      S(6) => frames_left0_carry_i_2_n_0,
      S(5) => frames_left0_carry_i_3_n_0,
      S(4) => frames_left0_carry_i_4_n_0,
      S(3) => frames_left0_carry_i_5_n_0,
      S(2) => frames_left0_carry_i_6_n_0,
      S(1) => frames_left0_carry_i_7_n_0,
      S(0) => frames_left0_carry_i_8_n_0
    );
\frames_left0_carry__0\: unisim.vcomponents.CARRY8
     port map (
      CI => frames_left0_carry_n_0,
      CI_TOP => '0',
      CO(7) => \frames_left0_carry__0_n_0\,
      CO(6) => \frames_left0_carry__0_n_1\,
      CO(5) => \frames_left0_carry__0_n_2\,
      CO(4) => \frames_left0_carry__0_n_3\,
      CO(3) => \frames_left0_carry__0_n_4\,
      CO(2) => \frames_left0_carry__0_n_5\,
      CO(1) => \frames_left0_carry__0_n_6\,
      CO(0) => \frames_left0_carry__0_n_7\,
      DI(7) => \frames_left_reg_n_0_[16]\,
      DI(6) => \frames_left_reg_n_0_[15]\,
      DI(5) => \frames_left_reg_n_0_[14]\,
      DI(4) => \frames_left_reg_n_0_[13]\,
      DI(3) => \frames_left_reg_n_0_[12]\,
      DI(2) => \frames_left_reg_n_0_[11]\,
      DI(1) => \frames_left_reg_n_0_[10]\,
      DI(0) => \frames_left_reg_n_0_[9]\,
      O(7 downto 0) => data0(16 downto 9),
      S(7) => \frames_left0_carry__0_i_1_n_0\,
      S(6) => \frames_left0_carry__0_i_2_n_0\,
      S(5) => \frames_left0_carry__0_i_3_n_0\,
      S(4) => \frames_left0_carry__0_i_4_n_0\,
      S(3) => \frames_left0_carry__0_i_5_n_0\,
      S(2) => \frames_left0_carry__0_i_6_n_0\,
      S(1) => \frames_left0_carry__0_i_7_n_0\,
      S(0) => \frames_left0_carry__0_i_8_n_0\
    );
\frames_left0_carry__0_i_1\: unisim.vcomponents.LUT1
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => \frames_left_reg_n_0_[16]\,
      O => \frames_left0_carry__0_i_1_n_0\
    );
\frames_left0_carry__0_i_2\: unisim.vcomponents.LUT1
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => \frames_left_reg_n_0_[15]\,
      O => \frames_left0_carry__0_i_2_n_0\
    );
\frames_left0_carry__0_i_3\: unisim.vcomponents.LUT1
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => \frames_left_reg_n_0_[14]\,
      O => \frames_left0_carry__0_i_3_n_0\
    );
\frames_left0_carry__0_i_4\: unisim.vcomponents.LUT1
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => \frames_left_reg_n_0_[13]\,
      O => \frames_left0_carry__0_i_4_n_0\
    );
\frames_left0_carry__0_i_5\: unisim.vcomponents.LUT1
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => \frames_left_reg_n_0_[12]\,
      O => \frames_left0_carry__0_i_5_n_0\
    );
\frames_left0_carry__0_i_6\: unisim.vcomponents.LUT1
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => \frames_left_reg_n_0_[11]\,
      O => \frames_left0_carry__0_i_6_n_0\
    );
\frames_left0_carry__0_i_7\: unisim.vcomponents.LUT1
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => \frames_left_reg_n_0_[10]\,
      O => \frames_left0_carry__0_i_7_n_0\
    );
\frames_left0_carry__0_i_8\: unisim.vcomponents.LUT1
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => \frames_left_reg_n_0_[9]\,
      O => \frames_left0_carry__0_i_8_n_0\
    );
\frames_left0_carry__1\: unisim.vcomponents.CARRY8
     port map (
      CI => \frames_left0_carry__0_n_0\,
      CI_TOP => '0',
      CO(7) => \frames_left0_carry__1_n_0\,
      CO(6) => \frames_left0_carry__1_n_1\,
      CO(5) => \frames_left0_carry__1_n_2\,
      CO(4) => \frames_left0_carry__1_n_3\,
      CO(3) => \frames_left0_carry__1_n_4\,
      CO(2) => \frames_left0_carry__1_n_5\,
      CO(1) => \frames_left0_carry__1_n_6\,
      CO(0) => \frames_left0_carry__1_n_7\,
      DI(7) => \frames_left_reg_n_0_[24]\,
      DI(6) => \frames_left_reg_n_0_[23]\,
      DI(5) => \frames_left_reg_n_0_[22]\,
      DI(4) => \frames_left_reg_n_0_[21]\,
      DI(3) => \frames_left_reg_n_0_[20]\,
      DI(2) => \frames_left_reg_n_0_[19]\,
      DI(1) => \frames_left_reg_n_0_[18]\,
      DI(0) => \frames_left_reg_n_0_[17]\,
      O(7 downto 0) => data0(24 downto 17),
      S(7) => \frames_left0_carry__1_i_1_n_0\,
      S(6) => \frames_left0_carry__1_i_2_n_0\,
      S(5) => \frames_left0_carry__1_i_3_n_0\,
      S(4) => \frames_left0_carry__1_i_4_n_0\,
      S(3) => \frames_left0_carry__1_i_5_n_0\,
      S(2) => \frames_left0_carry__1_i_6_n_0\,
      S(1) => \frames_left0_carry__1_i_7_n_0\,
      S(0) => \frames_left0_carry__1_i_8_n_0\
    );
\frames_left0_carry__1_i_1\: unisim.vcomponents.LUT1
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => \frames_left_reg_n_0_[24]\,
      O => \frames_left0_carry__1_i_1_n_0\
    );
\frames_left0_carry__1_i_2\: unisim.vcomponents.LUT1
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => \frames_left_reg_n_0_[23]\,
      O => \frames_left0_carry__1_i_2_n_0\
    );
\frames_left0_carry__1_i_3\: unisim.vcomponents.LUT1
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => \frames_left_reg_n_0_[22]\,
      O => \frames_left0_carry__1_i_3_n_0\
    );
\frames_left0_carry__1_i_4\: unisim.vcomponents.LUT1
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => \frames_left_reg_n_0_[21]\,
      O => \frames_left0_carry__1_i_4_n_0\
    );
\frames_left0_carry__1_i_5\: unisim.vcomponents.LUT1
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => \frames_left_reg_n_0_[20]\,
      O => \frames_left0_carry__1_i_5_n_0\
    );
\frames_left0_carry__1_i_6\: unisim.vcomponents.LUT1
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => \frames_left_reg_n_0_[19]\,
      O => \frames_left0_carry__1_i_6_n_0\
    );
\frames_left0_carry__1_i_7\: unisim.vcomponents.LUT1
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => \frames_left_reg_n_0_[18]\,
      O => \frames_left0_carry__1_i_7_n_0\
    );
\frames_left0_carry__1_i_8\: unisim.vcomponents.LUT1
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => \frames_left_reg_n_0_[17]\,
      O => \frames_left0_carry__1_i_8_n_0\
    );
\frames_left0_carry__2\: unisim.vcomponents.CARRY8
     port map (
      CI => \frames_left0_carry__1_n_0\,
      CI_TOP => '0',
      CO(7 downto 6) => \NLW_frames_left0_carry__2_CO_UNCONNECTED\(7 downto 6),
      CO(5) => \frames_left0_carry__2_n_2\,
      CO(4) => \frames_left0_carry__2_n_3\,
      CO(3) => \frames_left0_carry__2_n_4\,
      CO(2) => \frames_left0_carry__2_n_5\,
      CO(1) => \frames_left0_carry__2_n_6\,
      CO(0) => \frames_left0_carry__2_n_7\,
      DI(7 downto 6) => B"00",
      DI(5) => \frames_left_reg_n_0_[30]\,
      DI(4) => \frames_left_reg_n_0_[29]\,
      DI(3) => \frames_left_reg_n_0_[28]\,
      DI(2) => \frames_left_reg_n_0_[27]\,
      DI(1) => \frames_left_reg_n_0_[26]\,
      DI(0) => \frames_left_reg_n_0_[25]\,
      O(7) => \NLW_frames_left0_carry__2_O_UNCONNECTED\(7),
      O(6 downto 0) => data0(31 downto 25),
      S(7) => '0',
      S(6) => \frames_left0_carry__2_i_1_n_0\,
      S(5) => \frames_left0_carry__2_i_2_n_0\,
      S(4) => \frames_left0_carry__2_i_3_n_0\,
      S(3) => \frames_left0_carry__2_i_4_n_0\,
      S(2) => \frames_left0_carry__2_i_5_n_0\,
      S(1) => \frames_left0_carry__2_i_6_n_0\,
      S(0) => \frames_left0_carry__2_i_7_n_0\
    );
\frames_left0_carry__2_i_1\: unisim.vcomponents.LUT1
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => \frames_left_reg_n_0_[31]\,
      O => \frames_left0_carry__2_i_1_n_0\
    );
\frames_left0_carry__2_i_2\: unisim.vcomponents.LUT1
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => \frames_left_reg_n_0_[30]\,
      O => \frames_left0_carry__2_i_2_n_0\
    );
\frames_left0_carry__2_i_3\: unisim.vcomponents.LUT1
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => \frames_left_reg_n_0_[29]\,
      O => \frames_left0_carry__2_i_3_n_0\
    );
\frames_left0_carry__2_i_4\: unisim.vcomponents.LUT1
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => \frames_left_reg_n_0_[28]\,
      O => \frames_left0_carry__2_i_4_n_0\
    );
\frames_left0_carry__2_i_5\: unisim.vcomponents.LUT1
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => \frames_left_reg_n_0_[27]\,
      O => \frames_left0_carry__2_i_5_n_0\
    );
\frames_left0_carry__2_i_6\: unisim.vcomponents.LUT1
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => \frames_left_reg_n_0_[26]\,
      O => \frames_left0_carry__2_i_6_n_0\
    );
\frames_left0_carry__2_i_7\: unisim.vcomponents.LUT1
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => \frames_left_reg_n_0_[25]\,
      O => \frames_left0_carry__2_i_7_n_0\
    );
frames_left0_carry_i_1: unisim.vcomponents.LUT1
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => \frames_left_reg_n_0_[8]\,
      O => frames_left0_carry_i_1_n_0
    );
frames_left0_carry_i_2: unisim.vcomponents.LUT1
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => \frames_left_reg_n_0_[7]\,
      O => frames_left0_carry_i_2_n_0
    );
frames_left0_carry_i_3: unisim.vcomponents.LUT1
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => \frames_left_reg_n_0_[6]\,
      O => frames_left0_carry_i_3_n_0
    );
frames_left0_carry_i_4: unisim.vcomponents.LUT1
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => \frames_left_reg_n_0_[5]\,
      O => frames_left0_carry_i_4_n_0
    );
frames_left0_carry_i_5: unisim.vcomponents.LUT1
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => \frames_left_reg_n_0_[4]\,
      O => frames_left0_carry_i_5_n_0
    );
frames_left0_carry_i_6: unisim.vcomponents.LUT1
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => \frames_left_reg_n_0_[3]\,
      O => frames_left0_carry_i_6_n_0
    );
frames_left0_carry_i_7: unisim.vcomponents.LUT1
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => \frames_left_reg_n_0_[2]\,
      O => frames_left0_carry_i_7_n_0
    );
frames_left0_carry_i_8: unisim.vcomponents.LUT1
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => \frames_left_reg_n_0_[1]\,
      O => frames_left0_carry_i_8_n_0
    );
\frames_left[0]_i_1\: unisim.vcomponents.LUT1
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => \frames_left_reg_n_0_[0]\,
      O => p_1_in(0)
    );
\frames_left[10]_i_1\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"80"
    )
        port map (
      I0 => busy,
      I1 => pwm_i_3_n_0,
      I2 => data0(10),
      O => p_1_in(10)
    );
\frames_left[11]_i_1\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"80"
    )
        port map (
      I0 => busy,
      I1 => pwm_i_3_n_0,
      I2 => data0(11),
      O => p_1_in(11)
    );
\frames_left[12]_i_1\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"80"
    )
        port map (
      I0 => busy,
      I1 => pwm_i_3_n_0,
      I2 => data0(12),
      O => p_1_in(12)
    );
\frames_left[13]_i_1\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"80"
    )
        port map (
      I0 => busy,
      I1 => pwm_i_3_n_0,
      I2 => data0(13),
      O => p_1_in(13)
    );
\frames_left[14]_i_1\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"80"
    )
        port map (
      I0 => busy,
      I1 => pwm_i_3_n_0,
      I2 => data0(14),
      O => p_1_in(14)
    );
\frames_left[15]_i_1\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"80"
    )
        port map (
      I0 => busy,
      I1 => pwm_i_3_n_0,
      I2 => data0(15),
      O => p_1_in(15)
    );
\frames_left[16]_i_1\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"80"
    )
        port map (
      I0 => busy,
      I1 => pwm_i_3_n_0,
      I2 => data0(16),
      O => p_1_in(16)
    );
\frames_left[17]_i_1\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"80"
    )
        port map (
      I0 => busy,
      I1 => pwm_i_3_n_0,
      I2 => data0(17),
      O => p_1_in(17)
    );
\frames_left[18]_i_1\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"80"
    )
        port map (
      I0 => busy,
      I1 => pwm_i_3_n_0,
      I2 => data0(18),
      O => p_1_in(18)
    );
\frames_left[19]_i_1\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"80"
    )
        port map (
      I0 => busy,
      I1 => pwm_i_3_n_0,
      I2 => data0(19),
      O => p_1_in(19)
    );
\frames_left[1]_i_1\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"F8F0"
    )
        port map (
      I0 => busy,
      I1 => pwm_i_3_n_0,
      I2 => busy3_out,
      I3 => data0(1),
      O => p_1_in(1)
    );
\frames_left[20]_i_1\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"80"
    )
        port map (
      I0 => busy,
      I1 => pwm_i_3_n_0,
      I2 => data0(20),
      O => p_1_in(20)
    );
\frames_left[21]_i_1\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"80"
    )
        port map (
      I0 => busy,
      I1 => pwm_i_3_n_0,
      I2 => data0(21),
      O => p_1_in(21)
    );
\frames_left[22]_i_1\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"80"
    )
        port map (
      I0 => busy,
      I1 => pwm_i_3_n_0,
      I2 => data0(22),
      O => p_1_in(22)
    );
\frames_left[23]_i_1\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"80"
    )
        port map (
      I0 => busy,
      I1 => pwm_i_3_n_0,
      I2 => data0(23),
      O => p_1_in(23)
    );
\frames_left[24]_i_1\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"80"
    )
        port map (
      I0 => busy,
      I1 => pwm_i_3_n_0,
      I2 => data0(24),
      O => p_1_in(24)
    );
\frames_left[25]_i_1\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"80"
    )
        port map (
      I0 => busy,
      I1 => pwm_i_3_n_0,
      I2 => data0(25),
      O => p_1_in(25)
    );
\frames_left[26]_i_1\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"80"
    )
        port map (
      I0 => busy,
      I1 => pwm_i_3_n_0,
      I2 => data0(26),
      O => p_1_in(26)
    );
\frames_left[27]_i_1\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"80"
    )
        port map (
      I0 => busy,
      I1 => pwm_i_3_n_0,
      I2 => data0(27),
      O => p_1_in(27)
    );
\frames_left[28]_i_1\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"80"
    )
        port map (
      I0 => busy,
      I1 => pwm_i_3_n_0,
      I2 => data0(28),
      O => p_1_in(28)
    );
\frames_left[29]_i_1\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"80"
    )
        port map (
      I0 => busy,
      I1 => pwm_i_3_n_0,
      I2 => data0(29),
      O => p_1_in(29)
    );
\frames_left[2]_i_1\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"80"
    )
        port map (
      I0 => busy,
      I1 => pwm_i_3_n_0,
      I2 => data0(2),
      O => p_1_in(2)
    );
\frames_left[30]_i_1\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"80"
    )
        port map (
      I0 => busy,
      I1 => pwm_i_3_n_0,
      I2 => data0(30),
      O => p_1_in(30)
    );
\frames_left[31]_i_1\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"B"
    )
        port map (
      I0 => \frames_left[5]_i_1_n_0\,
      I1 => busy,
      O => \frames_left[31]_i_1_n_0\
    );
\frames_left[31]_i_2\: unisim.vcomponents.LUT1
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => pwm_i_2_n_0,
      O => \frames_left[31]_i_2_n_0\
    );
\frames_left[31]_i_3\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"80"
    )
        port map (
      I0 => busy,
      I1 => pwm_i_3_n_0,
      I2 => data0(31),
      O => p_1_in(31)
    );
\frames_left[3]_i_1\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"80"
    )
        port map (
      I0 => busy,
      I1 => pwm_i_3_n_0,
      I2 => data0(3),
      O => p_1_in(3)
    );
\frames_left[4]_i_1\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"F8F0"
    )
        port map (
      I0 => busy,
      I1 => pwm_i_3_n_0,
      I2 => busy3_out,
      I3 => data0(4),
      O => p_1_in(4)
    );
\frames_left[5]_i_1\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"B"
    )
        port map (
      I0 => \s_axi_bresp[1]_i_4_n_0\,
      I1 => s_axi_aresetn,
      O => \frames_left[5]_i_1_n_0\
    );
\frames_left[5]_i_2\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"7"
    )
        port map (
      I0 => busy,
      I1 => pwm_i_2_n_0,
      O => \frames_left[5]_i_2_n_0\
    );
\frames_left[5]_i_3\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"F8F0"
    )
        port map (
      I0 => busy,
      I1 => pwm_i_3_n_0,
      I2 => busy3_out,
      I3 => data0(5),
      O => p_1_in(5)
    );
\frames_left[6]_i_1\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"80"
    )
        port map (
      I0 => busy,
      I1 => pwm_i_3_n_0,
      I2 => data0(6),
      O => p_1_in(6)
    );
\frames_left[7]_i_1\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"80"
    )
        port map (
      I0 => busy,
      I1 => pwm_i_3_n_0,
      I2 => data0(7),
      O => p_1_in(7)
    );
\frames_left[8]_i_1\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"80"
    )
        port map (
      I0 => busy,
      I1 => pwm_i_3_n_0,
      I2 => data0(8),
      O => p_1_in(8)
    );
\frames_left[9]_i_1\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"80"
    )
        port map (
      I0 => busy,
      I1 => pwm_i_3_n_0,
      I2 => data0(9),
      O => p_1_in(9)
    );
\frames_left_reg[0]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \frames_left[31]_i_2_n_0\,
      D => p_1_in(0),
      Q => \frames_left_reg_n_0_[0]\,
      R => \frames_left[31]_i_1_n_0\
    );
\frames_left_reg[10]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \frames_left[31]_i_2_n_0\,
      D => p_1_in(10),
      Q => \frames_left_reg_n_0_[10]\,
      R => \frames_left[31]_i_1_n_0\
    );
\frames_left_reg[11]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \frames_left[31]_i_2_n_0\,
      D => p_1_in(11),
      Q => \frames_left_reg_n_0_[11]\,
      R => \frames_left[31]_i_1_n_0\
    );
\frames_left_reg[12]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \frames_left[31]_i_2_n_0\,
      D => p_1_in(12),
      Q => \frames_left_reg_n_0_[12]\,
      R => \frames_left[31]_i_1_n_0\
    );
\frames_left_reg[13]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \frames_left[31]_i_2_n_0\,
      D => p_1_in(13),
      Q => \frames_left_reg_n_0_[13]\,
      R => \frames_left[31]_i_1_n_0\
    );
\frames_left_reg[14]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \frames_left[31]_i_2_n_0\,
      D => p_1_in(14),
      Q => \frames_left_reg_n_0_[14]\,
      R => \frames_left[31]_i_1_n_0\
    );
\frames_left_reg[15]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \frames_left[31]_i_2_n_0\,
      D => p_1_in(15),
      Q => \frames_left_reg_n_0_[15]\,
      R => \frames_left[31]_i_1_n_0\
    );
\frames_left_reg[16]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \frames_left[31]_i_2_n_0\,
      D => p_1_in(16),
      Q => \frames_left_reg_n_0_[16]\,
      R => \frames_left[31]_i_1_n_0\
    );
\frames_left_reg[17]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \frames_left[31]_i_2_n_0\,
      D => p_1_in(17),
      Q => \frames_left_reg_n_0_[17]\,
      R => \frames_left[31]_i_1_n_0\
    );
\frames_left_reg[18]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \frames_left[31]_i_2_n_0\,
      D => p_1_in(18),
      Q => \frames_left_reg_n_0_[18]\,
      R => \frames_left[31]_i_1_n_0\
    );
\frames_left_reg[19]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \frames_left[31]_i_2_n_0\,
      D => p_1_in(19),
      Q => \frames_left_reg_n_0_[19]\,
      R => \frames_left[31]_i_1_n_0\
    );
\frames_left_reg[1]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \frames_left[5]_i_2_n_0\,
      D => p_1_in(1),
      Q => \frames_left_reg_n_0_[1]\,
      R => \frames_left[5]_i_1_n_0\
    );
\frames_left_reg[20]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \frames_left[31]_i_2_n_0\,
      D => p_1_in(20),
      Q => \frames_left_reg_n_0_[20]\,
      R => \frames_left[31]_i_1_n_0\
    );
\frames_left_reg[21]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \frames_left[31]_i_2_n_0\,
      D => p_1_in(21),
      Q => \frames_left_reg_n_0_[21]\,
      R => \frames_left[31]_i_1_n_0\
    );
\frames_left_reg[22]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \frames_left[31]_i_2_n_0\,
      D => p_1_in(22),
      Q => \frames_left_reg_n_0_[22]\,
      R => \frames_left[31]_i_1_n_0\
    );
\frames_left_reg[23]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \frames_left[31]_i_2_n_0\,
      D => p_1_in(23),
      Q => \frames_left_reg_n_0_[23]\,
      R => \frames_left[31]_i_1_n_0\
    );
\frames_left_reg[24]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \frames_left[31]_i_2_n_0\,
      D => p_1_in(24),
      Q => \frames_left_reg_n_0_[24]\,
      R => \frames_left[31]_i_1_n_0\
    );
\frames_left_reg[25]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \frames_left[31]_i_2_n_0\,
      D => p_1_in(25),
      Q => \frames_left_reg_n_0_[25]\,
      R => \frames_left[31]_i_1_n_0\
    );
\frames_left_reg[26]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \frames_left[31]_i_2_n_0\,
      D => p_1_in(26),
      Q => \frames_left_reg_n_0_[26]\,
      R => \frames_left[31]_i_1_n_0\
    );
\frames_left_reg[27]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \frames_left[31]_i_2_n_0\,
      D => p_1_in(27),
      Q => \frames_left_reg_n_0_[27]\,
      R => \frames_left[31]_i_1_n_0\
    );
\frames_left_reg[28]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \frames_left[31]_i_2_n_0\,
      D => p_1_in(28),
      Q => \frames_left_reg_n_0_[28]\,
      R => \frames_left[31]_i_1_n_0\
    );
\frames_left_reg[29]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \frames_left[31]_i_2_n_0\,
      D => p_1_in(29),
      Q => \frames_left_reg_n_0_[29]\,
      R => \frames_left[31]_i_1_n_0\
    );
\frames_left_reg[2]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \frames_left[31]_i_2_n_0\,
      D => p_1_in(2),
      Q => \frames_left_reg_n_0_[2]\,
      R => \frames_left[31]_i_1_n_0\
    );
\frames_left_reg[30]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \frames_left[31]_i_2_n_0\,
      D => p_1_in(30),
      Q => \frames_left_reg_n_0_[30]\,
      R => \frames_left[31]_i_1_n_0\
    );
\frames_left_reg[31]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \frames_left[31]_i_2_n_0\,
      D => p_1_in(31),
      Q => \frames_left_reg_n_0_[31]\,
      R => \frames_left[31]_i_1_n_0\
    );
\frames_left_reg[3]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \frames_left[31]_i_2_n_0\,
      D => p_1_in(3),
      Q => \frames_left_reg_n_0_[3]\,
      R => \frames_left[31]_i_1_n_0\
    );
\frames_left_reg[4]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \frames_left[5]_i_2_n_0\,
      D => p_1_in(4),
      Q => \frames_left_reg_n_0_[4]\,
      R => \frames_left[5]_i_1_n_0\
    );
\frames_left_reg[5]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \frames_left[5]_i_2_n_0\,
      D => p_1_in(5),
      Q => \frames_left_reg_n_0_[5]\,
      R => \frames_left[5]_i_1_n_0\
    );
\frames_left_reg[6]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \frames_left[31]_i_2_n_0\,
      D => p_1_in(6),
      Q => \frames_left_reg_n_0_[6]\,
      R => \frames_left[31]_i_1_n_0\
    );
\frames_left_reg[7]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \frames_left[31]_i_2_n_0\,
      D => p_1_in(7),
      Q => \frames_left_reg_n_0_[7]\,
      R => \frames_left[31]_i_1_n_0\
    );
\frames_left_reg[8]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \frames_left[31]_i_2_n_0\,
      D => p_1_in(8),
      Q => \frames_left_reg_n_0_[8]\,
      R => \frames_left[31]_i_1_n_0\
    );
\frames_left_reg[9]\: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => \frames_left[31]_i_2_n_0\,
      D => p_1_in(9),
      Q => \frames_left_reg_n_0_[9]\,
      R => \frames_left[31]_i_1_n_0\
    );
\phase[0]_i_1\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"F7"
    )
        port map (
      I0 => busy,
      I1 => pwm_i_2_n_0,
      I2 => \frames_left[5]_i_1_n_0\,
      O => \phase[0]_i_1_n_0\
    );
\phase[0]_i_3\: unisim.vcomponents.LUT1
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => phase_reg(0),
      O => pwm1(0)
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
      S(0) => pwm1(0)
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
pwm_i_1: unisim.vcomponents.LUT6
    generic map(
      INIT => X"00FD00FD00FD0020"
    )
        port map (
      I0 => busy,
      I1 => pwm_i_2_n_0,
      I2 => pwm_i_3_n_0,
      I3 => \frames_left[5]_i_1_n_0\,
      I4 => pwm_i_4_n_0,
      I5 => busy3_out,
      O => pwm_i_1_n_0
    );
pwm_i_10: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FFFFFFFE"
    )
        port map (
      I0 => \frames_left_reg_n_0_[21]\,
      I1 => \frames_left_reg_n_0_[7]\,
      I2 => \frames_left_reg_n_0_[24]\,
      I3 => \frames_left_reg_n_0_[6]\,
      I4 => pwm_i_22_n_0,
      O => pwm_i_10_n_0
    );
pwm_i_11: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FFFFFFFE"
    )
        port map (
      I0 => \frames_left_reg_n_0_[26]\,
      I1 => \frames_left_reg_n_0_[10]\,
      I2 => \frames_left_reg_n_0_[23]\,
      I3 => \frames_left_reg_n_0_[4]\,
      I4 => pwm_i_23_n_0,
      O => pwm_i_11_n_0
    );
pwm_i_12: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FFFFFFFE"
    )
        port map (
      I0 => \frames_left_reg_n_0_[15]\,
      I1 => \frames_left_reg_n_0_[9]\,
      I2 => \frames_left_reg_n_0_[3]\,
      I3 => \frames_left_reg_n_0_[2]\,
      I4 => pwm_i_24_n_0,
      O => pwm_i_12_n_0
    );
pwm_i_14: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FEFEFEFFEEEEEEEE"
    )
        port map (
      I0 => pwm1(12),
      I1 => pwm1(13),
      I2 => pwm_i_26_n_0,
      I3 => pwm_i_27_n_0,
      I4 => pwm_i_28_n_0,
      I5 => pwm1(11),
      O => pwm_i_14_n_0
    );
pwm_i_16: unisim.vcomponents.LUT4
    generic map(
      INIT => X"FFFE"
    )
        port map (
      I0 => pwm_i_29_n_0,
      I1 => pwm_i_30_n_0,
      I2 => pwm_i_31_n_0,
      I3 => pwm_i_32_n_0,
      O => pwm_i_16_n_0
    );
pwm_i_17: unisim.vcomponents.LUT4
    generic map(
      INIT => X"FFFE"
    )
        port map (
      I0 => phase_reg(26),
      I1 => phase_reg(24),
      I2 => phase_reg(31),
      I3 => phase_reg(14),
      O => pwm_i_17_n_0
    );
pwm_i_18: unisim.vcomponents.LUT4
    generic map(
      INIT => X"FFFE"
    )
        port map (
      I0 => phase_reg(11),
      I1 => phase_reg(4),
      I2 => phase_reg(22),
      I3 => phase_reg(16),
      O => pwm_i_18_n_0
    );
pwm_i_19: unisim.vcomponents.LUT4
    generic map(
      INIT => X"7FFF"
    )
        port map (
      I0 => phase_reg(18),
      I1 => phase_reg(1),
      I2 => phase_reg(20),
      I3 => phase_reg(0),
      O => pwm_i_19_n_0
    );
pwm_i_2: unisim.vcomponents.LUT4
    generic map(
      INIT => X"FFFE"
    )
        port map (
      I0 => pwm_i_5_n_0,
      I1 => pwm_i_6_n_0,
      I2 => pwm_i_7_n_0,
      I3 => pwm_i_8_n_0,
      O => pwm_i_2_n_0
    );
pwm_i_20: unisim.vcomponents.LUT4
    generic map(
      INIT => X"FFFD"
    )
        port map (
      I0 => phase_reg(19),
      I1 => phase_reg(21),
      I2 => phase_reg(29),
      I3 => phase_reg(8),
      O => pwm_i_20_n_0
    );
pwm_i_21: unisim.vcomponents.LUT4
    generic map(
      INIT => X"FFFE"
    )
        port map (
      I0 => \frames_left_reg_n_0_[16]\,
      I1 => \frames_left_reg_n_0_[22]\,
      I2 => \frames_left_reg_n_0_[17]\,
      I3 => \frames_left_reg_n_0_[19]\,
      O => pwm_i_21_n_0
    );
pwm_i_22: unisim.vcomponents.LUT4
    generic map(
      INIT => X"FFFE"
    )
        port map (
      I0 => \frames_left_reg_n_0_[31]\,
      I1 => \frames_left_reg_n_0_[11]\,
      I2 => \frames_left_reg_n_0_[5]\,
      I3 => \frames_left_reg_n_0_[25]\,
      O => pwm_i_22_n_0
    );
pwm_i_23: unisim.vcomponents.LUT4
    generic map(
      INIT => X"FFFE"
    )
        port map (
      I0 => \frames_left_reg_n_0_[8]\,
      I1 => \frames_left_reg_n_0_[27]\,
      I2 => \frames_left_reg_n_0_[18]\,
      I3 => \frames_left_reg_n_0_[28]\,
      O => pwm_i_23_n_0
    );
pwm_i_24: unisim.vcomponents.LUT4
    generic map(
      INIT => X"FFEF"
    )
        port map (
      I0 => \frames_left_reg_n_0_[29]\,
      I1 => \frames_left_reg_n_0_[30]\,
      I2 => \frames_left_reg_n_0_[0]\,
      I3 => \frames_left_reg_n_0_[1]\,
      O => pwm_i_24_n_0
    );
pwm_i_26: unisim.vcomponents.LUT2
    generic map(
      INIT => X"E"
    )
        port map (
      I0 => pwm1(10),
      I1 => pwm1(9),
      O => pwm_i_26_n_0
    );
pwm_i_27: unisim.vcomponents.LUT4
    generic map(
      INIT => X"7FFF"
    )
        port map (
      I0 => pwm1(5),
      I1 => pwm1(8),
      I2 => pwm1(6),
      I3 => pwm1(7),
      O => pwm_i_27_n_0
    );
pwm_i_28: unisim.vcomponents.LUT5
    generic map(
      INIT => X"0000F7FF"
    )
        port map (
      I0 => pwm1(3),
      I1 => pwm1(1),
      I2 => phase_reg(0),
      I3 => pwm1(2),
      I4 => pwm1(4),
      O => pwm_i_28_n_0
    );
pwm_i_29: unisim.vcomponents.LUT4
    generic map(
      INIT => X"FFFE"
    )
        port map (
      I0 => pwm1(31),
      I1 => pwm1(32),
      I2 => pwm1(19),
      I3 => pwm1(21),
      O => pwm_i_29_n_0
    );
pwm_i_3: unisim.vcomponents.LUT4
    generic map(
      INIT => X"FFFE"
    )
        port map (
      I0 => pwm_i_9_n_0,
      I1 => pwm_i_10_n_0,
      I2 => pwm_i_11_n_0,
      I3 => pwm_i_12_n_0,
      O => pwm_i_3_n_0
    );
pwm_i_30: unisim.vcomponents.LUT4
    generic map(
      INIT => X"FFFE"
    )
        port map (
      I0 => pwm1(20),
      I1 => pwm1(29),
      I2 => pwm1(22),
      I3 => pwm1(27),
      O => pwm_i_30_n_0
    );
pwm_i_31: unisim.vcomponents.LUT4
    generic map(
      INIT => X"FFFE"
    )
        port map (
      I0 => pwm1(18),
      I1 => pwm1(28),
      I2 => pwm1(23),
      I3 => pwm1(30),
      O => pwm_i_31_n_0
    );
pwm_i_32: unisim.vcomponents.LUT4
    generic map(
      INIT => X"FFFD"
    )
        port map (
      I0 => busy,
      I1 => pwm1(24),
      I2 => pwm1(25),
      I3 => pwm1(26),
      O => pwm_i_32_n_0
    );
pwm_i_4: unisim.vcomponents.LUT6
    generic map(
      INIT => X"000000000111FFFF"
    )
        port map (
      I0 => pwm1(15),
      I1 => pwm1(16),
      I2 => pwm_i_14_n_0,
      I3 => pwm1(14),
      I4 => pwm1(17),
      I5 => pwm_i_16_n_0,
      O => pwm_i_4_n_0
    );
pwm_i_5: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FFFFFFFE"
    )
        port map (
      I0 => phase_reg(7),
      I1 => phase_reg(13),
      I2 => phase_reg(23),
      I3 => phase_reg(30),
      I4 => pwm_i_17_n_0,
      O => pwm_i_5_n_0
    );
pwm_i_6: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FFFFFFF7"
    )
        port map (
      I0 => phase_reg(5),
      I1 => phase_reg(6),
      I2 => phase_reg(12),
      I3 => phase_reg(25),
      I4 => pwm_i_18_n_0,
      O => pwm_i_6_n_0
    );
pwm_i_7: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FFFFBFFF"
    )
        port map (
      I0 => phase_reg(9),
      I1 => phase_reg(17),
      I2 => phase_reg(10),
      I3 => phase_reg(15),
      I4 => pwm_i_19_n_0,
      O => pwm_i_7_n_0
    );
pwm_i_8: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FFFFFEFF"
    )
        port map (
      I0 => phase_reg(2),
      I1 => phase_reg(28),
      I2 => phase_reg(27),
      I3 => phase_reg(3),
      I4 => pwm_i_20_n_0,
      O => pwm_i_8_n_0
    );
pwm_i_9: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FFFFFFFE"
    )
        port map (
      I0 => \frames_left_reg_n_0_[14]\,
      I1 => \frames_left_reg_n_0_[13]\,
      I2 => \frames_left_reg_n_0_[20]\,
      I3 => \frames_left_reg_n_0_[12]\,
      I4 => pwm_i_21_n_0,
      O => pwm_i_9_n_0
    );
pwm_reg: unisim.vcomponents.FDRE
    generic map(
      INIT => '0'
    )
        port map (
      C => s_axi_aclk,
      CE => '1',
      D => pwm_i_1_n_0,
      Q => \^servo_pwm\,
      R => '0'
    );
pwm_reg_i_13: unisim.vcomponents.CARRY8
     port map (
      CI => pwm_reg_i_25_n_0,
      CI_TOP => '0',
      CO(7) => pwm_reg_i_13_n_0,
      CO(6) => pwm_reg_i_13_n_1,
      CO(5) => pwm_reg_i_13_n_2,
      CO(4) => pwm_reg_i_13_n_3,
      CO(3) => pwm_reg_i_13_n_4,
      CO(2) => pwm_reg_i_13_n_5,
      CO(1) => pwm_reg_i_13_n_6,
      CO(0) => pwm_reg_i_13_n_7,
      DI(7 downto 0) => B"00000000",
      O(7 downto 0) => pwm1(16 downto 9),
      S(7 downto 0) => phase_reg(16 downto 9)
    );
pwm_reg_i_15: unisim.vcomponents.CARRY8
     port map (
      CI => pwm_reg_i_13_n_0,
      CI_TOP => '0',
      CO(7) => pwm_reg_i_15_n_0,
      CO(6) => pwm_reg_i_15_n_1,
      CO(5) => pwm_reg_i_15_n_2,
      CO(4) => pwm_reg_i_15_n_3,
      CO(3) => pwm_reg_i_15_n_4,
      CO(2) => pwm_reg_i_15_n_5,
      CO(1) => pwm_reg_i_15_n_6,
      CO(0) => pwm_reg_i_15_n_7,
      DI(7 downto 0) => B"00000000",
      O(7 downto 0) => pwm1(24 downto 17),
      S(7 downto 0) => phase_reg(24 downto 17)
    );
pwm_reg_i_25: unisim.vcomponents.CARRY8
     port map (
      CI => phase_reg(0),
      CI_TOP => '0',
      CO(7) => pwm_reg_i_25_n_0,
      CO(6) => pwm_reg_i_25_n_1,
      CO(5) => pwm_reg_i_25_n_2,
      CO(4) => pwm_reg_i_25_n_3,
      CO(3) => pwm_reg_i_25_n_4,
      CO(2) => pwm_reg_i_25_n_5,
      CO(1) => pwm_reg_i_25_n_6,
      CO(0) => pwm_reg_i_25_n_7,
      DI(7 downto 0) => B"00000000",
      O(7 downto 0) => pwm1(8 downto 1),
      S(7 downto 0) => phase_reg(8 downto 1)
    );
pwm_reg_i_33: unisim.vcomponents.CARRY8
     port map (
      CI => pwm_reg_i_15_n_0,
      CI_TOP => '0',
      CO(7) => pwm1(32),
      CO(6) => NLW_pwm_reg_i_33_CO_UNCONNECTED(6),
      CO(5) => pwm_reg_i_33_n_2,
      CO(4) => pwm_reg_i_33_n_3,
      CO(3) => pwm_reg_i_33_n_4,
      CO(2) => pwm_reg_i_33_n_5,
      CO(1) => pwm_reg_i_33_n_6,
      CO(0) => pwm_reg_i_33_n_7,
      DI(7 downto 0) => B"00000000",
      O(7) => NLW_pwm_reg_i_33_O_UNCONNECTED(7),
      O(6 downto 0) => pwm1(31 downto 25),
      S(7) => '1',
      S(6 downto 0) => phase_reg(31 downto 25)
    );
\s_axi_bresp[1]_i_10\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FFFFFFFFFFFFFFFB"
    )
        port map (
      I0 => \s_axi_bresp[1]_i_10_0\(11),
      I1 => \s_axi_bresp[1]_i_10_0\(1),
      I2 => busy,
      I3 => \s_axi_bresp[1]_i_10_0\(10),
      I4 => \s_axi_bresp[1]_i_18_n_0\,
      I5 => \s_axi_bresp[1]_i_17_n_0\,
      O => \s_axi_bresp[1]_i_10_n_0\
    );
\s_axi_bresp[1]_i_12\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0000000000000001"
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
\s_axi_bresp[1]_i_13\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"FFDF"
    )
        port map (
      I0 => \s_axi_bresp[1]_i_7_0\(2),
      I1 => \scratch[31]_i_2\(5),
      I2 => \s_axi_bresp[1]_i_7_0\(1),
      I3 => \scratch[31]_i_2\(1),
      O => \s_axi_bresp[1]_i_13_n_0\
    );
\s_axi_bresp[1]_i_14\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FFFFFDFFFFFFFFFF"
    )
        port map (
      I0 => \scratch[31]_i_2\(4),
      I1 => \scratch[31]_i_2\(3),
      I2 => \scratch[31]_i_2\(2),
      I3 => \s_axi_bresp[1]_i_7_0\(3),
      I4 => \scratch[31]_i_2\(0),
      I5 => \s_axi_bresp[1]_i_7_0\(0),
      O => \s_axi_bresp[1]_i_14_n_0\
    );
\s_axi_bresp[1]_i_15\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"FFFD"
    )
        port map (
      I0 => \s_axi_bresp[1]_i_10_0\(25),
      I1 => \s_axi_bresp[1]_i_10_0\(16),
      I2 => \s_axi_bresp[1]_i_10_0\(7),
      I3 => \s_axi_bresp[1]_i_10_0\(0),
      O => \s_axi_bresp[1]_i_15_n_0\
    );
\s_axi_bresp[1]_i_16\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FFFFFFFFFFFFFBFF"
    )
        port map (
      I0 => \s_axi_bresp[1]_i_19_n_0\,
      I1 => \s_axi_bresp[1]_i_10_0\(20),
      I2 => \s_axi_bresp[1]_i_10_0\(12),
      I3 => \s_axi_bresp[1]_i_10_0\(14),
      I4 => \s_axi_bresp[1]_i_10_0\(27),
      I5 => \s_axi_bresp[1]_i_20_n_0\,
      O => \s_axi_bresp[1]_i_16_n_0\
    );
\s_axi_bresp[1]_i_17\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"EFFF"
    )
        port map (
      I0 => \s_axi_bresp[1]_i_10_0\(31),
      I1 => \s_axi_bresp[1]_i_10_0\(19),
      I2 => \s_axi_bresp[1]_i_10_0\(22),
      I3 => \s_axi_bresp[1]_i_10_0\(4),
      O => \s_axi_bresp[1]_i_17_n_0\
    );
\s_axi_bresp[1]_i_18\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"FFF7"
    )
        port map (
      I0 => \s_axi_bresp[1]_i_10_0\(28),
      I1 => \s_axi_bresp[1]_i_10_0\(8),
      I2 => \s_axi_bresp[1]_i_10_0\(2),
      I3 => \s_axi_bresp[1]_i_10_0\(9),
      O => \s_axi_bresp[1]_i_18_n_0\
    );
\s_axi_bresp[1]_i_19\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"FFDF"
    )
        port map (
      I0 => \s_axi_bresp[1]_i_10_0\(6),
      I1 => \s_axi_bresp[1]_i_10_0\(15),
      I2 => \s_axi_bresp[1]_i_10_0\(30),
      I3 => \s_axi_bresp[1]_i_10_0\(26),
      O => \s_axi_bresp[1]_i_19_n_0\
    );
\s_axi_bresp[1]_i_2\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"BBBBBBBB8888888B"
    )
        port map (
      I0 => s_axi_bresp(0),
      I1 => \s_axi_bresp_reg[1]_0\,
      I2 => \scratch[31]_i_2\(5),
      I3 => \s_axi_bresp[1]_i_4_n_0\,
      I4 => busy3_out,
      I5 => \s_axi_bresp_reg[1]_1\,
      O => \s_axi_bresp_reg[1]\
    );
\s_axi_bresp[1]_i_20\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FFFFFEFF"
    )
        port map (
      I0 => \s_axi_bresp[1]_i_10_0\(3),
      I1 => \s_axi_bresp[1]_i_10_0\(21),
      I2 => \s_axi_bresp[1]_i_10_0\(23),
      I3 => \s_axi_bresp[1]_i_10_0\(18),
      I4 => \s_axi_bresp[1]_i_10_0\(5),
      O => \s_axi_bresp[1]_i_20_n_0\
    );
\s_axi_bresp[1]_i_4\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0000000000200000"
    )
        port map (
      I0 => \s_axi_bresp[1]_i_7_n_0\,
      I1 => \s_axi_bresp[1]_i_8_n_0\,
      I2 => \s_axi_bresp[1]_i_10_0\(9),
      I3 => \s_axi_bresp[1]_i_10_0\(2),
      I4 => \s_axi_bresp[1]_i_10_0\(10),
      I5 => \s_axi_bresp[1]_i_9_n_0\,
      O => \s_axi_bresp[1]_i_4_n_0\
    );
\s_axi_bresp[1]_i_5\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"02"
    )
        port map (
      I0 => \s_axi_bresp[1]_i_7_n_0\,
      I1 => \s_axi_bresp[1]_i_10_n_0\,
      I2 => \s_axi_bresp[1]_i_8_n_0\,
      O => busy3_out
    );
\s_axi_bresp[1]_i_7\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0000000000000080"
    )
        port map (
      I0 => \^aw_address_reg[10]\,
      I1 => \s_axi_bresp[1]_i_5_0\,
      I2 => aw_pending,
      I3 => \s_axi_bresp[1]_i_5_1\,
      I4 => \s_axi_bresp[1]_i_13_n_0\,
      I5 => \s_axi_bresp[1]_i_14_n_0\,
      O => \s_axi_bresp[1]_i_7_n_0\
    );
\s_axi_bresp[1]_i_8\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FFFFFFFFFFFFFEFF"
    )
        port map (
      I0 => \s_axi_bresp[1]_i_15_n_0\,
      I1 => \s_axi_bresp[1]_i_10_0\(13),
      I2 => \s_axi_bresp[1]_i_10_0\(29),
      I3 => \s_axi_bresp[1]_i_10_0\(24),
      I4 => \s_axi_bresp[1]_i_10_0\(17),
      I5 => \s_axi_bresp[1]_i_16_n_0\,
      O => \s_axi_bresp[1]_i_8_n_0\
    );
\s_axi_bresp[1]_i_9\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FFFFBFFF"
    )
        port map (
      I0 => \s_axi_bresp[1]_i_10_0\(1),
      I1 => \s_axi_bresp[1]_i_10_0\(11),
      I2 => \s_axi_bresp[1]_i_10_0\(8),
      I3 => \s_axi_bresp[1]_i_10_0\(28),
      I4 => \s_axi_bresp[1]_i_17_n_0\,
      O => \s_axi_bresp[1]_i_9_n_0\
    );
\s_axi_rdata[0]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"80AA8080AAAAAAAA"
    )
        port map (
      I0 => \s_axi_rdata_reg[8]\,
      I1 => s_axi_araddr(3),
      I2 => \s_axi_rdata_reg[0]\,
      I3 => \s_axi_rdata_reg[0]_0\,
      I4 => Q(0),
      I5 => \s_axi_rdata[0]_i_3_n_0\,
      O => D(0)
    );
\s_axi_rdata[0]_i_3\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"F7F3F3F3F7FFF3F3"
    )
        port map (
      I0 => \frames_left_reg_n_0_[0]\,
      I1 => s_axi_araddr(1),
      I2 => s_axi_araddr(3),
      I3 => s_axi_araddr(2),
      I4 => s_axi_araddr(0),
      I5 => busy,
      O => \s_axi_rdata[0]_i_3_n_0\
    );
\s_axi_rdata[10]_i_1\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"2"
    )
        port map (
      I0 => \s_axi_rdata_reg[8]\,
      I1 => \s_axi_rdata[10]_i_2_n_0\,
      O => D(10)
    );
\s_axi_rdata[10]_i_2\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"CFFFCFCF7070F0F0"
    )
        port map (
      I0 => Q(10),
      I1 => s_axi_araddr(3),
      I2 => s_axi_araddr(0),
      I3 => \frames_left_reg_n_0_[10]\,
      I4 => s_axi_araddr(1),
      I5 => s_axi_araddr(2),
      O => \s_axi_rdata[10]_i_2_n_0\
    );
\s_axi_rdata[11]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"0F001100"
    )
        port map (
      I0 => s_axi_araddr(2),
      I1 => s_axi_araddr(0),
      I2 => \s_axi_rdata[11]_i_2_n_0\,
      I3 => \s_axi_rdata_reg[8]\,
      I4 => s_axi_araddr(1),
      O => D(11)
    );
\s_axi_rdata[11]_i_2\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"CF73FF73"
    )
        port map (
      I0 => \frames_left_reg_n_0_[11]\,
      I1 => s_axi_araddr(2),
      I2 => s_axi_araddr(0),
      I3 => s_axi_araddr(3),
      I4 => Q(11),
      O => \s_axi_rdata[11]_i_2_n_0\
    );
\s_axi_rdata[12]_i_1\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"2"
    )
        port map (
      I0 => \s_axi_rdata_reg[8]\,
      I1 => \s_axi_rdata[12]_i_2_n_0\,
      O => D(12)
    );
\s_axi_rdata[12]_i_2\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FF7F66BBFF7FEEBB"
    )
        port map (
      I0 => s_axi_araddr(0),
      I1 => s_axi_araddr(1),
      I2 => \frames_left_reg_n_0_[12]\,
      I3 => s_axi_araddr(3),
      I4 => s_axi_araddr(2),
      I5 => Q(12),
      O => \s_axi_rdata[12]_i_2_n_0\
    );
\s_axi_rdata[13]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0080880000800000"
    )
        port map (
      I0 => \s_axi_rdata_reg[13]\,
      I1 => \s_axi_rdata_reg[8]\,
      I2 => Q(13),
      I3 => s_axi_araddr(2),
      I4 => s_axi_araddr(3),
      I5 => \frames_left_reg_n_0_[13]\,
      O => D(13)
    );
\s_axi_rdata[14]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"0F001100"
    )
        port map (
      I0 => s_axi_araddr(2),
      I1 => s_axi_araddr(0),
      I2 => \s_axi_rdata[14]_i_2_n_0\,
      I3 => \s_axi_rdata_reg[8]\,
      I4 => s_axi_araddr(1),
      O => D(14)
    );
\s_axi_rdata[14]_i_2\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"CF73FF73"
    )
        port map (
      I0 => \frames_left_reg_n_0_[14]\,
      I1 => s_axi_araddr(2),
      I2 => s_axi_araddr(0),
      I3 => s_axi_araddr(3),
      I4 => Q(14),
      O => \s_axi_rdata[14]_i_2_n_0\
    );
\s_axi_rdata[15]_i_1\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"2"
    )
        port map (
      I0 => \s_axi_rdata_reg[8]\,
      I1 => \s_axi_rdata[15]_i_2_n_0\,
      O => D(15)
    );
\s_axi_rdata[15]_i_2\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"F53FFFFFF0FFFF0F"
    )
        port map (
      I0 => \frames_left_reg_n_0_[15]\,
      I1 => Q(15),
      I2 => s_axi_araddr(3),
      I3 => s_axi_araddr(2),
      I4 => s_axi_araddr(0),
      I5 => s_axi_araddr(1),
      O => \s_axi_rdata[15]_i_2_n_0\
    );
\s_axi_rdata[16]_i_1\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"2"
    )
        port map (
      I0 => \s_axi_rdata_reg[8]\,
      I1 => \s_axi_rdata[16]_i_2_n_0\,
      O => D(16)
    );
\s_axi_rdata[16]_i_2\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"DDFFFFFF3FCCCC00"
    )
        port map (
      I0 => \frames_left_reg_n_0_[16]\,
      I1 => s_axi_araddr(3),
      I2 => Q(16),
      I3 => s_axi_araddr(1),
      I4 => s_axi_araddr(0),
      I5 => s_axi_araddr(2),
      O => \s_axi_rdata[16]_i_2_n_0\
    );
\s_axi_rdata[17]_i_1\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"2"
    )
        port map (
      I0 => \s_axi_rdata_reg[8]\,
      I1 => \s_axi_rdata[17]_i_2_n_0\,
      O => D(17)
    );
\s_axi_rdata[17]_i_2\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"F4F33FFCF4F3FFFC"
    )
        port map (
      I0 => \frames_left_reg_n_0_[17]\,
      I1 => s_axi_araddr(1),
      I2 => s_axi_araddr(3),
      I3 => s_axi_araddr(0),
      I4 => s_axi_araddr(2),
      I5 => Q(17),
      O => \s_axi_rdata[17]_i_2_n_0\
    );
\s_axi_rdata[18]_i_1\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"2"
    )
        port map (
      I0 => \s_axi_rdata_reg[8]\,
      I1 => \s_axi_rdata[18]_i_2_n_0\,
      O => D(18)
    );
\s_axi_rdata[18]_i_2\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"F3FC7C3CFFFC7C3C"
    )
        port map (
      I0 => \frames_left_reg_n_0_[18]\,
      I1 => s_axi_araddr(0),
      I2 => s_axi_araddr(2),
      I3 => s_axi_araddr(1),
      I4 => s_axi_araddr(3),
      I5 => Q(18),
      O => \s_axi_rdata[18]_i_2_n_0\
    );
\s_axi_rdata[19]_i_1\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"2"
    )
        port map (
      I0 => \s_axi_rdata_reg[8]\,
      I1 => \s_axi_rdata[19]_i_2_n_0\,
      O => D(19)
    );
\s_axi_rdata[19]_i_2\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"DC3FFFCFDCFFFFCF"
    )
        port map (
      I0 => \frames_left_reg_n_0_[19]\,
      I1 => s_axi_araddr(3),
      I2 => s_axi_araddr(1),
      I3 => s_axi_araddr(2),
      I4 => s_axi_araddr(0),
      I5 => Q(19),
      O => \s_axi_rdata[19]_i_2_n_0\
    );
\s_axi_rdata[1]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"A8A888A8"
    )
        port map (
      I0 => \s_axi_rdata_reg[8]\,
      I1 => \s_axi_rdata[1]_i_2_n_0\,
      I2 => \s_axi_rdata_reg[1]\,
      I3 => s_axi_araddr(1),
      I4 => Q(1),
      O => D(1)
    );
\s_axi_rdata[1]_i_2\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0C080C0C00080C0C"
    )
        port map (
      I0 => \^servo_pwm\,
      I1 => s_axi_araddr(1),
      I2 => s_axi_araddr(3),
      I3 => s_axi_araddr(2),
      I4 => s_axi_araddr(0),
      I5 => \frames_left_reg_n_0_[1]\,
      O => \s_axi_rdata[1]_i_2_n_0\
    );
\s_axi_rdata[20]_i_1\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"2"
    )
        port map (
      I0 => \s_axi_rdata_reg[8]\,
      I1 => \s_axi_rdata[20]_i_2_n_0\,
      O => D(20)
    );
\s_axi_rdata[20]_i_2\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"F34FFF4FFCFCFCFC"
    )
        port map (
      I0 => \frames_left_reg_n_0_[20]\,
      I1 => s_axi_araddr(1),
      I2 => s_axi_araddr(2),
      I3 => s_axi_araddr(3),
      I4 => Q(20),
      I5 => s_axi_araddr(0),
      O => \s_axi_rdata[20]_i_2_n_0\
    );
\s_axi_rdata[21]_i_1\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"2"
    )
        port map (
      I0 => \s_axi_rdata_reg[8]\,
      I1 => \s_axi_rdata[21]_i_2_n_0\,
      O => D(21)
    );
\s_axi_rdata[21]_i_2\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FFFF6E6E77FFFFFF"
    )
        port map (
      I0 => s_axi_araddr(0),
      I1 => s_axi_araddr(1),
      I2 => Q(21),
      I3 => \frames_left_reg_n_0_[21]\,
      I4 => s_axi_araddr(2),
      I5 => s_axi_araddr(3),
      O => \s_axi_rdata[21]_i_2_n_0\
    );
\s_axi_rdata[22]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"22A2AAAA22A222A2"
    )
        port map (
      I0 => \s_axi_rdata_reg[8]\,
      I1 => \s_axi_rdata_reg[22]\,
      I2 => Q(22),
      I3 => \s_axi_rdata_reg[0]_0\,
      I4 => \s_axi_rdata_reg[22]_0\,
      I5 => \frames_left_reg_n_0_[22]\,
      O => D(22)
    );
\s_axi_rdata[23]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"20AA2020AAAAAAAA"
    )
        port map (
      I0 => \s_axi_rdata_reg[8]\,
      I1 => \s_axi_rdata_reg[22]_0\,
      I2 => \frames_left_reg_n_0_[23]\,
      I3 => \s_axi_rdata_reg[0]_0\,
      I4 => Q(23),
      I5 => \s_axi_rdata_reg[23]\,
      O => D(23)
    );
\s_axi_rdata[24]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"20AA2020AAAAAAAA"
    )
        port map (
      I0 => \s_axi_rdata_reg[8]\,
      I1 => \s_axi_rdata_reg[22]_0\,
      I2 => \frames_left_reg_n_0_[24]\,
      I3 => \s_axi_rdata_reg[0]_0\,
      I4 => Q(24),
      I5 => \s_axi_rdata_reg[23]\,
      O => D(24)
    );
\s_axi_rdata[25]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"2802200208020002"
    )
        port map (
      I0 => \s_axi_rdata_reg[25]\,
      I1 => s_axi_araddr(2),
      I2 => s_axi_araddr(3),
      I3 => s_axi_araddr(0),
      I4 => \frames_left_reg_n_0_[25]\,
      I5 => Q(25),
      O => D(25)
    );
\s_axi_rdata[26]_i_1\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"2"
    )
        port map (
      I0 => \s_axi_rdata_reg[8]\,
      I1 => \s_axi_rdata[26]_i_2_n_0\,
      O => D(26)
    );
\s_axi_rdata[26]_i_2\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FFFF6E6E77FFFFFF"
    )
        port map (
      I0 => s_axi_araddr(0),
      I1 => s_axi_araddr(1),
      I2 => Q(26),
      I3 => \frames_left_reg_n_0_[26]\,
      I4 => s_axi_araddr(2),
      I5 => s_axi_araddr(3),
      O => \s_axi_rdata[26]_i_2_n_0\
    );
\s_axi_rdata[27]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0080880000800000"
    )
        port map (
      I0 => \s_axi_rdata_reg[13]\,
      I1 => \s_axi_rdata_reg[8]\,
      I2 => Q(27),
      I3 => s_axi_araddr(2),
      I4 => s_axi_araddr(3),
      I5 => \frames_left_reg_n_0_[27]\,
      O => D(27)
    );
\s_axi_rdata[28]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"8A88AAAA8A888A88"
    )
        port map (
      I0 => \s_axi_rdata_reg[8]\,
      I1 => \s_axi_rdata_reg[28]\,
      I2 => \s_axi_rdata_reg[0]_0\,
      I3 => Q(28),
      I4 => \s_axi_rdata_reg[22]_0\,
      I5 => \frames_left_reg_n_0_[28]\,
      O => D(28)
    );
\s_axi_rdata[29]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0080880000800000"
    )
        port map (
      I0 => \s_axi_rdata_reg[13]\,
      I1 => \s_axi_rdata_reg[8]\,
      I2 => Q(29),
      I3 => s_axi_araddr(2),
      I4 => s_axi_araddr(3),
      I5 => \frames_left_reg_n_0_[29]\,
      O => D(29)
    );
\s_axi_rdata[2]_i_1\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"2"
    )
        port map (
      I0 => \s_axi_rdata_reg[8]\,
      I1 => \s_axi_rdata[2]_i_2_n_0\,
      O => D(2)
    );
\s_axi_rdata[2]_i_2\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FF30500FFF0FFFF0"
    )
        port map (
      I0 => Q(2),
      I1 => \frames_left_reg_n_0_[2]\,
      I2 => s_axi_araddr(0),
      I3 => s_axi_araddr(3),
      I4 => s_axi_araddr(2),
      I5 => s_axi_araddr(1),
      O => \s_axi_rdata[2]_i_2_n_0\
    );
\s_axi_rdata[30]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"AA20AAAAAA20AA20"
    )
        port map (
      I0 => \s_axi_rdata_reg[8]\,
      I1 => \s_axi_rdata_reg[0]_0\,
      I2 => Q(30),
      I3 => \s_axi_rdata_reg[28]\,
      I4 => \s_axi_rdata_reg[22]_0\,
      I5 => \frames_left_reg_n_0_[30]\,
      O => D(30)
    );
\s_axi_rdata[31]_i_2\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"2C20000000000000"
    )
        port map (
      I0 => Q(31),
      I1 => s_axi_araddr(2),
      I2 => s_axi_araddr(3),
      I3 => \frames_left_reg_n_0_[31]\,
      I4 => \s_axi_rdata_reg[13]\,
      I5 => \s_axi_rdata_reg[8]\,
      O => D(31)
    );
\s_axi_rdata[3]_i_1\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"2"
    )
        port map (
      I0 => \s_axi_rdata_reg[8]\,
      I1 => \s_axi_rdata[3]_i_2_n_0\,
      O => D(3)
    );
\s_axi_rdata[3]_i_2\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"CCFCCFCF7F7F0303"
    )
        port map (
      I0 => Q(3),
      I1 => s_axi_araddr(3),
      I2 => s_axi_araddr(1),
      I3 => \frames_left_reg_n_0_[3]\,
      I4 => s_axi_araddr(0),
      I5 => s_axi_araddr(2),
      O => \s_axi_rdata[3]_i_2_n_0\
    );
\s_axi_rdata[4]_i_1\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"2"
    )
        port map (
      I0 => \s_axi_rdata_reg[8]\,
      I1 => \s_axi_rdata[4]_i_2_n_0\,
      O => D(4)
    );
\s_axi_rdata[4]_i_2\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FFFF7F7F00C0CCCC"
    )
        port map (
      I0 => \frames_left_reg_n_0_[4]\,
      I1 => s_axi_araddr(0),
      I2 => s_axi_araddr(1),
      I3 => Q(4),
      I4 => s_axi_araddr(3),
      I5 => s_axi_araddr(2),
      O => \s_axi_rdata[4]_i_2_n_0\
    );
\s_axi_rdata[5]_i_1\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"2"
    )
        port map (
      I0 => \s_axi_rdata_reg[8]\,
      I1 => \s_axi_rdata[5]_i_2_n_0\,
      O => D(5)
    );
\s_axi_rdata[5]_i_2\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FF0CFFFF44FF33FF"
    )
        port map (
      I0 => \frames_left_reg_n_0_[5]\,
      I1 => s_axi_araddr(1),
      I2 => Q(5),
      I3 => s_axi_araddr(2),
      I4 => s_axi_araddr(0),
      I5 => s_axi_araddr(3),
      O => \s_axi_rdata[5]_i_2_n_0\
    );
\s_axi_rdata[6]_i_1\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"2"
    )
        port map (
      I0 => \s_axi_rdata_reg[8]\,
      I1 => \s_axi_rdata[6]_i_2_n_0\,
      O => D(6)
    );
\s_axi_rdata[6]_i_2\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"C7F3F7F3C3FCC3FC"
    )
        port map (
      I0 => \frames_left_reg_n_0_[6]\,
      I1 => s_axi_araddr(2),
      I2 => s_axi_araddr(3),
      I3 => s_axi_araddr(1),
      I4 => Q(6),
      I5 => s_axi_araddr(0),
      O => \s_axi_rdata[6]_i_2_n_0\
    );
\s_axi_rdata[7]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"8A80AAAA"
    )
        port map (
      I0 => \s_axi_rdata_reg[7]\,
      I1 => \frames_left_reg_n_0_[7]\,
      I2 => s_axi_araddr(2),
      I3 => Q(7),
      I4 => s_axi_araddr(0),
      O => D(7)
    );
\s_axi_rdata[8]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0100FFFF01000100"
    )
        port map (
      I0 => s_axi_araddr(2),
      I1 => s_axi_araddr(0),
      I2 => s_axi_araddr(1),
      I3 => \s_axi_rdata_reg[8]\,
      I4 => \s_axi_rdata[8]_i_2_n_0\,
      I5 => \s_axi_rdata_reg[7]\,
      O => D(8)
    );
\s_axi_rdata[8]_i_2\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"2A222AAA"
    )
        port map (
      I0 => s_axi_araddr(0),
      I1 => s_axi_araddr(1),
      I2 => \frames_left_reg_n_0_[8]\,
      I3 => s_axi_araddr(2),
      I4 => Q(8),
      O => \s_axi_rdata[8]_i_2_n_0\
    );
\s_axi_rdata[9]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"2082008220020002"
    )
        port map (
      I0 => \s_axi_rdata_reg[25]\,
      I1 => s_axi_araddr(2),
      I2 => s_axi_araddr(0),
      I3 => s_axi_araddr(3),
      I4 => Q(9),
      I5 => \frames_left_reg_n_0_[9]\,
      O => D(9)
    );
end STRUCTURE;
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
library UNISIM;
use UNISIM.VCOMPONENTS.ALL;
entity pwm_bench_probe_0_aura_pwm_probe is
  port (
    s_axi_rdata : out STD_LOGIC_VECTOR ( 31 downto 0 );
    s_axi_rresp : out STD_LOGIC_VECTOR ( 0 to 0 );
    s_axi_bvalid_reg_0 : out STD_LOGIC;
    s_axi_wready : out STD_LOGIC;
    s_axi_awready : out STD_LOGIC;
    s_axi_arready : out STD_LOGIC;
    s_axi_rvalid_reg_0 : out STD_LOGIC;
    servo_pwm : out STD_LOGIC;
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
  attribute ORIG_REF_NAME : string;
  attribute ORIG_REF_NAME of pwm_bench_probe_0_aura_pwm_probe : entity is "aura_pwm_probe";
end pwm_bench_probe_0_aura_pwm_probe;

architecture STRUCTURE of pwm_bench_probe_0_aura_pwm_probe is
  signal aw_address : STD_LOGIC_VECTOR ( 11 downto 0 );
  signal aw_pending : STD_LOGIC;
  signal aw_pending0 : STD_LOGIC;
  signal aw_pending_i_1_n_0 : STD_LOGIC;
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
  signal burst_n_4 : STD_LOGIC;
  signal burst_n_5 : STD_LOGIC;
  signal burst_n_6 : STD_LOGIC;
  signal burst_n_7 : STD_LOGIC;
  signal burst_n_8 : STD_LOGIC;
  signal burst_n_9 : STD_LOGIC;
  signal p_0_in : STD_LOGIC;
  signal p_1_in_0 : STD_LOGIC;
  signal p_2_in : STD_LOGIC;
  signal \^s_axi_bresp\ : STD_LOGIC_VECTOR ( 0 to 0 );
  signal \s_axi_bresp[1]_i_11_n_0\ : STD_LOGIC;
  signal \s_axi_bresp[1]_i_1_n_0\ : STD_LOGIC;
  signal \s_axi_bresp[1]_i_3_n_0\ : STD_LOGIC;
  signal \s_axi_bresp[1]_i_6_n_0\ : STD_LOGIC;
  signal s_axi_bvalid_i_1_n_0 : STD_LOGIC;
  signal \^s_axi_bvalid_reg_0\ : STD_LOGIC;
  signal \s_axi_rdata[0]_i_2_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[1]_i_3_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[22]_i_2_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[24]_i_2_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[25]_i_2_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[30]_i_2_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[30]_i_3_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[30]_i_4_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[31]_i_3_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[31]_i_4_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[31]_i_5_n_0\ : STD_LOGIC;
  signal \s_axi_rdata[8]_i_3_n_0\ : STD_LOGIC;
  signal \s_axi_rresp[1]_i_1_n_0\ : STD_LOGIC;
  signal s_axi_rvalid01_out : STD_LOGIC;
  signal s_axi_rvalid_i_1_n_0 : STD_LOGIC;
  signal \^s_axi_rvalid_reg_0\ : STD_LOGIC;
  signal scratch : STD_LOGIC_VECTOR ( 31 downto 0 );
  signal \scratch[15]_i_1_n_0\ : STD_LOGIC;
  signal \scratch[23]_i_1_n_0\ : STD_LOGIC;
  signal \scratch[31]_i_1_n_0\ : STD_LOGIC;
  signal \scratch[31]_i_2_n_0\ : STD_LOGIC;
  signal \scratch[31]_i_3_n_0\ : STD_LOGIC;
  signal \scratch[7]_i_1_n_0\ : STD_LOGIC;
  signal w_data : STD_LOGIC_VECTOR ( 31 downto 0 );
  signal w_pending : STD_LOGIC;
  signal w_pending0 : STD_LOGIC;
  signal w_pending_i_2_n_0 : STD_LOGIC;
  signal w_pending_reg_n_0 : STD_LOGIC;
  signal \w_strobes_reg_n_0_[3]\ : STD_LOGIC;
  attribute SOFT_HLUTNM : string;
  attribute SOFT_HLUTNM of aw_pending_i_1 : label is "soft_lutpair30";
  attribute SOFT_HLUTNM of s_axi_arready_INST_0 : label is "soft_lutpair29";
  attribute SOFT_HLUTNM of s_axi_awready_INST_0 : label is "soft_lutpair28";
  attribute SOFT_HLUTNM of \s_axi_bresp[1]_i_3\ : label is "soft_lutpair26";
  attribute X_INTERFACE_INFO : string;
  attribute X_INTERFACE_INFO of \s_axi_bresp_reg[1]\ : label is "xilinx.com:interface:aximm:1.0 S_AXI BRESP";
  attribute SOFT_HLUTNM of s_axi_bvalid_i_1 : label is "soft_lutpair26";
  attribute X_INTERFACE_INFO of s_axi_bvalid_reg : label is "xilinx.com:interface:aximm:1.0 S_AXI BVALID";
  attribute SOFT_HLUTNM of \s_axi_rdata[0]_i_2\ : label is "soft_lutpair27";
  attribute SOFT_HLUTNM of \s_axi_rdata[1]_i_3\ : label is "soft_lutpair27";
  attribute SOFT_HLUTNM of \s_axi_rdata[22]_i_2\ : label is "soft_lutpair24";
  attribute SOFT_HLUTNM of \s_axi_rdata[24]_i_2\ : label is "soft_lutpair24";
  attribute SOFT_HLUTNM of \s_axi_rdata[25]_i_2\ : label is "soft_lutpair31";
  attribute SOFT_HLUTNM of \s_axi_rdata[30]_i_2\ : label is "soft_lutpair25";
  attribute SOFT_HLUTNM of \s_axi_rdata[30]_i_3\ : label is "soft_lutpair25";
  attribute SOFT_HLUTNM of \s_axi_rdata[30]_i_4\ : label is "soft_lutpair23";
  attribute SOFT_HLUTNM of \s_axi_rdata[31]_i_3\ : label is "soft_lutpair31";
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
  attribute SOFT_HLUTNM of \s_axi_rresp[1]_i_1\ : label is "soft_lutpair23";
  attribute X_INTERFACE_INFO of \s_axi_rresp_reg[1]\ : label is "xilinx.com:interface:aximm:1.0 S_AXI RRESP";
  attribute SOFT_HLUTNM of s_axi_rvalid_i_1 : label is "soft_lutpair29";
  attribute X_INTERFACE_INFO of s_axi_rvalid_reg : label is "xilinx.com:interface:aximm:1.0 S_AXI RVALID";
  attribute SOFT_HLUTNM of s_axi_wready_INST_0 : label is "soft_lutpair28";
  attribute SOFT_HLUTNM of w_pending_i_2 : label is "soft_lutpair30";
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
burst: entity work.pwm_bench_probe_0_pwm_burst
     port map (
      D(31) => burst_n_2,
      D(30) => burst_n_3,
      D(29) => burst_n_4,
      D(28) => burst_n_5,
      D(27) => burst_n_6,
      D(26) => burst_n_7,
      D(25) => burst_n_8,
      D(24) => burst_n_9,
      D(23) => burst_n_10,
      D(22) => burst_n_11,
      D(21) => burst_n_12,
      D(20) => burst_n_13,
      D(19) => burst_n_14,
      D(18) => burst_n_15,
      D(17) => burst_n_16,
      D(16) => burst_n_17,
      D(15) => burst_n_18,
      D(14) => burst_n_19,
      D(13) => burst_n_20,
      D(12) => burst_n_21,
      D(11) => burst_n_22,
      D(10) => burst_n_23,
      D(9) => burst_n_24,
      D(8) => burst_n_25,
      D(7) => burst_n_26,
      D(6) => burst_n_27,
      D(5) => burst_n_28,
      D(4) => burst_n_29,
      D(3) => burst_n_30,
      D(2) => burst_n_31,
      D(1) => burst_n_32,
      D(0) => burst_n_33,
      Q(31 downto 0) => scratch(31 downto 0),
      \aw_address_reg[10]\ => burst_n_1,
      aw_pending => aw_pending,
      s_axi_aclk => s_axi_aclk,
      s_axi_araddr(3 downto 0) => s_axi_araddr(5 downto 2),
      s_axi_aresetn => s_axi_aresetn,
      s_axi_bresp(0) => \^s_axi_bresp\(0),
      \s_axi_bresp[1]_i_10_0\(31 downto 0) => w_data(31 downto 0),
      \s_axi_bresp[1]_i_5_0\ => w_pending_reg_n_0,
      \s_axi_bresp[1]_i_5_1\ => \^s_axi_bvalid_reg_0\,
      \s_axi_bresp[1]_i_7_0\(3) => \w_strobes_reg_n_0_[3]\,
      \s_axi_bresp[1]_i_7_0\(2) => p_2_in,
      \s_axi_bresp[1]_i_7_0\(1) => p_1_in_0,
      \s_axi_bresp[1]_i_7_0\(0) => p_0_in,
      \s_axi_bresp_reg[1]\ => burst_n_34,
      \s_axi_bresp_reg[1]_0\ => \s_axi_bresp[1]_i_3_n_0\,
      \s_axi_bresp_reg[1]_1\ => \s_axi_bresp[1]_i_6_n_0\,
      \s_axi_rdata_reg[0]\ => \s_axi_rdata[0]_i_2_n_0\,
      \s_axi_rdata_reg[0]_0\ => \s_axi_rdata[30]_i_2_n_0\,
      \s_axi_rdata_reg[13]\ => \s_axi_rdata[31]_i_3_n_0\,
      \s_axi_rdata_reg[1]\ => \s_axi_rdata[1]_i_3_n_0\,
      \s_axi_rdata_reg[22]\ => \s_axi_rdata[22]_i_2_n_0\,
      \s_axi_rdata_reg[22]_0\ => \s_axi_rdata[30]_i_4_n_0\,
      \s_axi_rdata_reg[23]\ => \s_axi_rdata[24]_i_2_n_0\,
      \s_axi_rdata_reg[25]\ => \s_axi_rdata[25]_i_2_n_0\,
      \s_axi_rdata_reg[28]\ => \s_axi_rdata[30]_i_3_n_0\,
      \s_axi_rdata_reg[7]\ => \s_axi_rdata[8]_i_3_n_0\,
      \s_axi_rdata_reg[8]\ => \s_axi_rdata[31]_i_4_n_0\,
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
      O => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_bresp[1]_i_11\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"E"
    )
        port map (
      I0 => aw_address(1),
      I1 => aw_address(0),
      O => \s_axi_bresp[1]_i_11_n_0\
    );
\s_axi_bresp[1]_i_3\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"BF"
    )
        port map (
      I0 => \^s_axi_bvalid_reg_0\,
      I1 => aw_pending,
      I2 => w_pending_reg_n_0,
      O => \s_axi_bresp[1]_i_3_n_0\
    );
\s_axi_bresp[1]_i_6\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FFBEBFBEFFFFFFFF"
    )
        port map (
      I0 => \s_axi_bresp[1]_i_11_n_0\,
      I1 => aw_address(3),
      I2 => aw_address(2),
      I3 => aw_address(5),
      I4 => aw_address(4),
      I5 => burst_n_1,
      O => \s_axi_bresp[1]_i_6_n_0\
    );
\s_axi_bresp_reg[1]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => '1',
      D => burst_n_34,
      Q => \^s_axi_bresp\(0),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
s_axi_bvalid_i_1: unisim.vcomponents.LUT4
    generic map(
      INIT => X"0F88"
    )
        port map (
      I0 => w_pending_reg_n_0,
      I1 => aw_pending,
      I2 => s_axi_bready,
      I3 => \^s_axi_bvalid_reg_0\,
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
\s_axi_rdata[0]_i_2\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"01"
    )
        port map (
      I0 => s_axi_araddr(4),
      I1 => s_axi_araddr(2),
      I2 => s_axi_araddr(3),
      O => \s_axi_rdata[0]_i_2_n_0\
    );
\s_axi_rdata[1]_i_3\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"40"
    )
        port map (
      I0 => s_axi_araddr(4),
      I1 => s_axi_araddr(2),
      I2 => s_axi_araddr(5),
      O => \s_axi_rdata[1]_i_3_n_0\
    );
\s_axi_rdata[22]_i_2\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"FFF8"
    )
        port map (
      I0 => s_axi_araddr(5),
      I1 => s_axi_araddr(3),
      I2 => s_axi_araddr(2),
      I3 => s_axi_araddr(4),
      O => \s_axi_rdata[22]_i_2_n_0\
    );
\s_axi_rdata[24]_i_2\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"FEEF"
    )
        port map (
      I0 => s_axi_araddr(4),
      I1 => s_axi_araddr(2),
      I2 => s_axi_araddr(3),
      I3 => s_axi_araddr(5),
      O => \s_axi_rdata[24]_i_2_n_0\
    );
\s_axi_rdata[25]_i_2\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"8"
    )
        port map (
      I0 => \s_axi_rdata[31]_i_4_n_0\,
      I1 => s_axi_araddr(3),
      O => \s_axi_rdata[25]_i_2_n_0\
    );
\s_axi_rdata[30]_i_2\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"F7FF"
    )
        port map (
      I0 => s_axi_araddr(5),
      I1 => s_axi_araddr(3),
      I2 => s_axi_araddr(4),
      I3 => s_axi_araddr(2),
      O => \s_axi_rdata[30]_i_2_n_0\
    );
\s_axi_rdata[30]_i_3\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"0001"
    )
        port map (
      I0 => s_axi_araddr(5),
      I1 => s_axi_araddr(2),
      I2 => s_axi_araddr(4),
      I3 => s_axi_araddr(3),
      O => \s_axi_rdata[30]_i_3_n_0\
    );
\s_axi_rdata[30]_i_4\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"BFFF"
    )
        port map (
      I0 => s_axi_araddr(5),
      I1 => s_axi_araddr(3),
      I2 => s_axi_araddr(4),
      I3 => s_axi_araddr(2),
      O => \s_axi_rdata[30]_i_4_n_0\
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
\s_axi_rdata[31]_i_3\: unisim.vcomponents.LUT2
    generic map(
      INIT => X"8"
    )
        port map (
      I0 => s_axi_araddr(3),
      I1 => s_axi_araddr(2),
      O => \s_axi_rdata[31]_i_3_n_0\
    );
\s_axi_rdata[31]_i_4\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"02"
    )
        port map (
      I0 => \s_axi_rdata[31]_i_5_n_0\,
      I1 => s_axi_araddr(0),
      I2 => s_axi_araddr(1),
      O => \s_axi_rdata[31]_i_4_n_0\
    );
\s_axi_rdata[31]_i_5\: unisim.vcomponents.LUT6
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
      O => \s_axi_rdata[31]_i_5_n_0\
    );
\s_axi_rdata[8]_i_3\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0000000000000880"
    )
        port map (
      I0 => \s_axi_rdata[31]_i_5_n_0\,
      I1 => s_axi_araddr(3),
      I2 => s_axi_araddr(4),
      I3 => s_axi_araddr(5),
      I4 => s_axi_araddr(1),
      I5 => s_axi_araddr(0),
      O => \s_axi_rdata[8]_i_3_n_0\
    );
\s_axi_rdata_reg[0]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_33,
      Q => s_axi_rdata(0),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[10]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_23,
      Q => s_axi_rdata(10),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[11]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_22,
      Q => s_axi_rdata(11),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[12]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_21,
      Q => s_axi_rdata(12),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[13]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_20,
      Q => s_axi_rdata(13),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[14]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_19,
      Q => s_axi_rdata(14),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[15]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_18,
      Q => s_axi_rdata(15),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[16]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_17,
      Q => s_axi_rdata(16),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[17]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_16,
      Q => s_axi_rdata(17),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[18]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_15,
      Q => s_axi_rdata(18),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[19]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_14,
      Q => s_axi_rdata(19),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[1]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_32,
      Q => s_axi_rdata(1),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[20]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_13,
      Q => s_axi_rdata(20),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[21]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_12,
      Q => s_axi_rdata(21),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[22]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_11,
      Q => s_axi_rdata(22),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[23]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_10,
      Q => s_axi_rdata(23),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[24]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_9,
      Q => s_axi_rdata(24),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[25]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_8,
      Q => s_axi_rdata(25),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[26]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_7,
      Q => s_axi_rdata(26),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[27]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_6,
      Q => s_axi_rdata(27),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[28]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_5,
      Q => s_axi_rdata(28),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[29]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_4,
      Q => s_axi_rdata(29),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[2]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_31,
      Q => s_axi_rdata(2),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[30]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_3,
      Q => s_axi_rdata(30),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[31]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_2,
      Q => s_axi_rdata(31),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[3]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_30,
      Q => s_axi_rdata(3),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[4]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_29,
      Q => s_axi_rdata(4),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[5]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_28,
      Q => s_axi_rdata(5),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[6]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_27,
      Q => s_axi_rdata(6),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[7]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_26,
      Q => s_axi_rdata(7),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[8]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_25,
      Q => s_axi_rdata(8),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rdata_reg[9]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => s_axi_rvalid01_out,
      D => burst_n_24,
      Q => s_axi_rdata(9),
      R => \s_axi_bresp[1]_i_1_n_0\
    );
\s_axi_rresp[1]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"A0B0FFFF"
    )
        port map (
      I0 => s_axi_araddr(5),
      I1 => s_axi_araddr(2),
      I2 => s_axi_araddr(4),
      I3 => s_axi_araddr(3),
      I4 => \s_axi_rdata[31]_i_4_n_0\,
      O => \s_axi_rresp[1]_i_1_n_0\
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
      R => \s_axi_bresp[1]_i_1_n_0\
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
      O => \scratch[15]_i_1_n_0\
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
      O => \scratch[23]_i_1_n_0\
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
      O => \scratch[31]_i_1_n_0\
    );
\scratch[31]_i_2\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"22222000"
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
      INIT => X"F7FFF7F7F7FFF7FF"
    )
        port map (
      I0 => w_pending_reg_n_0,
      I1 => aw_pending,
      I2 => \^s_axi_bvalid_reg_0\,
      I3 => aw_address(1),
      I4 => aw_address(0),
      I5 => aw_address(5),
      O => \scratch[31]_i_3_n_0\
    );
\scratch[7]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0000000800000000"
    )
        port map (
      I0 => \scratch[31]_i_2_n_0\,
      I1 => p_0_in,
      I2 => aw_address(0),
      I3 => aw_address(1),
      I4 => aw_address(4),
      I5 => aw_address(3),
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
      INIT => X"55D5"
    )
        port map (
      I0 => s_axi_aresetn,
      I1 => w_pending_reg_n_0,
      I2 => aw_pending,
      I3 => \^s_axi_bvalid_reg_0\,
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
      Q => p_0_in,
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
      Q => p_1_in_0,
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
entity pwm_bench_probe_0 is
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
  attribute NotValidForBitStream of pwm_bench_probe_0 : entity is true;
  attribute CHECK_LICENSE_TYPE : string;
  attribute CHECK_LICENSE_TYPE of pwm_bench_probe_0 : entity is "pwm_bench_probe_0,aura_pwm_probe,{}";
  attribute DowngradeIPIdentifiedWarnings : string;
  attribute DowngradeIPIdentifiedWarnings of pwm_bench_probe_0 : entity is "yes";
  attribute IP_DEFINITION_SOURCE : string;
  attribute IP_DEFINITION_SOURCE of pwm_bench_probe_0 : entity is "package_project";
  attribute X_CORE_INFO : string;
  attribute X_CORE_INFO of pwm_bench_probe_0 : entity is "aura_pwm_probe,Vivado 2022.2";
end pwm_bench_probe_0;

architecture STRUCTURE of pwm_bench_probe_0 is
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
inst: entity work.pwm_bench_probe_0_aura_pwm_probe
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
