"""Read source pins and filtered non-UI speech state; no devices, writes or inference."""
import datetime
import hashlib
import http.client
import json
from pathlib import Path
import subprocess
import time

BUSINESS = Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
STARTUP = BUSINESS/'startup/config.json'
boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
startup_raw = STARTUP.read_bytes()
startup = json.loads(startup_raw)
aura = Path(startup['runtime'])/'aura'
pins = startup['component_sha256']
assert isinstance(pins, dict) and 300 <= len(pins) <= 500
actual = {}
for relative, expected in pins.items():
    target = aura/relative
    assert target.resolve().is_relative_to(aura.resolve()) and target.is_file() and not target.is_symlink()
    assert target.suffix not in ('.sqlite', '.sqlite3', '.db') and target.stat().st_size <= 64_000_000
    actual[relative] = hashlib.sha256(target.read_bytes()).hexdigest()
assert actual == pins and STARTUP.read_bytes() == startup_raw

wanted = (
    'board/runtime/board_business.py',
    'board/runtime/board_dialogue.py',
    'board/runtime/board_dialogue_client.py',
    'board/runtime/compact_request_adapter.py',
    'board/runtime/audio/board_dialogue_jobs.py',
    'board/runtime/audio/board_asr.py',
    'board/runtime/audio/automatic_capture.py',
    'board/runtime/audio/board_frontend_auto.py',
    'board/runtime/audio/board_frontend.py',
    'board/runtime/audio/persistent_playback.py',
    'tools/streaming_controller.py',
    'tools/production_output_format.py',
    'tools/production_frontend_selection.py',
    'tools/production_listening.py',
    'tools/voice_first_recording.py',
    'tools/handsfree_recording.py',
    'tools/realtime_bridge.py',
)
sources = {}
for relative in wanted:
    if relative in pins:
        data = (aura/relative).read_bytes()
        assert hashlib.sha256(data).hexdigest() == pins[relative]
        sources[relative] = {'sha256': pins[relative], 'source': data.decode('utf-8')}

ui = json.loads((aura/'config/board_avatar_gtk.json').read_bytes())
allowed = {'asr_variant', 'asr_threads', 'frontend_optimization', 'frontend_threads',
           'capture_process', 'frontend_process', 'capture_nice', 'entry_mode',
           'handsfree_dialogue', 'automatic_turns', 'streaming_conversation',
           'persistent_audio', 'early_listen', 'voice_barge_in', 'sample_rate',
           'audio_rate', 'chunk_ms', 'audio_buffer_ms', 'audio_period_ms',
           'model_host', 'model_port', 'retention_enabled', 'output_format'}
configuration = {key: ui[key] for key in allowed if key in ui and type(ui[key]) in (str, bool, int, float)}
business_config = ui.get('board_business', {})
configuration['board_business'] = {key: business_config[key] for key in allowed if key in business_config and type(business_config[key]) in (str, bool, int, float)}

def request(host, port, path):
    connection = http.client.HTTPConnection(host, port, timeout=3)
    try:
        connection.request('GET', path)
        response = connection.getresponse()
        raw = response.read(2_097_153)
        assert response.status == 200 and len(raw) <= 2_097_152
        value = json.loads(raw)
        assert isinstance(value, dict)
        return value
    finally:
        connection.close()

def scalar(value, keys):
    return {k: value[k] for k in keys if isinstance(value, dict) and k in value and (value[k] is None or type(value[k]) in (bool, int, float))}

def enum(value, allowed):
    return value if type(value) is str and value in allowed else None

def obj(value, key):
    result = value.get(key, {}) if isinstance(value, dict) else {}
    return result if isinstance(result, dict) else {}

api = {}
try:
    value = request('127.0.0.1', 8783, '/api/state')
    business = obj(value, 'board_business')
    dialogue = obj(business, 'dialogue')
    latency = obj(dialogue, 'latency')
    api = {
        'available': True,
        'playback': scalar(value, ('playing', 'paused')),
        'handsfree': scalar(obj(value, 'handsfree_dialogue'), ('enabled', 'microphone_open')),
        'dialogue': scalar(dialogue, ('active', 'queued', 'completed', 'discarded', 'failed', 'cancelled')),
        'latency': {k: v for k, v in latency.items() if type(v) in (bool, int, float) or v is None},
        'business_clock': scalar(obj(business, 'clock'), ('anchored', 'event_time_available', 'same_boot', 'safe_for_compaction')),
        'memory': scalar(obj(business, 'memory'), ('running', 'queued', 'active', 'completed', 'discarded', 'failure_streak')),
        'business_error_present': bool(business.get('error')),
        'dialogue_error_present': bool(dialogue.get('error')),
    }
except (OSError, ValueError, AssertionError, http.client.HTTPException) as error:
    api = {'available': False, 'error_type': type(error).__name__}

health = {}
try:
    value = request('192.168.50.1', 8797, '/health')
    backend = obj(value, 'backend')
    health = {'available': True, 'ok': value.get('ok') is True,
              'role': enum(value.get('role'), {'model_inference_only'}),
              'execution': scalar(value, ('active', 'pending')),
              'backend': scalar(backend, ('num_step', 'tts_ready', 'num_ctx')),
              'model': enum(backend.get('model'), {'aura-qwen3.8-27b-abliterated:iq4_xs'}),
              'tts': enum(backend.get('tts'), {'omnivoice'}),
              'voice': {'alive': obj(backend, 'voice').get('alive') is True,
                        'error_present': bool(obj(backend, 'voice').get('error'))}}
except (OSError, ValueError, AssertionError, http.client.HTTPException) as error:
    health = {'available': False, 'error_type': type(error).__name__}

unit = subprocess.run(['systemctl', 'show', 'aura-avatar-ui.service',
                       '--property=MainPID,ActiveState,SubState,Job'],
                      capture_output=True, text=True, timeout=4)
assert unit.returncode == 0
fields = dict(row.split('=', 1) for row in unit.stdout.splitlines() if '=' in row)
assert STARTUP.read_bytes() == startup_raw and Path('/proc/sys/kernel/random/boot_id').read_text().strip() == boot
print(json.dumps({'schema': 'aura-current-nonui-speech-source-readonly-1',
                  'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  'boot_id': boot, 'startup_sha256': hashlib.sha256(startup_raw).hexdigest(),
                  'runtime': str(aura), 'component_count': len(pins), 'all_component_sha256_verified': True,
                  'component_sha256': pins, 'sources': sources, 'configuration': configuration,
                  'speech_api_metadata': api, 'model_health': health,
                  'service_readonly_snapshot': {'pid': int(fields['MainPID']),
                      'active': fields['ActiveState'] == 'active', 'running': fields['SubState'] == 'running',
                      'job_pending': bool(fields['Job'])},
                  'board_mutations': False, 'microphone_or_model_requests': False,
                  'private_database_or_text_read': False, 'axis_read_or_action': False}, sort_keys=True))
