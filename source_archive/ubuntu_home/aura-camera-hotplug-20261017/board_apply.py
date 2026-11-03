"""Apply the reviewed camera-only release, preserving an exact rollback copy."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

stage = Path(__file__).resolve().parent
manifest = json.loads((stage/'manifest.json').read_text())
runtime = Path('/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009/aura')
unit = 'aura-camera-ui.service'


def run(args, timeout=12):
    p = subprocess.run(args, cwd=str(runtime), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, text=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError(str(args) + ': ' + p.stdout[-4000:])
    return p.stdout


def atomic(path, data, mode=0o644):
    temp = path.with_name(path.name + '.hotplug-' + manifest['release_id'])
    with temp.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(temp, mode)
    os.replace(temp, path)


backup = stage/'backup'
assert not backup.exists(), 'This release was already applied; inspect its evidence first'
before = {}
for name, row in manifest['files'].items():
    data = (stage/'payload'/name).read_bytes()
    assert hashlib.sha256(data).hexdigest() == row['sha256'], name
    if name.endswith('.py'):
        compile(data, name, 'exec')
    target = Path(row['target'])
    assert str(target).startswith(str(runtime) + '/') or str(target) == '/etc/systemd/system/' + unit
    assert not target.is_symlink(), 'Refuse to replace a symlink: ' + str(target)
    actual = hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None
    assert actual == row['before_sha256'], (str(target), actual, row['before_sha256'])
    before[name] = {'target': str(target), 'existed': target.exists(),
                    'mode': target.stat().st_mode & 0o777 if target.exists() else 0o644}

backup.mkdir(mode=0o700)
for name, row in before.items():
    if row['existed']:
        p = backup/name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(Path(row['target']).read_bytes())
(backup/'before.json').write_text(json.dumps(before, indent=2))
gui_before = run(['systemctl', 'show', 'aura-avatar-ui.service', '-p', 'MainPID', '-p', 'ActiveState'])
changed = []
try:
    run(['systemctl', 'stop', unit], timeout=20)
    for name, row in manifest['files'].items():
        target = Path(row['target'])
        atomic(target, (stage/'payload'/name).read_bytes(), before[name]['mode'])
        changed.append(name)
        assert hashlib.sha256(target.read_bytes()).hexdigest() == row['sha256']
    run(['systemctl', 'daemon-reload'])
    tests = run(['python3', '-B', '-m', 'unittest',
                 'tests.framework.test_camera_device', 'tests.framework.test_camera_ui_service',
                 'tests.framework.test_local_camera_preview', 'tests.framework.test_yolo_dpu',
                 'tests.framework.test_person_bytetrack'], timeout=35)
    settings = run(['systemctl', 'show', unit, '-p', 'StartLimitIntervalUSec', '-p', 'RestartUSec', '-p', 'Restart'])
    assert {'StartLimitIntervalUSec=0', 'RestartUSec=3s', 'Restart=on-failure'} <= set(settings.splitlines()), settings
    run(['systemctl', 'reset-failed', unit])
    run(['systemctl', '--no-block', 'start', unit])
    gui_after = run(['systemctl', 'show', 'aura-avatar-ui.service', '-p', 'MainPID', '-p', 'ActiveState'])
    assert gui_after == gui_before, 'GUI changed during the camera-only update'
    result = {'applied': True, 'release_id': manifest['release_id'], 'tests': tests,
              'settings': settings, 'gui_before': gui_before, 'gui_after': gui_after,
              'backup': str(backup), 'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
except Exception as exc:
    rollback = []
    try:
        run(['systemctl', 'stop', unit], timeout=20)
        for name in reversed(changed):
            row = before[name]
            target = Path(row['target'])
            if row['existed']:
                atomic(target, (backup/name).read_bytes(), row['mode'])
            else:
                target.unlink()
            rollback.append(name)
        run(['systemctl', 'daemon-reload'])
        run(['systemctl', 'reset-failed', unit])
        run(['systemctl', '--no-block', 'start', unit])
        rollback_error = None
    except Exception as rollback_exc:
        rollback_error = str(rollback_exc)
    result = {'applied': False, 'error': str(exc), 'restored': rollback, 'rollback_error': rollback_error}
(stage/'apply-result.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result))
raise SystemExit(0 if result['applied'] else 1)
