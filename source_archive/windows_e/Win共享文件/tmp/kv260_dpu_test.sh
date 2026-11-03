#!/usr/bin/env bash
# KV260 / Vitis AI 3.0: inference smoke test and short DPU benchmark.
set -Eeuo pipefail
export LC_ALL=C

SAMPLE_DIR=/home/root/Vitis-AI/examples/vai_library/samples/classification
MODEL_FILE=/usr/share/vitis_ai_library/models/resnet18/resnet18.xmodel
FIRMWARE=/lib/firmware/xilinx/kv260-benchmark-b4096/kv260-benchmark-b4096.xclbin
ZOCL=/sys/bus/platform/devices/axi:zyxclmm_drm
DEFAULT_IMAGE=/home/root/Vitis-AI/examples/vai_runtime/images/dpu_test.jpg
IMAGE=${1:-$DEFAULT_IMAGE}

fail() { printf 'STOP: %s\n' "$*" >&2; exit 1; }
[[ "$(uname -m)" == aarch64 ]] || fail "Run this script in the KV260 Linux SSH session."
[[ -z "${XCL_EMULATION_MODE:-}" ]] || fail "XCL_EMULATION_MODE is set; hardware test stopped."
[[ -z "${XLNX_VART_FIRMWARE:-}" ]] || fail "XLNX_VART_FIRMWARE is set; check its firmware before testing."
for tool in timeout sha256sum tee mktemp realpath; do
  command -v "$tool" >/dev/null || fail "Required command missing: $tool"
done
[[ -x "$SAMPLE_DIR/test_jpeg_classification" ]] || fail "Classification executable missing."
[[ -x "$SAMPLE_DIR/test_performance_classification" ]] || fail "Performance executable missing."
[[ -r "$IMAGE" ]] || fail "Input image missing: $IMAGE. Supply an existing JPG as the first argument."
IMAGE=$(realpath "$IMAGE")
[[ -r "$MODEL_FILE" && -r "$FIRMWARE" ]] || fail "Expected resnet18 model or B4096 xclbin missing."
[[ "$(cat /sys/class/fpga_manager/fpga0/state)" == operating ]] || fail "FPGA is not operating."
[[ "$(cat /sys/kernel/config/device-tree/overlays/kv260-benchmark-b4096_image_1/status)" == applied ]] || fail "B4096 overlay is not applied."
grep -Eq '^[[:space:]]*firmware:[[:space:]]*/lib/firmware/xilinx/kv260-benchmark-b4096/kv260-benchmark-b4096\.xclbin[[:space:]]*$' /etc/vart.conf || fail "VART firmware differs from the reviewed B4096 configuration."
[[ "$(sha256sum "$MODEL_FILE" | cut -d ' ' -f 1)" == 4d4d669c84b6d5aa6f731b389ebcf0f51fb1449752cf5fa4a4beddd496c3c0ef ]] || fail "resnet18 differs from the reviewed model."
[[ "$(sha256sum "$FIRMWARE" | cut -d ' ' -f 1)" == fc3abb934eec544e49a17c484336cf177258f475522cefc994ec458b726f69ac ]] || fail "xclbin differs from the reviewed package."

RUN_DIR=$(mktemp -d /tmp/kv260-dpu-test.XXXXXX)
exec > >(tee "$RUN_DIR/session.log") 2>&1
trap 'rc=$?; printf "\nTEST STOPPED (exit %s). Evidence: %s\n" "$rc" "$RUN_DIR"; exit "$rc"' ERR
printf 'RESULT_DIR=%s\n' "$RUN_DIR"
printf 'HOST=%s\n' "$(hostname)"
printf 'BOOT_ID=%s\n' "$(cat /proc/sys/kernel/random/boot_id)"
printf 'UPTIME=%s\n' "$(cat /proc/uptime)"
cat /etc/os-release /etc/vart.conf
sha256sum "$MODEL_FILE" "$FIRMWARE" "$IMAGE"
if command -v xmutil >/dev/null; then xmutil listapps; fi
if [[ -r "$ZOCL/xclbinid" ]]; then cat "$ZOCL/xclbinid"; fi

snapshot() {
  local name=$1
  if [[ -r "$ZOCL/kds_stat" ]]; then cat "$ZOCL/kds_stat" | tee "$RUN_DIR/$name.kds_stat.txt"; fi
  for f in /sys/class/thermal/thermal_zone*/temp; do
    if [[ -r "$f" ]]; then printf '%s=%s\n' "$f" "$(cat "$f")"; fi
  done
}
snapshot before
cd "$RUN_DIR"
printf '\n=== SINGLE-IMAGE INFERENCE ===\n'
timeout --signal=TERM --kill-after=5s 45s "$SAMPLE_DIR/test_jpeg_classification" resnet18 "$IMAGE" 2>&1 | tee inference.log
printf '%s\n' "$IMAGE" > image.list
printf '\n=== ONE THREAD, 10 SECONDS ===\n'
timeout --signal=TERM --kill-after=5s 45s "$SAMPLE_DIR/test_performance_classification" resnet18 -t 1 -s 10 "$RUN_DIR/image.list" 2>&1 | tee performance_1thread.log
printf '\n=== TWO THREADS, 10 SECONDS ===\n'
timeout --signal=TERM --kill-after=5s 45s "$SAMPLE_DIR/test_performance_classification" resnet18 -t 2 -s 10 "$RUN_DIR/image.list" 2>&1 | tee performance_2threads.log
snapshot after
printf '\n=== PERFORMANCE OUTPUT ===\n'
grep -E '^(FPS|E2E_MEAN|DPU_MEAN)=' performance_*.log || true
printf '\nCommands completed. RESULT_DIR=%s\n' "$RUN_DIR"
printf 'This is an inference/throughput test. Accuracy needs a reference output; CPU speedup needs a matched CPU baseline.\n'

