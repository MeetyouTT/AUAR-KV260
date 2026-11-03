#!/usr/bin/env bash
set -eo pipefail
control_root=/home/ghmd/kv260-dpu41-control-20261001
source /home/ghmd/Xilinx_2022.2/Vitis/2022.2/settings64.sh
export TRD_PATH="$control_root/dependencies/DPUCZDX8G_VAI_v3.0"
overlay_dir="$control_root/src/kv260/overlays/examples/benchmark"
platform_file="$control_root/platform/kv260_ispMipiRx_vcu_DP.xpfm"
case "${1:-}" in
  xo)
    make -C "$overlay_dir" binary_container_1/dpu.xo PLATFORM="$platform_file" JOBS=4
    ;;
  probe)
    cd "$control_root"
    vivado -mode batch -source "$control_root/evidence/probe_dpu41.tcl" \
      -log "$control_root/logs/probe_dpu41_vivado.log" \
      -journal "$control_root/logs/probe_dpu41_vivado.jou"
    ;;
  overlay)
    make -C "$overlay_dir" all PLATFORM="$platform_file" JOBS=4 \
      VPP='v++ --vivado.synth.jobs 4 --vivado.impl.jobs 4'
    ;;
  review)
    cd "$control_root"
    vivado -mode batch -source "$control_root/evidence/review_routed.tcl" \
      -log "$control_root/logs/review_routed_vivado.log" \
      -journal "$control_root/logs/review_routed_vivado.jou"
    ;;
  *)
    echo 'Usage: run_dpu41_build.sh xo|probe|overlay|review' >&2
    exit 2
    ;;
esac
