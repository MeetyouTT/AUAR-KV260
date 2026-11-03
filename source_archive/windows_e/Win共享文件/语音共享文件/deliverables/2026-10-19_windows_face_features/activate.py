"""Idle board-only switch to tested face targets, with automatic rollback."""
import hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))
p=json.loads((HERE/'preflight.json').read_text(encoding='utf-8'))
assert c['tests_passed'] and c['preflight_passed'] and c['body_tracking_file_preserved']
assert all(p[key] for key in ('real_models_passed','bootstrap_passed','widget_passed'))
for name,sha in c['files'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha,name
remote=r'''
import hashlib,json,os,re,subprocess,time,urllib.request,uuid
from pathlib import Path
c=CANDIDATE;root=Path(c['runtime']);stage=Path(c['stage'])
assert stage.parent==Path('/home/root/aura-windows-face-features-20261019') and root.parent==stage
get=lambda port,path,host='127.0.0.1':json.load(urllib.request.urlopen('http://'+host+':'+str(port)+path,timeout=4))
def idle():
 state=get(8783,'/api/state')
 assert state['phase']=='IDLE' and not state['playing'] and not state['paused']
 assert state['local_recording']['state']!='RECORDING' and not state['local_transcription']['service']['pending']
 assert not state['automatic_conversation']['enabled'] and not state.get('ui_runtime',{}).get('pending_count')
 return state
idle();before=get(8790,'/health');pc=get(8792,'/health','192.168.50.1')
assert pc['identity_voice_enrollment']['sampling_guidance_version']==3
assert pc['identity_features']['ready'] and pc['identity_features']['backend']=='WINDOWS_CPU_SFACE_ORT'
assert pc['identity_features']['model_id']=='sface-2021dec-0ba9fbfa01b5'
assert pc['ready'] and not pc['busy'] and pc['num_step']==16 and pc['llm_model']=='aura-qwen3.8-27b-abliterated:iq4_xs'
for name,sha in c['files'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==sha,name
cfg=json.loads(Path(c['camera_config']).read_text());identity=json.loads(Path(cfg['identity']['config']).read_text())
old_camera=json.loads(Path(c['old_camera_config']).read_text())
assert identity['threshold']==.85 and identity['ambiguity_margin']==.1
assert {k:v for k,v in cfg.items() if k!='identity'}=={k:v for k,v in old_camera.items() if k!='identity'}
old_identity=json.loads(Path(old_camera['identity']['config']).read_text());assert {k:v for k,v in identity.items() if k!='feature_backend'}=={k:v for k,v in old_identity.items() if k!='feature_backend'}
assert identity['feature_backend']=={'kind':'windows_sface','host':'192.168.50.1','port':8792,'timeout_ms':650}
assert old_identity.get('feature_backend') in (None,identity['feature_backend'])
db=Path(identity['database']).expanduser();db_before=hashlib.sha256(db.read_bytes()).hexdigest()
paths={name:Path('/etc/systemd/system')/name for name in ('aura-camera-ui.service','aura-avatar-ui.service')}
old={name:path.read_bytes() for name,path in paths.items()}
links={name:os.readlink(path) if path.is_symlink() else None for name,path in paths.items()}
assert c['old_ui_config'] in old['aura-avatar-ui.service'].decode()
assert c['old_camera_config'] in old['aura-camera-ui.service'].decode()
backup=stage/('activation-backup-'+uuid.uuid4().hex[:10]);backup.mkdir()
for name,raw in old.items():(backup/name).write_bytes(raw)
(backup/'rollback.json').write_text(json.dumps({'unit_links':links,'previous_ui_config':c['old_ui_config'],'previous_camera_config':c['old_camera_config']},indent=2))
for source in Path(c['source_runtime']).glob('*_settings.json'):
 target=root/source.name;assert not target.is_symlink();target.write_bytes(source.read_bytes())
new_ui=old['aura-avatar-ui.service'].decode().replace(c['source_runtime'],str(root))
new_ui=re.sub(r'^ExecStart=.*$','ExecStart=/usr/bin/python3 -B '+c['startup']+'/launcher.py --config '+c['startup']+'/config.json',new_ui,flags=re.M)
new_camera=re.sub(r'^ExecStart=.*$','ExecStart=/usr/bin/python3 -B '+str(root/'aura/board/vision/ui_camera_service.py')+' --config '+c['camera_config'],old['aura-camera-ui.service'].decode(),flags=re.M)
new_camera=re.sub(r'^WorkingDirectory=.*$','WorkingDirectory='+str(root/'aura'),new_camera,flags=re.M)
new={'aura-avatar-ui.service':new_ui.encode(),'aura-camera-ui.service':new_camera.encode()}
def run(args,timeout=35):return subprocess.run(args,check=True,capture_output=True,text=True,timeout=timeout)
def atomic(path,raw):
 temp=path.with_name(path.name+'.face-target-tmp');temp.write_bytes(raw);temp.chmod(0o644);os.replace(temp,path)
def restore():
 for name,path in paths.items():
  if links[name]:
   temp=path.with_name(path.name+'.face-target-rollback');temp.symlink_to(links[name]);os.replace(temp,path)
  else:atomic(path,old[name])
 run(['systemctl','daemon-reload']);run(['systemctl','start','--no-block',*paths])
report={'runtime':str(root),'backup':str(backup),'camera_before':before,'pc_before':pc,
 'matching_threshold_changed':False,'identity_database_modified':False,'body_tracking_config_changed':False,
 'database_revision_before':get(8790,'/v1/ui/status')['modules']['identity']['db_version']}
try:
 idle();run(['systemctl','stop','aura-avatar-ui.service','aura-camera-ui.service'],45)
 for name,path in paths.items():atomic(path,new[name])
 run(['systemctl','daemon-reload']);run(['systemctl','start','--no-block',*paths])
 deadline=time.monotonic()+160
 while time.monotonic()<deadline:
  try:
   camera=get(8790,'/health');state=get(8783,'/api/state');view=get(8790,'/v1/ui/status')
   if camera.get('identity',{}).get('error'):raise RuntimeError(camera['identity']['error'])
   if (camera.get('identity',{}).get('ready') and not camera.get('camera_error') and not camera.get('detector_error')
       and view['modules']['identity'].get('enrollment_sampling') is not None and state.get('audio_output_state')=='IDLE_READY' and view['modules']['identity'].get('target_kind')=='face'):
    if run(['systemctl','is-active','aura-avatar-ui.service'],5).stdout.strip()=='active':break
  except (OSError,ValueError,subprocess.CalledProcessError):pass
  time.sleep(.4)
 else:raise RuntimeError('Face-target candidate did not become ready')
 assert camera['identity']['backend']=='WINDOWS_CPU_SFACE_ORT'
 assert camera['detector']==before['detector'] and camera['board_boot_id']==before['board_boot_id']
 assert hashlib.sha256(db.read_bytes()).hexdigest()==db_before,'User identity database changed during deployment'
 assert not state['automatic_conversation']['enabled']
 report.update(status='WINDOWS_FACE_FEATURES_DEPLOYED_AWAITING_REAL_USER_VALIDATION',camera_after=camera,
  ui_phase=state['phase'],database_revision_after=view['modules']['identity']['db_version'],
  enrolled_count=len(view['modules']['identity']['people']),identity_state=view['modules']['identity']['state'],
  target_kind=view['modules']['identity']['target_kind'])
except Exception as exc:
 subprocess.run(['systemctl','stop',*paths],capture_output=True,timeout=45)
 restore();report.update(status='ROLLED_BACK',error=type(exc).__name__+': '+str(exc))
report['pc_after']=get(8792,'/health','192.168.50.1')
(stage/'deployment.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
'''.replace('CANDIDATE',repr(c),1)
result=json.loads(ssh('python3 -B -',remote,timeout=240))
(HERE/'deployment.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({key:value for key,value in result.items() if key not in ('camera_before','camera_after','pc_before','pc_after')},ensure_ascii=True))
assert result['status']=='WINDOWS_FACE_FEATURES_DEPLOYED_AWAITING_REAL_USER_VALIDATION'
