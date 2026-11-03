"""Re-read the exact public validator import sources; never execute or import them."""
from pathlib import Path
import ast
import hashlib
import json
import os
import time

ROOT = Path('/home/root/aura-native-live-20261024/candidates/native-r4-metrics-fix/aura')
paths = [ROOT/'board/__init__.py', ROOT/'board/vision/__init__.py',
         ROOT/'board/vision/native_protection.py', ROOT/'board/vision/native_binding.py']
result = {'schema': 'aura-checkpoint-import-sources-static-1',
          'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
          'board_monotonic_ns': time.monotonic_ns(), 'board_mutations': False,
          'project_imported': False, 'validator_called': False, 'checkpoint_read': False,
          'checkpoint_consumed': False, 'device_opened': False, 'database_opened': False,
          'sources': {}, 'parent_paths': {}}
for p in paths:
    rec = {'exists': p.exists(), 'is_symlink': p.is_symlink()}
    if p.is_symlink():
        rec['link_target'] = os.readlink(str(p))
    if p.is_file():
        raw = p.read_bytes()
        rec.update(sha256=hashlib.sha256(raw).hexdigest(), size=len(raw), text=raw.decode('utf-8'))
        tree = ast.parse(raw)
        rec['module_statements'] = [{'kind': type(node).__name__, 'line': node.lineno,
                                    'end_line': getattr(node, 'end_lineno', None),
                                    'name': getattr(node, 'name', None)} for node in tree.body]
    result['sources'][str(p)] = rec
for p in (ROOT, ROOT/'board', ROOT/'board/vision'):
    info = p.lstat()
    result['parent_paths'][str(p)] = {'is_symlink': p.is_symlink(), 'realpath': str(p.resolve()),
                                     'uid': info.st_uid, 'mode': oct(info.st_mode & 0o7777)}
print(json.dumps(result, sort_keys=True))
