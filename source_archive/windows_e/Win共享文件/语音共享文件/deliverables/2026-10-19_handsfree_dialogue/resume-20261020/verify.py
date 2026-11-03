"""Verify active UI source and unchanged camera; observe without injecting audio."""
import hashlib,json,sys,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))
d=json.loads((HERE/'deployment.json').read_text(encoding='utf-8'))
assert d['status']=='UI_ONLY_DEPLOYED'
remote=r'''
import hashlib,json,re,subprocess,time,urllib.request
from pathlib import Path
c=CANDIDATE;d=DEPLOYMENT;root=Path(c['runtime'])
def get(port,path):return json.load(urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=4))
unit=lambda name:subprocess.check_output(['systemctl','cat',name],text=True)
assert unit('aura-avatar-ui.service')==d['ui_unit']
assert unit('aura-camera-ui.service')==d['camera_unit']
for n,sha in dict(c['files'],**c['preserved']).items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==sha,n
camera_path=Path(re.search(r'--config (\S+)',d['camera_unit']).group(1))
assert hashlib.sha256(camera_path.read_bytes()).hexdigest()==d['camera_config_sha256']
identity_path=Path(json.loads(camera_path.read_text())['identity']['config'])
assert hashlib.sha256(identity_path.read_bytes()).hexdigest()==d['identity_config_sha256']
db=Path(json.loads(identity_path.read_text())['database']).expanduser()
assert hashlib.sha256(db.read_bytes()).hexdigest()==d['identity_db_sha256']
rows=[];end=time.monotonic()+10
while time.monotonic()<end:
 u=get(8783,'/api/state');hf=u['handsfree_dialogue']
 assert 'diagnostics' in hf
 rows.append({'handsfree':hf,'recording':u['local_recording']['state'],'playing':u['playing'],
  'transcription':u['local_transcription']['state'],'completed_turns':u['automatic_conversation']['completed_turns']})
 time.sleep(.25)
cam=get(8790,'/health');assert cam['pid']==d['camera_pid']
pref=json.loads(Path(d['preference_path']).read_text())
print(json.dumps({'status':'ACTIVE_UI_VERIFIED','runtime':str(root),'camera_pid':cam['pid'],
 'camera_unchanged':True,'identity_database_unchanged':True,'preserved_source_count':len(c['preserved']),
 'active_ui_pid':int(subprocess.check_output(['systemctl','show','-p','MainPID','--value','aura-avatar-ui.service'],text=True)),
 'monitor_preference':pref,'passive_observation':rows,'human_hearing_verified':False,
 'test_audio_injected':False,'actual_microphone_recording_started_by_operator':False}))
'''.replace('CANDIDATE',repr(c),1).replace('DEPLOYMENT',repr(d),1)
r=json.loads(ssh('python3 -B -',remote,timeout=40))
(HERE/'active_verification.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
with zipfile.ZipFile(HERE/'verified_changes.zip','w',zipfile.ZIP_DEFLATED) as z:
 for n,sha in c['files'].items():
  source=HERE/'merged_sources'/n
  if not source.exists():source=ROOT/n
  raw=source.read_bytes();assert hashlib.sha256(raw).hexdigest()==sha;z.writestr(n,raw)
 z.writestr('manifest.json',json.dumps(c['files'],indent=2))
print(json.dumps({k:v for k,v in r.items() if k!='passive_observation'}))
print(json.dumps({'states':sorted({row['handsfree']['state'] for row in r['passive_observation']}),
 'latest':r['passive_observation'][-1]}))
