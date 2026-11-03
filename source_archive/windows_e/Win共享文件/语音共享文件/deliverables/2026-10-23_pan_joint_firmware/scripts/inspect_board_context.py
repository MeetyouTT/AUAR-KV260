#!/usr/bin/env python3
"""Read current board context without MMIO, DPU jobs, service changes or commands."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess

SERVICES = ('aura-camera-ui.service', 'aura-avatar-ui.service', 'xserver-nodm.service')


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            value.update(block)
    return value.hexdigest()


def read_file(path, binary=False):
    try:
        return Path(path).read_bytes() if binary else Path(path).read_text().strip()
    except OSError:
        return None


def service_context(name):
    result = subprocess.run(['systemctl', 'show', name, '--no-pager',
        '--property=ActiveState,SubState,MainPID,NRestarts,WorkingDirectory,FragmentPath'],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=5)
    value = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
    value['query_returncode'] = result.returncode
    pid = value.get('MainPID', '0')
    if pid.isdigit() and int(pid):
        argv = (read_file('/proc/' + pid + '/cmdline', binary=True) or b'').split(b'\0')
        # Retain only executable/Python script paths, never arbitrary arguments.
        value['entry_paths'] = [a.decode(errors='replace') for a in argv
            if a.startswith(b'/') and (a.endswith(b'.py') or a == argv[0])][:3]
    return value


def lock_holders(stat, text):
    expected = f'{os.major(stat.st_dev):02x}:{os.minor(stat.st_dev):02x}:{stat.st_ino}'
    matches = []
    for line in text.splitlines():
        fields = line.split()
        if '->' in fields:
            continue  # A blocked waiter does not own the lock.
        if len(fields) >= 6 and fields[5].lower() == expected:
            matches.append({'type': fields[1], 'mode': fields[3], 'pid': int(fields[4])})
    return matches


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if platform.machine() != 'aarch64' or os.geteuid() != 0:
        raise SystemExit('KV260 root-only inspection; host execution refused')
    firmware = read_file('/proc/device-tree/fpga-full/firmware-name', binary=True)
    vart = read_file('/etc/vart.conf')
    fdt = Path('/sys/firmware/fdt')
    result = {'schema_version': 1, 'timestamp_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'boot_id': read_file('/proc/sys/kernel/random/boot_id'),
        'firmware_name': firmware.rstrip(b'\0').decode(errors='replace') if firmware else None,
        'fpga_state': read_file('/sys/class/fpga_manager/fpga0/state'),
        'fdt_sha256': digest(fdt) if fdt.exists() else None,
        'vart_firmware_paths': [line.split(':', 1)[1].strip() for line in (vart or '').splitlines()
                                if line.strip().startswith('firmware:')],
        'services': {name: service_context(name) for name in SERVICES},
        'lock_observation_is_not_ownership_or_permission': True,
        'mmio_opened': False, 'dpu_jobs_submitted': 0, 'movement_commands_sent': 0,
        'services_modified': False, 'qualified_for_motion': False}
    lock = Path('/run/aura-vsrv.lock')
    try:
        result['motion_lock_holders'] = lock_holders(lock.stat(), read_file('/proc/locks') or '')
        result['motion_lock_exists'] = True
    except OSError:
        result['motion_lock_exists'] = False
        result['motion_lock_holders'] = []
    # Refuse to overwrite an existing report; no production path is written.
    with args.output.open('x') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({'report': str(args.output), 'boot_id': result['boot_id'],
                      'firmware_name': result['firmware_name'], 'qualified_for_motion': False}))


if __name__ == '__main__':
    main()
