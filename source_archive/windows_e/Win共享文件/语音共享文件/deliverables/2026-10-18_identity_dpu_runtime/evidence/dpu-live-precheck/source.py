"""Read current UI/camera/PC readiness without recording, playback or restart."""
import ipaddress
import json
import os
from pathlib import Path
import urllib.request

assert os.uname().machine == 'aarch64'
assert Path('/sys/block/mmcblk1/device/cid').read_text().strip() == '0353445345333247805558c00401a100'
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def get(url):
    with opener.open(url, timeout=3) as response:
        raw = response.read(131073)
        assert len(raw) <= 131072
        return json.loads(raw)


report = {'status': 'READ_ONLY', 'board_boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
try:
    ui = get('http://127.0.0.1:8783/api/state')
    recording = ui.get('local_recording', {})
    transcription = ui.get('local_transcription', {})
    service = transcription.get('service', {})
    report['ui'] = {k: ui.get(k) for k in ('ui_page', 'phase', 'playing', 'audio_output_state')}
    report['recording'] = {k: recording.get(k) for k in ('state', 'can_start', 'can_stop')}
    report['transcription_state'] = transcription.get('state')
    report['voice'] = {k: service.get(k) for k in ('enabled', 'host', 'port', 'conversation', 'streaming', 'voice_identity')}
    if service.get('enabled'):
        host = str(ipaddress.IPv4Address(service['host']))
        port = service['port']
        assert type(port) is int and 1024 <= port <= 65535
        try:
            pc = get('http://'+host+':'+str(port)+'/health')
            report['pc_health'] = {k: pc.get(k) for k in ('ready', 'source_kind', 'asr_model', 'llm_model',
                'tts', 'num_step', 'voice_text_channel', 'busy')}
        except Exception as exc:
            report['pc_error'] = type(exc).__name__+': '+str(exc)[:160]
except Exception as exc:
    report['ui_error'] = type(exc).__name__+': '+str(exc)[:160]
try:
    camera = get('http://127.0.0.1:8790/health')
    report['camera'] = {k: camera.get(k) for k in ('pid', 'identity_recognition', 'camera_error', 'detector_error',
                                                'observation_age_ms', 'detection_hz')}
except Exception as exc:
    report['camera_error'] = type(exc).__name__+': '+str(exc)[:160]
print(json.dumps(report), flush=True)
