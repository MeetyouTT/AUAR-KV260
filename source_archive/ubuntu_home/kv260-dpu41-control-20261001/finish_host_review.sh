#!/usr/bin/env bash
set -euo pipefail

control_root=/home/ghmd/kv260-dpu41-control-20261001
source /home/ghmd/Xilinx_2022.2/Vitis/2022.2/settings64.sh
sd_dir="$control_root/src/kv260/overlays/examples/benchmark/binary_container_1/sd_card"
xclbin="$sd_dir/dpu.xclbin"
routed="$control_root/src/kv260/overlays/examples/benchmark/binary_container_1/link/vivado/vpl/prj/prj.runs/impl_1/kv260_ispMipiRx_vcu_DP_wrapper_routed.dcp"

test -s "$xclbin"
test -s "$routed"
test -s "$sd_dir/kv260_ispMipiRx_vcu_DP_wrapper.bit"
test -s "$sd_dir/kv260_ispMipiRx_vcu_DP.hwh"
test -s "$sd_dir/arch.json"

xclbinutil --input "$xclbin" --info > "$control_root/evidence/xclbin_info.log" 2>&1
xclbinutil --input "$xclbin" \
  --dump-section "IP_LAYOUT:JSON:$control_root/evidence/xclbin_IP_LAYOUT.json" \
  --dump-section "CONNECTIVITY:JSON:$control_root/evidence/xclbin_CONNECTIVITY.json" \
  --force > "$control_root/logs/xclbin_sections.log" 2>&1

if ! rg -q 'DPU41_ROUTED_REVIEW_COMPLETE' "$control_root/logs/review_routed.log" 2>/dev/null; then
  bash "$control_root/run_dpu41_build.sh" review > "$control_root/logs/review_routed.log" 2>&1
fi
python3 "$control_root/prepare_test_bundle.py" hardware > "$control_root/logs/prepare_hardware.log" 2>&1
python3 "$control_root/collect_review.py" > "$control_root/logs/collect_review.log" 2>&1

(
  cd "$control_root/test_bundle"
  sha256sum -c SHA256SUMS
) > "$control_root/logs/bundle_hash_check.log" 2>&1

echo 'DPU41_HOST_REVIEW_SCRIPTS_COMPLETED'
