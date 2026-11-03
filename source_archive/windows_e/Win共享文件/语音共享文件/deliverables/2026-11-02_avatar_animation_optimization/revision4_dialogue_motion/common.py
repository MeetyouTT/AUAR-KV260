from pathlib import Path
import json,hashlib,subprocess,datetime,base64,io,tarfile,shutil
HERE=Path(__file__).resolve().parent
BASE=HERE.parent
PROJECT=BASE.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,x):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def remote(script,host,timeout=40):
 r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=7',host,'python3 -B -'],input=script.encode(),capture_output=True,timeout=timeout)
 if r.returncode:raise RuntimeError((r.stderr+r.stdout).decode(errors='replace')[-6000:])
 return r.stdout
def board(script,timeout=40):
 h=load(HERE/'DEVICE_HANDOFF_R4.json')
 assert h.get('permission_active') is True
 assert h.get('exclusive_GUI_maintenance_holder',h.get('receiving_thread_id'))=='01a19efd-bb40-7f32-a6e4-a5f0cb59ffe8'
 if (HERE/'DEVICE_RETURN_R4.json').exists():
  r=load(HERE/'DEVICE_RETURN_R4.json')
  if r.get('handoff_id')==h.get('handoff_id') and r.get('permission_active_for_animation') is False:
   raise RuntimeError('R4 maintenance already returned; a new handoff is required')
 return remote(script,'aura-kv260',timeout)
