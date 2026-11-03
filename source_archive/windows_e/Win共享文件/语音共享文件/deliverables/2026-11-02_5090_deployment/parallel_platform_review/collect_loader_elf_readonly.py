"""Static ELF inspection using fixed objdump/readelf commands, never executing targets."""
from pathlib import Path
import hashlib
import json
import subprocess
import time

ROOT = Path('/home/root/kv260-dfx-state-boardtest-20261004/staging/extracted')
DAEMON = '/usr/local/lib/kv260-dfx-state-repair-20261003/dfx-mgrd'
CLIENT = '/usr/bin/dfx-mgr-client'
result = {'schema': 'aura-loader-static-elf-1',
          'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
          'board_monotonic_ns': time.monotonic_ns(), 'board_mutations': False,
          'loader_executed': False, 'project_imported': False,
          'device_opened': False, 'database_opened': False, 'files': {}, 'commands': []}
for p in (ROOT/'bin/dfx-mgrd', ROOT/'bin/dfx-mgr-client', ROOT/'BUILD_STATUS.json',
          ROOT/'PROVENANCE.json', ROOT/'SOURCE_MANIFEST.json', Path(DAEMON), Path(CLIENT)):
    if not p.is_file():
        continue
    raw = p.read_bytes()
    rec = {'size': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    if p.suffix == '.json':
        rec['json'] = json.loads(raw)
    result['files'][str(p)] = rec
commands = [
    ['/usr/bin/readelf', '-n', CLIENT],
    ['/usr/bin/readelf', '-d', CLIENT],
    ['/usr/bin/objdump', '-d', '--disassemble=main', CLIENT],
    ['/usr/bin/readelf', '-d', DAEMON],
    ['/usr/bin/objdump', '-d', '--disassemble=process_dfx_req', DAEMON],
    ['/usr/bin/objdump', '-d', '--disassemble=sys_remove_accel', DAEMON],
    ['/usr/bin/objdump', '-d', '--disassemble=sys_load_accel', DAEMON],
]
for argv in commands:
    done = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, timeout=15)
    result['commands'].append({'argv': argv, 'returncode': done.returncode,
                               'stdout': done.stdout.decode('utf-8'),
                               'stderr': done.stderr.decode('utf-8')})
print(json.dumps(result, sort_keys=True))
