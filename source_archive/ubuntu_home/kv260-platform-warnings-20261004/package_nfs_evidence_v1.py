#!/usr/bin/env python3
"""Freeze and re-read the NFS runtime evidence without altering earlier releases."""
import datetime
import hashlib
import io
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parent
UART_ROOT = Path('/home/ghmd/kv260-dfx-state-boardtest-20261004')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    pointer = json.loads((ROOT / 'CURRENT_NFS_REVIEW.json').read_text())
    review_path = Path(pointer['review'])
    review = json.loads(review_path.read_text())
    if not pointer['passed'] or not review['passed'] or review['mode'] != 'warm':
        raise RuntimeError('A passed independent warm review is required')
    files = {}

    def add(name, path):
        path = Path(path)
        if name in files or path.is_symlink() or not path.is_file():
            raise RuntimeError('Unexpected input: ' + name)
        files[name] = path.read_bytes()

    for name in ['NFS_REPAIR_REPORT.md', 'NFS_REPAIR_STATUS.json', 'WARNING_REPAIR_PLAN.md',
                 'DIAGNOSIS_STATUS.json', 'NFS_WARM_EXPORT.json', 'HOST_REVIEW_COMPATIBILITY.json',
                 'review_nfs_evidence.py', 'package_nfs_evidence.py']:
        add('reports/' + name, ROOT / name)
    for p in sorted((ROOT / 'reviews').glob('*/review.json')):
        add('host-reviews/' + p.parent.name + '/review.json', p)
    for p in sorted(Path(review['extracted']).rglob('*')):
        if p.is_file():
            add('board/' + p.relative_to(review['extracted']).as_posix(), p)
    add('raw/nfs-warm-evidence.tar.gz', review['archive'])
    if digest(files['raw/nfs-warm-evidence.tar.gz']) != review['archive_sha256']:
        raise RuntimeError('Returned board archive changed')
    for p in sorted((UART_ROOT / 'manifests').glob('*.json')):
        if 24 <= int(p.name.split('-', 1)[0]) <= 35:
            add('uart/manifests/' + p.name, p)
    for folder in sorted((UART_ROOT / 'evidence').iterdir()):
        manifest = folder / 'manifest.json'
        if not manifest.is_file():
            continue
        status = json.loads((folder / 'status.json').read_text())
        original = Path(status['manifest']).name
        if 24 <= int(original.split('-', 1)[0]) <= 35:
            for p in sorted(folder.rglob('*')):
                if p.is_file():
                    add('uart/evidence/' + folder.name + '/' + p.relative_to(folder).as_posix(), p)
    add('tools/uart_phase.py', UART_ROOT / 'scripts/uart_phase.py')
    add('tools/watch_coldboot.py', UART_ROOT / 'scripts/watch_coldboot.py')
    add('tools/validate_v5.py', UART_ROOT / 'board/validate.py')
    add('project/2026-10-04-NFS-STARTUP-REPAIR.md',
        '/home/ghmd/AMD_Smart/logs/daily/2026-10-04-NFS-STARTUP-REPAIR.md')
    add('project/PROJECT_BOOK_INDEX.md', '/home/ghmd/AMD_Smart/PROJECT_BOOK_INDEX.md')
    manifest = {name: {'bytes': len(data), 'sha256': digest(data)} for name, data in sorted(files.items())}
    files['PACKAGED_INPUTS.json'] = (json.dumps(manifest, indent=2, ensure_ascii=False) + '\n').encode()
    release = ROOT / 'release'
    release.mkdir(exist_ok=True)
    target = release / 'nfs-startup-repair-20261004-warm-verified.tar.gz'
    with tarfile.open(target, 'x:gz') as tar:
        for name, data in sorted(files.items()):
            member = tarfile.TarInfo(name)
            member.size = len(data)
            member.mode = 0o644
            tar.addfile(member, io.BytesIO(data))
    with tarfile.open(target) as tar:
        members = tar.getmembers()
        if len(members) != len(files) or len({m.name for m in members}) != len(files):
            raise RuntimeError('Archive member mismatch')
        for member in members:
            if not member.isfile() or tar.extractfile(member).read() != files[member.name]:
                raise RuntimeError('Archive re-read mismatch: ' + member.name)
    result = {'recorded_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'archive': str(target), 'bytes': target.stat().st_size,
              'sha256': digest(target.read_bytes()), 'members': len(files),
              'verified_input_files': len(manifest), 'archive_reread_passed': True,
              'warm_board_verified': True, 'nfs_cold_boot_verified': False,
              'review': str(review_path), 'purpose': 'Evidence snapshot; scripts retain their original board/workspace paths.'}
    (ROOT / 'NFS_RELEASE.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
