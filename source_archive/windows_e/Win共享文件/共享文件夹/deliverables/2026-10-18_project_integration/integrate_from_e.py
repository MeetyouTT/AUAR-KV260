"""Merge the E-drive project into this workspace with verified sources and backups."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
TARGET = HERE.parents[1]
SOURCE = Path('E:/Win共享文件/共享文件夹')
CHECKSUMS = Path('E:/Win共享文件_校验清单_20261017_235746.sha256')
SKIP_DIRS = {'.verysync', '.git', '.pytest_cache', '__pycache__', 'node_modules', 'site-packages',
             'tmp', 'cache', 'host-env', 'venv', 'env'}
LOCAL_FILES = {'machine_config.json', 'last_launch.json', 'avatar_user_settings.json',
               'avatar_transcription_settings.json'}

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def expected_hashes():
    values = {}
    prefix = 'Win共享文件/共享文件夹/'
    for line in CHECKSUMS.read_text(encoding='utf-8').splitlines():
        if len(line) > 66 and line[64:66] == '  ' and line[66:].startswith(prefix):
            values[line[66 + len(prefix):]] = line[:64]
    return values

def source_files():
    for parent, dirs, files in os.walk(SOURCE, followlinks=False):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith('.venv')
                   and not Path(parent, d).is_symlink()]
        for name in files:
            p = Path(parent, name)
            rel = p.relative_to(SOURCE).as_posix()
            if p.is_symlink() or name in LOCAL_FILES or '.sync-conflict-' in name:
                continue
            if '/data/identities/' in '/' + rel or name.endswith(('.pyc', '.pyo', '.lock')):
                continue
            # Preserve live machine logs while retaining archived report/test evidence.
            if name.endswith('.log') and not ('/report/' in '/' + rel or 'regression' in name):
                continue
            yield p, rel

def plan():
    hashes = expected_hashes()
    assert SOURCE.resolve() != TARGET.resolve() and hashes
    rows = []
    same = 0
    for source, rel in source_files():
        dest = TARGET / rel
        expected = hashes.get(rel)
        if expected is None:
            raise RuntimeError('Missing source copy-checksum record: ' + rel)
        if dest.is_file() and dest.stat().st_size == source.stat().st_size and digest(dest) == expected:
            same += 1
            continue
        if rel.startswith('deliverables/2026-10-11_voice_accepted/'):
            raise RuntimeError('Accepted immutable baseline differs; manual review required: ' + rel)
        rows.append({'path': rel, 'action': 'replace' if dest.exists() else 'add',
                     'source_sha256': expected, 'source_bytes': source.stat().st_size,
                     'local_sha256': digest(dest) if dest.is_file() else None})
    report = {'source': str(SOURCE), 'target': str(TARGET), 'authority': 'User requested E-drive project integration',
              'same_files': same, 'added': sum(r['action'] == 'add' for r in rows),
              'replaced': sum(r['action'] == 'replace' for r in rows), 'files': rows,
              'preserved': ['local environments', 'VerySync metadata', 'machine paths/settings',
                            'sync-conflict variants', 'local-only files', 'accepted voice baseline'],
              'status': 'PLANNED', 'utc': datetime.now(timezone.utc).isoformat()}
    (HERE / 'integration_plan.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('PLAN', same, 'unchanged;', report['added'], 'add;', report['replaced'], 'replace', flush=True)
    return report

def apply(report):
    if report['source'] != str(SOURCE) or report['target'] != str(TARGET):
        raise RuntimeError('Plan belongs to another workspace')
    rows = report['files']
    for row in rows:
        relative = Path(row['path'])
        if relative.is_absolute() or '..' in relative.parts:
            raise RuntimeError('Invalid planned relative path')
    for row in rows:
        source = SOURCE / row['path']
        if digest(source) != row['source_sha256']:
            raise RuntimeError('Source changed since E-drive copy: ' + row['path'])
    for row in rows:
        dest = TARGET / row['path']
        if not dest.resolve().is_relative_to(TARGET.resolve()):
            raise RuntimeError('Target outside workspace')
        current = digest(dest) if dest.is_file() else None
        if current != row['local_sha256']:
            raise RuntimeError('Local file changed during inventory: ' + row['path'])
        if row['action'] == 'replace':
            backup = HERE / 'before' / row['path']
            if backup.exists():
                raise RuntimeError('Backup already exists: ' + row['path'])
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dest, backup)
            if digest(backup) != current:
                raise RuntimeError('Backup verification failed')
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SOURCE / row['path'], dest)
        if digest(dest) != row['source_sha256']:
            raise RuntimeError('Destination verification failed: ' + row['path'])
        row['verified'] = True
    report['status'] = 'PASS_FILES_INTEGRATED'
    (HERE / 'integration_result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('INTEGRATION_PASS', flush=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if args.apply:
        apply(json.loads((HERE / 'integration_plan.json').read_text(encoding='utf-8')))
    else:
        plan()
