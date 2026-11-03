"""Bundle only identity/UI sources and existing face models; no user data."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

SHARE = Path('/home/ghmd/Win共享文件')
MAIN = SHARE/'共享文件夹/aura'
VOICE = SHARE/'语音共享文件/aura'
JOB = Path(__file__).parent
TASK = SHARE/'协作任务/2026-10-18_双机联调'
EVIDENCE = TASK/'evidence/ubuntu/identity-ui-20261018'
CHANGED = ['board/identity/store.py', 'board/identity/live.py', 'board/identity/camera_faces.py',
    'board/vision/ui_camera_service.py', 'board/interaction/ui_contract.py', 'tools/board_avatar_gtk.py',
    'tools/check_board_identity.py', 'tools/package_board_avatar.py', 'config/board_camera_ui.json',
    'config/board_identity.json', 'tests/framework/test_camera_identity.py', 'docs/BOARD_IDENTITY.md']
DEPENDENCIES = ['board/identity/__init__.py', 'board/vision/reference_faces.py', 'common/contracts.py',
                'models/vision/yunet_2022mar.onnx', 'models/vision/sface_2021dec.onnx']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    rows = []
    for rel in CHANGED+DEPENDENCIES:
        source, mirror = MAIN/rel, VOICE/rel
        assert source.read_bytes() == mirror.read_bytes(), 'Mirror changed: '+rel
        item = {'path': 'aura/'+rel, 'bytes': source.stat().st_size, 'sha256': sha(source)}
        previous = JOB/'before/共享文件夹'/rel
        item['previous_source_sha256'] = sha(previous) if previous.exists() else None
        rows.append(item)
    protected = {}
    for rel in ['tools/board_model_host.py', 'tools/dialogue_host_ollama.py', 'tools/gstreamer_audio_engine.py']:
        protected[rel] = {'legacy_sha256': sha(MAIN/rel), 'voice_sha256': sha(VOICE/rel)}
    manifest = {'status': 'HOST_VERIFIED_CANDIDATE_NOT_BOARD_DEPLOYED', 'created_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'Source overlay only. Compare board sources/config/startup manifest before applying; do not overwrite active release blindly.',
        'changed_paths': CHANGED, 'files': rows, 'protected_voice_files': protected,
        'board_verified': False, 'accuracy_calibrated': False, 'database_included': False,
        'llm_weights_included': False, 'user_recordings_or_embeddings_included': False,
        'tests': {'legacy_framework': 220, 'voice_framework': 224, 'real_static_model_checks': 13,
                  'native_identity_fixture_checks': 10, 'layout_pages': 9}}
    identity = hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()[:16]
    target = TASK/('identity-ui-candidate-'+identity+'.zip')
    assert not target.exists(), 'Existing candidate must not be overwritten'
    with zipfile.ZipFile(target, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for item in rows:
            archive.write(SHARE/'共享文件夹'/item['path'], item['path'])
        archive.writestr('IDENTITY_CANDIDATE.json', json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    with zipfile.ZipFile(target) as archive:
        assert len(archive.infolist()) == len(rows)+1
        for item in rows:
            data = archive.read(item['path'])
            assert len(data) == item['bytes'] and hashlib.sha256(data).hexdigest() == item['sha256']
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    copies = [
        (JOB/'framework-tests-host.log', 'framework-main.log'),
        (JOB/'framework-tests-voice-root.log', 'framework-voice.log'),
        (JOB/'framework-tests.log', 'framework-sandbox-first-attempt.log'),
        (JOB/'real-model-check.json', 'real-model-check.json'),
        (JOB/'native-dialog-tests.log', 'native-dialog-tests.log'),
        (JOB/'native-dialog-diagnosis.log', 'native-dialog-first-failure.log'),
        (JOB/'preview_identity_acceptance.py', 'native_fixture_check.py'),
        (JOB/'ui-preview/validation.json', 'layout-validation.json'),
        (JOB/'identity-ui/validation.json', 'native-identity-validation.json'),
        (JOB/'identity-ui/unknown.png', 'unknown.png'),
        (JOB/'identity-ui/known.png', 'known.png'),
        (JOB/'identity-ui/deleted_unknown.png', 'deleted-unknown.png')]
    for source, name in copies:
        shutil.copyfile(source, EVIDENCE/name)
        assert sha(source) == sha(EVIDENCE/name)
    summary = dict(manifest, candidate_file=target.name, candidate_bytes=target.stat().st_size,
                   candidate_sha256=sha(target), archive_entries_verified=len(rows),
                   mirrored_source_files_verified=len(CHANGED), evidence_copies_verified=len(copies))
    (EVIDENCE/'verification.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k: summary[k] for k in ['status', 'candidate_file', 'candidate_bytes', 'candidate_sha256',
        'archive_entries_verified', 'mirrored_source_files_verified', 'evidence_copies_verified']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
