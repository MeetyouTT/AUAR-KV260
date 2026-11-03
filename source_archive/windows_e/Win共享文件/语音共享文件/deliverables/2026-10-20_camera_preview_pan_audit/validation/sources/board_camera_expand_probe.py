"""Open a fresh preview sink to distinguish capture from X11 embedding."""
import base64,hashlib,importlib.util,json,time,urllib.request
from pathlib import Path
base='http://127.0.0.1:8783';op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
req=urllib.request.Request(base+'/api/command',data=json.dumps({'type':'preview_open'}).encode(),headers={'Content-Type':'application/json','Origin':base})
with op.open(req,timeout=3) as r:ack=json.load(r)
time.sleep(1)
root=Path('/home/root/aura-voice-barge-in-20261020/candidate-667b70d586ca/runtime/aura')
sp=importlib.util.spec_from_file_location('cap',str(root/'tools/board_screen_capture.py'));m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
p=Path('/tmp/aura-camera-expanded-private.png');m.capture(p)
from PIL import Image
with Image.open(str(p)) as im:
 im.thumbnail((768,450));im.save(str(p),optimize=True)
d=p.read_bytes()
print(json.dumps({'ack':ack,'artifacts':{'expanded-private.png':{'base64':base64.b64encode(d).decode(),'sha256':hashlib.sha256(d).hexdigest()}}}),flush=True)
