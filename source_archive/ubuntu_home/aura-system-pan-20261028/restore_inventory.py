import hashlib,json,subprocess,urllib.request
from pathlib import Path
def run(a,t=8):
 p=subprocess.run(a,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=t);return {'rc':p.returncode,'text':p.stdout[-16000:]}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):
 try:return Path(p).read_text()
 except OSError:return None
root=Path('/lib/firmware/xilinx/aura-visual-servo-b4096-v2');d={'boot_id':read('/proc/sys/kernel/random/boot_id').strip(),'joint_files':{},'vart':read('/etc/vart.conf'),'apps':run(['xmutil','listapps'],15),'units':{n:run(['systemctl','cat',n]) for n in ['dpu-auto-config.service','aura-camera-ui.service']}}
if root.exists():
 for p in root.iterdir():
  if p.is_file():d['joint_files'][p.name]={'bytes':p.stat().st_size,'sha256':sha(p)}
base=Path('/home/root/aura-windows-portrait-20261027/handoff-31b0c262c5b74d52966c00b978dfef3f');c=json.loads((base/'startup/config.json').read_text())
d['config_keys']=list(c);d['config_paths']={k:v for k,v in c.items() if k in ['runtime','launch_file','component_manifest','gui','gui_script','candidate_root','runtime_dir']}
d['pan_configs']={}
for p in (base/'runtime').rglob('*pan*.json'):
 if p.stat().st_size<30000:d['pan_configs'][str(p)]={'sha256':sha(p),'document':json.loads(p.read_text())}
print(json.dumps(d))
