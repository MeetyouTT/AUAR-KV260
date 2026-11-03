#!/usr/bin/env bash
set -uo pipefail
restore_dir="/home/ghmd/kv260-dpu41-control-20261001/evidence/official_restore_20261002T102513Z"
cd -- "$restore_dir" || exit 1
if [[ -e terminal.log || -e restore_result.json ]]; then
    printf '已有日志，拒绝重复运行或覆盖。\n'
    exec bash --noprofile --norc -i
fi
python3 -u "$restore_dir/restore_official.py" 2>&1 | tee "$restore_dir/terminal.log"
restore_status=${PIPESTATUS[0]}
if [[ "$restore_status" -eq 0 ]]; then
    python3 - "$restore_dir" <<'PY'
from pathlib import Path
import hashlib,sys
root=Path(sys.argv[1])
with (root/'SHA256SUMS').open('x') as out:
    for path in sorted(root.iterdir()):
        if path.is_file() and path.name != 'SHA256SUMS':
            out.write(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+path.name+'\n')
PY
    printf '\n官方核验已通过。进入板卡串口后，按回车显示 root 提示符。\n退出串口：Ctrl-A，再 Ctrl-X。\n'
    picocom --baud 115200 --flow n --noinit --noreset /dev/serial/by-id/usb-Xilinx_ML_Carrier_Card_XFL1EMEBC1R5-if01-port0
else
    printf '\n核验未通过，已停止。日志：%s\n' "$restore_dir/terminal.log"
fi
exec bash --noprofile --norc -i

