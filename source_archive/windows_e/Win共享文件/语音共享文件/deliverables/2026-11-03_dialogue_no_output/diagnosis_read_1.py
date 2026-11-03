"""Read-only public voice route diagnostics; never exports utterances or biometrics."""
import hashlib
import http.client
import json
from pathlib import Path
import re
import subprocess
import time


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def unit(name):
    result = subprocess.run(['systemctl', 'show', name,
        '--property=MainPID,ActiveState,SubState,Job,Result,ExecMainStatus,Restart,KillMode,SendSIGKILL,TimeoutStopUSec'],
        capture_output=True, text=True, timeout=4)
    assert result.returncode == 0
    return dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)


def owner(pid):
    path = Path('/proc') / str(pid)
    return dict(pid=int(pid), birth_ticks=path.joinpath('stat').read_text().rsplit(')', 1)[1].split()[19],
                command_sha256=sha(path / 'cmdline'))


def diagnostic(value, depth=0):
    if not isinstance(value, dict) or depth > 5:
        return None
    result = {}
    string_keys = {'state', 'phase', 'mode', 'reason', 'code', 'kind', 'entry', 'entry_mode', 'route',
                   'status', 'voice_state', 'visual_state', 'quality_reason', 'entry_reason', 'wakeword', 'error_class', 'outcome'}
    for key, item in value.items():
        if any(word in key.lower() for word in ('score', 'probability', 'sample_value', 'embedding', 'vector',
            'template', 'transcript', 'display_name', 'reply_text', 'user_text', 'text', 'pcm', 'path', 'audio_bytes')):
            continue
        if type(item) in (int, float, bool) or item is None:
            result[key] = item
        elif key in string_keys and isinstance(item, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,120}', item):
            result[key] = item
        elif isinstance(item, dict):
            child = diagnostic(item, depth + 1)
            if child:
                result[key] = child
    return result


out = dict(schema='aura-voice-only-current-readonly-diagnosis-1', board_mono_ms=int(time.monotonic() * 1000),
    control_writes=0, microphone_operations=0, new_audio_capture=0, inference_calls=0,
    private_store_reads=0, no_utterances_audio_templates_names_or_scores_exported=True)
startup_path = Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json')
cfg = json.loads(startup_path.read_bytes())
aura = Path(cfg['runtime']) / 'aura'
out.update(boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
    startup_path=str(startup_path), startup_sha256=sha(startup_path), component_count=len(cfg['component_sha256']),
    actual_component_mismatches=[path for path, digest in cfg['component_sha256'].items() if sha(aura / path) != digest])
out['GUI_unit'] = unit('aura-avatar-ui.service')
out['camera_unit'] = unit('aura-camera-ui.service')
for key, u in (('gui_owner', out['GUI_unit']), ('camera_owner', out['camera_unit'])):
    if int(u['MainPID']) > 0:
        out[key] = owner(int(u['MainPID']))
launch = json.loads((Path(cfg['runtime']) / 'launch.json').read_bytes())
if Path('/proc', str(launch['pid'])).exists():
    out['gtk_owner'] = owner(launch['pid'])
out['saved_listening_preference'] = json.loads(Path('/home/root/.local/share/aura-board-business/listening_preference.json').read_bytes())
connection = http.client.HTTPConnection('127.0.0.1', 8783, timeout=3)
try:
    connection.request('GET', '/api/state')
    response = connection.getresponse()
    raw = response.read(2097153)
    assert response.status == 200 and len(raw) <= 2097152
    value = json.loads(raw)
finally:
    connection.close()
business = value.get('board_business') or {}
dialogue = business.get('dialogue') or {}
speaker = business.get('speaker') or {}
route = dialogue.get('last_voice_route') or {}
out['current_state'] = dict(ui_page=value.get('ui_page'), phase=value.get('phase'),
    pair_state=(value.get('character_pair') or {}).get('state'), fault_count=(value.get('runtime_faults') or {}).get('count'),
    playing=bool(value.get('playing')), pending_job=bool(value.get('pending_job')),
    handsfree=diagnostic(value.get('handsfree_dialogue') or {}), speaker=diagnostic(speaker),
    last_voice_route=diagnostic(route), recording=diagnostic(value.get('local_recording') or {}),
    audio_frontend=diagnostic(value.get('audio_frontend') or {}),
    dialogue=diagnostic({key: dialogue[key] for key in ('state', 'phase', 'latency', 'last_playback_ack', 'diagnostics', 'cleanup_error', 'feedback_error') if key in dialogue}),
    following=(value.get('manual_pan') or {}).get('automatic_following'))
out['public_field_names'] = dict(speaker=sorted(speaker), dialogue=sorted(dialogue), route=sorted(route),
    handsfree=sorted(value.get('handsfree_dialogue') or {}), recording=sorted(value.get('local_recording') or {}),
    frontend=sorted(value.get('audio_frontend') or {}), business=sorted(business))
gui_path = aura / 'config/board_avatar_gtk.json'
out['GUI_config_sha256'] = sha(gui_path)
out['GUI_config_field_names'] = sorted(json.loads(gui_path.read_bytes()))
flag = Path('/run/aura-dialogue-thinking-test.json')
if flag.exists():
    assert not flag.is_symlink()
    flag_raw=flag.read_bytes();assert len(flag_raw)<=1024
    out['thinking_flag']=json.loads(flag_raw)
else:out['thinking_flag']=None
out['runtime_faults_numeric']=diagnostic(value.get('runtime_faults') or {})
c=http.client.HTTPConnection('192.168.50.1',8797,timeout=3)
try:
    c.request('GET','/health');r=c.getresponse();raw=r.read(1048577)
    assert r.status==200 and len(raw)<=1048576
    health=json.loads(raw);backend=health.get('backend') or {}
    out['model_health']=dict(ok=health.get('ok'),active=health.get('active'),pending=health.get('pending'),
        counts=diagnostic(health.get('counts') or {}),model=backend.get('model'),num_step=backend.get('num_step'),
        tts_ready=backend.get('tts_ready'),voice=diagnostic(backend.get('voice') or {}))
except Exception as error:out['model_health']=dict(error_class=type(error).__name__)
finally:c.close()
out['status']='CURRENT_NO_OUTPUT_DIAGNOSTICS_READ'
print(json.dumps(out))
