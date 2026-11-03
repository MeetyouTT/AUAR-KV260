"""Owned, guarded UI-only deployment; no microphone or motion resume."""
import base64,json,sys
from pathlib import Path
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((H/'candidate.json').read_text());assert json.loads((H/'board_tests.json').read_text())['returncode']==0
drop='/etc/systemd/system/aura-avatar-ui.service.d/'+'z'*40+'-aura-device-skills.conf'
guard=r'''
import subprocess
from pathlib import Path
s=Path(STAGE);p=Path(DROP)
if (s/'committed').exists() or (s/'rolled_back').exists():raise SystemExit(0)
if p.is_file() and str(s) in p.read_text():
 subprocess.run(['systemctl','stop','aura-avatar-ui.service'],timeout=40)
 p.unlink();subprocess.run(['systemctl','daemon-reload'],check=True,timeout=20)
 subprocess.run(['systemctl','start','--no-block','aura-avatar-ui.service'],check=True,timeout=20)
 (s/'rolled_back').write_text('Watchdog restored previous entry')
'''.replace('STAGE',repr(c['stage'])).replace('DROP',repr(drop))
script=r'''
import base64,hashlib,json,os,statistics,subprocess,time,urllib.request
from pathlib import Path
c=CANDIDATE;stage=Path(c['stage']);root=Path(c['runtime']);drop=Path(DROP)
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==c['boot']
assert c['source_startup'] in subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart'],text=True)
assert hashlib.sha256((Path(c['source_startup'])/'config.json').read_bytes()).hexdigest()==c['source_config_sha256']
assert not drop.exists(),'Deployment override already exists; inspect before retry'
for n,d in c['pins'].items():assert hashlib.sha256((root/'aura'/n).read_bytes()).hexdigest()==d,n
old=Path(c['source_runtime'])/'aura'
for p in (old/'config').rglob('*'):
 if p.is_file():assert (root/'aura'/p.relative_to(old)).read_bytes()==p.read_bytes(),str(p)
def state():
 with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4) as f:return json.load(f)
def idle():
 s=state();p=s['manual_pan'];h=s['handsfree_dialogue']
 assert p['automatic_following'] is False and p['state'] not in ('MOVING','STOPPING') and not p.get('readback',{}).get('active')
 assert h['enabled'] is False and not h.get('microphone_open')
 assert s['phase']=='IDLE' and not s.get('playing') and s['audio_output_state']=='IDLE_READY' and not s.get('error')
 assert not s['local_transcription']['service'].get('pending')
 return s
before=idle();time.sleep(.5);idle()
pref=Path('/root/.local/share/aura/handsfree_dialogue.json');preference=pref.read_bytes()
camera=subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','MainPID','--value'],text=True).strip()
if (stage/'rolled_back').exists():
 assert json.loads((stage/'deployment.json').read_text())['status']=='ROLLED_BACK'
 (stage/'rolled_back').unlink()
(stage/'guard.py').write_bytes(base64.b64decode(GUARD))
unit='aura-devices-guard-'+stage.name[:10]
subprocess.run(['systemd-run','--unit='+unit,'--on-active=300','/usr/bin/python3','-B',str(stage/'guard.py')],check=True,capture_output=True,timeout=20)
report={'status':'RUNNING','runtime':c['runtime'],'boot':c['boot'],'microphone_opened':False,'motor_command':False}
try:
 drop.write_text('[Service]\nExecStart=\nExecStart=/usr/bin/python3 -B '+c['startup']+'/launcher.py --config '+c['startup']+'/config.json\n')
 subprocess.run(['systemctl','daemon-reload'],check=True,capture_output=True,timeout=20)
 subprocess.run(['systemctl','restart','--no-block','aura-avatar-ui.service'],check=True,capture_output=True,timeout=20)
 deadline=time.monotonic()+150;error=''
 while time.monotonic()<deadline:
  try:
   s=idle();assert s['handsfree_dialogue'].get('entry_mode')=='wake_word'
   assert s['handsfree_dialogue']['visual_required'] is False
   assert s['portrait_offload']['mode']=='remote'
   break
  except Exception as exc:error=repr(exc);time.sleep(.5)
 else:raise TimeoutError('Candidate not ready: '+error)
 rows=[]
 for i in range(30):
  s=idle();d=s['avatar_display'];assert d['kind']=='native_sink_handoff' and d['age_ms']<1000
  assert s['portrait_offload']['mode']=='remote'
  rows.append(dict(at=time.monotonic(),received=d['received'],p95=d['p95_ms'],p99=d['p99_ms']));time.sleep(1)
 sample={'fps':(rows[-1]['received']-rows[0]['received'])/(rows[-1]['at']-rows[0]['at']),
         'p95_ms':statistics.median(r['p95'] for r in rows),'p99_ms':statistics.median(r['p99'] for r in rows)}
 report['sample']=sample
 assert sample['fps']>=15.2 and sample['p95_ms']<=78.125 and sample['p99_ms']<=125,'Existing 16fps gate failed'
 report['preservation']={'preference_equal':pref.read_bytes()==preference,
   'camera_before':camera,'camera_after':subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','MainPID','--value'],text=True).strip(),
   'pan_before':{k:before['manual_pan'].get(k) for k in ('state','pulse_us')},
   'pan_after':{k:s['manual_pan'].get(k) for k in ('state','pulse_us')},
   'mixer_before':{k:before['ui_settings'].get(k) for k in ('volume','muted')},
   'mixer_after':{k:s['ui_settings'].get(k) for k in ('volume','muted')},
   'ui_fields_changed':[k for k in before['ui_settings'] if before['ui_settings'].get(k)!=s['ui_settings'].get(k)]}
 preserved=report['preservation']
 assert preserved['preference_equal'],'Listening preference changed'
 assert preserved['camera_before']==preserved['camera_after'],'Camera process changed'
 assert preserved['pan_before']==preserved['pan_after'],'Mechanical state changed'
 assert preserved['mixer_before']==preserved['mixer_after'],'Mixer volume or mute changed'
 report.update(status='COMMITTED',entry_mode=s['handsfree_dialogue']['entry_mode'],camera_pid_preserved=camera,
               mechanical_state=s['manual_pan']['state'],listening=False,device_observer=s.get('device_observer'),visual_social=s.get('visual_social'))
 (stage/'committed').write_text('Voice independent of visual; listener paused; no motion resume')
except Exception as exc:
 report.update(status='ROLLED_BACK',error=repr(exc))
 subprocess.run(['python3','-B',str(stage/'guard.py')],check=True,capture_output=True,timeout=85)
finally:
 (stage/'deployment.json').write_text(json.dumps(report,indent=2))
 subprocess.run(['systemctl','stop',unit+'.timer',unit+'.service'],capture_output=True,timeout=20)
print(json.dumps(report))
'''.replace('CANDIDATE',repr(c)).replace('DROP',repr(drop)).replace('GUARD',repr(base64.b64encode(guard.encode()).decode()))
v=json.loads(ssh('python3 -B -',script,timeout=280));(H/'deployment.json').write_text(json.dumps(v,indent=2));print(json.dumps(v));assert v['status']=='COMMITTED'
