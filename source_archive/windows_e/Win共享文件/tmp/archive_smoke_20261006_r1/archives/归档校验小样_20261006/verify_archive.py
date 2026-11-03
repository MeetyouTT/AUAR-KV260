"""Verify a restored baseline using its SHA-256 manifest; no third-party packages."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath


def digest_file(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def safe_child(root, relative):
    name = PurePosixPath(relative)
    if name.is_absolute() or not name.parts or any(part in ('', '.', '..') or ':' in part or '\\' in part for part in name.parts):
        raise ValueError('Unsafe manifest path: ' + relative)
    candidate = root.joinpath(*name.parts)
    if not candidate.resolve().is_relative_to(root.resolve()):
        raise ValueError('Path escapes archive root: ' + relative)
    return candidate


def verify(root):
    root = Path(root).resolve()
    manifest = json.loads((root / 'archive_manifest.json').read_text(encoding='utf-8'))
    source = safe_child(root, manifest['source_subdirectory'])
    failures = []
    for entry in manifest['files']:
        path = safe_child(source, entry['path'])
        if not path.is_file():
            failures.append({'path': entry['path'], 'error': 'missing'})
        elif path.stat().st_size != entry['size_bytes']:
            failures.append({'path': entry['path'], 'error': 'size mismatch'})
        elif digest_file(path) != entry['sha256']:
            failures.append({'path': entry['path'], 'error': 'SHA-256 mismatch'})
    expected = {entry['path'] for entry in manifest['files']}
    actual = {path.relative_to(source).as_posix() for path in source.rglob('*') if path.is_file()}
    extra = sorted(actual - expected)
    result = {'status': 'PASS' if not failures and not extra else 'FAIL',
              'files_verified': len(manifest['files']) - len(failures),
              'source_bytes': sum(entry['size_bytes'] for entry in manifest['files']),
              'failures': failures, 'extra_files': extra}
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', nargs='?', default=str(Path(__file__).resolve().parent))
    args = parser.parse_args()
    report = verify(args.root)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report['status'] == 'PASS' else 1)
