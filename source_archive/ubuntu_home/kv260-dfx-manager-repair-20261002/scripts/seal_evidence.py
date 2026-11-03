#!/usr/bin/env python3
"""Seal this independent repair and verify the six previously sealed indexes."""
import datetime
import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = Path('/home/ghmd/kv260-m3-boardtest-20261002')
DAILY = Path('/home/ghmd/AMD_Smart/logs/daily/2026-10-02-DFX.md')


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1048576), b''):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    summary = json.loads((ROOT / 'evidence/validation_summary.json').read_text())
    assert summary['board_verified'] and summary['original_baseline_restored']
    assert summary['successful_board_commands'] == 24
    assert summary['failed_board_commands'] == 1
    assert not summary['permanent_installation']
    outputs = [ROOT / 'EVIDENCE.sha256', ROOT / 'EVIDENCE_VERIFY.json',
               ROOT / 'evidence/seal_manifest.json']
    assert not any(p.exists() for p in outputs), 'No overwrite of a sealed run'
    expected = json.loads((OLD / 'evidence/20261003T021012Z/run.json').read_text())['preserved_indexes']
    expected[str(OLD / 'EVIDENCE.sha256')] = '915fac1f83df1d44b6b5d57f41a9e865822f307f21f893689d4bb8a55500aadd'
    assert len(expected) == 6
    checks = []
    for filename, original_hash in sorted(expected.items()):
        path = Path(filename)
        assert sha(path) == original_hash, 'Preserved index changed: ' + filename
        cwd = path.parent
        if 'kv260-m3-axilite' in filename:
            cwd = Path('/home/ghmd/kv260-m3-axilite-20261002')
        argv = ['sha256sum', '-c', '--quiet', str(path)]
        result = subprocess.run(argv, cwd=cwd, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True)
        checks.append({
            'index': filename, 'sha256': sha(path),
            'entries': len(path.read_text().splitlines()),
            'argv': argv, 'cwd': str(cwd), 'exit_code': result.returncode,
            'stdout': result.stdout, 'stderr': result.stderr
        })
    assert all(c['exit_code'] == 0 for c in checks), 'Preserved evidence check failed'
    release_argv = ['sha256sum', '-c', '--quiet', 'SHA256SUMS']
    release_result = subprocess.run(
        release_argv, cwd=ROOT / 'release/kv260-dfx-watch-reviewed',
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert release_result.returncode == 0
    assert DAILY.is_file()
    paths = [p for p in ROOT.rglob('*') if p.is_file() and not p.is_symlink()
             and '__pycache__' not in p.parts]
    paths.append(DAILY)
    symlinks = [{
        'path': str(p.relative_to(ROOT)), 'target': os.readlink(p),
        'resolved_target': str(p.resolve()),
        'resolved_sha256': sha(p.resolve())
    } for p in ROOT.rglob('*') if p.is_symlink()]
    assert len(symlinks) == 1
    assert symlinks[0]['path'] == 'deps/lib/libdfx.so'
    assert symlinks[0]['target'] == 'libdfx.so.1.0'
    assert symlinks[0]['resolved_sha256'] == '1acb6c9ac1f27e0ea769dc231f32db5565f6ca02a53be00e969fc48c038d290f'
    metadata = {
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'scope': 'All regular files in this independent repair, including source, build records, failed probes, raw UART, artifacts, reports, packages and the additive daily log',
        'excluded': ['__pycache__', 'EVIDENCE.sha256', 'EVIDENCE_VERIFY.json'],
        'symlinks': symlinks, 'symlink_targets_in_regular_file_index': True,
        'preserved_index_checks': checks,
        'release_checksums': {
            'argv': release_argv,
            'cwd': str(ROOT / 'release/kv260-dfx-watch-reviewed'),
            'exit_code': release_result.returncode,
            'stdout': release_result.stdout, 'stderr': release_result.stderr
        },
        'entries_including_this_manifest': len(paths) + 1
    }
    outputs[2].write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n')
    paths.append(outputs[2])
    paths = sorted(paths, key=lambda p: os.path.relpath(p, ROOT))
    outputs[0].write_text(''.join(sha(p) + '  ' + os.path.relpath(p, ROOT) + '\n'
                                for p in paths))
    argv = ['sha256sum', '-c', '--quiet', outputs[0].name]
    result = subprocess.run(argv, cwd=ROOT, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True)
    own = {
        'index': str(outputs[0]), 'sha256': sha(outputs[0]),
        'entries': len(paths), 'argv': argv, 'cwd': str(ROOT),
        'exit_code': result.returncode, 'stdout': result.stdout,
        'stderr': result.stderr
    }
    verification = {
        'verified_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'passed': result.returncode == 0,
        'preserved_input_checks': checks, 'new_index_check': own
    }
    outputs[1].write_text(json.dumps(verification, ensure_ascii=False, indent=2) + '\n')
    assert verification['passed']
    print(json.dumps({
        'passed': True, 'preserved_indexes_verified': len(checks),
        'preserved_entries_verified': sum(c['entries'] for c in checks),
        'new_entries_verified': len(paths), 'index_sha256': sha(outputs[0])
    }))


if __name__ == '__main__':
    main()
