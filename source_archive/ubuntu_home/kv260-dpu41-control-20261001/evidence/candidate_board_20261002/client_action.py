"""Board-side guarded dfx-mgr operation with actual return code and slot verification."""
from pathlib import Path
import subprocess
import sys
import time

action, before, after = sys.argv[1:4]
if action not in ('remove', 'load'):
    raise SystemExit('Unexpected operation')
if Path('/sys/block/mmcblk1/device/cid').read_text().strip() != '0353445345333247805558c00401a100':
    raise SystemExit('Unexpected SD card')

def active_apps():
    result = subprocess.run(['dfx-mgr-client', '-listPackage'], stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, universal_newlines=True, timeout=20)
    print(result.stdout, flush=True)
    if result.returncode:
        raise SystemExit(result.returncode)
    apps = []
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) == 6 and fields[1] == 'XRT_FLAT' and fields[-1].rstrip(',') == '0':
            apps.append(fields[0])
    return apps

expected_before = [] if before == 'NONE' else [before]
if active_apps() != expected_before:
    raise SystemExit('Unexpected active application before operation')
busy = []
names = {'test_jpeg_classification', 'test_performance_classification', 'xdputil', 'dpu_runner'}
for entry in Path('/proc').iterdir():
    if not entry.name.isdigit():
        continue
    try:
        argv = (entry / 'cmdline').read_bytes().split(b'\0')
        candidates = argv[:2]
        if any(Path(word.decode('utf-8', 'replace')).name in names for word in candidates if word):
            busy.append(int(entry.name))
    except (OSError, ValueError):
        continue
if busy:
    raise SystemExit('Active inference processes: ' + repr(busy))
command = ['dfx-mgr-client', '-remove'] if action == 'remove' else ['dfx-mgr-client', '-load', after]
print('DFX_COMMAND', repr(command), flush=True)
result = subprocess.run(command, timeout=75)
print('DFX_CLIENT_RETURN_CODE', result.returncode, flush=True)
if result.returncode:
    raise SystemExit(result.returncode)
time.sleep(1)
expected_after = [] if after == 'NONE' else [after]
actual = active_apps()
if actual != expected_after:
    raise SystemExit('Unexpected active application after operation: ' + repr(actual))
print('DFX_ACTIVE_SLOT_VERIFIED', repr(actual), flush=True)
