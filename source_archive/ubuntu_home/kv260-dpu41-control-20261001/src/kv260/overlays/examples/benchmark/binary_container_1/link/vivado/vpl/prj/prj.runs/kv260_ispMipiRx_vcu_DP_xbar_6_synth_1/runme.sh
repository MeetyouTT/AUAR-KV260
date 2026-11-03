#!/bin/sh

# 
# Vivado(TM)
# runme.sh: a Vivado-generated Runs Script for UNIX
# Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
# 

if [ -z "$PATH" ]; then
  PATH=/home/ghmd/Xilinx_2022.2/Vitis/2022.2/bin:/home/ghmd/Xilinx_2022.2/Vitis/2022.2/bin:/home/ghmd/Xilinx_2022.2/Vitis/2022.2/bin:/home/ghmd/Xilinx_2022.2/Vitis/2022.2/bin:/home/ghmd/Xilinx_2022.2/Vivado/2022.2/bin
else
  PATH=/home/ghmd/Xilinx_2022.2/Vitis/2022.2/bin:/home/ghmd/Xilinx_2022.2/Vitis/2022.2/bin:/home/ghmd/Xilinx_2022.2/Vitis/2022.2/bin:/home/ghmd/Xilinx_2022.2/Vitis/2022.2/bin:/home/ghmd/Xilinx_2022.2/Vivado/2022.2/bin:$PATH
fi
export PATH

if [ -z "$LD_LIBRARY_PATH" ]; then
  LD_LIBRARY_PATH=
else
  LD_LIBRARY_PATH=:$LD_LIBRARY_PATH
fi
export LD_LIBRARY_PATH

HD_PWD='/home/ghmd/kv260-dpu41-control-20261001/src/kv260/overlays/examples/benchmark/binary_container_1/link/vivado/vpl/prj/prj.runs/kv260_ispMipiRx_vcu_DP_xbar_6_synth_1'
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

EAStep vivado -log kv260_ispMipiRx_vcu_DP_xbar_6.vds -m64 -product Vivado -mode batch -messageDb vivado.pb -notrace -source kv260_ispMipiRx_vcu_DP_xbar_6.tcl
