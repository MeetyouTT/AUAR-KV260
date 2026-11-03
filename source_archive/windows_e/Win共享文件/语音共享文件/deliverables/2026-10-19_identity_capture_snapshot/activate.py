"""Switch only idle UI to fresh-face voice queries, with rollback and DB guards."""
import hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))
p=json.loads((HERE/'preflight.json').read_text(encoding='utf-8'))
assert c['tests_passed'] and c['preflight_passed'] and all(p[k] for k in ('capture_source_passed','bootstrap_passed'))
for name,sha in c['files'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha,name
remote=r'''
import hashlib,json,os,re,sqlite3,subprocess,time,urllib.request,uuid
from pathlib import Path
c=CANDIDATE;stage=Path(c['stage']);root=Path(c['runtime'])
assert root.parent==stage and stage.parent==Path('/home/root/aura-identity-capture-snapshot-20261019')
get=lambda port,path,host='127.0.0.1':json.load(urllib.request.urlopen('http://'+host+':'+str(port)+path,timeout=4))
def idle():
 s=get(8783,'/api/state');assert s['phase']=='IDLE' and not s['playing'] and not s['paused']
 assert s['local_recording']['state']!='RECORDING' and not s['local_transcription']['service']['pending']
 assert not s['automatic_conversation']['enabled'];assert not s['local_transcription']['service']['voice_enrollment']['active'];return s
idle();camera=get(8790,'/health');pc=get(8792,'/health','192.168.50.1')
assert pc['ready'] and not pc['busy'] and pc['identity_voice_enrollment']['identity_query_version']==1 and pc['identity_voice_enrollment'].get('identity_query_intent_revision')==2
assert camera['identity']['enrollment_photos']['enabled'] and camera['identity']['enrollment_photos']['ready']
assert pc['identity_features']['ready'] and pc['llm_model']=='aura-qwen3.8-27b-abliterated:iq4_xs' and pc['num_step']==16
camera_unit=subprocess.check_output(['systemctl','cat','aura-camera-ui.service'],text=True)
args=Path('/proc/%d/cmdline'%camera['pid']).read_bytes().decode().split('\0')
camera_path=Path(args[args.index('--config')+1]);assert str(camera_path)==c['old_camera_config']
identity_path=Path(json.loads(camera_path.read_text())['identity']['config']);identity_raw=identity_path.read_bytes();cfg=json.loads(identity_raw)
assert cfg['threshold']==.8 and cfg['ambiguity_margin']==.1
db=Path(cfg['database']).expanduser();db_hash=hashlib.sha256(db.read_bytes()).hexdigest()
def counts():
 with sqlite3.connect('file:'+str(db)+'?mode=ro',uri=True) as conn:
  return {'identities':conn.execute('SELECT count(*) FROM identities').fetchone()[0],
   'templates':conn.execute('SELECT count(*) FROM templates').fetchone()[0],
   'revision':conn.execute("SELECT value FROM metadata WHERE key='revision'").fetchone()[0]}
db_before=counts();assert db_before=={'identities':1,'templates':1,'revision':14}
for n,sha in c['files'].items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==sha,n
preserved={n:hashlib.sha256((root/n).read_bytes()).hexdigest()==hashlib.sha256((Path(c['source_runtime'])/n).read_bytes()).hexdigest()
 for n in ('aura/config/board_avatar_gtk.json','aura/board/vision/person_bytetrack.py',
  'aura/tools/streaming_controller.py','aura/tools/gstreamer_persistent_engine.py')}
assert all(preserved.values())
unit_path=Path('/etc/systemd/system/aura-avatar-ui.service');old=unit_path.read_bytes()
assert c['old_ui_config'] in old.decode();link=os.readlink(unit_path) if unit_path.is_symlink() else None
backup=stage/('activation-backup-'+uuid.uuid4().hex[:10]);backup.mkdir();(backup/unit_path.name).write_bytes(old)
(backup/'rollback.json').write_text(json.dumps({'unit_link':link,'previous_config':c['old_ui_config']},indent=2))
for source in Path(c['source_runtime']).glob('*_settings.json'):
 target=root/source.name;assert not target.is_symlink();target.write_bytes(source.read_bytes())
unit=old.decode().replace(c['source_runtime'],str(root))
unit=re.sub(r'^ExecStart=.*$','ExecStart=/usr/bin/python3 -B '+c['startup']+'/launcher.py --config '+c['startup']+'/config.json',unit,flags=re.M)
def run(args,timeout=35):return subprocess.run(args,check=True,capture_output=True,text=True,timeout=timeout)
def atomic(raw):
 p=unit_path.with_name(unit_path.name+'.spoken-query-tmp');p.write_bytes(raw);p.chmod(0o644);os.replace(p,unit_path)
report={'runtime':str(root),'backup':str(backup),'camera_before':camera,'pc_health':pc,
 'camera_service_restarted':False,'database_before':db_before,'threshold':cfg['threshold'],
 'preserved_source_config':preserved,'templates_exported':False,'photos_exported':False}
try:
 idle();run(['systemctl','stop','aura-avatar-ui.service']);atomic(unit.encode());run(['systemctl','daemon-reload'])
 run(['systemctl','start','--no-block','aura-avatar-ui.service'])
 deadline=time.monotonic()+170
 while time.monotonic()<deadline:
  try:
   state=get(8783,'/api/state');active=run(['systemctl','is-active','aura-avatar-ui.service'],5).stdout.strip()
   if active=='active' and state.get('audio_output_state')=='IDLE_READY' and state['automatic_conversation']['can_start']:
    flow=state['local_transcription']['service'].get('voice_enrollment')
    if flow is not None:break
  except (OSError,ValueError,subprocess.CalledProcessError):pass
  time.sleep(.5)
 else:raise RuntimeError('Spoken identity query UI did not become ready')
 assert counts()==db_before and hashlib.sha256(db.read_bytes()).hexdigest()==db_hash
 assert identity_path.read_bytes()==identity_raw
 assert subprocess.check_output(['systemctl','cat','aura-camera-ui.service'],text=True)==camera_unit
 report.update(status='IDENTITY_CAPTURE_SOURCE_FIXED_PHOTO_CAMERA_PRESERVED',ui_phase=state['phase'],flow=flow,
   automatic=state['automatic_conversation'],database_after=counts(),database_hash_unchanged=True)
except Exception as exc:
 subprocess.run(['systemctl','stop','aura-avatar-ui.service'],capture_output=True,timeout=35)
 if link:
  path=unit_path.with_name(unit_path.name+'.spoken-query-rollback');path.symlink_to(link);os.replace(path,unit_path)
 else:atomic(old)
 run(['systemctl','daemon-reload']);run(['systemctl','start','--no-block','aura-avatar-ui.service'])
 report.update(status='ROLLED_BACK',error=type(exc).__name__+': '+str(exc))
after=get(8790,'/health');report['camera_after']=after;report['camera_pid_preserved']=after['pid']==camera['pid']
(stage/'deployment.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
'''.replace('CANDIDATE',repr(c),1)
r=json.loads(ssh('python3 -B -',remote,timeout=240))
(HERE/'deployment.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in r.items() if k not in ('camera_before','camera_after','pc_health')},ensure_ascii=True))
assert r['status']=='IDENTITY_CAPTURE_SOURCE_FIXED_PHOTO_CAMERA_PRESERVED' and r['camera_pid_preserved']
