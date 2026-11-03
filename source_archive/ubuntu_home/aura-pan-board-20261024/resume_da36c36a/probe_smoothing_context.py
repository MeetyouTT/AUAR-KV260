import hashlib,json,re,subprocess,urllib.request
from pathlib import Path
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
raw=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart','--value'],text=True)
sc=Path(re.search(r'--config (/[^ ;]+)',raw).group(1));startup=json.loads(sc.read_text());app=Path(startup['runtime'])/'aura'
pins_ok=all(hashlib.sha256((app/n).read_bytes()).hexdigest()==h for n,h in startup['component_sha256'].items())
face=app/'config/pan_face.local.json';manual_cfg=json.loads((app/'config/pan_manual.local.json').read_text())
referenced=Path(manual_cfg['face_follow_config']);u=get(8783,'/api/state');h=get(8790,'/health');m=u['manual_pan']
print(json.dumps(dict(boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),startup_path=str(sc),startup_sha256=hashlib.sha256(sc.read_bytes()).hexdigest(),app_root=str(app),pins_ok=pins_ok,pin_count=len(startup['component_sha256']),face_config=json.loads(face.read_text()),manual_config=manual_cfg,referenced_face_config_path=str(referenced),referenced_face_config=json.loads(referenced.read_text()),camera_pid=h['pid'],gui_pid=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True).strip(),phase=u.get('phase'),playing=u.get('playing'),audio=u.get('audio_output_state'),manual=m,packet=get(8790,'/v1/motion/face/observation'),motor_commands_sent=0),ensure_ascii=False))
