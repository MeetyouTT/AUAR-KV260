"""Existing native UI and real PCM clock, with verified MCP01 playback muted."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '2026-10-18_board_dialogue'))
from board_ssh import ssh

c = json.loads((HERE / 'baseline_candidate.json').read_text(encoding='utf-8'))
script = r'''
import hashlib,json,os,statistics,subprocess,sys,time,urllib.request
from pathlib import Path
c=CANDIDATE;root=Path(c['runtime']);stage=Path(c['stage']);sys.path.insert(0,str(root/'aura'))
from tools.board_ui_settings import AlsaMixer
assert c['startup'] in subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart'],text=True)
assert json.loads((stage/'deployment.json').read_text())['status']=='COMMITTED'
def get():
    with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4) as f:return json.load(f)
def post(value):
    request=urllib.request.Request('http://127.0.0.1:8783/api/command',data=json.dumps(value).encode(),
        headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8783'})
    with urllib.request.urlopen(request,timeout=5) as f:result=json.load(f)
    assert result.get('ok'),result
    return result
def safe(s):
    p=s['manual_pan'];h=s['handsfree_dialogue']
    assert h['enabled'] is False and not h.get('microphone_open')
    assert p['automatic_following'] is False and p['state'] not in ('MOVING','STOPPING') and not p.get('readback',{}).get('active')
    assert p['pulse_us']==position
    assert not s.get('error'),s.get('error')
def wait_idle(seconds=8):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        s=get();safe(s)
        if s['phase']=='IDLE' and not s.get('playing') and s['audio_output_state']=='IDLE_READY':return s
        time.sleep(.1)
    raise TimeoutError('Muted test has not returned to idle')
def mixer_set(values):
    post({'type':'ui_settings','values':values});end=time.monotonic()+7
    while time.monotonic()<end:
        s=get();m=s['ui_settings']
        if m.get('available') and not m.get('pending') and all(m.get(k)==v for k,v in values.items()):
            direct=AlsaMixer().read()
            assert all(direct[k]==v for k,v in values.items())
            return s
        time.sleep(.1)
    raise TimeoutError('Playback mixer readback did not match')
before=get();position=before['manual_pan']['pulse_us'];safe(before)
assert before['phase']=='IDLE' and before['audio_output_state']=='IDLE_READY' and not before.get('playing')
assert before['cached_only'] is True
assert before['portrait_offload']['mode']=='remote'
original={k:before['ui_settings'][k] for k in ('volume','muted')}
assert before['ui_settings']['available'] and not before['ui_settings'].get('pending')
assert AlsaMixer().read()==original
finished=stage/'muted_probe_finished'
assert not finished.exists(),'Do not repeat the real PCM test without reviewing prior evidence'
guard=r"""
import json,time,urllib.request
from pathlib import Path
stage=Path(STAGE);original=ORIGINAL
if (stage/'muted_probe_finished').exists():raise SystemExit(0)
def get():
    with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4) as f:return json.load(f)
