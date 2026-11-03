"""Read current project evidence; optionally run existing host framework tests."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path('/home/ghmd/Win共享文件/共享文件夹/aura')
OUT = ROOT / 'report/project_status_20261017'
PYTHON = '/home/ghmd/aura-board-tracking-20261011/host-env/bin/python'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(relative):
    return json.loads((ROOT / relative).read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tests', action='store_true')
    parser.add_argument('--label', default='host')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    runtime = read('config/runtime.kv260.json')
    datasets = {name: read('data/' + name + '_manifest.json')
                for name in ('calibration', 'test')}
    rtl = (ROOT / 'hardware/rtl/visual_servo.sv').read_text()
    scheduler = (ROOT / 'board/fusion/scheduler.py').read_text()
    conflicts = []
    for path in sorted(ROOT.rglob('*sync-conflict*')):
        if not path.is_file() or any(part in ('.venv', '__pycache__') for part in path.parts):
            continue
        base = path.with_name(path.name.split('.sync-conflict-')[0] + path.suffix)
        conflicts.append({'path': str(path.relative_to(ROOT)),
                          'active_path': str(base.relative_to(ROOT)),
                          'active_exists': base.is_file(),
                          'identical': base.is_file() and path.read_bytes() == base.read_bytes(),
                          'sha256': digest(path),
                          'active_sha256': digest(base) if base.is_file() else None})
    result = {
        'checked_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'scope': 'local source/configuration and saved evidence; no new board/Windows operation',
        'runtime_release': runtime['release_id'],
        'unified_runtime': {
            'identity_backend': runtime['identity']['backend'],
            'dialogue_backend': runtime['dialogue']['backend'],
            'motion_backend': runtime['motion']['backend'],
            'motion_physical_actuation': runtime['motion']['physical_actuation'],
            'detector_model_exists': (ROOT / runtime['vision']['model']).is_file(),
            'detector_sha256_configured': bool(runtime['vision']['model_sha256']),
            'detector_fingerprint_configured': bool(runtime['vision']['arch_fingerprint']),
            'detector_entrypoint_configured': bool(runtime['vision']['entrypoint']),
            'freshness_calibrated': runtime['freshness']['calibration']['verified'],
            'cost_estimate_origin': runtime['scheduler']['estimate_origin'],
            'note': 'Independent deployed YOLO/ByteTrack/UI/ASR packages must be evaluated separately.'
        },
        'datasets': {name: {'status': data['status'], 'items': len(data['items']),
                            'annotations': len(data['annotations'])}
                     for name, data in datasets.items()},
        'mechanical_calibration': read('config/servo_calibration.json'),
        'experiments': {'status': read('config/experiments.json')['status'],
                        'groups': [x['id'] for x in read('config/experiments.json')['groups']]},
        'rtl_relative_lease_on_commit': 'lease_left<=sh_lease[8:0]' in rtl,
        'software_scheduler_detection_identity_only':
            '{"detection": deque(maxlen=128), "identity": deque(maxlen=128)}' in scheduler,
        'submission_marked_not_final': 'FRAMEWORK_NOT_FINAL_COMPETITION_RELEASE' in
            (ROOT / 'submission/aura_junior/README.md').read_text(),
        'skill_files': [str(p.relative_to(ROOT)) for p in
                        sorted((ROOT / 'submission/aura_junior/skill').rglob('*')) if p.is_file()],
        'sync_conflicts': conflicts,
        'saved_evidence': {},
        'current_source_hashes': {},
    }
    evidence = {
        'asr_deployment': '/home/ghmd/aura-asr-integration-20261016/validation.json',
        'camera_hotplug': '/home/ghmd/aura-camera-hotplug-20261017/validation.json',
        'sync': '/home/ghmd/aura-sync-inventory-20261017/verysync-status/validation.json',
        'source_inventory': '/home/ghmd/aura-sync-inventory-20261017/inventory.json',
        'real_tracking': '/home/ghmd/aura-board-tracking-20261011/continuation_validation.json',
        'ui_layers': '/home/ghmd/aura-ui-layers-board-20261016/validation.json',
    }
    for name, filename in evidence.items():
        path = Path(filename)
        data = json.loads(path.read_text())
        item = {'path': filename, 'sha256': digest(path),
                'status': data.get('status', data.get('result'))}
        if name == 'asr_deployment':
            for key in ('update_id', 'host_framework_tests', 'board_related_tests',
                        'live_board_asr_and_lan_verified', 'asr_target_ready_verified'):
                item[key] = data[key]
        result['saved_evidence'][name] = item
    for rel in [
        'config/runtime.kv260.json', 'config/model_manifest.json', 'config/experiments.json',
        'data/calibration_manifest.json', 'data/test_manifest.json', 'config/servo_calibration.json',
        'hardware/rtl/visual_servo.sv', 'board/fusion/scheduler.py',
        'board/identity/backends.py', 'board/identity/store.py',
        'board/vision/ui_camera_service.py', 'tools/asr_server.py',
        'board/runtime/audio/transcription.py', 'tools/board_recording.py',
        'tools/board_avatar_gtk.py', 'docs/FRAMEWORK_STATUS.md',
        'submission/aura_junior/README.md',
    ]:
        result['current_source_hashes'][rel] = digest(ROOT / rel)
    if args.tests:
        command = [PYTHON, '-B', '-s', '-m', 'unittest', 'discover', '-s', 'tests/framework', '-v']
        process = subprocess.run(command, cwd=str(ROOT), stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, text=True, timeout=120)
        log = OUT / ('framework_tests_' + args.label + '.log')
        log.write_text(process.stdout)
        match = re.search(r'Ran (\d+) tests? in ([0-9.]+)s', process.stdout)
        result['host_framework_tests_this_audit'] = {
            'command': command, 'cwd': str(ROOT), 'exit_code': process.returncode,
            'count': int(match.group(1)) if match else None,
            'seconds': float(match.group(2)) if match else None,
            'log': log.name,
            'scope': 'host software tests, including synthetic ASR HTTP; not real hardware/model acceptance',
        }
        print(process.stdout[-5200:])
    target = OUT / ('audit_checks_' + args.label + '.json')
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'audit': str(target), 'conflicts': len(conflicts),
                      'tests': result.get('host_framework_tests_this_audit')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
