"""One supervised GUI-owned follow window; normal STOP in all exit paths."""
import hashlib
import json
import time
import urllib.request
from pathlib import Path

R = Path('/home/root/aura-pan-current-20261024/16a07283')
G = R / 'gui-manual-bound-v1'
A = G / 'runtime/aura'
F = Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5')
P = F / 'continuous-v10r12'
S = F / 'face-source-v16'
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def get(port, path):
    with opener.open('http://127.0.0.1:%d%s' % (port, path), timeout=3) as response:
        return json.load(response)


def toggle():
    base = 'http://127.0.0.1:8783'
    request = urllib.request.Request(base + '/api/command',
        data=b'{"type":"pan_face_follow"}',
        headers={'Origin': base, 'Content-Type': 'application/json'})
    with opener.open(request, timeout=4) as response:
        result = json.load(response)
    assert result.get('ok'), result
    return result


sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
state = json.loads((R / 'state.json').read_text())
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == state['boot']
cfg = json.loads((G / 'startup/config.json').read_text())
assert all(sha(A / name) == digest for name, digest in cfg['component_sha256'].items())
face = json.loads((A / 'config/pan_face.local.json').read_text())
assert face['release_root'] == str(P)
assert face['manifest_sha256'] == sha(P / 'deployment-manifest.json')
assert all(sha(pin['destination']) == pin['sha256'] for pin in json.loads((P / 'deployment-manifest.json').read_text())['files'])
assert all(sha(name) == digest for name, digest in json.loads((S / 'deployment-manifest.json').read_text())['pins'].items())
direction = json.loads((R / 'direction-calibration.json').read_text())
assert direction['axis_camera_mirrored_control_polarity'] == 1
before_health = get(8790, '/health')
before_manual = get(8783, '/api/state')['manual_pan']
assert before_health['pid'] == state['current_camera_pid']
assert not before_health['dpu_schedule']['owner_fenced']
assert before_manual['state'] == 'READY' and not before_manual['automatic_following']
assert before_manual['readback']['flags'] == 0 and before_manual['readback']['lease_left_ms'] == 0
initial_face = get(8790, '/v1/motion/face/observation')
assert initial_face['face_tracking']['algorithm_version'] == 14

tag = str(time.monotonic_ns())
evidence = R / ('r12-v16-supervised-' + tag + '.json')
data = dict(boot_id=state['boot'], controller_manifest_sha256=face['manifest_sha256'],
    source_manifest_sha256=sha(S / 'deployment-manifest.json'), window_requested_s=30,
    before_manual=before_manual, initial_face_state=initial_face['state'],
    health_before={'primary_overruns': before_health['dpu_schedule']['primary_period_overruns']},
    samples=[], report=None, physical_motion_verified=False)
requested = False
began = None
last_report = None
error = None
stop_error = None
try:
    requested = True
    data['start_reply'] = toggle()
    began = time.monotonic()
    while time.monotonic() - began < 30:
        manual = get(8783, '/api/state')['manual_pan']
        current = dict(elapsed_s=round(time.monotonic() - began, 3),
            manual_state=manual['state'], automatic_following=manual['automatic_following'],
            face_follow=manual.get('face_follow'), readback=manual.get('readback'))
        path = (manual.get('face_follow') or {}).get('report')
        if path:
            report_path = Path(path)
            assert report_path.is_relative_to(P / 'runs')
            if report_path.exists():
                report = json.loads(report_path.read_text())
                assert report['boot_id'] == state['boot']
                assert report['consumer_manifest_sha256'] == face['manifest_sha256']
                data['report'] = str(report_path)
                last_report = report
                current.update(result=report.get('result'), input_summary=report.get('input_summary'),
                    observations=report.get('observation_trace', [])[-2:])
                if report.get('result', {}).get('fatal'):
                    data['samples'].append(current)
                    raise RuntimeError('Follow reported fatal: ' + str(report.get('result', {}).get('reason')))
        data['samples'].append(current)
        if not manual['automatic_following'] and time.monotonic() - began > 2:
            raise RuntimeError('GUI follow ended before supervised window')
        time.sleep(.4)
except BaseException as exc:
    error = type(exc).__name__ + ': ' + str(exc)[:250]
finally:
    if requested:
        try:
            manual = get(8783, '/api/state')['manual_pan']
            if manual['automatic_following']:
                data['stop_reply'] = toggle()
            deadline = time.monotonic() + 12
            while time.monotonic() < deadline:
                manual = get(8783, '/api/state')['manual_pan']
                if not manual['automatic_following']:
                    rb = manual.get('readback') or {}
                    if manual['state'] == 'READY' and rb.get('flags') == 0 and rb.get('lease_left_ms') == 0:
                        break
                time.sleep(.2)
            data['after_manual'] = manual
            assert not manual['automatic_following'] and manual['state'] == 'READY', manual
            assert manual['readback']['flags'] == 0 and manual['readback']['lease_left_ms'] == 0
        except BaseException as exc:
            stop_error = type(exc).__name__ + ': ' + str(exc)[:250]
    data['elapsed_s'] = round(time.monotonic() - began, 3) if began else 0
    data.update(error=error, stop_error=stop_error)
    if data['report'] and Path(data['report']).exists():
        last_report = json.loads(Path(data['report']).read_text())
        data['final_report_sha256'] = sha(data['report'])
        data['final_report'] = last_report
    evidence.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')

health_after = get(8790, '/health')
stopped = not stop_error and not data.get('after_manual', {}).get('automatic_following', True)
if stopped:
    state.update(phase='R12_SOURCE_V16_SUPERVISED_STOPPED', automatic_following=False,
        latest_supervised_trial=str(evidence), latest_supervised_report=data['report'])
    tmp = R / ('state.json.trial-' + tag)
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(R / 'state.json')
summary = dict(status='SUPERVISED_WINDOW_STOPPED' if stopped else 'STOP_NOT_VERIFIED',
    error=error, stop_error=stop_error, elapsed_s=data['elapsed_s'], evidence=str(evidence),
    report=data['report'], camera_pid=health_after['pid'], sample_count=len(data['samples']),
    initial_face_state=data['initial_face_state'], after_manual=data.get('after_manual'),
    health_before=data['health_before'], primary_overruns_after=health_after['dpu_schedule']['primary_period_overruns'],
    optional_overruns={name: health_after['dpu_schedule']['optional'][name]['overruns'] for name in ('yunet','sface')},
    physical_motion_verified=False)
if last_report:
    for name in ('status', 'result', 'input_summary', 'input_timing', 'submission_timing', 'reader_queue', 'telemetry'):
        summary['follow_' + name] = last_report.get(name)
    summary['observations'] = last_report.get('observation_trace', [])[-12:]
print(json.dumps(summary))
assert stopped, stop_error
