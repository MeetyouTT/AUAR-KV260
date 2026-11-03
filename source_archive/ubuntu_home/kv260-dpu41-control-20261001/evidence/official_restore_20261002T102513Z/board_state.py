"""Read current board state and verify the preserved official files."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

if os.geteuid() != 0:
    raise SystemExit('Board root shell required')
cid = Path('/sys/block/mmcblk1/device/cid').read_text().strip()
if cid != '0353445345333247805558c00401a100':
    raise SystemExit('Unexpected SD card; no application change permitted')
model = Path('/proc/device-tree/model').read_bytes().rstrip(b'\0').decode()
if 'K26' not in model:
    raise SystemExit('Unexpected board model')
result = subprocess.run(['dfx-mgr-client', '-listPackage'], stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT, universal_newlines=True, timeout=20)
print(result.stdout, flush=True)
if result.returncode:
    raise SystemExit(result.returncode)
active = []
for line in result.stdout.splitlines():
    fields = line.split()
    if len(fields) == 6 and fields[1] == 'XRT_FLAT' and fields[-1].rstrip(',') == '0':
        active.append(fields[0])
if active not in ([], ['kv260-benchmark-b4096'], ['kv260-benchmark-b4096-dpu41']):
    raise SystemExit('Unexpected active application: ' + repr(active))
busy = []
names = {'test_jpeg_classification', 'test_performance_classification', 'xdputil', 'dpu_runner'}
for proc in Path('/proc').iterdir():
    if not proc.name.isdigit():
        continue
    try:
        argv = (proc / 'cmdline').read_bytes().split(b'\0')
        if any(Path(word.decode('utf-8', 'replace')).name in names for word in argv[:2] if word):
            busy.append(int(proc.name))
    except (OSError, ValueError):
        pass
if busy:
    raise SystemExit('Active DPU clients; stopped without terminating them: ' + repr(busy))
expected = {
    '/lib/firmware/xilinx/kv260-benchmark-b4096/kv260-benchmark-b4096.bit.bin': '7d12c877e0fde40a243d2350b1a2227f565788bf9e2dcae4439d07f213d40a3f',
    '/lib/firmware/xilinx/kv260-benchmark-b4096/kv260-benchmark-b4096.dtbo': '36338937904e5ec988566d7341f6504edba34c01bd7e2e3f2025ab0069337e35',
    '/lib/firmware/xilinx/kv260-benchmark-b4096/kv260-benchmark-b4096.xclbin': 'fc3abb934eec544e49a17c484336cf177258f475522cefc994ec458b726f69ac',
    '/lib/firmware/xilinx/kv260-benchmark-b4096/shell.json': '2967ccbc1f75c8d4accd1b6fecc11b16a32a5d7992e56c6eebceb99a3410f777',
    '/usr/share/vitis_ai_library/models/resnet18/resnet18.xmodel': '4d4d669c84b6d5aa6f731b389ebcf0f51fb1449752cf5fa4a4beddd496c3c0ef',
    '/usr/share/vitis_ai_library/models/resnet18/resnet18.prototxt': '691c393b15ae87976060a125067534334bd034c3a5193a96f6f5db3f4da3729c',
    '/home/root/kv260-test-20261001/pytorch-resnet-dog.jpg': 'f3f87bb8ab3c26c7ecfd3ac60421d7f32b0503d1d6c5baf8bac42ed93d86351a',
    '/home/root/kv260-test-20261001/samoyed.list': 'bf02d74370fbfdd8d008c7916109a14be3a5b33bd6057522fbb14e95ac2e9caa',
    '/home/root/Vitis-AI/examples/vai_library/samples/classification/test_jpeg_classification': '322dd07736f409cba02416782475c0dc2b5951435ddbb6d0671d3cda8fac0c0e',
    '/home/root/Vitis-AI/examples/vai_library/samples/classification/test_performance_classification': 'b9f52e4fd21d6526a8ac1e73b6e839b28308368451c4bb30e845a9f96343f1b4',
}
actual = {}
for name, wanted in expected.items():
    value = hashlib.sha256(Path(name).read_bytes()).hexdigest()
    actual[name] = value
    if value != wanted:
        raise SystemExit('Preserved official firmware/input hash mismatch: ' + name)

def read_optional(name):
    p = Path(name)
    return p.read_bytes().rstrip(b'\0\n').decode() if p.exists() else None

vart = read_optional('/etc/vart.conf') or ''
firmware_lines = [line.strip() for line in vart.splitlines() if line.strip().startswith('firmware:')]
state = {
    'board_model': model, 'sd_cid': cid, 'active_apps': active,
    'fpga_manager': read_optional('/sys/class/fpga_manager/fpga0/state'),
    'live_firmware_name': read_optional('/proc/device-tree/fpga-full/firmware-name'),
    'vart_firmware_lines': firmware_lines, 'official_file_and_input_hashes': actual,
    'busy_dpu_clients': busy,
}
print('STATE_JSON ' + json.dumps(state, ensure_ascii=False), flush=True)

