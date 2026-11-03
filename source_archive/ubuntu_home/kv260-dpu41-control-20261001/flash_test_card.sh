#!/usr/bin/env bash
set -euo pipefail

# Writes only the identified, freshly formatted independent test card.
target=/dev/sda
expected_serial=121220160204
expected_card_bytes=31914983424
image=/home/ghmd/下载/xilinx-kv260-dpu-v2022.2-v3.0.0.img
expected_image_bytes=9482799104
evidence_root=/home/ghmd/kv260-dpu41-control-20261001
log="$evidence_root/logs/test_card_flash.log"

[[ $EUID -eq 0 ]] || { echo 'Administrator authorization required'; exit 1; }
exec > >(tee -a "$log") 2>&1
printf 'FLASH_START %s\n' "$(date --iso-8601=seconds)"
[[ -b $target && -f $image ]] || { echo 'Missing image or target'; exit 1; }
properties=$(udevadm info --query=property --name="$target")
serial=$(sed -n 's/^ID_SERIAL_SHORT=//p' <<< "$properties")
bus=$(sed -n 's/^ID_BUS=//p' <<< "$properties")
card_bytes=$(blockdev --getsize64 "$target")
removable=$(cat /sys/class/block/sda/removable)
[[ $serial == "$expected_serial" && $bus == usb && $removable == 1 && $card_bytes == "$expected_card_bytes" ]] || {
  echo 'Target identity mismatch; nothing written'; exit 1;
}
[[ $(stat -c %s "$image") == "$expected_image_bytes" ]] || { echo 'Image size mismatch'; exit 1; }
sha256sum -c "$evidence_root/evidence/test_card_source_image.sha256"
lsblk -o NAME,PATH,SIZE,MODEL,TRAN,RM,TYPE,FSTYPE,MOUNTPOINT "$target"

mapfile -t partitions < <(lsblk -ln -o PATH,TYPE "$target" | awk '$2 == "part" {print $1}')
for partition in "${partitions[@]}"; do
  if findmnt -rn -S "$partition" >/dev/null; then
    umount -- "$partition"
  fi
done
for device in "$target" "${partitions[@]}"; do
  if findmnt -rn -S "$device" >/dev/null; then
    echo 'Target still mounted; nothing written'; exit 1
  fi
done
printf 'WRITE_START target=%s bytes=%s %s\n' "$target" "$expected_image_bytes" "$(date --iso-8601=seconds)"
dd if="$image" of="$target" bs=4M conv=fsync status=progress
echo 'WRITE_COMPLETE; verifying every image byte against SD card'
cmp -n "$expected_image_bytes" -- "$image" "$target"
printf 'FULL_READBACK_COMPARE_PASS bytes=%s %s\n' "$expected_image_bytes" "$(date --iso-8601=seconds)"
blockdev --rereadpt "$target"
udevadm settle
lsblk -o NAME,PATH,SIZE,MODEL,TRAN,RM,TYPE,FSTYPE,MOUNTPOINT "$target"
printf 'FLASH_VERIFIED_COMPLETE %s\n' "$(date --iso-8601=seconds)"
