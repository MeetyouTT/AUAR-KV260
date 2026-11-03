"""Find and read public dfx loader sources only; never invoke the ELF client/daemon."""
from pathlib import Path
import hashlib
import json
import os
import time

roots = ('/usr/src/debug', '/home/root/kv260-dfx-manager-repair-20261003T042453Z',
         '/home/root/kv260-dfx-state-boardtest-20261004')
result = {'schema': 'aura-loader-public-sources-1',
          'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
          'board_monotonic_ns': time.monotonic_ns(), 'board_mutations': False,
          'project_imported': False, 'loader_executed': False,
          'database_opened': False, 'device_opened': False,
          'directories': {}, 'source_candidates': [], 'sources': {}}
for root in roots:
    p = Path(root)
    if not p.is_dir():
        continue
    result['directories'][root] = [{'name': q.name, 'is_dir': q.is_dir(),
                                   'is_symlink': q.is_symlink()} for q in sorted(p.iterdir())]
    for current, dirs, files in os.walk(str(p), followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in ('.git', '__pycache__') and
                         not (Path(current)/d).is_symlink())
        if len(Path(current).relative_to(p).parts) > 8:
            dirs[:] = []
            continue
        for name in sorted(files):
            q = Path(current)/name
            if q.suffix.lower() not in ('.c', '.h', '.cpp', '.hpp', '.patch', '.diff', '.json', '.md', '.txt'):
                continue
            # /usr/src/debug can contain unrelated system sources. Only dfx subtrees qualify.
            if root == '/usr/src/debug' and 'dfx' not in str(q).lower():
                continue
            info = q.stat()
            record = {'path': str(q), 'size': info.st_size, 'is_symlink': q.is_symlink()}
            result['source_candidates'].append(record)
            if q.is_symlink() or not q.is_file() or info.st_size > 750000:
                continue
            raw = q.read_bytes()
            result['sources'][str(q)] = {'size': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
                                         'text': raw.decode('utf-8')}
print(json.dumps(result, sort_keys=True))
