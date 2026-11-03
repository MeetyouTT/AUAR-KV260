import hashlib,json,subprocess,urllib.request
from pathlib import Path
G=Path('/home/root/aura-pan-wide-resume-20261029/gui-wide-v1');cfg=json.loads((G/'startup/config.json').read_text());A=Path(cfg['runtime'])/'aura'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def props(unit):
 return subprocess.check_output(['systemctl','show',unit,'-p','MainPID','-p','ActiveState','-p','ExecStart'],text=True)
with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=3) as f:u=json.load(f)
with urllib.request.urlopen('http://127.0.0.1:8790/health',timeout=3) as f:h=json.load(f)
manual=json.loads((A/'config/pan_manual.local.json').read_text());face=json.loads(Path(manual['face_follow_config']).read_text());settings=Path(face['arguments']['zone-settings']);old=Path('/home/root/aura-pan-current-20261024/da36c36a/face-zone-settings.json')
d={'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'gui':props('aura-avatar-ui.service'),'editor':props('aura-face-zone-editor.service'),'camera_pid':h['pid'],'startup_sha256':sha(G/'startup/config.json'),'all_components_match':all(sha(A/n)==v for n,v in cfg['component_sha256'].items()),'components':len(cfg['component_sha256']),'settings_path':str(settings),'settings':json.loads(settings.read_text()),'settings_sha256':sha(settings),'old_settings':json.loads(old.read_text()),'old_settings_sha256':sha(old),'editor_unit_sha256':sha('/etc/systemd/system/aura-face-zone-editor.service'),'ui':{'page':u['ui_page'],'phase':u['phase'],'playing':u['playing'],'audio':u['audio_output_state'],'following':u['manual_pan']['automatic_following'],'manual':u['manual_pan']['state'],'readback':u['manual_pan'].get('readback'),'listening':u['handsfree_dialogue']['enabled']}}
print(json.dumps(d))
