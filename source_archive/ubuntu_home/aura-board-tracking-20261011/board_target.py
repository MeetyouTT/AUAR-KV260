"""Bounded real-camera observation and native target selection; no service restart."""
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.request

STAGE = Path('/home/root/aura-bytetrack-20261011/update-ea926df36eb116cd')
sys.path.insert(0, str(STAGE / 'payload'))
manifest = json.loads((STAGE / 'payload' / 'manifest.json').read_text())
for name in ('board_probe.py', 'board_acceptance.py'):
    assert hashlib.sha256((STAGE / 'payload' / name).read_bytes()).hexdigest() == manifest['files'][name]['sha256'], name
from board_probe import api, click, report


def get(path):
    with urllib.request.urlopen('http://127.0.0.1:8790' + path, timeout=4) as stream:
        return json.load(stream)


def save_preview(label):
    # Retry only if the bounded JPEG ring no longer contains the requested frame.
    for _ in range(3):
        snapshot = get('/v1/ui/status')
        ref = snapshot.get('preview')
        if not ref:
            return None
        url = 'http://127.0.0.1:8790/v1/ui/preview.jpg?camera_epoch=' + ref['camera_epoch'] + '&frame_id=' + str(ref['frame_id'])
        try:
            with urllib.request.urlopen(url, timeout=4) as stream:
                assert stream.headers['X-Aura-Frame-Id'] == str(ref['frame_id'])
                blob = stream.read()
            result['artifacts'][label] = {'base64': base64.b64encode(blob).decode(), 'bytes': len(blob),
                                         'sha256': hashlib.sha256(blob).hexdigest()}
            return {'reference': ref, 'target': snapshot['modules']['target'],
                    'people_count': snapshot['modules']['vision'].get('people_count')}
        except urllib.error.HTTPError as exc:
            if exc.code not in (404, 410):
                raise
    return None


before = get('/health')
preferences = api()['ui_settings']
assert before['detector']['tracking_backend'] == 'BYTETRACK_PINNED_NUMPY', before
assert not any(before[key] for key in ('camera_error', 'detector_error', 'preview_error')), before
result = {'scope': 'REAL_CAMERA_TARGET_SELECTION', 'before': before, 'artifacts': {}, 'observations': []}
result['first_preview'] = save_preview('camera-first.jpg')

# Show a large live view while the user positions the camera.
assert api({'type': 'ui_page', 'page': 'main'})['ok']
time.sleep(.35)
_, geometry = report()
dialogs = geometry['ui_geometry']['dialogs']
if not dialogs:
    rect = geometry['ui_geometry']['visible_controls']['camera_expand']
    assert rect['sensitive'], rect
    click(rect['x'] + rect['width'] / 2, rect['y'] + rect['height'] / 2)
    time.sleep(.35)
    _, geometry = report()
    dialogs = geometry['ui_geometry']['dialogs']
assert len(dialogs) == 1 and dialogs[0]['title'] == '摄像头实时画面', dialogs
result['large_view'] = dialogs[0]

start = time.monotonic()
deadline = start + 45
positive = False
while time.monotonic() < deadline:
    snapshot = get('/v1/ui/status')
    health = get('/health')
    assert snapshot['source_kind'] == 'actual'
    assert health['service_epoch'] == before['service_epoch'] and health['camera_epoch'] == before['camera_epoch']
    assert not any(health[key] for key in ('camera_error', 'detector_error', 'preview_error')), health
    tracks = snapshot['modules']['target']['tracks']
    result['observations'].append({'elapsed_s': round(time.monotonic() - start, 3),
        'sequence': snapshot['sequence'], 'selected': snapshot['modules']['target']['selected'], 'tracks': tracks,
        'people_count': snapshot['modules']['vision'].get('people_count'),
        'detected_frames': health['detected_frames'], 'capture_frames': health['capture_frames']})
    if tracks:
        positive = True
        result['positive_preview'] = save_preview('person-observed.jpg')
        break
    time.sleep(.2)
result['observation_seconds'] = round(time.monotonic() - start, 3)
result['positive_observed'] = positive
if positive:
    dialog = result['large_view']
    click(dialog['x'] + dialog['width'] - 80, dialog['y'] + dialog['height'] - 34)
    time.sleep(.3)
    native = subprocess.run(['python3', '-B', str(STAGE / 'payload' / 'board_acceptance.py')],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=100)
    result['native_exit_code'] = native.returncode
    if native.returncode:
        result['native_error'] = native.stdout[-6000:]
        result['status'] = 'NATIVE_SELECTION_FAILED'
    else:
        accepted = json.loads(native.stdout)
        result['artifacts'].update(accepted.pop('artifacts', {}))
        result['native'] = accepted
        result['status'] = 'PASS' if accepted.get('native_target_chooser') else 'PENDING_PERSON_LEFT_BEFORE_SELECTION'
else:
    result['status'] = 'PENDING_REAL_PERSON'
result['last_preview'] = save_preview('camera-last.jpg')
result['after'] = get('/health')
result['ui_after'] = api()
assert result['after']['capture_frames'] > before['capture_frames']
assert result['after']['detected_frames'] > before['detected_frames']
for key in ('volume', 'muted', 'fullscreen', 'economy'):
    assert result['ui_after']['ui_settings'][key] == preferences[key], key
result['settings_preserved'] = True
print(json.dumps(result, ensure_ascii=False))
