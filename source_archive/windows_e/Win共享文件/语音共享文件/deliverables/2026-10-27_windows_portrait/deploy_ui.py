"""Idle-only UI trial with independent rollback; no microphone or test playback."""
import base64,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))
assert json.loads((HERE/'full_gtk_smoke.json').read_text())['passed']
assert json.loads((HERE/'board_tests.json').read_text())['passed']
assert json.loads((HERE/'board_focused.json').read_text())['passed']
tested=json.loads((HERE/'board_focused.json').read_text())['source_text_sha256']
guardian=r'''
import json,subprocess,time
from pathlib import Path
stage=Path(STAGE);drop=Path(DROP)
if (stage/'committed').exists() or (stage/'trial_finished').exists():raise SystemExit(0)
if drop.exists() and str(stage) not in drop.read_text():raise SystemExit('Unrelated override; no rollback')
subprocess.run(['systemctl','stop','aura-avatar-ui.service'],capture_output=True,timeout=45)
if drop.exists():drop.unlink()
subprocess.run(['systemctl','daemon-reload'],check=True,capture_output=True,timeout=20)
subprocess.run(['systemctl','start','--no-block','aura-avatar-ui.service'],check=True,capture_output=True,timeout=20)
(stage/'watchdog_rollback.json').write_text(json.dumps({'reason':'UI trial was not committed','at':time.time()}))
'''
drop='/etc/systemd/system/aura-avatar-ui.service.d/'+'z'*32+'-aura-windows-portrait.conf'
guardian=guardian.replace('STAGE',repr(c['stage'])).replace('DROP',repr(drop))
script=r'''
import base64,hashlib,http.client,importlib.util,json,os,re,statistics,subprocess,time,urllib.request
from pathlib import Path
os.environ['PATH']='/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:'+os.environ.get('PATH','')
c=CANDIDATE;stage=Path(c['stage']);drop=Path(DROP);report={'status':'PREPARING','microphone':False,'test_playback':False}
for relative,digest in TESTED.items():
    assert hashlib.sha256((Path(c['runtime'])/'aura'/relative).read_text().encode()).hexdigest()==digest,('Untested candidate source',relative)
def save():
    (stage/'deployment.json').write_text(json.dumps(report,indent=2))
def get():
    for attempt in range(4):
        try:
            with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4) as r:return json.load(r)
        except (OSError,ValueError,http.client.HTTPException):
            if attempt==3:raise
            time.sleep(.15)
def idle():
    value=get();hf=value.get('handsfree_dialogue',{})
    assert value.get('phase')=='IDLE' and not value.get('playing') and not value.get('streaming_reply')
    assert value.get('audio_output_state')=='IDLE_READY' and hf.get('enabled') is False and not hf.get('microphone_open')
    assert not value.get('local_transcription',{}).get('service',{}).get('pending')
    pan=value.get('manual_pan',{})
    assert pan.get('automatic_following') is False,'User requested preserving ongoing follow; wait for it to finish'
    assert pan.get('state') not in ('MOVING','STOPPING') and not pan.get('readback',{}).get('active')
    return value
def camera_pids():
    found=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            args=(p/'cmdline').read_bytes().decode().split('\0')
            if any(x.endswith('/entry.py') and 'face-source-' in x for x in args):found.append(int(p.name))
        except (OSError,UnicodeError):pass
    return sorted(found)
def cpu():
    supervisor=int(subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True))
    args=Path('/proc/%d/cmdline'%supervisor).read_bytes().decode().split('\0')
    active_config=Path(args[args.index('--config')+1])
    runtime=Path(json.loads(active_config.read_text())['runtime'])
    pid=json.loads((runtime/'launch.json').read_text())['pid']
    fields=Path('/proc/%d/stat'%pid).read_text().split(') ',1)[1].split()
    return pid,int(fields[11])+int(fields[12])
def measure(seconds):
    rows=[];began=time.monotonic();pid,ticks=cpu()
    while time.monotonic()-began<seconds:
        value=idle();d=value.get('avatar_display',{})
        assert d.get('kind')=='native_sink_handoff' and d.get('age_ms',9999)<1000 and not value.get('error')
        if report.get('measuring_remote'):assert value.get('portrait_offload',{}).get('mode')=='remote','Remote portrait fallback during measurement'
        rows.append({'at':time.monotonic(),'display':{k:d.get(k) for k in ('received','fps','p95_ms','p99_ms','age_ms')},
                     'audio':value['audio_output_state']})
        time.sleep(1)
    endpid,endticks=cpu();assert endpid==pid
    elapsed=time.monotonic()-began
    return dict(rows=rows,fps=(rows[-1]['display']['received']-rows[0]['display']['received'])/(rows[-1]['at']-rows[0]['at']),
        p95_ms=statistics.median(r['display']['p95_ms'] for r in rows),p99_ms=statistics.median(r['display']['p99_ms'] for r in rows),
        cpu_percent=100*(endticks-ticks)/os.sysconf('SC_CLK_TCK')/elapsed)
def rollback():
    if drop.exists():
        assert str(stage) in drop.read_text()
        subprocess.run(['systemctl','stop','aura-avatar-ui.service'],capture_output=True,timeout=45)
        drop.unlink();subprocess.run(['systemctl','daemon-reload'],check=True,capture_output=True,timeout=20)
        subprocess.run(['systemctl','start','--no-block','aura-avatar-ui.service'],check=True,capture_output=True,timeout=20)
    report['status']='ROLLED_BACK';save()
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==c['boot']
def semantic_entry(text):
    argv=re.search(r'argv\[\]=(.*?);',text).group(1).strip()
    drops=next(line for line in text.splitlines() if line.startswith('DropInPaths='))
    return argv,drops
assert semantic_entry(subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart','-p','DropInPaths'],text=True))==semantic_entry(c['baseline_effective'])
assert not drop.exists()
for rel,digest in c['unchanged_python_sha256'].items():
    assert hashlib.sha256((Path(c['source_runtime'])/'aura'/rel).read_bytes()).hexdigest()==digest,('Upstream source changed',rel)
pref=Path('/root/.local/share/aura/handsfree_dialogue.json');pref_before=pref.read_bytes()
camera_before=camera_pids();report['camera_pids_before']=camera_before
isolated={'pan_config_sha256':c['original_pan_sha256']}
original_pan=Path(c['source_runtime'])/'aura/config/pan_manual.local.json'
assert hashlib.sha256(original_pan.read_bytes()).hexdigest()==isolated['pan_config_sha256']
spec=importlib.util.spec_from_file_location('checked_ui_launcher',Path(c['startup'])/'launcher.py')
launcher=importlib.util.module_from_spec(spec);spec.loader.exec_module(launcher)
cfg=json.loads((Path(c['startup'])/'config.json').read_text())
assert not launcher.display_retrain_needed(cfg),'Display retrain pending; honor paused display investigation'
baseline_until=time.monotonic()+90
while True:
    try:idle();break
    except (OSError,AssertionError,ValueError,http.client.HTTPException):
        if time.monotonic()>baseline_until:raise TimeoutError('Original UI idle readiness failed')
        time.sleep(.5)
report['pan_us_before']=idle().get('manual_pan',{}).get('pulse_us')
report['baseline']=measure(30);save()
baseline=report['baseline']
assert baseline['fps']>=7.6,'Current baseline below 8fps route; no switch'
idle();assert pref.read_bytes()==pref_before
assert hashlib.sha256(original_pan.read_bytes()).hexdigest()==isolated['pan_config_sha256']
launcher.preflight(cfg)
watchdog='aura-windows-portrait-watchdog-'+stage.name[:10]
finished=stage/'trial_finished'
if finished.exists():
    assert finished.read_text()=='ROLLED_BACK' and not (stage/'committed').exists()
    finished.unlink()
(stage/'guardian.py').write_bytes(base64.b64decode(GUARDIAN))
subprocess.run(['systemd-run','--unit='+watchdog,'--on-active=360','/usr/bin/python3','-B',str(stage/'guardian.py')],
    check=True,capture_output=True,timeout=20)
try:
    drop.write_text('[Service]\nExecStart=\nExecStart=/usr/bin/python3 -B '+c['startup']+'/launcher.py --config '+c['startup']+'/config.json\n')
    subprocess.run(['systemctl','daemon-reload'],check=True,capture_output=True,timeout=20)
    subprocess.run(['systemctl','restart','--no-block','aura-avatar-ui.service'],check=True,capture_output=True,timeout=20)
    until=time.monotonic()+110
    while True:
        try:
            value=idle()
            effective=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart'],text=True)
            if c['startup']+'/launcher.py' in effective and value.get('local_transcription',{}).get('service',{}).get('profile_memory',{}).get('mode')=='guest' and value.get('portrait_offload',{}).get('mode')=='remote':break
        except (OSError,AssertionError,ValueError,http.client.HTTPException):pass
        if time.monotonic()>until:raise TimeoutError('Candidate UI readiness failed')
        time.sleep(.5)
    warm_until=time.monotonic()+25
    while time.monotonic()<warm_until:idle();time.sleep(.5)
    report['measuring_remote']=True
    report['trial']=measure(40);trial=report['trial']
    gate={'min_fps':11.4,'max_p95_ms':104.167,'max_p99_ms':166.667,'max_cpu_percent':max(150.,baseline['cpu_percent']*1.25+10)}
    report['gate']=gate
    assert trial['fps']>=gate['min_fps'] and trial['p95_ms']<=gate['max_p95_ms'] and trial['p99_ms']<=gate['max_p99_ms'] and trial['cpu_percent']<=gate['max_cpu_percent'],'UI regression gate failed'
    assert pref.read_bytes()==pref_before and camera_pids()==camera_before
    assert idle().get('manual_pan',{}).get('pulse_us')==report['pan_us_before'],'Pan readback changed during frame-only trial'
    assert hashlib.sha256(original_pan.read_bytes()).hexdigest()==isolated['pan_config_sha256']
    report.update(status='COMMITTED',camera_pids_after=camera_pids(),monitor_preference_preserved=True,
                  default_profile_mode='guest',native_video=True,physical_follow_tested=False,
                  strict_12fps_interval_target_passed=trial['p95_ms']<=104.167 and trial['p99_ms']<=166.667)
    (stage/'committed').write_text('Wired portrait 12fps native idle gates passed\n');save()
except Exception as exc:
    report['error']=type(exc).__name__+': '+str(exc);rollback();raise
finally:
    subprocess.run(['systemctl','stop',watchdog+'.timer',watchdog+'.service'],capture_output=True,timeout=20)
    (stage/'trial_finished').write_text(report['status'])
print(json.dumps(report))
'''.replace('CANDIDATE',repr(c)).replace('DROP',repr(drop)).replace('GUARDIAN',repr(base64.b64encode(guardian.encode()).decode())).replace('TESTED',repr(tested))
compile(script,'<ui-trial>','exec')
value=json.loads(ssh('python3 -B -',script,timeout=330))
(HERE/'deployment.json').write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in value.items() if k not in ('baseline','trial')}))
print(json.dumps({n:{k:v for k,v in value[n].items() if k!='rows'} for n in ('baseline','trial')}))
