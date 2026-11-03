"""Restart the unchanged original UI only after USB and idle safety checks."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'candidate.json').read_text(encoding='utf-8'));baseline=json.loads((HERE/'baseline.json').read_text(encoding='utf-8'))
script=r'''
import importlib.util,json,subprocess,time,urllib.request
from pathlib import Path
c=CANDIDATE;baseline=BASELINE
def get():
    with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4) as f:return json.load(f)
s=get();assert s['phase']=='IDLE' and not s.get('playing') and not s.get('streaming_reply')
assert s['handsfree_dialogue']['enabled'] is False and not s['handsfree_dialogue'].get('microphone_open')
assert s.get('manual_pan',{}).get('state') not in ('MOVING','STOPPING')
assert not s.get('manual_pan',{}).get('readback',{}).get('active')
assert 'MCP01' in Path('/proc/asound/cards').read_text()
cfg_path=Path(baseline['startup_config']);cfg=json.loads(cfg_path.read_text())
spec=importlib.util.spec_from_file_location('original_audio_launcher',cfg_path.with_name('launcher.py'))
launcher=importlib.util.module_from_spec(spec);spec.loader.exec_module(launcher)
assert not launcher.display_retrain_needed(cfg),'Display retrain is paused'
pref=Path('/root/.local/share/aura/handsfree_dialogue.json');before=pref.read_bytes();position=s.get('manual_pan',{}).get('pulse_us')
subprocess.run(['systemctl','restart','--no-block','aura-avatar-ui.service'],check=True,capture_output=True,timeout=15)
end=time.monotonic()+115
while time.monotonic()<end:
    try:
        s=get()
        if s.get('phase')=='IDLE' and s.get('audio_output_state')=='IDLE_READY':break
    except Exception:pass
    time.sleep(.5)
else:raise TimeoutError('Original audio did not recover after USB reconnection')
assert pref.read_bytes()==before and s['handsfree_dialogue']['enabled'] is False
assert s.get('manual_pan',{}).get('pulse_us')==position,'Current pan readback changed; do not issue a corrective movement'
print(json.dumps({'status':'PASS','audio_output_state':s['audio_output_state'],'monitor_enabled':False,'pan_readback_preserved':position,
 'source_runtime':c['source_runtime'],'microphone_used':False,'physical_speech_played':False,'motor_command_issued':False}))
'''.replace('CANDIDATE',repr(c)).replace('BASELINE',repr(baseline))
v=json.loads(ssh('python3 -B -',script,timeout=145))
(HERE/'original_audio_recovery.json').write_text(json.dumps(v,indent=2),encoding='utf-8');print(json.dumps(v))
