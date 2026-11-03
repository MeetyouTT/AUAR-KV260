"""Limited performance trial, independent timed rollback and explicit regression gates."""
import json,base64,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'budget_candidate.json').read_text());v=json.loads((HERE/'budget_verification.json').read_text());assert v['passed']
guardian=r'''
import json,subprocess,time
from pathlib import Path
p=Path(STAGE);drop=Path('/etc/systemd/system/aura-avatar-ui.service.d/zz-aura-render-budget-trial.conf')
if (p/'committed').exists() or not drop.exists():raise SystemExit(0)
if str(p) not in drop.read_text():raise SystemExit('Unrelated override; refusing rollback')
subprocess.run(['systemctl','stop','aura-avatar-ui.service'],timeout=40,capture_output=True)
drop.unlink();subprocess.run(['systemctl','daemon-reload'],check=True,timeout=20)
subprocess.run(['systemctl','start','--no-block','aura-avatar-ui.service'],check=True,timeout=20)
(p/'watchdog_rollback.json').write_text(json.dumps({'reason':'Trial was not committed before deadline','at':time.time()}))
'''.replace('STAGE',repr(c['stage']),1)
remote=r'''
import json,subprocess,time,urllib.request,hashlib,statistics,base64,os
from pathlib import Path
c=CANDIDATE;stage=Path(c['stage']);drop=Path('/etc/systemd/system/aura-avatar-ui.service.d/zz-aura-render-budget-trial.conf');assert not drop.exists()
assert subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart','-p','DropInPaths'],text=True)==c['baseline_effective'],'Actual startup changed'
assert hashlib.sha256((Path(c['runtime'])/'aura/tools/libaura_pixels.so').read_bytes()).hexdigest()==c['library_sha256']
def get(port=8783,path='/api/state'):
 return json.load(urllib.request.urlopen('http://127.0.0.1:%d%s'%(port,path),timeout=4))
def idle():
 s=get();assert s['phase']=='IDLE' and not s['playing'] and not s['paused']
 assert not s.get('handsfree_dialogue',{}).get('microphone_open')
 assert s.get('local_recording',{}).get('state')!='RECORDING'
 assert not s.get('local_transcription',{}).get('service',{}).get('pending')
 return s
def pid_cpu():
 for q in Path('/proc').iterdir():
  if not q.name.isdigit():continue
  try:
   cmd=(q/'cmdline').read_bytes().decode().split('\0')
   if any(x.endswith('/tools/board_avatar_pan.py') for x in cmd):
    stat=(q/'stat').read_text().split(') ',1)[1].split();return int(q.name),int(stat[11])+int(stat[12])
  except (OSError,UnicodeError):pass
 raise RuntimeError('Pan UI process unavailable')
def measure(seconds,gate=None):
 rows=[];started=time.monotonic();pid,ticks=pid_cpu();hz=os.sysconf('SC_CLK_TCK');bad=0
 while time.monotonic()-started<seconds:
  s=get();d=s['avatar_display'];assert not s.get('error'),s.get('error');assert s.get('audio_output_state') not in ('ERROR','FAILED')
  assert d.get('kind')=='native_sink_handoff' and d.get('age_ms',0)<1000,'Display stalled'
  rows.append({'at':time.monotonic(),'phase':s['phase'],'display':d,'renderer':s['avatar_renderer'],'handsfree':s['handsfree_dialogue'],'audio':s.get('audio_output_state')})
  if gate:
   bad=bad+1 if d['fps']<gate['min_fps'] or d['p95_ms']>gate['max_p95_ms'] else 0
   if bad>=5:raise RuntimeError('10-second rolling performance regression')
  time.sleep(2)
 endpid,endticks=pid_cpu();assert endpid==pid,'UI process restarted'
 fps=(rows[-1]['display']['received']-rows[0]['display']['received'])/(rows[-1]['at']-rows[0]['at'])
 return {'rows':rows,'fps':fps,'p95_ms':statistics.median(r['display']['p95_ms'] for r in rows),'cpu_percent':100*(endticks-ticks)/hz/(time.monotonic()-started)}
before=idle();camera=get(8790,'/health');pref=Path('/root/.local/share/aura/handsfree_dialogue.json');pref_before=pref.read_bytes();camera_unit=subprocess.check_output(['systemctl','cat','aura-camera-ui.service'],text=True)
report={'candidate':c,'before_handsfree':before['handsfree_dialogue'],'camera_pid_before':camera['pid'],'state':'PREPARING'}
baseline=measure(30);report['baseline']=baseline
gate={'min_fps':max(15,baseline['fps']*.95),'max_p95_ms':baseline['p95_ms']*1.10};report['gate']=gate
(stage/'baseline.json').write_text(json.dumps(report,indent=2))
if baseline['fps']<15:
 report.update(state='POSTPONED',error='Baseline below 15fps; no service mutation')
 (stage/'trial.json').write_text(json.dumps(report,indent=2));print(json.dumps(report));raise SystemExit(0)
idle();assert pref.read_bytes()==pref_before,'User preference changed during baseline'
(stage/'guardian.py').write_bytes(base64.b64decode(GUARDIAN));assert not (stage/'committed').exists()
watchdog='aura-budget-watchdog-'+stage.name
subprocess.run(['systemd-run','--unit='+watchdog,'--on-active=360','/usr/bin/python3','-B',str(stage/'guardian.py')],check=True,capture_output=True,timeout=20)
def rollback():
 subprocess.run(['systemctl','stop','aura-avatar-ui.service'],capture_output=True,timeout=40)
 if drop.exists():
  assert str(stage) in drop.read_text();drop.unlink()
 subprocess.run(['systemctl','daemon-reload'],check=True,timeout=20);subprocess.run(['systemctl','start','--no-block','aura-avatar-ui.service'],check=True,timeout=20)
try:
 subprocess.run(['systemctl','stop','aura-avatar-ui.service'],check=True,capture_output=True,timeout=40)
 assert pref.read_bytes()==pref_before,'Shutdown changed preference'
 drop.write_text('[Service]\nExecStart=\nExecStart=/usr/bin/python3 -B '+c['startup']+'/launcher.py --config '+c['startup']+'/config.json\n');drop.chmod(0o644)
 subprocess.run(['systemctl','daemon-reload'],check=True,timeout=20);subprocess.run(['systemctl','start','--no-block','aura-avatar-ui.service'],check=True,timeout=20)
 deadline=time.monotonic()+180
 while time.monotonic()<deadline:
  try:
   s=get()
   if s.get('audio_output_state')=='IDLE_READY' and s.get('avatar_display',{}).get('received',0)>240:break
  except (OSError,ValueError):pass
  time.sleep(1)
 else:raise RuntimeError('Candidate startup timed out')
 trial=measure(60,gate);report['trial']=trial
 assert trial['fps']>=gate['min_fps'] and trial['p95_ms']<=gate['max_p95_ms'],'Aggregate performance regression'
 improvement=trial['fps']>=baseline['fps']*1.05 or trial['p95_ms']<=baseline['p95_ms']*.90 or trial['cpu_percent']<=baseline['cpu_percent']*.90
 assert improvement,'No measurable benefit; keep existing version'
 assert pref.read_bytes()==pref_before,'User preference changed'
 assert get(8790,'/health')['pid']==camera['pid'],'Camera restarted'
 assert subprocess.check_output(['systemctl','cat','aura-camera-ui.service'],text=True)==camera_unit
 assert get()['handsfree_dialogue']['voice_barge_in']==before['handsfree_dialogue']['voice_barge_in']
 (stage/'committed').write_text('Performance and preservation gates passed\n');report['state']='COMMITTED'
except Exception as exc:
 report.update(state='ROLLED_BACK',error=type(exc).__name__+': '+str(exc));rollback()
finally:
 subprocess.run(['systemctl','stop',watchdog+'.timer'],capture_output=True,timeout=20)
 (stage/'trial.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
'''.replace('CANDIDATE',repr(c),1).replace('GUARDIAN',repr(base64.b64encode(guardian.encode()).decode()),1)
r=json.loads(ssh('python3 -B -',remote,timeout=390));(HERE/'budget_trial.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in r.items() if k not in ('baseline','trial')}));print(json.dumps({key:{k:v for k,v in r[key].items() if k!='rows'} for key in ('baseline','trial') if key in r}))
