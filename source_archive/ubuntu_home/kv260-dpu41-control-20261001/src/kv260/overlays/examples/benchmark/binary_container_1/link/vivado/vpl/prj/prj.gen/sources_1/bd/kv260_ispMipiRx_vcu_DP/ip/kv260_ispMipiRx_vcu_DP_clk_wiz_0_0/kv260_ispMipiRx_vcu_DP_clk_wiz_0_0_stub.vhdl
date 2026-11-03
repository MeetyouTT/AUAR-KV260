-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- --------------------------------------------------------------------------------
-- Tool Version: Vivado v.2022.2 (lin64) Build 3671981 Fri Oct 14 04:59:54 MDT 2022
-- Date        : Thu Oct  1 01:16:43 2026
-- Host        : ghmd-MRA-XXX running 64-bit Ubuntu 20.04.4 LTS
-- Command     : write_vhdl -force -mode synth_stub -rename_top kv260_ispMipiRx_vcu_DP_clk_wiz_0_0 -prefix
--               kv260_ispMipiRx_vcu_DP_clk_wiz_0_0_ kv260_ispMipiRx_vcu_DP_clk_wiz_0_0_stub.vhdl
-- Design      : kv260_ispMipiRx_vcu_DP_clk_wiz_0_0
-- Purpose     : Stub declaration of top-level module interface
-- Device      : xck26-sfvc784-2LV-c
-- --------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;

entity kv260_ispMipiRx_vcu_DP_clk_wiz_0_0 is
  Port ( 
    clk_200M : out STD_LOGIC;
    clk_100M : out STD_LOGIC;
    clk_300M : out STD_LOGIC;
    clk_50M : out STD_LOGIC;
    clk_600M : out STD_LOGIC;
    resetn : in STD_LOGIC;
    locked : out STD_LOGIC;
    clk_in1 : in STD_LOGIC
  );

end kv260_ispMipiRx_vcu_DP_clk_wiz_0_0;

architecture stub of kv260_ispMipiRx_vcu_DP_clk_wiz_0_0 is
attribute syn_black_box : boolean;
attribute black_box_pad_pin : string;
attribute syn_black_box of stub : architecture is true;
attribute black_box_pad_pin of stub : architecture is "clk_200M,clk_100M,clk_300M,clk_50M,clk_600M,resetn,locked,clk_in1";
begin
end;
