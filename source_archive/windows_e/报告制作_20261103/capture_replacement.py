from pathlib import Path
from datetime import datetime,timezone
import subprocess,json,sys
sys.stdout.reconfigure(encoding='utf-8')
W=Path(r'E:\报告制作_20261103\face_redaction');W.mkdir(exist_ok=True)
code=r'''from pathlib import Path
import os,sys,json,base64,urllib.request
os.environ['DISPLAY']=':0'
import gi
gi.require_version('Gdk','3.0')
from gi.repository import Gdk
w=Gdk.get_default_root_window()
pix=Gdk.pixbuf_get_from_window(w,0,0,w.get_width(),w.get_height())
ok,data=pix.save_to_bufferv('png',[],[])
def get(port,path):
 try:return json.load(urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=6))
 except Exception as e:return {'error':str(e)}
gui=get(8783,'/api/state');cam=get(8790,'/health')
print(json.dumps({'image':base64.b64encode(data).decode(),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'gui':{k:gui.get(k) for k in ['ui_page','state','dialogue_enabled','manual_pan','automatic_conversation']},
 'camera':{k:cam.get(k) for k in ['capture_frames','detected_frames','capture_age_ms','observation_age_ms','people_count','identity','camera_error','detector_error']}}))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=8','aura-kv260','python3 -'],input=code.encode(),capture_output=True,timeout=30)
if r.returncode:print(r.stderr.decode(errors='replace'));sys.exit(r.returncode)
d=json.loads(r.stdout);import base64
(W/'current_raw.png').write_bytes(base64.b64decode(d.pop('image')))
d['host_capture_utc']=datetime.now(timezone.utc).isoformat()
(W/'capture_metadata_private.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'capture_path':str(W/'current_raw.png'),'boot_id':d['boot_id'],'ui_page':d['gui']['ui_page'],'state':d['gui']['state'],'people_count':d['camera']['people_count'],'host_utc':d['host_capture_utc']},ensure_ascii=False))
