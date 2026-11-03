#!/usr/bin/env python3
"""Observe an already-running functional loop, then preserve read-only evidence."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

ROOT = Path('/home/root/kv260-runtime-persistent-backup-20261003')
OUT = ROOT / 'postboot-soak'
EXPECTED_BOOT = '0251d729-0d3c-44e8-abb9-27121306c081'
EXPECTED_TOP5 = [(258, '0.949879'), (270, '0.00931229'),
                 (259, '0.00821807'), (257, '0.00498451'), (279, '0.00388194')]
BOOT_PATH = Path('/proc/sys/kernel/random/boot_id')

def read(path):
    return Path(path).read_text().strip()

def write_json(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n')

def collect(name, argv):
    try:
        result = subprocess.run(argv, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=60)
        (OUT / (name + '.stdout')).write_bytes(result.stdout)
        (OUT / (name + '.stderr')).write_bytes(result.stderr)
        (OUT / (name + '.rc')).write_text(str(result.returncode) + '\n')
        return result.returncode, result.stdout.decode(errors='replace')
    except Exception as exc:
        (OUT / (name + '.stderr')).write_text(repr(exc) + '\n')
        (OUT / (name + '.rc')).write_text('exception\n')
        return None, ''

pid = int(read(OUT / 'launcher.pid'))
stat = read('/proc/%d/stat' % pid).rsplit(')', 1)[1].split()
hz = os.sysconf('SC_CLK_TCK')
start_uptime = int(stat[19]) / hz
initial = {
    'launcher_pid': pid, 'clock_ticks_per_second': hz,
    'launcher_start_boot_seconds': start_uptime,
    'observer_start_boot_seconds': float(read('/proc/uptime').split()[0]),
    'board_wall_clock_epoch': time.time(), 'boot_id': read(BOOT_PATH),
    'measurement': '60 single-image calls separated by 30-second sleeps; not continuous full-load inference',
    'late_kernel_snapshot': 'kernel-observer-start.stdout is captured after the loop started',
}
write_json('observer-start.json', initial)
collect('kernel-observer-start', ['dmesg'])
collect('memory-observer-start', ['cat', '/proc/meminfo'])

deadline = time.monotonic() + 2400
while not (OUT / 'finished.txt').exists():
    if read(BOOT_PATH) != initial['boot_id']:
        raise SystemExit('boot_id changed')
    if not Path('/proc/%d' % pid).exists():
        raise SystemExit('loop exited without finished.txt')
    if time.monotonic() > deadline:
        raise SystemExit('observation timeout')
    time.sleep(1)

finished_uptime = float(read('/proc/uptime').split()[0])
duration = {
    'launcher_start_boot_seconds': start_uptime,
    'observer_detected_finish_boot_seconds': finished_uptime,
    'observed_elapsed_seconds': round(finished_uptime - start_uptime, 2),
    'finish_detection_uncertainty_seconds': 1.1,
    'board_wall_clock_epoch_at_finish': time.time(),
    'boot_id_unchanged': read(BOOT_PATH) == EXPECTED_BOOT,
}
write_json('duration.json', duration)

run_results = []
for index in range(60):
    path = OUT / ('run-%02d.log' % index)
    matches = re.findall(r'r.index (\d+) .*?r.score ([0-9.eE+-]+)', path.read_text()) if path.exists() else []
    top5 = [(int(a), b) for a, b in matches]
    run_results.append({'index': index, 'top5_matches_baseline': top5 == EXPECTED_TOP5,
                        'parsed_top5': top5})
write_json('top5-validation.json', run_results)

rows = (OUT / 'summary.csv').read_text().splitlines()[1:]
return_codes = [row.split(',', 3)[:3] for row in rows]
states = (OUT / 'state.csv').read_text().splitlines()
pid_samples = [re.search(r'manager_pid=([^,]*)', row).group(1) for row in states]
ref_samples = [re.search(r'zocl_refcnt=([^,]*)', row).group(1) for row in states]
memory_samples = [int(re.search(r'MemAvailable_kB=(\d+)', row).group(1)) for row in states]

commands = {
    'dpu-query-final': ['xdputil', 'query'],
    'apps-final': ['xmutil', 'listapps'],
    'kernel-final': ['dmesg'],
    'memory-final': ['cat', '/proc/meminfo'],
    'manager-state-final': ['systemctl', 'show', 'dfx-mgr.service',
                            '-p', 'MainPID', '-p', 'ActiveState', '-p', 'SubState',
                            '-p', 'Result', '-p', 'ExecMainStatus', '-p', 'ExecStart',
                            '-p', 'DropInPaths'],
    'loader-state-final': ['systemctl', 'show', 'kv260-repaired-zocl.service',
                           '-p', 'ActiveState', '-p', 'SubState', '-p', 'Result',
                           '-p', 'ExecMainStatus'],
    'service-journal-final': ['journalctl', '-b', '-u', 'dfx-mgr.service',
                              '-u', 'kv260-repaired-zocl.service',
                              '--no-pager', '-o', 'short-monotonic'],
    'stock-check-final': ['sha256sum', '-c', str(ROOT / 'original/stock.sha256')],
}
results = {name: collect(name, argv) for name, argv in commands.items()}
runtime = {
    'boot_id': read(BOOT_PATH), 'zocl_srcversion': read('/sys/module/zocl/srcversion'),
    'zocl_refcnt': read('/sys/module/zocl/refcnt'),
    'card_cid': read('/sys/class/block/mmcblk1/device/cid'),
}
write_json('runtime-final.json', runtime)
try:
    query = json.loads(results['dpu-query-final'][1])
except Exception:
    query = None
summary = {
    'duration': duration, 'loop_rows': len(rows),
    'successful_return_codes': sum(row[2] == '0' for row in return_codes),
    'all_60_top5_match_baseline': all(row['top5_matches_baseline'] for row in run_results),
    'state_samples': len(states), 'manager_pids': sorted(set(pid_samples)),
    'zocl_refcounts': sorted(set(ref_samples)),
    'memavailable_kB': {'first': memory_samples[0], 'last': memory_samples[-1],
                         'minimum': min(memory_samples), 'maximum': max(memory_samples)},
    'collection_return_codes': {name: pair[0] for name, pair in results.items()},
    'runtime': runtime, 'dpu_query_parseable': query is not None,
    'scope': 'post-reboot sampled functional observation; not FPS, full-load stress, power-loss or actuator acceptance',
}
write_json('summary.json', summary)
manifest = []
for path in sorted(OUT.iterdir()):
    if path.is_file() and path.name != 'evidence.sha256':
        manifest.append(hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + path.name)
(OUT / 'evidence.sha256').write_text('\n'.join(manifest) + '\n')
print(json.dumps(summary, ensure_ascii=False))
