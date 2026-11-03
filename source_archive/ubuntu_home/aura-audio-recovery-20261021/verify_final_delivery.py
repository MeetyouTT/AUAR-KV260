"""Verify packaging and provenance; does not execute inference or production code."""
import ast
import csv
import hashlib
import json
import re
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote

BASE = Path('/home/ghmd/Win共享文件/语音共享文件/deliverables')
LIVE = BASE / '2026-10-21_dpu_live_baseline'
INITIAL = BASE / '2026-10-21_dpu_vision_start'
INVENTORY = BASE / '2026-10-21_model_inventory'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_manifest(path):
    count = 0
    for line in path.read_text().splitlines():
        expected, relative = line.split('  ', 1)
        target = path.parent / relative
        assert target.is_file() and digest(target) == expected, str(target)
        count += 1
    return count


def main():
    release = json.loads((LIVE / 'release.json').read_text())
    pilot = json.loads((LIVE / release['evidence']['sface_shadow_real_face']).read_text())
    audit = json.loads((LIVE / release['evidence']['final_audit']).read_text())
    assert release['sface']['shadow_board_verified'] and not release['sface']['shadow_production_enabled']
    assert not release['sface']['field_threshold_validated'] and not release['sface']['new_database_created']
    assert pilot['passed'] and pilot['complete'] and pilot['rollback_verified']
    assert release['runtime']['camera_pid'] == audit['pid'] == pilot['restored']['pid']
    assert audit['source_hashes'] == release['yunet']['candidate_source_sha256']
    assert audit['model_sha256'] == release['yunet']['model_sha256']
    assert audit['manifest_sha256'] == release['yunet']['compiler_manifest_sha256']
    assert audit['sface_shadow_absent'] and not audit['active_owned_rollback_timers']
    for relative in release['evidence'].values():
        assert (LIVE / relative).is_file(), relative
    for name, tests in [('sface-candidate', 21), ('sface-shadow-candidate', 16)]:
        assert 'Ran %d tests' % tests in (LIVE / name / 'test-results.txt').read_text()
        assert (LIVE / name / 'test-results.txt').read_text().rstrip().endswith('OK')
    assert 'Ran 3 tests' in (LIVE / 'sface-shadow-candidate/deploy-preparation/local-test-results.txt').read_text()
    frozen = {}
    for name in ['sface-candidate/FILES.sha256', 'sface-shadow-candidate/FILES.sha256',
                 'sface-shadow-candidate/deploy-preparation/FILES.sha256']:
        frozen[name] = verify_manifest(LIVE / name)

    archive = LIVE / 'source/sface-shadow-deploy-patch.tar.gz'
    assert digest(archive) == pilot['patch_sha256']
    with tarfile.open(archive) as tf:
        members = tf.getmembers()
        assert len(members) == 7
        for item in members:
            assert item.isfile() and '..' not in Path(item.name).parts and not item.name.startswith('/')
            assert item.name.endswith(('.py', '.json'))
    syntax = 0
    jsons = 0
    links = 0
    for root in [LIVE, INITIAL, INVENTORY]:
        for path in root.rglob('*'):
            assert not path.is_symlink(), str(path)
            if not path.is_file():
                continue
            assert '__pycache__' not in path.parts
            assert path.suffix.lower() not in {'.png','.jpg','.jpeg','.webp','.wav','.flac','.mp3','.mp4','.npy','.npz','.db','.sqlite','.sqlite3','.raw'}
            if path.suffix == '.py':
                ast.parse(path.read_text(), filename=str(path))
                syntax += 1
            elif path.suffix == '.json':
                json.loads(path.read_text())
                jsons += 1
            elif path.suffix == '.md':
                for target in re.findall(r'\]\(([^)]+)\)', path.read_text()):
                    if target.startswith(('http:', 'https:', '#')):
                        continue
                    target = unquote(target.strip('<>').split('#', 1)[0])
                    if target == 'evidence/final-delivery-validation.json':
                        continue
                    assert (path.parent / target).exists(), (path, target)
                    links += 1
    matrix = INVENTORY / '板端协同_实验矩阵.csv'
    with matrix.open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 6 and all(None not in row for row in rows)
    result = {
        'verified_utc': datetime.now(timezone.utc).isoformat(),
        'status': 'PASS', 'scope': 'Packaging, frozen file hashes, numeric evidence consistency, syntax and local links; not new model tests or Windows sync acceptance',
        'frozen_manifest_entries_verified': frozen,
        'python_files_ast_parsed': syntax,
        'json_files_parsed_before_report': jsons,
        'local_markdown_links_checked': links,
        'experiment_rows': len(rows),
        'real_face_pilot_and_rollback_evidence_consistent': True,
        'archive_sha_and_only_six_python_sources_plus_manifest_verified': True,
        'blocked_media_array_database_raw_uart_extensions_absent': True,
        'production_sface_identity_migrated': False,
        'windows_sync_confirmed': False,
    }
    (LIVE / 'evidence/final-delivery-validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    manifests = {}
    for root in [LIVE, INITIAL]:
        manifest = root / 'FILES.sha256'
        paths = sorted(p for p in root.rglob('*') if p.is_file() and p != manifest)
        manifest.write_text(''.join(digest(p) + '  ' + str(p.relative_to(root)) + '\n' for p in paths))
        manifests[root.name] = verify_manifest(manifest)
    print(json.dumps({'validation': result, 'parent_manifest_entries_verified': manifests}, ensure_ascii=False))


if __name__ == '__main__':
    main()
