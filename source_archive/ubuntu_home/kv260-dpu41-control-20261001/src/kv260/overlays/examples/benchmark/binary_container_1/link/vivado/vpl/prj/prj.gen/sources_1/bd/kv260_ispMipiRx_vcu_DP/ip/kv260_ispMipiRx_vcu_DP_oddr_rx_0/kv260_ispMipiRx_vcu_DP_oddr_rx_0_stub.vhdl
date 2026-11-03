-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- --------------------------------------------------------------------------------
-- Tool Version: Vivado v.2022.2 (lin64) Build 3671981 Fri Oct 14 04:59:54 MDT 2022
-- Date        : Thu Oct  1 01:27:23 2026
-- Host        : ghmd-MRA-XXX running 64-bit Ubuntu 20.04.4 LTS
-- Command     : write_vhdl -force -mode synth_stub -rename_top kv260_ispMipiRx_vcu_DP_oddr_rx_0 -prefix
--               kv260_ispMipiRx_vcu_DP_oddr_rx_0_ kv260_ispMipiRx_vcu_DP_oddr_tx_0_stub.vhdl
-- Design      : kv260_ispMipiRx_vcu_DP_oddr_tx_0
-- Purpose     : Stub declaration of top-level module interface
-- Device      : xck26-sfvc784-2LV-c
-- --------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;

entity kv260_ispMipiRx_vcu_DP_oddr_rx_0 is
  Port ( 
    clk_in : in STD_LOGIC;
    clk_out : out STD_LOGIC
  );

end kv260_ispMipiRx_vcu_DP_oddr_rx_0;

architecture stub of kv260_ispMipiRx_vcu_DP_oddr_rx_0 is
attribute syn_black_box : boolean;
attribute black_box_pad_pin : string;
attribute syn_black_box of stub : architecture is true;
attribute black_box_pad_pin of stub : architecture is "clk_in,clk_out";
attribute X_CORE_INFO : string;
attribute X_CORE_INFO of stub : architecture is "oddr_v1_0_2_oddr,Vivado 2022.2";
begin
end;
