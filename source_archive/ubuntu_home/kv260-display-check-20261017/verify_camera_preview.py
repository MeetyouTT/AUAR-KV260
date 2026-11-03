"""Verify actual camera progress and make its existing UI page visible."""
import json
import subprocess
import time
import urllib.request


def get(base, path):
    with urllib.request.urlopen(base + path, timeout=3) as stream:
        return json.load(stream)


def command(data):
    base = 'http://127.0.0.1:8783'
    req = urllib.request.Request(base + '/api/command', data=json.dumps(data).encode(),
                                 headers={'Content-Type': 'application/json', 'Origin': base})
    with urllib.request.urlopen(req, timeout=3) as stream:
        return json.load(stream)


camera = 'http://127.0.0.1:8790'
gui = 'http://127.0.0.1:8783'
deadline = time.monotonic() + 15
health = None
error = None
while time.monotonic() < deadline:
    try:
        health = get(camera, '/health')
        if health.get('capture_frames', 0) >= 3 and health.get('detected_frames', 0) >= 3:
            break
    except Exception as exc:
        error = str(exc)
    time.sleep(.3)
if not health or health.get('capture_frames', 0) < 3:
    journal = subprocess.check_output(['journalctl', '-b', '-u', 'aura-camera-ui.service', '-n', '15', '--no-pager'], text=True)
    print(json.dumps({'ready': False, 'health': health, 'error': error, 'journal': journal}))
    raise SystemExit(1)
before = health
assert command({'type': 'ui_page', 'page': 'vision'})['ok']
time.sleep(2)
after = get(camera, '/health')
state = get(gui, '/api/state')
runtime = state['ui_runtime']
ok = (after['capture_frames'] > before['capture_frames'] and
      after['detected_frames'] > before['detected_frames'] and
      not any(after.get(k) for k in ['camera_error', 'detector_error', 'preview_error']) and
      runtime.get('frame_visible') and runtime.get('link') == 'READY' and
      (runtime.get('snapshot') or {}).get('source_kind') == 'actual')
print(json.dumps({'ready': bool(ok), 'before': before, 'after': after,
                  'ui_page': state['ui_page'], 'ui_runtime': runtime}, ensure_ascii=False))
raise SystemExit(0 if ok else 1)
