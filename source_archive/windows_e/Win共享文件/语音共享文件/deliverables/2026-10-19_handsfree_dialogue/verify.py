"""Active source/config audit plus bounded passive observation, no test audio."""
import hashlib,json,sys,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))
b=json.loads((HERE/'before_state.json').read_text(encoding='utf-8'))
d=json.loads((HERE/'deployment.json').read_text(encoding='utf-8'))
assert d['status']=='HANDS_FREE_AV_ENTRY_DEPLOYED'
remote=r'''
import hashlib,json,re,subprocess,time,urllib.request
from pathlib import Path
c=CANDIDATE;b=BEFORE;root=Path(c['runtime'])
get=lambda port,path:json.load(urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=4))
assert c['startup']+'/config.json' in subprocess.check_output(['systemctl','cat','aura-avatar-ui.service'],text=True)
assert c['camera_config'] in subprocess.check_output(['systemctl','cat','aura-camera-ui.service'],text=True)
for name,sha in c['files'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==sha,name
cfg=json.loads(Path(c['camera_config']).read_text());icfg=json.loads(Path(cfg['identity']['config']).read_text())
assert icfg==b['identity_config']
cfg['identity']['config']=b['camera_config']['identity']['config'];assert cfg==b['camera_config']
db=Path(icfg['database']).expanduser();assert hashlib.sha256(db.read_bytes()).hexdigest()==b['identity_db_sha256']
sys_path=__import__('sys').path;sys_path.insert(0,str(root/'aura'))
from board.interaction.ui_contract import validate_snapshot,millis
rows=[];deadline=time.monotonic()+12
while time.monotonic()<deadline:
 u=get(8783,'/api/state');s=validate_snapshot(get(8790,'/v1/ui/status'),Path('/proc/sys/kernel/random/boot_id').read_text().strip(),millis())
 hf=u['handsfree_dialogue'];identity=s['modules']['identity'];a=identity.get('face_attention')
 rows.append({'observed_mono_ms':millis(),'face_count':identity.get('face_count'),
  'attention_present':a is not None,'frontal':a['frontal'] if a else None,
  'source_age_ms':millis()-a['captured_mono_ms'] if a else None,
  'handsfree':hf,'recording':u['local_recording']['state'],'playing':u['playing'],
  'transcription_state':u['local_transcription']['state'],'automatic':u['automatic_conversation']})
 time.sleep(.25)
cam=get(8790,'/health')
print(json.dumps({'status':'PASS_ACTIVE_HANDSFREE_SOURCE_AND_CONFIG','runtime':str(root),
 'threshold_preserved':icfg['threshold'],'identity_database_unchanged':True,
 'camera_pid':cam['pid'],'camera_identity_ready':cam['identity']['ready'],
 'photos':cam['identity']['enrollment_photos'],'passive_observation':rows,
 'human_declared_test':False,'operator_started_recording':False,'startup_config':Path(c['startup']+'/config.json').read_text()}))
'''.replace('CANDIDATE',repr(c),1).replace('BEFORE',repr(b),1)
r=json.loads(ssh('python3 -B -',remote,timeout=45));startup=r.pop('startup_config')
(HERE/'source_verification.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
manifest={}
with zipfile.ZipFile(HERE/'verified_source.zip','w',zipfile.ZIP_DEFLATED) as archive:
 for name,sha in c['files'].items():
  raw=(ROOT/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==sha,name
  archive.writestr(name,raw);manifest[name]={'sha256':sha,'bytes':len(raw)}
 archive.writestr('startup_config.json',startup)
 archive.writestr('source_manifest.json',json.dumps(manifest,indent=2))
(HERE/'source_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps({k:r[k] for k in ('status','runtime','threshold_preserved','camera_pid','camera_identity_ready')}))
print(json.dumps({'passive_states':sorted(set(row['handsfree']['state'] for row in r['passive_observation'])),
                  'frames_with_attention':sum(row['attention_present'] for row in r['passive_observation']),
                  'human_test':False}))
