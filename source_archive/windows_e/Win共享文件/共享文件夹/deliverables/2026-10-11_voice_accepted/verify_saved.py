"""Verify synchronized accepted models and the frozen source archive (stdlib only)."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def main():
    reports = ['model_files.json', 'baseline_files.json']
    count = 0
    for name in reports:
        for row in json.loads((HERE / name).read_text(encoding='utf-8'))['files']:
            path = (ROOT / row['path']).resolve()
            if not path.is_relative_to(ROOT.resolve()):
                raise ValueError('Manifest path outside project')
            if not path.is_file() or path.stat().st_size != row['bytes'] or digest(path) != row['sha256']:
                raise SystemExit('FAILED: ' + row['path'])
            count += 1
    print(f'PASS: {count} saved files; synchronized baseline intact')

if __name__ == '__main__':
    main()
