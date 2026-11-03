"""Read the active UI transcription prerequisites without recording or sending audio."""
import hashlib
import json
from pathlib import Path
import urllib.request

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open('http://127.0.0.1:8783/api/state', timeout=4) as reply:
    state = json.load(reply)
transcription = state.get('local_transcription') or {}
recording = state.get('local_recording') or {}
clip = recording.get('result') or {}
text = transcription.get('text') or ''
camera = {}
try:
    with opener.open('http://127.0.0.1:8790/health', timeout=3) as reply:
        info = json.load(reply)
    camera = {key: info.get(key) for key in
              ('pid', 'service_epoch', 'capture_frames', 'detection_frames', 'ready', 'error')}
except Exception as error:
    camera = {'error': type(error).__name__}
print(json.dumps({
    'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
    'ui': {key: state.get(key) for key in ('ui_layer', 'ui_page', 'phase', 'playing', 'paused', 'error')},
    'recording': {key: recording.get(key) for key in ('state', 'can_start', 'sample_count', 'error')},
    'retained_clip': {key: clip.get(key) for key in ('capture_id', 'sample_count', 'pcm_sha256')},
    'transcription': {key: transcription.get(key) for key in ('state', 'service', 'error')},
    'transcript_characters': len(text),
    'transcript_sha256': hashlib.sha256(text.encode()).hexdigest() if text else None,
    'camera': camera, 'recording_started_by_this_check': False,
}, ensure_ascii=False))
