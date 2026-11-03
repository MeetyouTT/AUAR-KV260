#!/bin/sh

# 
# Vivado(TM)
# runme.sh: a Vivado-generated Runs Script for UNIX
# Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
# 

if [ -z "$PATH" ]; then
  PATH=/home/ghmd/Xilinx_2022.2/Vitis/2022.2/bin:/home/ghmd/Xilinx_2022.2/Vivado/2022.2/bin
else
  PATH=/home/ghmd/Xilinx_2022.2/Vitis/2022.2/bin:/home/ghmd/Xilinx_2022.2/Vivado/2022.2/bin:$PATH
fi
export PATH

if [ -z "$LD_LIBRARY_PATH" ]; then
  LD_LIBRARY_PATH=
else
  LD_LIBRARY_PATH=:$LD_LIBRARY_PATH
fi
export LD_LIBRARY_PATH

HD_PWD='/home/ghmd/kv260-j2-pin3-static-20261006/evidence/20261006T061747.501900Z-build/project/pwm_bench.runs/synth_1'
cd "$HD_PWD"

HD_LOG=runme.log
/bin/touch $HD_LOG

ISEStep="./ISEWrap.sh"
EAStep()
{
     $ISEStep $HD_LOG "$@" >> $HD_LOG 2>&1
     if [ $? -ne 0 ]
     then
         exit
     fi
}

EAStep vivado -log pwm_bench_wrapper.vds -m64 -product Vivado -mode batch -messageDb vivado.pb -notrace -source pwm_bench_wrapper.tcl
