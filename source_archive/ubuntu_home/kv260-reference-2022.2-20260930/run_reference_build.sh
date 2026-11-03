#!/usr/bin/env bash
set -eo pipefail

work_dir=/home/ghmd/kv260-reference-2022.2-20260930
source /home/ghmd/Xilinx_2022.2/Vitis/2022.2/settings64.sh

case "${1:-}" in
  platform)
    make -C "$work_dir/src/kv260" platform \
      PFM=kv260_ispMipiRx_vcu_DP JOBS=4 \
      XSCT="$XILINX_VITIS/bin/xsct -nodisp"
    ;;
  overlay)
    make -C "$work_dir/src/kv260" overlay \
      OVERLAY=benchmark JOBS=4 \
      XSCT="$XILINX_VITIS/bin/xsct -nodisp"
    ;;
  *)
    echo 'Usage: run_reference_build.sh platform|overlay' >&2
    exit 2
    ;;
esac
