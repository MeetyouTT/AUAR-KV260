import base64,hashlib,json,subprocess,urllib.request
from pathlib import Path
BOOT='55152f95-ea3a-4c6c-82e6-51bd553d96fd'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def get(port,path):
 with urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=4) as r:return json.load(r)
def props(unit):
 return dict(s.split('=',1) for s in subprocess.check_output(['systemctl','show',unit,'-p','MainPID','-p','FragmentPath','-p','DropInPaths','-p','Restart','-p','KillMode','-p','SendSIGKILL','-p','TimeoutStopUSec','-p','ExecStart'],text=True).splitlines() if '=' in s)
O=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735');meta=json.loads((O/'meta.json').read_text());cfg=json.loads(Path(meta['candidate_config']).read_text())
G=Path('/home/root/aura-device-skills-20261028/0cd7c3445a84475098b938d5b97175e0');start=json.loads((G/'startup/config.json').read_text());A=Path(start['runtime'])/'aura'
h=get(8790,'/health');u=get(8783,'/api/state');cp=Path(cfg['native_execution']['checkpoint_output']);raw=Path('/sys/firmware/fdt').read_bytes()
d={'boot_id':BOOT,'fdt_sha256':sha('/sys/firmware/fdt'),'fdt_base64':base64.b64encode(raw).decode(),'gui_root':str(G),'gui_config_sha256':sha(G/'startup/config.json'),'gui_components':start['component_sha256'],'gui_components_match':all(sha(A/n)==s for n,s in start['component_sha256'].items()),'gui_launcher_sha256':sha(G/'startup/launcher.py'),'camera_props':props('aura-camera-ui.service'),'gui_props':props('aura-avatar-ui.service'),'candidate_config':meta['candidate_config'],'candidate_config_sha256':sha(meta['candidate_config']),'checkpoint_path':str(cp),'checkpoint_sha256':sha(cp),'checkpoint':json.loads(cp.read_text()),'native_handoff':h['dpu_schedule']['protection_handoff'],'native_schedule':h['dpu_schedule'],'sface_completed':h['identity']['feature_inference']['completed'],'current_sources':{},'motion_sources':{},'pan_configs':{}}
for n in ['native_entry.py','native_entry_pan_face_v5.py']:
 p=O/n;d['current_sources'][str(p)]={'sha256':sha(p),'source':p.read_text()}
for p in (A/'board/motion').glob('*.py'):d['motion_sources'][str(p.relative_to(A))]={'sha256':sha(p),'source':p.read_text()}
for n in ['config/pan_manual.local.json','config/pan_face.local.json','config/pan_direction.current.json']:
 p=A/n
 if p.exists():d['pan_configs'][n]={'sha256':sha(p),'document':json.loads(p.read_text())}
print(json.dumps(d))
