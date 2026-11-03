"""Replace only our existing override for the verified settings layout fix."""
import base64
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '2026-10-18_board_dialogue'))
from board_ssh import ssh

c = json.loads((HERE / 'candidate.json').read_text(encoding='utf-8'))
assert json.loads((HERE / 'board_focused.json').read_text(encoding='utf-8'))['passed']
assert set(c['performance_changed']) == {'tools/board_avatar_worker.py','tools/render_performance.py'}
guard = r'''
import subprocess
from pathlib import Path
stage=Path(STAGE);drop=Path(DROP)
if (stage/'committed').exists() or (stage/'layout_trial_finished').exists():raise SystemExit(0)
assert drop.exists() and str(stage) in drop.read_text(),'Override ownership changed; do not overwrite'
subprocess.run(['systemctl','stop','aura-avatar-ui.service'],capture_output=True,timeout=45)
drop.write_bytes((stage/'previous_override.conf').read_bytes())
subprocess.run(['systemctl','daemon-reload'],check=True,capture_output=True,timeout=20)
subprocess.run(['systemctl','start','--no-block','aura-avatar-ui.service'],check=True,capture_output=True,timeout=20)
(stage/'layout_watchdog_rollback').write_text('Restored the previously accepted 16fps UI')
'''
drop = '/etc/systemd/system/aura-avatar-ui.service.d/' + 'z' * 32 + '-aura-windows-portrait.conf'
guard = guard.replace('STAGE', repr(c['stage'])).replace('DROP', repr(drop))
script = r'''
import base64,hashlib,http.client,importlib.util,json,os,statistics,subprocess,time,urllib.request
from pathlib import Path
c=CANDIDATE;old=c['previous_candidate'];stage=Path(c['stage']);root=Path(c['runtime']);drop=Path(DROP)
os.environ['PATH']='/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==c['boot']
assert old['startup'] in subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart'],text=True)
assert drop.is_file() and old['startup'] in drop.read_text()
assert not (stage/'committed').exists()
assert hashlib.sha256((root/'aura/tools/board_avatar_gtk.py').read_text().encode()).hexdigest()==c['gui_text_sha256']
for package in ('tools','board','common','host'):
    for p in (Path(old['runtime'])/'aura'/package).rglob('*.py'):
        rel=p.relative_to(Path(old['runtime'])/'aura')
        if rel.as_posix() in c['performance_changed']:continue
        assert (root/'aura'/rel).read_bytes()==p.read_bytes(),str(rel)
for rel,digest in c['performance_sha256'].items():assert hashlib.sha256((root/'aura'/rel).read_bytes()).hexdigest()==digest,rel
old_cfg=json.loads((Path(old['startup'])/'config.json').read_text())
for rel,digest in old_cfg['component_sha256'].items():
    assert hashlib.sha256((Path(old['runtime'])/'aura'/rel).read_bytes()).hexdigest()==digest,rel
cfg=json.loads((Path(c['startup'])/'config.json').read_text())
spec=importlib.util.spec_from_file_location('layout_ui_launcher',Path(c['startup'])/'launcher.py')
launcher=importlib.util.module_from_spec(spec);spec.loader.exec_module(launcher)
assert not launcher.display_retrain_needed(cfg)
launcher.preflight(cfg)
ui_cfg=json.loads((root/'aura/config/board_avatar_gtk.json').read_text())
assert ui_cfg['portrait_offload']['fps']==16 and ui_cfg['stable_avatar_fps']==16
def state():
    for attempt in range(3):
        try:
            with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4) as f:return json.load(f)
        except (OSError,ValueError,http.client.HTTPException):
            if attempt==2:raise
            time.sleep(.15)
def idle():
    s=state();p=s['manual_pan'];h=s['handsfree_dialogue']
    assert s['phase']=='IDLE' and s['audio_output_state']=='IDLE_READY' and not s.get('error') and not s.get('playing')
    assert h['enabled'] is False and not h.get('microphone_open')
    assert p['automatic_following'] is False and p['state'] not in ('MOVING','STOPPING') and not p.get('readback',{}).get('active')
    return s
def cameras():
    rows=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            args=(p/'cmdline').read_bytes().decode().split('\0')
            if any('face-source-' in x and x.endswith('/entry.py') for x in args):rows.append(int(p.name))
        except (OSError,UnicodeError):pass
    return sorted(rows)
before=idle();time.sleep(.5);idle();pan_before=before['manual_pan']['pulse_us'];camera_before=cameras()
pref=Path('/root/.local/share/aura/handsfree_dialogue.json');preference= pref.read_bytes()
previous=drop.read_bytes();(stage/'previous_override.conf').write_bytes(previous)
finished=stage/'layout_trial_finished'
if finished.exists():
    assert finished.read_text()=='ROLLED_BACK','Unexpected prior trial status'
    finished.unlink()
old_pid=int(subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True).strip())
(stage/'layout_guard.py').write_bytes(base64.b64decode(GUARD))
watchdog='aura-portrait-layout-'+stage.name[-10:]
subprocess.run(['systemd-run','--unit='+watchdog,'--on-active=300','/usr/bin/python3','-B',str(stage/'layout_guard.py')],check=True,capture_output=True,timeout=20)
report={'status':'RUNNING','previous_stage':old['stage'],'stage':c['stage'],'target_fps':16,
        'changed':c['performance_changed'],'other_sources_unchanged':True,'gui_text_sha256':c['gui_text_sha256'],'performance_sha256':c['performance_sha256']}
try:
    assert drop.read_bytes()==previous
    drop.write_text('[Service]\nExecStart=\nExecStart=/usr/bin/python3 -B '+c['startup']+'/launcher.py --config '+c['startup']+'/config.json\n')
    subprocess.run(['systemctl','daemon-reload'],check=True,capture_output=True,timeout=20)
    subprocess.run(['systemctl','restart','--no-block','aura-avatar-ui.service'],check=True,capture_output=True,timeout=20)
    end=time.monotonic()+150;last_ready_error=None
    while time.monotonic()<end:
        try:
            new_pid=int(subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True).strip())
            assert new_pid>0 and new_pid!=old_pid
            assert str(Path(c['startup'])/'launcher.py') in Path('/proc/'+str(new_pid)+'/cmdline').read_bytes().decode().split('\0')
            s=idle()
            if s['portrait_offload']['mode']=='remote' and s['portrait_offload']['target_fps']==16:break
        except (OSError,ValueError,KeyError,AssertionError,http.client.HTTPException) as exc:
            last_ready_error=repr(exc)
            try:
                detail=state();report['last_readiness']={k:detail.get(k) for k in ('phase','audio_output_state','error','manual_pan','portrait_offload')}
            except (OSError,ValueError,http.client.HTTPException):pass
        time.sleep(.5)
    else:raise TimeoutError('Candidate readiness failed: '+str(last_ready_error))
    end=time.monotonic()+20
    while time.monotonic()<end:idle();time.sleep(.5)
    rows=[];end=time.monotonic()+35
    while time.monotonic()<end:
        s=idle();d=s['avatar_display'];assert s['portrait_offload']['mode']=='remote'
        assert d['age_ms']<1000 and d['kind']=='native_sink_handoff'
        rows.append(dict(at=time.monotonic(),received=d['received'],p95_ms=d['p95_ms'],p99_ms=d['p99_ms']))
        time.sleep(1)
    sample={'fps':(rows[-1]['received']-rows[0]['received'])/(rows[-1]['at']-rows[0]['at']),
            'p95_ms':statistics.median(x['p95_ms'] for x in rows),'p99_ms':statistics.median(x['p99_ms'] for x in rows)}
    report.update(sample=sample,rows=rows)
    assert sample['fps']>=15.2 and sample['p95_ms']<=78.125 and sample['p99_ms']<=125.,'Original 16fps gate failed'
    s=idle();assert s['manual_pan']['pulse_us']==pan_before and cameras()==camera_before
    assert pref.read_bytes()==preference
    assert s['ui_settings']['volume']==before['ui_settings']['volume'] and s['ui_settings']['muted']==before['ui_settings']['muted']
    assert s['local_transcription']['service']['profile_memory']['mode']=='guest'
    report.update(status='COMMITTED',pan_us_preserved=pan_before,camera_pids_preserved=camera_before,
                  listener_preserved=False,mixer_preserved=True,microphone=False,motor_command_issued=False)
    (stage/'committed').write_text('16fps remote handoff trial passed; mechanical FAULT preserved\n')
except Exception as exc:
    report.update(status='ROLLED_BACK',error=repr(exc))
    assert c['startup'] in drop.read_text()
    subprocess.run(['systemctl','stop','aura-avatar-ui.service'],capture_output=True,timeout=45)
    drop.write_bytes(previous);subprocess.run(['systemctl','daemon-reload'],check=True,capture_output=True,timeout=20)
    subprocess.run(['systemctl','start','--no-block','aura-avatar-ui.service'],check=True,capture_output=True,timeout=20)
finally:
    (stage/'deployment.json').write_text(json.dumps(report,indent=2))
    (stage/'layout_trial_finished').write_text(report['status'])
    subprocess.run(['systemctl','stop',watchdog+'.timer',watchdog+'.service'],capture_output=True,timeout=20)
print(json.dumps(report))
'''.replace('CANDIDATE', repr(c)).replace('DROP', repr(drop)).replace('GUARD', repr(base64.b64encode(guard.encode()).decode()))
compile(script, '<layout-native-trial>', 'exec')
v = json.loads(ssh('python3 -B -', script, timeout=285))
(HERE / 'layout_deployment.json').write_text(json.dumps(v, indent=2), encoding='utf-8')
print(json.dumps({key: value for key, value in v.items() if key != 'rows'}))
assert v['status'] == 'COMMITTED'
