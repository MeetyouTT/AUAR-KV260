#!/usr/bin/env python3
"""Seal this completed evidence directory and independently read it back."""
import hashlib
import json
from pathlib import Path

root = Path('/home/ghmd/kv260-fs-repair-reboot-20261003')
manifest = root / 'HOST_SHA256SUMS'
if manifest.exists():
    raise SystemExit('Existing seal retained; do not overwrite it')
(root / 'kv260-fs-repair-reboot-20261003.tar.gz').chmod(0o600)
verification = json.loads((root / 'HOST_VERIFICATION.json').read_text())
assert verification['all_checks_passed']
files = sorted(path for path in root.rglob('*') if path.is_file())
entries = [(hashlib.sha256(path.read_bytes()).hexdigest(), path.relative_to(root).as_posix())
           for path in files]
manifest.write_text(''.join(sha + '  ' + relative + '\n' for sha, relative in entries))
invalid = [relative for sha, relative in entries
           if hashlib.sha256((root / relative).read_bytes()).hexdigest() != sha]
assert not invalid, invalid
print(json.dumps({'host_manifest_files': len(entries), 'all_hashes_match': True,
                  'host_checks_passed': len(verification['checks'])}))
