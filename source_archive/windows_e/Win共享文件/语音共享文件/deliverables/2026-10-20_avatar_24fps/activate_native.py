"""Switch an idle UI only after candidate checks; preserve and verify camera/PC."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'candidate.json').read_text())
v=json.loads((HERE/'verification.json').read_text());assert v['passed']; smoke=json.loads((HERE/'native_smoke.json').read_text()); assert smoke['code']==0
remote=r'''
import hashlib,json,os,re,shutil,subprocess,time,urllib.request
from pathlib import Path
c=CANDIDATE;stage=Path(c['stage']);root=Path(c['runtime'])
def get(port,path,host='127.0.0.1'):
 return json.load(urllib.request.urlopen('http://%s:%d%s'%(host,port,path),timeout=4))
def idle():
 s=get(8783,'/api/state')
 assert s['phase']=='IDLE' and not s['playing'] and not s['paused'],'Conversation is active'
 assert not s['automatic_conversation']['enabled'],'Automatic conversation is active'
 assert s['local_recording']['state']!='RECORDING' and not s['local_transcription']['service']['pending']
 assert not s['local_transcription']['service']['voice_enrollment']['active']
 return s
before=idle();pref=Path('/root/.local/share/aura/handsfree_dialogue.json');pref_raw=pref.read_bytes() if pref.exists() else None
camera=get(8790,'/health');pc=get(8792,'/health','192.168.50.1')
assert pc['ready'] and not pc['busy']
camera_unit=subprocess.check_output(['systemctl','cat','aura-camera-ui.service'],text=True)
args=Path('/proc/%d/cmdline'%camera['pid']).read_bytes().decode().split('\0')
camera_cfg=Path(args[args.index('--config')+1]);identity_cfg=Path(json.loads(camera_cfg.read_text())['identity']['config'])
identity_raw=identity_cfg.read_bytes();identity=json.loads(identity_raw);db=Path(identity['database']).expanduser()
db_hash=hashlib.sha256(db.read_bytes()).hexdigest()
unit=Path('/etc/systemd/system/aura-avatar-ui.service');old=unit.read_bytes();link=os.readlink(unit) if unit.is_symlink() else None
assert c['source_config'] in old.decode(),'Active deployment changed; rebase'
for n,sha in c['files'].items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==sha,n
for source in Path(c['source_runtime']).glob('*_settings.json'):
 target=root/source.name;assert not target.is_symlink();shutil.copy2(source,target)
backup=stage/'activation-backup';backup.mkdir(exist_ok=False);(backup/'aura-avatar-ui.service').write_bytes(old)

if pref_raw is not None:(backup/'handsfree_dialogue.json').write_bytes(pref_raw)
(backup/'rollback.json').write_text(json.dumps({'unit_link':link,'source_config':c['source_config']}))
new=old.decode().replace(c['source_runtime'],str(root))
new=re.sub(r'^ExecStart=.*$','ExecStart=/usr/bin/python3 -B '+c['startup']+'/launcher.py --config '+c['startup']+'/config.json',new,flags=re.M)
def run(args,timeout=35):return subprocess.run(args,check=True,capture_output=True,text=True,timeout=timeout)
def install(raw):
 tmp=unit.with_name(unit.name+'.performance-tmp');tmp.write_bytes(raw);tmp.chmod(0o644);os.replace(tmp,unit)
report={'runtime':str(root),'backup':str(backup),'source_runtime':c['source_runtime'],'camera_pid_before':camera['pid'],
        'identity_threshold':identity['threshold'],'identity_database_sha256_before':db_hash,'pc_before':pc,
        'handsfree_before':before.get('handsfree_dialogue'),'camera_restarted':False,'pc_restarted':False}
try:
 idle();run(['systemctl','stop','aura-avatar-ui.service']);install(new.encode());
 if pref_raw is not None:pref.write_bytes(pref_raw)
 run(['systemctl','daemon-reload'])
 run(['systemctl','start','--no-block','aura-avatar-ui.service'])
 deadline=time.monotonic()+180
 while time.monotonic()<deadline:
  try:
   state=get(8783,'/api/state')
   if state.get('audio_output_state')=='IDLE_READY' and state.get('avatar_display',{}).get('received',0)>30:
    break
  except (OSError,ValueError):pass
  time.sleep(.5)
 else:raise RuntimeError('Optimized UI did not become ready')
 assert pref_raw is None or pref.read_bytes()==pref_raw,'Handsfree preference changed'
 assert state.get('avatar_display',{}).get('kind')=='native_sink_handoff'
 after=get(8790,'/health');pc_after=get(8792,'/health','192.168.50.1')
 assert after['pid']==camera['pid']
 assert hashlib.sha256(db.read_bytes()).hexdigest()==db_hash and identity_cfg.read_bytes()==identity_raw
 assert subprocess.check_output(['systemctl','cat','aura-camera-ui.service'],text=True)==camera_unit
 assert pc_after['llm_model']==pc['llm_model'] and pc_after['num_step']==pc['num_step']
 report.update(status='PERFORMANCE_UI_READY',camera_pid_after=after['pid'],identity_database_unchanged=True,
               identity_config_unchanged=True,pc_after=pc_after,display=state['avatar_display'],renderer=state['avatar_renderer'],handsfree_after=state.get('handsfree_dialogue'))
except Exception as exc:
 subprocess.run(['systemctl','stop','aura-avatar-ui.service'],capture_output=True,timeout=40)
 if link:
  tmp=unit.with_name(unit.name+'.performance-rollback');tmp.symlink_to(link);os.replace(tmp,unit)
 else:install(old)
 
 if pref_raw is not None:pref.write_bytes(pref_raw)
 run(['systemctl','daemon-reload']);run(['systemctl','start','--no-block','aura-avatar-ui.service'])
 report.update(status='ROLLED_BACK',error=type(exc).__name__+': '+str(exc))
(stage/'deployment.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
'''.replace('CANDIDATE',repr(c),1)
r=json.loads(ssh('python3 -B -',remote,timeout=260))
(HERE/'deployment.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r))
assert r['status']=='PERFORMANCE_UI_READY'
