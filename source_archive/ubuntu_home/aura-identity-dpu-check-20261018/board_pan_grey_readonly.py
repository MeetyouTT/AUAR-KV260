"""Read pan state and the right-side controls only; no command or motion."""
import base64,hashlib,importlib.util,json,subprocess,time,urllib.request
from pathlib import Path
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def read():
 with op.open('http://127.0.0.1:8783/api/state',timeout=1) as r:s=json.load(r)
 return {k:s.get(k) for k in ['ui_page','sequence','ui_tick_ms','error','manual_pan']}
samples=[]
for _ in range(3):
 samples.append(read());time.sleep(.25)
root=Path(subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','WorkingDirectory','--value'],text=True).strip())
v={'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'samples':samples,'root':str(root),'pan_source_sha256':hashlib.sha256((root/'tools/pan_controls.py').read_bytes()).hexdigest(),'artifacts':{}}
if samples[-1]['ui_page']=='vision' and samples[-1]['manual_pan'].get('panel_open'):
 sp=importlib.util.spec_from_file_location('cap',str(root/'tools/board_screen_capture.py'));cap=importlib.util.module_from_spec(sp);sp.loader.exec_module(cap)
 target=Path('/tmp/aura-pan-grey-screen-private.png');assert cap.capture(target)==(1024,600)
 from PIL import Image
 with Image.open(str(target)) as full:
  crop=full.crop((593,0,1024,548));crop.save('/tmp/aura-pan-grey-panel-only.png',optimize=True)
 data=Path('/tmp/aura-pan-grey-panel-only.png').read_bytes()
 v['artifacts']['panel-only.png']={'base64':base64.b64encode(data).decode(),'sha256':hashlib.sha256(data).hexdigest()}
print(json.dumps(v),flush=True)
