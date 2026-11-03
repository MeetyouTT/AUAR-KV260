"""Read the effective deployed UI and wired services without audio or motion IO."""
import json, sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '2026-10-18_board_dialogue'))
from board_ssh import ssh

c = json.loads((HERE / 'candidate.json').read_text(encoding='utf-8'))
script = r'''
import hashlib, http.client, json, socket, subprocess, sys, time, urllib.request
from pathlib import Path
c=CANDIDATE; stage=Path(c['stage']); root=Path(c['runtime'])
deployment=json.loads((stage/'deployment.json').read_text())
assert deployment['status']=='COMMITTED' and (stage/'committed').exists()
effective=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart','-p','DropInPaths','-p','ActiveState'],text=True)
assert c['startup']+'/launcher.py' in effective and 'ActiveState=active' in effective
with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=5) as f:state=json.load(f)
hf=state['handsfree_dialogue']; display=state['avatar_display']
assert state['phase']=='IDLE' and state['audio_output_state']=='IDLE_READY' and not state.get('error')
assert not state.get('playing') and not state.get('streaming_reply')
assert not hf['enabled'] and not hf.get('microphone_open')
assert display['kind']=='native_sink_handoff' and display['age_ms']<1000
profile=state['local_transcription']['service']['profile_memory']
assert profile['mode']=='guest'
services={}
for port in (8791,8792):
    conn=http.client.HTTPConnection('192.168.50.1',port,timeout=6)
    try:
        conn.request('GET','/health');response=conn.getresponse();value=json.loads(response.read())
        assert response.status==200, (port,response.status)
        services[str(port)]={'http_status':response.status,**{k:value[k] for k in (
            'ready','service_revision','source_fingerprint','capabilities','llm_model','voice_protocol') if k in value}}
    finally:conn.close()
sys.path.insert(0,str(root/'aura'))
from common.frontend_wire import PROTOCOL,send,receive
with socket.create_connection(('192.168.50.1',8795),timeout=3) as connection:
    send(connection,{'protocol':PROTOCOL,'kind':'health'});frontend,pcm=receive(connection,1)
assert not pcm and frontend.get('protocol')==PROTOCOL and frontend.get('ready') is True
services['8795']={'transport':'framed_tcp','protocol':frontend['protocol'],'ready':True}
assert services['8792']['capabilities']['audio_clock_animation']==1
assert services['8792']['service_revision']=='voice-animation-dialogue-20261026-r3'
different=[]; unchanged=0; expected=set(c['changes'])
for directory in ('board','common','host','tools'):
    source=Path(c['source_runtime'])/'aura'/directory
    for file in source.rglob('*.py'):
        rel=file.relative_to(source.parent).as_posix()
        if rel in expected:continue
        target=root/'aura'/rel
        if not target.exists() or hashlib.sha256(file.read_bytes()).digest()!=hashlib.sha256(target.read_bytes()).digest():
            different.append(rel)
        else:unchanged+=1
assert not different, different
camera=[]
for proc in Path('/proc').iterdir():
    if not proc.name.isdigit():continue
    try:
        args=(proc/'cmdline').read_bytes().decode().split('\0')
        if any(arg.endswith('/entry.py') and 'face-source-' in arg for arg in args):camera.append(int(proc.name))
    except (OSError,UnicodeError):pass
assert sorted(camera)==deployment['camera_pids_before']
isolation=json.loads((stage/'config_isolation.json').read_text())
pin=root/'aura/config/pan_manual.local.json'
assert hashlib.sha256(pin.read_bytes()).hexdigest()==isolation['pan_config_sha256']
value={'status':'PASS','effective_entry':effective,'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
       'phase':state['phase'],'audio_output_state':state['audio_output_state'],'error':state.get('error'),
       'monitor_enabled':hf['enabled'],'microphone_open':hf.get('microphone_open',False),
       'profile_mode':profile['mode'],'avatar_display':display,'camera_pids':sorted(camera),
       'manual_pan_state':state.get('manual_pan',{}).get('state'),'visual_bound':hf.get('visual_bound'),
       'feedback_ready':state['local_transcription']['service'].get('feedback_ready'),
       'unchanged_python_files_verified':unchanged,'unexpected_source_differences':different,
       'changed_source_sha256':{rel:hashlib.sha256((root/'aura'/rel).read_bytes()).hexdigest() for rel in c['changes']},
       'pan_config_sha256':isolation['pan_config_sha256'],'services':services,
       'watchdog_active':subprocess.run(['systemctl','is-active','aura-animation-dialogue-watchdog-'+stage.name[:10]+'.timer'],capture_output=True,text=True).stdout.strip(),
       'microphone_used':False,'physical_playback':False,'physical_motion':False}
assert value['watchdog_active']!='active'
print(json.dumps(value))
'''.replace('CANDIDATE', repr(c))
compile(script, '<final-live-check>', 'exec')
value = json.loads(ssh('python3 -B -', script, timeout=50))
value['checked_at_utc'] = datetime.now(timezone.utc).isoformat()
(HERE / 'live_runtime_verification.json').write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({k: v for k, v in value.items() if k not in ('changed_source_sha256', 'effective_entry')}))
