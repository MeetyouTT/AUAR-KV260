"""UI-only speech enrollment release; preserve the running identity camera."""
import hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'voice_candidate.json').read_text(encoding='utf-8'))
assert c['tests_passed'] and c['preflight_passed']
for n,sha in c['files'].items():assert hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==sha,n
remote=r'''
import hashlib,json,os,re,subprocess,time,urllib.request,uuid
from pathlib import Path
c=CANDIDATE;stage=Path(c['stage']);root=Path(c['runtime'])
assert root.parent==stage and stage.parent==Path('/home/root/aura-voice-enrollment-20261018')
def get(port,path,host='127.0.0.1'):return json.load(urllib.request.urlopen('http://'+host+':'+str(port)+path,timeout=4))
def idle():
 s=get(8783,'/api/state')
 assert s['phase']=='IDLE' and not s['playing'] and not s['paused']
 assert s['local_recording']['state']!='RECORDING' and not s['local_transcription']['service']['pending']
 assert not s.get('automatic_conversation',{}).get('enabled')
 return s
idle();camera=get(8790,'/health');pc=get(8792,'/health','192.168.50.1')
assert pc['ready'] and not pc['busy'] and pc['identity_voice_enrollment']['version']==1
assert pc['llm_model']=='aura-qwen3.8-27b-abliterated:iq4_xs' and pc['tts']=='omnivoice' and pc['num_step']==16
for n,sha in c['files'].items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==sha,n
unit_path=Path('/etc/systemd/system/aura-avatar-ui.service');old=unit_path.read_bytes()
assert c['old_config'] in old.decode()
link=os.readlink(str(unit_path)) if unit_path.is_symlink() else None
backup=stage/('activation-backup-'+uuid.uuid4().hex[:10]);backup.mkdir();(backup/unit_path.name).write_bytes(old)
(backup/'rollback.json').write_text(json.dumps({'unit_link':link,'previous_config':c['old_config']},indent=2))
for source in Path(c['source_runtime']).glob('*_settings.json'):
 target=root/source.name;assert not target.is_symlink();target.write_bytes(source.read_bytes())
unit=old.decode().replace(c['source_runtime'],str(root))
unit=re.sub(r'^ExecStart=.*$','ExecStart=/usr/bin/python3 -B '+c['startup']+'/launcher.py --config '+c['startup']+'/config.json',unit,flags=re.M)
def run(args,timeout=35):return subprocess.run(args,check=True,capture_output=True,text=True,timeout=timeout)
def atomic(raw):
 p=unit_path.with_name(unit_path.name+'.voice-enrollment-tmp');p.write_bytes(raw);p.chmod(0o644);os.replace(p,unit_path)
report={'runtime':str(root),'backup':str(backup),'camera_before':camera,'pc_health':pc,'camera_service_restarted':False}
try:
 idle();run(['systemctl','stop','aura-avatar-ui.service']);atomic(unit.encode());run(['systemctl','daemon-reload'])
 run(['systemctl','start','--no-block','aura-avatar-ui.service'])
 deadline=time.monotonic()+150
 while time.monotonic()<deadline:
  try:
   state=get(8783,'/api/state');active=run(['systemctl','is-active','aura-avatar-ui.service'],5).stdout.strip()
   if active=='active' and state.get('audio_output_state')=='IDLE_READY':
    flow=state['local_transcription']['service'].get('voice_enrollment')
    if flow is not None:break
  except (OSError,ValueError,subprocess.CalledProcessError):pass
  time.sleep(.4)
 else:raise RuntimeError('Speech enrollment UI did not become ready')
 report.update(status='VOICE_ENROLLMENT_READY_NOT_LISTENING',ui_phase=state['phase'],flow=flow,automatic=state['automatic_conversation'])
except Exception as ex:
 subprocess.run(['systemctl','stop','aura-avatar-ui.service'],capture_output=True,timeout=35)
 if link:
  p=unit_path.with_name(unit_path.name+'.voice-enrollment-rollback');p.symlink_to(link);os.replace(p,unit_path)
 else:atomic(old)
 run(['systemctl','daemon-reload']);run(['systemctl','start','--no-block','aura-avatar-ui.service'])
 report.update(status='ROLLED_BACK',error=str(ex))
after=get(8790,'/health');report['camera_after']=after;report['camera_pid_preserved']=after['pid']==camera['pid']
(stage/'deployment.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
'''.replace('CANDIDATE',repr(c))
r=json.loads(ssh('python3 -',remote,timeout=240))
(HERE/'voice_deployment.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in r.items() if k not in ('camera_before','camera_after','pc_health')},ensure_ascii=True))
assert r['status']=='VOICE_ENROLLMENT_READY_NOT_LISTENING' and r['camera_pid_preserved']
