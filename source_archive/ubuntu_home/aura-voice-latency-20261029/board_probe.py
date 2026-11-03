"""Read service metadata only; no audio, motion, configuration or process writes."""
import json
import subprocess
import urllib.request
from pathlib import Path


def get(url):
    with urllib.request.urlopen(url, timeout=4) as response:
        return json.load(response)


def timing_only(value):
    if isinstance(value, list):
        return [timing_only(item) for item in value[-12:]]
    if isinstance(value, dict):
        output = {}
        for key, item in value.items():
            if key in ('text', 'transcript', 'reply_text', 'first_clause_text', 'prompt', 'history', 'messages'):
                continue
            if isinstance(item, (dict, list)):
                filtered = timing_only(item)
                if filtered:
                    output[key] = filtered
            elif type(item) in (int, float, bool) or (key in ('backend', 'thinking_mode', 'status', 'stage') and isinstance(item, str)):
                output[key] = item
        return output
    return None


def recent_turns(value):
    found = []
    if isinstance(value, dict):
        if 'request_to_answer_seconds' in value:
            found.append(timing_only(value))
        else:
            for item in value.values():
                found.extend(recent_turns(item))
    elif isinstance(value, list):
        for item in value[-12:]:
            found.extend(recent_turns(item))
    return found[-12:]


result = {"boot_id": Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
for label, url in (
    ('ui', 'http://127.0.0.1:8783/api/state'),
    ('camera', 'http://127.0.0.1:8790/health'),
    ('windows', 'http://192.168.50.1:8792/health'),
):
    try:
        value = get(url)
        if label == 'ui':
            result[label] = {key: value.get(key) for key in ('phase', 'playing', 'audio_output_state')}
            result[label].update(
                listening=value.get('handsfree_dialogue', {}).get('enabled'),
                recording=value.get('local_recording', {}).get('state'),
                pending=value.get('local_transcription', {}).get('service', {}).get('pending'),
                automatic_following=value.get('manual_pan', {}).get('automatic_following'),
            )
            result[label]['recent_turns'] = recent_turns(value)
        elif label == 'windows':
            result[label] = {key: value.get(key) for key in (
                'ready', 'busy', 'service_revision', 'source_fingerprint', 'latency_options',
                'llm_model', 'asr_model', 'tts', 'num_step', 'startup_warmup_complete',
            )}
            result[label]['health_keys'] = sorted(value)
            result[label]['capabilities'] = value.get('capabilities', {})
            result[label]['request_diagnostics'] = timing_only(value.get('voice_request_diagnostics', {}))
        else:
            result[label] = {key: value.get(key) for key in ('pid', 'service_epoch', 'ready')}
    except Exception as error:
        result[label] = {'error_type': type(error).__name__, 'error': str(error)[:180]}
result['unit_pids'] = {
    name: subprocess.check_output(['systemctl', 'show', name, '-p', 'MainPID', '--value'], text=True).strip()
    for name in ('aura-avatar-ui.service', 'aura-camera-ui.service')
}
print(json.dumps(result))
