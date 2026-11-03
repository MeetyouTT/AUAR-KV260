//Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
//--------------------------------------------------------------------------------
//Tool Version: Vivado v.2022.2 (lin64) Build 3671981 Fri Oct 14 04:59:54 MDT 2022
//Date        : Mon Oct  5 02:26:10 2026
//Host        : ghmd-MRA-XXX running 64-bit Ubuntu 20.04.4 LTS
//Command     : generate_target pwm_bench_wrapper.bd
//Design      : pwm_bench_wrapper
//Purpose     : IP block netlist
//--------------------------------------------------------------------------------
`timescale 1 ps / 1 ps

module pwm_bench_wrapper
   (servo_pwm);
  output servo_pwm;

  wire servo_pwm;

  pwm_bench pwm_bench_i
       (.servo_pwm(servo_pwm));
endmodule