def post(value):
    request=urllib.request.Request('http://127.0.0.1:8783/api/command',data=json.dumps(value).encode(),headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8783'})
    with urllib.request.urlopen(request,timeout=5) as f:return json.load(f)
try:
    s=get()
    if s['phase']!='IDLE' or s.get('playing'):post({'type':'event','event':'cancel'})
    end=time.monotonic()+8
    while time.monotonic()<end:
        s=get()
        if s['phase']=='IDLE' and not s.get('playing') and s['audio_output_state']=='IDLE_READY':break
        time.sleep(.2)
    else:raise RuntimeError('Output still active; leave playback muted')
    post({'type':'ui_settings','values':original})
    (stage/'muted_probe_guard_restore.json').write_text(json.dumps({'restoration_requested':original}))
except Exception as exc:(stage/'muted_probe_guard_error.txt').write_text(repr(exc))
""".replace('STAGE',repr(str(stage))).replace('ORIGINAL',repr(original))
(stage/'muted_probe_guard.py').write_text(guard)
watchdog='aura-muted-portrait-'+stage.name[:10]
subprocess.run(['systemd-run','--unit='+watchdog,'--on-active=90','/usr/bin/python3','-B',str(stage/'muted_probe_guard.py')],check=True,capture_output=True,timeout=15)
report={'status':'RUNNING','scope':'real PCM playback clock and existing native sink with hardware playback muted',
        'original_mixer':original,'microphone':False,'motor_command_issued':False,'audible_playback':False}
rows=[];previews=set();began=time.monotonic();restored=False
try:
    mixer_set({'volume':0,'muted':True})
    report['mute_verified_directly']=True
    result=post({'type':'demo','index':3});report['command_id']=result['command_id']
    deadline=time.monotonic()+45;started=False
    while time.monotonic()<deadline:
        s=get();safe(s);m=s['ui_settings']
        assert m['muted'] and m['volume']==0 and not m.get('pending')
        assert s['portrait_offload']['selected']
        if s.get('playing') and s['phase']=='SPEAKING':started=True
        rows.append({'at':time.monotonic()-began,'phase':s['phase'],'state':s['state'],
            'audio_time':s.get('audio_time'),'mouth_level':s.get('mouth_level'),
            'received':s['avatar_display']['received'],'p95_ms':s['avatar_display']['p95_ms'],
            'p99_ms':s['avatar_display']['p99_ms'],'display_age_ms':s['avatar_display']['age_ms'],
            'mode':s['portrait_offload']['mode'],'target_fps':s['portrait_offload']['target_fps'],
            'max_audio_lag_ms':s['portrait_offload']['max_accepted_audio_lag_ms']})
        if started and s['phase']=='SPEAKING' and len(rows)%5==0:
            with urllib.request.urlopen('http://127.0.0.1:8783/api/frame',timeout=3) as f:image=f.read(2_000_000)
            previews.add(hashlib.sha256(image).hexdigest())
        if started and s['phase']=='IDLE' and not s.get('playing'):break
        time.sleep(.1)
    else:raise TimeoutError('Muted cached demo did not finish')
    speaking=[r for r in rows if r['phase']=='SPEAKING'];assert len(speaking)>25
    assert speaking[-1]['audio_time']>speaking[0]['audio_time']+3
    assert max(r['mouth_level'] or 0 for r in speaking)>min(r['mouth_level'] or 0 for r in speaking)
    assert len(previews)>3
    summary={'seconds':speaking[-1]['at']-speaking[0]['at'],
      'native_fps':(speaking[-1]['received']-speaking[0]['received'])/(speaking[-1]['at']-speaking[0]['at']),
      'p95_ms_median':statistics.median(r['p95_ms'] for r in speaking),
      'p99_ms_median':statistics.median(r['p99_ms'] for r in speaking),
      'max_audio_lag_ms':max(r['max_audio_lag_ms'] for r in speaking),
      'remote_fraction':sum(r['mode']=='remote' for r in speaking)/len(speaking),
      'unique_previews':len(previews)}
    # This is an observation under PCM load, not the 35-second native rate gate.
    report.update(status='PASS',speaking=summary,pan_readback_preserved=position,rows=rows)
except Exception as exc:
    report.update(status='FAIL',error=repr(exc),rows=rows)
finally:
    s=get()
    if s['phase']!='IDLE' or s.get('playing'):post({'type':'event','event':'cancel'})
    wait_idle();mixer_set(original);restored=True
    report['original_mixer_restored']=True;report['final_audio_output_state']='IDLE_READY'
    (stage/'muted_speech_probe.json').write_text(json.dumps(report,indent=2))
    finished.write_text(report['status'])
    subprocess.run(['systemctl','stop',watchdog+'.timer',watchdog+'.service'],capture_output=True,timeout=15)
print(json.dumps(report))
'''.replace('CANDIDATE', repr(c))
compile(script, '<muted-speech-probe>', 'exec')
value = json.loads(ssh('python3 -B -', script, timeout=80))
(HERE / 'baseline_speech.json').write_text(json.dumps(value, indent=2), encoding='utf-8')
print(json.dumps({key: item for key, item in value.items() if key != 'rows'}))
assert value['status'] == 'PASS'
