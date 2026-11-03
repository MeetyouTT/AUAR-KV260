"""Compare recorded transaction guards and export only coordinate evidence."""
import base64
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request

tx = Path('/home/root/aura-pan-follow-20261020/activation-axis-01')
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def out(args): return subprocess.check_output(args,text=True,timeout=5).strip()
value = {'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(), 'artifacts':{}}
preserved=json.loads((tx/'preserved-source-hashes.json').read_text())
value['preserved_sources_total']=len(preserved)
value['preserved_sources_changed']=[p for p,digest in preserved.items() if not Path(p).is_file() or sha(Path(p))!=digest]
value['camera_unit_is_original']=Path('/etc/systemd/system/aura-camera-ui.service').read_bytes()==(tx/'camera-unit.before').read_bytes()
value['vart_conf_unchanged']=Path('/etc/vart.conf').read_bytes()==(tx/'vart.conf.before').read_bytes()
value['camera_pid']=out(['systemctl','show','aura-camera-ui.service','-p','MainPID','--value'])
value['gui_pid']=out(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'])
value['gui_root']=out(['systemctl','show','aura-avatar-ui.service','-p','WorkingDirectory','--value'])
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
for name,port,path,keys in [
 ('camera',8790,'/health',['identity_recognition','camera_error','detector_error','detected_frames','observation_age_ms','detection_hz']),
 ('gui',8783,'/api/state',['ui_page','phase','playing','automatic_conversation'])]:
 with opener.open('http://127.0.0.1:%d%s'%(port,path),timeout=2) as r:state=json.load(r)
 value[name]={k:state.get(k) for k in keys}
for name in ['result.json','joint-loaded.json','live-source.jsonl','live-shadow.jsonl','live-shadow.jsonl.summary.json']:
 raw=(tx/name).read_bytes()
 data=gzip.compress(raw,mtime=0) if name.endswith('.jsonl') else raw
 dest=name+'.gz' if name.endswith('.jsonl') else name
 value['artifacts'][dest]={'base64':base64.b64encode(data).decode(),'sha256':hashlib.sha256(data).hexdigest()}
print(json.dumps(value),flush=True)
