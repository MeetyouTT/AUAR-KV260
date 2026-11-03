"""Board-side metadata/source collector. Never executes a loader or imports project code."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import time


def file_metadata(path, include_text=False):
    p = Path(path)
    result = {'path': str(p), 'exists': p.exists(), 'is_symlink': p.is_symlink()}
    if p.is_symlink():
        result['link_target'] = os.readlink(str(p))
    if not p.is_file():
        return result
    info = p.stat()
    result.update(realpath=str(p.resolve()), size=info.st_size, uid=info.st_uid,
                  mode=oct(info.st_mode & 0o7777))
    raw = p.read_bytes()
    result['sha256'] = hashlib.sha256(raw).hexdigest()
    result['elf'] = raw.startswith(b'\x7fELF')
    if include_text and not result['elf'] and len(raw) <= 500000:
        result['text'] = raw.decode('utf-8')
    return result


result = {'schema': 'aura-loader-static-inventory-1',
          'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
          'board_monotonic_ns': time.monotonic_ns(),
          'board_mutations': False, 'project_imported': False,
          'device_opened': False, 'database_opened': False,
          'loader_executed': False,
          'path_environment': os.environ.get('PATH'),
          'files': {}, 'directories': {}, 'processes': []}
for name in ('dfx-mgr-client', 'dfx-mgrd', 'xmutil', 'readelf', 'objdump', 'strings'):
    found = shutil.which(name)
    result.setdefault('executable_resolution', {})[name] = found
    if found:
        result['files'][found] = file_metadata(found, include_text=True)
for path in ('/usr/local/lib/kv260-dfx-state-repair-20261003/dfx-mgrd',
             '/usr/local/lib/kv260-runtime-repair/dfx-mgrd',
             '/etc/systemd/system/dfx-mgr.service.d/10-kv260-repaired.conf',
             '/etc/systemd/system/dfx-mgr.service.d/20-kv260-dfx-state-repaired.conf'):
    result['files'][path] = file_metadata(path, include_text=True)
for path in ('/usr/local/src', '/usr/src', '/usr/local/lib/kv260-dfx-state-repair-20261003'):
    p = Path(path)
    if p.is_dir():
        result['directories'][path] = [{'name': c.name, 'is_dir': c.is_dir(),
                                        'is_symlink': c.is_symlink()} for c in sorted(p.iterdir())]
result['root_dfx_candidates'] = [p.name for p in sorted(Path('/home/root').iterdir())
                                 if any(s in p.name.lower() for s in ('dfx', 'repair', '20261003'))]
for p in Path('/proc').iterdir():
    if not p.name.isdigit():
        continue
    try:
        command = (p/'cmdline').read_bytes()
        if b'dfx-mgr' not in command:
            continue
        stat = (p/'stat').read_text()
        exe = os.readlink(str(p/'exe'))
        result['processes'].append({'pid': int(p.name), 'birth_ticks': int(stat.rsplit(')', 1)[1].split()[19]),
                                    'command_sha256': hashlib.sha256(command).hexdigest(),
                                    'command': command.replace(b'\0', b' ').decode('utf-8'), 'exe': exe,
                                    'exe_sha256': hashlib.sha256((p/'exe').read_bytes()).hexdigest()})
    except (FileNotFoundError, ProcessLookupError, PermissionError):
        continue
print(json.dumps(result, sort_keys=True))
