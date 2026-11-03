#!/usr/bin/env python3
"""Audit real-board startup/restart records, including preserved failures."""
import datetime
import base64
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    manifest = json.loads((ROOT/'release_manifest.json').read_text())
    records = []
    responses = 0
    for file in sorted((ROOT/'evidence').glob('*/status.json')):
        status = json.loads(file.read_text())
        for command in status['commands']:
            data = (file.parent/command['output']).read_bytes()
            assert len(data) == command['bytes']
            assert hashlib.sha256(data).hexdigest() == command['sha256']
            if command['exit_code'] == 0:
                decoded = json.loads(data)
                saved = file.parent/Path(command['output']).with_suffix('.json')
                assert decoded == json.loads(saved.read_text())
            responses += 1
        assert status['console_echo_restored']
        if status['complete']:
            records.append((file.parent, status, json.loads((file.parent/'result.json').read_text())))

    def latest(phase, current=True):
        matches = [r for r in records if r[1]['phase'] == phase and
                   (not current or r[1]['release_id'] == manifest['release_id'])]
        return matches[-1]

    stage_path, unused, staged = latest('stage')
    assert staged['files'] == manifest['files']
    unused, unused, installed = latest('install', False)
    unused, unused, replaced = latest('replace')
    restart_path, unused, restart = latest('restart')
    final_path, unused, final = latest('status')
    service = dict(line.split('=', 1) for line in final['service'].splitlines())
    assert service['ActiveState'] == 'active' and service['SubState'] == 'running'
    assert service['Result'] == 'success' and service['ExecMainStatus'] == '0'
    assert service['NRestarts'] == '0' and service['UnitFileState'] == 'enabled'
    assert service['ControlGroup'] == '/system.slice/aura-avatar-ui.service'
    launch = final['launch']
    before = restart['before']
    assert service['MainPID'] == str(launch['supervisor_pid'])
    assert launch['pid'] != before['launch']['pid']
    assert launch['supervisor_pid'] != before['launch']['supervisor_pid']
    assert launch['session'] != before['launch']['session']
    assert launch['boot_id'] == final['boot_id'] == before['launch']['boot_id'] == installed['before']['boot_id']
    for name in ('Xorg', 'dfx-mgrd', 'realtime_vision.py'):
        assert final['processes'].get(name, []) == installed['before']['processes'].get(name, [])
    assert final['protected'] == before['protected'] == replaced['before']['protected'] == installed['before']['protected']
    gui = final['processes']['board_avatar_gtk.py']
    workers = final['processes']['gstreamer_audio_worker.py']
    assert len(gui) == len(workers) == 1
    assert gui[0]['pid'] == launch['pid'] and gui[0]['ppid'] == launch['supervisor_pid']
    assert workers[0]['ppid'] == launch['pid']
    assert final['unit_sha256'] == manifest['files']['aura-avatar-ui.service']['sha256']
    config = json.loads((ROOT/'config.json').read_text())
    assert final['module_sha256'] == config['touch_module_sha256']
    assert config['output']+' connected primary '+config['mode']+'+0+0' in final['checks']['display']
    assert 'Touch mode: direct' in final['checks']['touch']
    assert final['checks']['enabled'] == 'enabled'
    state = final['state']
    assert state['backend'] == 'gtk3-gstreamer' and state['cached_only']
    assert not state['error'] and state['touch_devices']
    mix = state['ui_settings']
    assert mix['available'] and not mix['pending'] and not mix['error']
    assert final['saved_settings'] == before['saved_settings']
    for name, value in final['saved_settings']['values'].items():
        assert mix[name] == value
    extra = {}
    touch = Path('/home/ghmd/aura-waveshare-touch-20261009/evidence')
    for phase in ('settings-page', 'report', 'window'):
        file = sorted(touch.glob('*-'+phase+'/status.json'))[-1]
        status = json.loads(file.read_text())
        assert status['complete'] and status['exit_code'] == 0 and status['console_echo_restored']
        data = (file.parent/'response.output').read_bytes()
        assert len(data) == status['bytes'] and hashlib.sha256(data).hexdigest() == status['sha256']
        decoded = json.loads(data)
        if phase == 'window':
            image = base64.b64decode(decoded.pop('jpeg_base64'), validate=True)
            assert hashlib.sha256(image).hexdigest() == decoded['sha256']
            assert image == (file.parent/'board-window.jpg').read_bytes()
            assert decoded['source'].startswith(launch['evidence']+'/window_')
        assert decoded == json.loads((file.parent/'result.json').read_text())
        extra[phase] = decoded
        responses += 1
    assert extra['report']['record']['report'].startswith(launch['evidence']+'/stage_')
    assert extra['report']['source_hashes_at_launch']['tools/board_avatar_gtk.py'] == config['gui_sha256']
    assert not extra['report']['errors']
    result = {
        'verified_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'release_id': manifest['release_id'], 'response_integrity_verified': responses,
        'stage_evidence': str(stage_path), 'restart_evidence': str(restart_path),
        'final_evidence': str(final_path), 'boot_id': final['boot_id'],
        'service_enabled_verified': True, 'actual_service_ready_verified': True,
        'rapid_managed_restart_verified': True, 'single_gui_and_audio_worker_verified': True,
        'settings_preserved_verified': True, 'saved_settings': final['saved_settings']['values'],
        'display_and_touch_detected_verified': True, 'protected_files_and_processes_preserved': True,
        'gui_pid': launch['pid'], 'supervisor_pid': launch['supervisor_pid'],
        'gui_source_pin_verified': True, 'window_source': extra['window']['source'],
        'next_boot_verified': False, 'physical_touch_retested_after_restart': False,
        'runtime_crash_recovery_tested': False,
    }
    (ROOT/'startup_validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
