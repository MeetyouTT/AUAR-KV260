"""Public read-only board metadata. Run as `python3 -B -`; no project import/device I/O.

Only /proc, /sys metadata and explicitly listed public config/source files are read.
The allowlisted subprocesses are systemctl inspection, journalctl inspection and xmutil listapps.
No service state, FPGA state, lock, checkpoint, register, audio, database or motion mutation.
"""
import datetime
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import time

EXPECTED_BOOT = '903cfade-b93c-48fa-804e-379be1967313'
STARTUP = Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json')

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def run(argv, timeout=15):
    p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    return {'argv': argv, 'returncode': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr}

def public_file(path, cap=160000):
    p = Path(path)
    result = {'path': str(p), 'exists': p.exists(), 'is_symlink': p.is_symlink()}
    if not p.exists():
        return result
    st = p.stat()
    result.update(size=st.st_size, mode=oct(stat.S_IMODE(st.st_mode)))
    if p.is_symlink():
        result['symlink_target'] = os.readlink(p)
    if p.is_file():
        try:
            data = p.read_bytes()
        except OSError as error:
            result['read_error'] = type(error).__name__
            return result
        result['sha256'] = hashlib.sha256(data).hexdigest()
        if len(data) <= cap and b'\0' not in data[:4096]:
            result['text'] = data.decode('utf-8', 'replace')
    return result

def inventory(path, depth=1):
    p = Path(path)
    if not p.is_dir():
        return []
    out = []
    for child in sorted(p.iterdir(), key=lambda item: item.name):
        item = {'path': str(child), 'is_dir': child.is_dir(), 'is_symlink': child.is_symlink()}
        if child.is_symlink():
            item['target'] = os.readlink(child)
        elif child.is_file():
            item['size'] = child.stat().st_size
        if depth > 1 and child.is_dir() and not child.is_symlink():
            item['children'] = inventory(child, depth - 1)
        out.append(item)
    return out

def process(pid):
    p = Path('/proc') / str(pid)
    try:
        raw = (p / 'cmdline').read_bytes()
        stat_tail = (p / 'stat').read_text().rsplit(')', 1)[1].split()
        argv = [x.decode('utf-8', 'replace') for x in raw.split(b'\0') if x]
        return {'pid': int(pid), 'birth_ticks': int(stat_tail[19]),
                'command_sha256': hashlib.sha256(raw).hexdigest(), 'argv': argv}
    except (OSError, ValueError, IndexError):
        return None

def dpu_users():
    out = []
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        paths = []
        try:
            for fd in (proc / 'fd').iterdir():
                try:
                    target = os.readlink(fd)
                except OSError:
                    continue
                if target.startswith('/dev/dri/renderD') or target.startswith('/dev/dpu'):
                    paths.append(target)
        except OSError:
            continue
        if paths:
            item = process(proc.name)
            if item:
                item['device_handles'] = sorted(set(paths))
                out.append(item)
    return out

boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert boot == EXPECTED_BOOT, 'Boot changed: collect a new context before using this probe'
units = ['dfx-mgr.service', 'aura-camera-ui.service', 'aura-avatar-ui.service',
         'aura-native-rescue-be72669aa53de735.service']
props = ['Id', 'FragmentPath', 'DropInPaths', 'MainPID', 'ActiveState', 'SubState', 'UnitFileState',
         'Requires', 'Wants', 'Requisite', 'After', 'Before', 'Conflicts', 'BindsTo', 'PartOf',
         'ExecStartPre', 'ExecStart', 'ExecStop', 'ExecStopPost', 'Restart', 'KillMode',
         'SendSIGKILL', 'TimeoutStartUSec', 'TimeoutStopUSec', 'Job', 'Result']
files = ['/etc/vart.conf', '/sys/class/fpga_manager/fpga0/state',
         '/sys/class/fpga_manager/fpga0/firmware', '/etc/dfx-mgrd/daemon.conf',
         '/etc/dfx-mgrd/default_firmware', '/etc/dfx-mgrd/dfx-mgrd.conf',
         '/etc/default/dfx-mgr', '/etc/default/dfx-mgrd', '/etc/default/xmutil',
         '/usr/bin/xmutil', '/usr/bin/dfx-mgrd', '/usr/sbin/dfx-mgrd',
         '/etc/systemd/system/dfx-mgr.service', '/lib/systemd/system/dfx-mgr.service',
         '/usr/local/lib/kv260-dfx-state-repair-20261003/README.md']
fw_paths = ['/lib/firmware/xilinx/kv260-benchmark-b4096',
            '/lib/firmware/xilinx/aura-visual-servo-b4096-wide-v1']
result = {'schema': 'aura-platform-readonly-1', 'boot_id': boot,
          'board_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'board_monotonic': time.monotonic(), 'startup_sha256': sha(STARTUP),
          'fdt_sha256': sha('/sys/firmware/fdt'),
          'files': {p: public_file(p) for p in files},
          'inventories': {p: inventory(p, 2) for p in
                          ['/etc/dfx-mgrd', '/etc/dfx-mgr', '/etc/dfx-mgrd.conf',
                           '/usr/local/lib/kv260-dfx-state-repair-20261003'] + fw_paths},
          'units': {u: {'show': run(['systemctl', 'show', u] + ['--property=' + p for p in props]),
                        'cat': run(['systemctl', 'cat', u])} for u in units},
          'unit_files': run(['systemctl', 'list-unit-files', '--no-pager']),
          'dfx_journal': run(['journalctl', '-b', '-u', 'dfx-mgr.service', '--no-pager', '-n', '200']),
          'xmutil_apps': run(['/usr/bin/xmutil', 'listapps']),
          'dpu_users': dpu_users(),
          'board_mutations': False, 'device_opened': False, 'database_opened': False,
          'project_imported': False, 'motion_requested': False}
for directory in fw_paths:
    for child in Path(directory).iterdir():
        if child.is_file():
            result['files'][str(child)] = public_file(child, cap=100000)
print(json.dumps(result, ensure_ascii=False, sort_keys=True))
