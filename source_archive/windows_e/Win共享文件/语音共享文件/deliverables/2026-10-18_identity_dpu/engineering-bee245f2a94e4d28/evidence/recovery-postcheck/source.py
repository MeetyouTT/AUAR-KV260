"""Observe restored camera/UI for 20 seconds; do not request capture or inference."""
import json
import os
from pathlib import Path
import statistics
import subprocess
import time
import urllib.request

assert os.uname().machine == 'aarch64'
assert Path('/sys/block/mmcblk1/device/cid').read_text().strip() == '0353445345333247805558c00401a100'
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
samples = []
started = time.monotonic()
for i in range(20):
    with opener.open('http://127.0.0.1:8790/health', timeout=3) as response:
        s = json.load(response)
    samples.append({k: s.get(k) for k in ('pid', 'service_epoch', 'detected_frames', 'capture_frames',
        'detection_hz', 'observation_age_ms', 'last_inference_ms', 'camera_error', 'detector_error', 'identity_recognition')})
    time.sleep(max(0, started+i+1-time.monotonic()))
with opener.open('http://127.0.0.1:8783/api/state', timeout=3) as response:
    ui = json.load(response)
good = all(s['pid'] == samples[0]['pid'] and s['service_epoch'] == samples[0]['service_epoch'] and
           not s['camera_error'] and not s['detector_error'] and s['observation_age_ms'] is not None and s['observation_age_ms'] < 750 for s in samples)
report = {'status': 'PASS_20_SECOND_RESTORED_CAMERA' if good and samples[-1]['detected_frames'] > samples[0]['detected_frames'] else 'FAILED_POSTCHECK',
          'samples': samples, 'elapsed_s': time.monotonic()-started,
          'observed_detection_hz': (samples[-1]['detected_frames']-samples[0]['detected_frames'])/19.,
          'maximum_observation_age_ms': max(s['observation_age_ms'] for s in samples),
          'median_detection_call_ms': statistics.median(s['last_inference_ms'] for s in samples),
          'ui': {k: ui.get(k) for k in ('ui_page', 'phase', 'playing', 'audio_output_state')},
          'streaming_enabled': ui.get('local_transcription', {}).get('service', {}).get('streaming'),
          'active_test_restore_timers': subprocess.run(['systemctl', 'list-timers', 'aura-sface-engineering-restore-*', '--no-legend', '--no-pager'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=5).stdout.strip(),
          'production_identity_enabled': samples[-1]['identity_recognition']}
print(json.dumps(report), flush=True)
