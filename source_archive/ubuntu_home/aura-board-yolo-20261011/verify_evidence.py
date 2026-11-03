#!/usr/bin/env python3
"""Read-only independent verification of saved board responses and release bytes."""
import base64
import hashlib
import json
from pathlib import Path
import zipfile

WORK = Path(__file__).resolve().parent
REPO = Path('/home/ghmd/Win共享文件/共享文件夹/aura')


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def load(path):
    return json.loads(path.read_text())


def main():
    responses = []
    failures = []
    artifacts = []
    sessions = list(sorted((WORK / 'evidence').glob('*/result.json')))
    for result_path in sessions:
        folder = result_path.parent
        result = load(result_path)
        assert result['console_echo_restored'] is True, folder.name
        commands = result.get('commands')
        entries = commands if commands is not None else [dict(result, label='response')]
        for entry in entries:
            output = folder / (entry['label'] + '.output')
            blob = output.read_bytes()
            assert len(blob) == entry['bytes'] and sha(blob) == entry['sha256'], output
            responses.append(str(output.relative_to(WORK)))
            if entry['exit_code']:
                assert folder.name == '20261011T112536.689176Z-probe'
                assert entry['exit_code'] == 1 and result['complete'] is False
                assert b'collect2: error: ld returned 1 exit status' in blob
                failures.append({'session': folder.name, 'exit_code': 1,
                                 'resolved_by': 'Link with -lvitis_ai_library-dpu_task; later probe PASS'})
                continue
            if not blob.strip():
                continue
            value = json.loads(blob)
            for name, artifact in value.get('artifacts', {}).items():
                data = base64.b64decode(artifact['base64'], validate=True)
                assert len(data) == artifact['bytes'] and sha(data) == artifact['sha256']
                assert (folder / name).read_bytes() == data
                artifacts.append(str((folder / name).relative_to(WORK)))
            for name in ('screenshot', 'main_screenshot'):
                artifact = value.get(name)
                if artifact and 'jpeg_base64' in artifact:
                    data = base64.b64decode(artifact['jpeg_base64'], validate=True)
                    assert len(data) == artifact['bytes'] and sha(data) == artifact['sha256']
                    assert (folder / (name + '.jpg')).read_bytes() == data
                    artifacts.append(str((folder / (name + '.jpg')).relative_to(WORK)))
        if not any(entry['exit_code'] for entry in entries):
            assert result['complete'] is True
        if result.get('command_set_sha256'):
            text = '\n'.join((folder / (entry['label'] + '.command')).read_text()[:-1] for entry in entries)
            assert sha(text.encode()) == result['command_set_sha256']
    assert len(failures) == 1
    meta = load(WORK / 'package_validation.json')
    manifest = load(WORK / 'manifest.json')
    archive_path = Path(meta['archive'])
    archive_blob = archive_path.read_bytes()
    assert len(archive_blob) == meta['bytes'] and sha(archive_blob) == meta['sha256']
    assert (REPO / 'artifacts/releases' / archive_path.name).read_bytes() == archive_blob
    with zipfile.ZipFile(archive_path) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == set(manifest['files']) | {'manifest.json'}
        assert json.loads(archive.read('manifest.json')) == manifest
        for name, info in manifest['files'].items():
            data = archive.read(name)
            assert len(data) == info['bytes'] and sha(data) == info['sha256'], name
            if name.endswith('.py'):
                compile(data, name, 'exec')
        for name in manifest['runtime_files']:
            assert name.startswith('aura/')
            assert sha((REPO / name[5:]).read_bytes()) == manifest['files'][name]['sha256'], name
    delta_blob = Path(meta['delta_archive']).read_bytes()
    assert len(delta_blob) == meta['delta_bytes'] and sha(delta_blob) == meta['delta_sha256']
    startup = load(REPO / 'scripts/board_ui_startup/release_manifest.json')
    assert startup['release_id'] == meta['startup_release_id']
    for name, info in startup['files'].items():
        data = (REPO / 'scripts/board_ui_startup' / name).read_bytes()
        assert len(data) == info['bytes'] and sha(data) == info['sha256']
        assert info == manifest['files']['startup/' + name]

    deploy = WORK / 'evidence/20261011T115732.399537Z-deploy'
    final = WORK / 'evidence/20261011T120839.771421Z-final'
    status = load(final / 'status.json')
    watch = load(final / 'watch.json')
    host = load(WORK / 'host_validation.json')
    profile = load(deploy / 'profile.json')
    before = load(Path('/home/ghmd/aura-board-ui-design-20261009/evidence/20261011T110156.613986Z-preview-profile/preview-profile.json'))
    controls = load(deploy / 'camera-test.json')
    assert host['status'] == status['status'] == watch['status'] == 'PASS'
    assert host['framework_tests'] == 126 and status['native_tests'] == 68
    assert 'Ran 126 tests' in (WORK / 'host-framework-tests.log').read_text()
    assert status['model_check']['yolo_reference'] == {'reference_people': 4, 'blank_people': 0}
    for name in manifest['runtime_files']:
        assert status['runtime_hashes'][name] == manifest['files'][name]['sha256']
    assert status['camera_owners'] == [status['health']['pid']]
    assert status['saved_settings']['values'] == {'volume': 18, 'muted': False, 'fullscreen': True, 'economy': False}
    assert status['hardware_changed'] is False and status['motion_command_emitted'] is False
    for service in status['services'].values():
        assert 'ActiveState=active' in service and 'SubState=running' in service
        assert 'UnitFileState=enabled' in service and 'NRestarts=0' in service
    assert load(deploy / 'status.json')['protected'] == status['protected']
    assert watch['positive_observed'] and watch['max_people_count'] == 1
    assert (final / 'real-positive.jpg').exists()
    assert watch['positive']['snapshot']['source_kind'] == 'actual'
    assert watch['positive']['snapshot']['modules']['vision']['people_count'] == 1
    assert watch['positive']['snapshot']['modules']['npu']['state'] == 'READY'
    assert watch['positive']['snapshot']['preview'] == watch['positive']['frame_reference']
    for key in ('pid', 'board_boot_id', 'service_epoch', 'camera_epoch'):
        assert watch['before'][key] == watch['after'][key] == status['health'][key]
    for key in ('capture_frames', 'detected_frames', 'preview_frames'):
        assert watch['after'][key] > watch['before'][key]
    assert watch['source_fresh_samples'] == 154
    for row in watch['rows']:
        assert not any(row.get(key) for key in ('camera_error', 'detector_error', 'preview_error'))
    for sample in (before, profile):
        assert len(sample['rows']) == 120
        assert all(row['frame_visible'] and not row['preview_error'] and not row['ui_error'] for row in sample['rows'])
    assert controls['dialog']['width'] == 960 and controls['dialog']['height'] == 550
    assert len(controls['checks_passed']) == 8
    result = {
        'status': 'PASS', 'sessions': len(sessions),
        'response_bodies_verified': len(responses), 'successful_responses': len(responses) - len(failures),
        'known_failed_responses': failures, 'artifacts_verified': artifacts,
        'payload_files': len(manifest['files']), 'runtime_files': len(manifest['runtime_files']),
        'archive_sha256': meta['sha256'], 'startup_release_id': meta['startup_release_id'],
        'host_tests': 126, 'board_software_tests': 68,
        'reference_people': 4, 'blank_people': 0,
        'live_person_positive': True, 'positive_image_visually_inspected': True,
        'live_watch_fresh_samples': 154, 'live_inference_ms': watch['inference_ms'],
        'preview_before_fps': before['preview_display_hz'], 'preview_after_fps': profile['preview_display_hz'],
        'detect_after_hz': profile['detection_hz_measured'], 'blank_preview_samples': 0,
        'source_matches_deployed_runtime': True, 'startup_sources_match_release': True,
        'services_active_enabled': True, 'protected_hashes_unchanged': True,
        'settings_preserved': True, 'full_asset_archive_rebuilt': False,
        'limits': ['Short sampling only; no physical panel latency measurement',
                   'No new full-board cold-boot acceptance', 'No multi-person/occlusion accuracy acceptance',
                   'ByteTrack and identity not integrated', 'Unified runtime configuration still incomplete'],
        'responses': responses,
    }
    (WORK / 'validation_final.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({key: value for key, value in result.items() if key != 'responses'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
