"""Persist only the accepted native portrait rate, without restarting the UI."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '2026-10-18_board_dialogue'))
from board_ssh import ssh

c = json.loads((HERE / 'candidate.json').read_text(encoding='utf-8'))
steps = json.loads((HERE / 'fps_steps.json').read_text(encoding='utf-8'))
assert steps['status'] == 'COMPLETE'
fps = steps['best_fps']
assert fps in (12, 16, 24)
script = r'''
import hashlib,json,os,subprocess,urllib.request
from pathlib import Path
c=CANDIDATE;fps=FPS;root=Path(c['runtime']);stage=Path(c['stage']);startup=Path(c['startup'])
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==c['boot']
assert str(startup) in subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart'],text=True)
assert json.loads((stage/'deployment.json').read_text())['status']=='COMMITTED'
remote_steps=json.loads((stage/'fps_steps.json').read_text())
assert remote_steps['status']=='COMPLETE' and remote_steps['best_fps']==fps
with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4) as response:s=json.load(response)
pan=s['manual_pan'];portrait=s['portrait_offload']
assert s['phase']=='IDLE' and s['audio_output_state']=='IDLE_READY' and not s.get('error')
assert s['handsfree_dialogue']['enabled'] is False and not s['handsfree_dialogue'].get('microphone_open')
assert pan['automatic_following'] is False and pan['state'] not in ('MOVING','STOPPING') and not pan.get('readback',{}).get('active')
assert portrait['selected'] and portrait['mode']=='remote' and portrait['target_fps']==fps
ui_path=root/'aura/config/board_avatar_gtk.json';startup_path=startup/'config.json'
before_ui=ui_path.read_bytes();before_startup=startup_path.read_bytes()
ui=json.loads(before_ui);cfg=json.loads(before_startup)
for relative,digest in cfg['component_sha256'].items():
    assert hashlib.sha256((root/'aura'/relative).read_bytes()).hexdigest()==digest,relative
assert ui['portrait_offload']['enabled'] is True and ui['portrait_offload']['host']=='192.168.50.1'
assert ui['portrait_offload']['revision']==c['revision']
backup=stage/'fps_config_before.json'
if not backup.exists():backup.write_text(json.dumps({'ui':ui,'startup':cfg},indent=2))
def atomic(path,raw):
    temp=path.with_name(path.name+'.portrait-fps.tmp');temp.write_bytes(raw);os.replace(temp,path)
try:
    ui['portrait_offload']['fps']=fps
    ui['stable_avatar_fps']=fps
    atomic(ui_path,(json.dumps(ui,indent=2)+'\n').encode())
    cfg['component_sha256']['config/board_avatar_gtk.json']=hashlib.sha256(ui_path.read_bytes()).hexdigest()
    atomic(startup_path,(json.dumps(cfg,indent=2)+'\n').encode())
    check=subprocess.run(['python3','-B',str(startup/'launcher.py'),'--config',str(startup_path),'--preflight'],
        env=dict(os.environ,PATH='/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'),capture_output=True,text=True,timeout=25)
    assert check.returncode==0,check.stdout+check.stderr
except BaseException:
    atomic(ui_path,before_ui);atomic(startup_path,before_startup);raise
report={'status':'PERSISTED','accepted_fps':fps,'restart_performed':False,'preflight':check.stdout.strip(),
 'ui_config_sha256':hashlib.sha256(ui_path.read_bytes()).hexdigest(),
 'startup_config_sha256':hashlib.sha256(startup_path.read_bytes()).hexdigest(),
 'pan_us':pan['pulse_us'],'automatic_following':False,'microphone_open':False}
(stage/'fps_persisted.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
'''.replace('CANDIDATE', repr(c)).replace('FPS', repr(fps))
value = json.loads(ssh('python3 -B -', script, timeout=40))
(HERE / 'fps_persisted.json').write_text(json.dumps(value, indent=2), encoding='utf-8')
print(json.dumps(value))
