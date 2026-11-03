#!/usr/bin/env python3
"""Seal additive board evidence, preserving the earlier 177-entry index."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()


def main():
    root = Path(__file__).resolve().parents[1]
    run = Path(sys.argv[1]).resolve()
    index = root / 'BOARD_EVIDENCE.sha256'
    metadata = run / 'board_seal_manifest.json'
    verification = root / 'BOARD_EVIDENCE_VERIFY.json'
    assert not any(path.exists() for path in [index, metadata, verification]), 'Refusing to overwrite sealed evidence'
    original_index = root / 'EVIDENCE.sha256'
    original_lines = original_index.read_text().splitlines()
    sealed = {line.split('  ', 1)[1] for line in original_lines}
    assert len(sealed) == 177
    assert sha(original_index) == json.loads((run / 'run.json').read_text())['sealed_index_sha256']
    summary = json.loads((run / 'board_validation_summary.json').read_text())
    audit = json.loads((run / 'preflight_and_diagnostics_review.json').read_text())
    assert summary['board_verified'] and audit['passed']

    selected = {root / 'BOARD_REPAIR_REPORT.md', root / 'CURRENT_STATUS.md',
                Path('/home/ghmd/AMD_Smart/logs/daily/2026-10-02.md')}
    selected.update(path for path in run.rglob('*') if path.is_file())
    selected.update(path for path in (root / 'evidence/board_preflight').rglob('*') if path.is_file())
    selected.update((root / 'evidence').glob('host-connection-20261003*.json'))
    selected.update((root / 'scripts').glob('*.py'))
    selected = {path for path in selected if os.path.relpath(str(path), str(root)) not in sealed}
    for path in selected:
        assert path.is_file() and not path.is_symlink(), 'Unexpected evidence path: ' + str(path)
    relative = sorted(os.path.relpath(str(path), str(root)) for path in selected)
    metadata.write_text(json.dumps({
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'original_index': 'EVIDENCE.sha256', 'original_index_sha256': sha(original_index),
        'original_index_entries': 177,
        'supplement_index': index.name, 'supplement_entries': len(selected) + 1,
        'scope': 'Captured board run, new preflight outputs, connection evidence, additive scripts/reports and daily log',
        'files_excluding_this_manifest': relative,
        'verification_record': verification.name,
        'note': 'The index does not include itself or the verification record generated after checking it.'
    }, indent=2, ensure_ascii=False) + '\n')
    selected.add(metadata)
    ordered = sorted(selected, key=lambda path: os.path.relpath(str(path), str(root)))
    index.write_text(''.join(sha(path) + '  ' + os.path.relpath(str(path), str(root)) + '\n' for path in ordered))

    checks = []
    for checked_index in [original_index, index]:
        command = ['sha256sum', '-c', '--quiet', checked_index.name]
        result = subprocess.run(command, cwd=str(root), stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True)
        checks.append({'argv': command, 'cwd': str(root), 'exit_code': result.returncode,
                       'stdout': result.stdout, 'stderr': result.stderr,
                       'index_sha256': sha(checked_index),
                       'entries': len(checked_index.read_text().splitlines())})
    record = {'verified_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'passed': all(check['exit_code'] == 0 for check in checks), 'checks': checks}
    verification.write_text(json.dumps(record, indent=2, ensure_ascii=False) + '\n')
    assert record['passed'], 'Checksum verification failed; see ' + str(verification)
    print(json.dumps({'passed': True, 'original_entries': 177, 'supplement_entries': len(ordered),
                      'supplement_sha256': sha(index), 'verification': str(verification)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
