"""Short read-only observation of real camera YOLO; never inject a test image."""
import base64
import hashlib
import json
import statistics
import time
import urllib.request

def get(path):
    with urllib.request.urlopen('http://127.0.0.1:8790' + path, timeout=3) as response:return json.load(response)

before = get('/health')
assert before['role'] == 'DPU_YOLOX_PERSON_PREVIEW'
rows = []
positive = None
end = time.monotonic() + 20
while time.monotonic() < end:
    health = get('/health')
    assert health['service_epoch'] == before['service_epoch'] and health['camera_epoch'] == before['camera_epoch']
    assert not health['camera_error'] and not health['detector_error'] and not health['preview_error']
    rows.append({k: health[k] for k in ['capture_frames', 'detected_frames', 'people_count',
        'capture_age_ms', 'observation_age_ms', 'last_inference_ms']})
    if positive is None and health.get('people_count', 0):
        snapshot = get('/v1/ui/status')
        ref = snapshot.get('preview')
        if ref and snapshot['modules']['vision'].get('people_count', 0):
            try:
                url = 'http://127.0.0.1:8790/v1/ui/preview.jpg?camera_epoch=' + ref['camera_epoch'] + '&frame_id=' + str(ref['frame_id'])
                with urllib.request.urlopen(url, timeout=3) as response:
                    assert response.headers['X-Aura-Camera-Epoch'] == ref['camera_epoch']
                    assert response.headers['X-Aura-Frame-Id'] == str(ref['frame_id'])
                    jpeg = response.read()
                positive = {'snapshot': snapshot, 'frame_reference': ref, 'jpeg': jpeg}
            except OSError:pass
    time.sleep(.12)
after = get('/health')
assert after['capture_frames'] > before['capture_frames'] and after['detected_frames'] > before['detected_frames']
values = [r['last_inference_ms'] for r in rows if r['last_inference_ms'] is not None]
result = {'status': 'PASS', 'scope': 'REAL_CAMERA_OBSERVATION', 'before': before, 'after': after,
    'rows': rows, 'positive_observed': bool(positive), 'max_people_count': max((r['people_count'] or 0) for r in rows),
    'inference_ms': {'samples': len(values), 'median': statistics.median(values), 'p95': sorted(values)[int(.95*(len(values)-1))]},
    'source_fresh_samples': sum(r['observation_age_ms'] < 750 for r in rows)}
if positive:
    jpeg = positive.pop('jpeg')
    result['positive'] = positive
    result['artifacts'] = {'real-positive.jpg': {'base64': base64.b64encode(jpeg).decode(),
        'bytes': len(jpeg), 'sha256': hashlib.sha256(jpeg).hexdigest()}}
print(json.dumps(result))
