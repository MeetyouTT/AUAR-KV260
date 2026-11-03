#!/usr/bin/env python3
"""Freeze this completed board acceptance, with independent archive read-back."""
import datetime
import hashlib
import io
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[1]
NATIVE = Path('/home/ghmd/kv260-dfx-state-validation-20261003/release')
NEW_SHA = '369c7fb0ddd023a7cf7af14896a7fda6036219a36f4980c73640889720c95dfd'
NATIVE_SHA = 'b6d8ab335041dc7f42e13e167c07c8d00e44d4469ae5278db8013b02e18d7a42'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    current = json.loads((ROOT / 'CURRENT_REVIEW.json').read_text())
    review_path = Path(current['review'])
    review = json.loads(review_path.read_text())
    assert current['passed'] and review['passed'] and review['mode'] == 'postboot'
    assert review['installed'] and review['cold_boot_verified']
    assert review['candidate_sha256'] == NEW_SHA
    assert digest((ROOT / 'scripts/review_board_evidence.py').read_bytes()) == review['reviewer_sha256']
    cold = json.loads((review_path.parent / 'COLD_BOOT_VERIFICATION.json').read_text())
    assert cold['passed']
    for name, expected in cold['host_proof_sha256'].items():
        assert digest((ROOT / name).read_bytes()) == expected
    assert json.loads((ROOT / 'SEALED_INPUTS_REVIEW.json').read_text())['passed']
    final = json.loads((ROOT / 'FINAL_STATUS.json').read_text())
    assert final['complete'] and final['cold_boot_verified'] and final['boot_id'] == review['boot_id']

    native = NATIVE / 'dfx-state-20261004-host-verified.tar.gz'
    native_bytes = native.read_bytes()
    assert digest(native_bytes) == NATIVE_SHA
    binary = (NATIVE / 'dfx-state-20261004-host-verified/bin/dfx-mgrd').read_bytes()
    assert len(binary) == 117856 and digest(binary) == NEW_SHA
    archive_path = Path(review['archive'])
    metadata = json.loads((ROOT / 'POSTBOOT_EXPORT_METADATA.json').read_text())
    assert digest(archive_path.read_bytes()) == metadata['sha256']

    payload = {}
    for path in sorted(ROOT.rglob('*')):
        relative = path.relative_to(ROOT)
        if not path.is_file() or path.is_symlink() or relative.parts[0] == 'release':
            continue
        if '__pycache__' in relative.parts or (relative.parts[0] == 'reviews' and 'board' in relative.parts):
            continue
        payload[relative.as_posix()] = path.read_bytes()
    payload['inputs/dfx-state-20261004-host-verified.tar.gz'] = native_bytes
    payload['bin/dfx-mgrd'] = binary
    install = json.loads((Path(review['extracted']) / 'persistent-install.json').read_text())
    config = install['content'].encode()
    assert digest(config) == review['persistent_dropin_sha256']
    payload['config/20-kv260-dfx-state-repaired.conf'] = config
    manifest = {
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'board_verified': True, 'installed': True, 'cold_boot_verified': True,
        'candidate_sha256': NEW_SHA, 'boot_id': review['boot_id'],
        'native_archive_sha256': NATIVE_SHA, 'board_export_sha256': metadata['sha256'],
        'review': review_path.relative_to(ROOT).as_posix(),
        'files': {name: {'bytes': len(data), 'sha256': digest(data)} for name, data in payload.items()},
        'limits': ['One user-confirmed physical power cycle; off duration not instrumented.',
                   'No real PL_DFX partial reconfiguration or hardware failure injection.',
                   'Existing NFS, TPM, clock and overlay warnings remain. TSan not run.']}
    payload['PACKAGE_MANIFEST.json'] = (json.dumps(manifest, indent=2, ensure_ascii=False) + '\n').encode()
    release = ROOT / 'release'
    release.mkdir(exist_ok=True)
    target = release / 'dfx-state-20261004-board-verified.tar.gz'
    with tarfile.open(target, 'x:gz') as tar:
        for name, data in sorted(payload.items()):
            item = tarfile.TarInfo(name)
            item.size = len(data)
            item.mode = 0o755 if name == 'bin/dfx-mgrd' else 0o644
            item.mtime = 0
            tar.addfile(item, io.BytesIO(data))
    with tarfile.open(target) as tar:
        members = tar.getmembers()
        assert len(members) == len(payload)
        assert len({m.name for m in members}) == len(members)
        assert all(m.isfile() and m.name in payload for m in members)
        for member in members:
            actual = tar.extractfile(member).read()
            assert len(actual) == len(payload[member.name]) and digest(actual) == digest(payload[member.name])
    verification = {
        'passed': True, 'archive': str(target), 'bytes': target.stat().st_size,
        'sha256': digest(target.read_bytes()), 'verified_members': len(members),
        'board_verified': True, 'installed': True, 'cold_boot_verified': True,
        'candidate_sha256': NEW_SHA, 'boot_id': review['boot_id'],
        'board_export_files': review['verified_exported_files'], 'classifications': review['classification_count'],
        'manifest_sha256': digest(payload['PACKAGE_MANIFEST.json'])}
    with (release / 'PACKAGE_VERIFICATION.json').open('x') as f:
        json.dump(verification, f, indent=2, ensure_ascii=False)
        f.write('\n')
    with (release / (target.name + '.sha256')).open('x') as f:
        f.write(verification['sha256'] + '  ' + target.name + '\n')
    print(json.dumps(verification, ensure_ascii=False))


if __name__ == '__main__':
    main()
