#!/usr/bin/env bash
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo 'Administrator authorization required'; exit 1; }
target=/dev/sda
evidence_root=/home/ghmd/kv260-dpu41-control-20261001
serial=$(udevadm info --query=property --name="$target" | sed -n 's/^ID_SERIAL_SHORT=//p')
[[ $serial == 121220160204 && $(blockdev --getsize64 "$target") == 31914983424 ]] || { echo 'Target identity mismatch'; exit 1; }
bytes=9482799104
expected=b5de568c8f008dd251cdc3c7fcc0b3942e973e752943152628519768f845aa9c
exec > >(tee -a "$evidence_root/logs/test_card_direct_readback.log") 2>&1
echo 'Waiting for the writer to finish fsync before direct readback'
deadline=$((SECONDS + 3600))
until /usr/bin/grep -q '^WRITE_COMPLETE;' "$evidence_root/logs/test_card_flash.log"; do
  [[ $SECONDS -lt $deadline ]] || { echo 'Writer completion timeout'; exit 1; }
  sleep 2
done
# Keep desktop automount from changing filesystem metadata before verification.
# This kernel flag clears when the reader is disconnected and reconnected.
blockdev --setro "$target"
echo 'Card temporarily read-only for verification'
printf 'DIRECT_READBACK_START %s\n' "$(date --iso-8601=seconds)"
actual=$(dd if="$target" bs=4M count="$bytes" iflag=direct,count_bytes status=progress | sha256sum | awk '{print $1}')
printf '%s  %s:first-%s-bytes\n' "$actual" "$target" "$bytes" > "$evidence_root/evidence/test_card_direct_readback.sha256"
[[ $actual == "$expected" ]] || { echo 'DIRECT_READBACK_SHA256_MISMATCH'; exit 1; }
printf 'DIRECT_READBACK_SHA256_PASS %s %s\n' "$actual" "$(date --iso-8601=seconds)"
