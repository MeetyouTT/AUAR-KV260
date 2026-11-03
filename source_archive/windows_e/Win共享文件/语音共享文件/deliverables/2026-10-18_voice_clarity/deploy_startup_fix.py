"""Deploy tested MCP01 startup padding with exact hashes, backups and rollback."""
import base64,hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
files={}
for name,before in [('aura/tools/gstreamer_audio_engine.py','gstreamer_audio_engine.before.py'),('aura/tests/framework/test_gstreamer_audio.py','test_gstreamer_audio.before.py')]:
 raw=(ROOT/name).read_bytes()
 files[name]={'raw':base64.b64encode(raw).decode(),'expected_before':hashlib.sha256((HERE/before).read_bytes()).hexdigest(),'sha256':hashlib.sha256(raw).hexdigest()}
payload={'files':files,'release_id':files['aura/tools/gstreamer_audio_engine.py']['sha256'][:12]}
script=r'''
import base64,hashlib,json,os,subprocess,urllib.request
from pathlib import Path
p=json.loads(base64.b64decode(PAYLOAD))
root=Path('/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009')
launcher=Path('/home/root/aura-ui-startup-20261009/releases/voice-b980a9dd2ebb917a-r2')
def get(port,path):return json.load(urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=3))
u=get(8783,'/api/state');camera=get(8790,'/health')
assert u['phase']=='IDLE' and not u['playing'] and u['local_recording']['state']!='RECORDING' and not u['local_transcription']['service']['pending'],'Board busy'
unit=subprocess.check_output(['systemctl','cat','aura-avatar-ui.service'],universal_newlines=True)
assert str(launcher) in unit,'Startup release changed'
config_path=launcher/'config.json';old_config=config_path.read_bytes();config=json.loads(old_config)
backup=Path('/home/root/aura-audio-clarity-20261018')/('startup-fix-'+p['release_id']);backup.mkdir()
raw_files={}
for name,row in p['files'].items():
 target=root/name
 assert target.resolve().is_relative_to(root.resolve()),'Out of runtime'
 old=target.read_bytes();assert hashlib.sha256(old).hexdigest()==row['expected_before'],'Source changed: '+name
 raw=base64.b64decode(row['raw']);assert hashlib.sha256(raw).hexdigest()==row['sha256'];compile(raw,str(target),'exec')
 saved=backup/name;saved.parent.mkdir(parents=True,exist_ok=True);saved.write_bytes(old);raw_files[name]=raw
(backup/'config.json').write_bytes(old_config)
(backup/'avatar_user_settings.json').write_bytes((root/'avatar_user_settings.json').read_bytes())
stage=backup/'candidate';(stage/'aura/tools').mkdir(parents=True);(stage/'tests').mkdir()
(stage/'aura/tools/__init__.py').write_text('')
(stage/'aura/tools/gstreamer_audio_engine.py').write_bytes(raw_files['aura/tools/gstreamer_audio_engine.py'])
(stage/'tests/test_gstreamer_audio.py').write_bytes(raw_files['aura/tests/framework/test_gstreamer_audio.py'])
test=subprocess.run(['python3','-B','-m','unittest','discover','-s',str(stage/'tests'),'-v'],cwd=stage,env=dict(os.environ,PYTHONPATH=str(stage/'aura')),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,universal_newlines=True,timeout=20)
(backup/'board_tests.log').write_text(test.stdout)
assert test.returncode==0,test.stdout

def atomic(path,raw):
 temp=path.with_name(path.name+'.startup-tmp');temp.write_bytes(raw);os.replace(str(temp),str(path))
r={'status':'STARTING','backup':str(backup),'files':{},'camera_pid_before':camera['pid'],'startup_silence_seconds':1.0,'board_tests':test.stdout}
try:
 subprocess.check_call(['systemctl','stop','aura-avatar-ui.service'])
 for name,raw in raw_files.items():
  target=root/name;atomic(target,raw);config['component_sha256'][name[len('aura/'):]]=hashlib.sha256(raw).hexdigest();r['files'][name]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
 atomic(config_path,(json.dumps(config,indent=2)+'\n').encode())
 pre=subprocess.run(['python3',str(launcher/'launcher.py'),'--config',str(config_path),'--preflight'],env=dict(os.environ,PATH='/usr/sbin:/usr/bin:/sbin:/bin'),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,universal_newlines=True,timeout=30)
 (backup/'preflight.log').write_text(pre.stdout)
 assert pre.returncode==0,pre.stdout
 subprocess.check_call(['systemctl','start','--no-block','aura-avatar-ui.service'])
 r['status']='DEPLOYED_STARTING'
except Exception as e:
 subprocess.call(['systemctl','stop','aura-avatar-ui.service'])
 for name in raw_files:atomic(root/name,(backup/name).read_bytes())
 atomic(config_path,old_config)
 subprocess.call(['systemctl','start','--no-block','aura-avatar-ui.service'])
 r.update(status='ROLLED_BACK',error=str(e))
r['camera_pid_after']=get(8790,'/health')['pid'];r['camera_preserved']=r['camera_pid_before']==r['camera_pid_after']
(backup/'deployment.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
'''.replace('PAYLOAD',repr(base64.b64encode(json.dumps(payload).encode()).decode()))
v=json.loads(ssh('python3 -',script,timeout=95));(HERE/'startup_fix_deployment.json').write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v[k] for k in v if k!='board_tests'}))
if v['status']!='DEPLOYED_STARTING':raise SystemExit(1)
