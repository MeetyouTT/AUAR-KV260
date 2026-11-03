import urllib.request,subprocess
from pathlib import Path
import json
op=urllib.request.build_opener(urllib.request.ProxyHandler({}));base='http://127.0.0.1:8783'
q=urllib.request.Request(base+'/api/command',data=b'{"type":"pan_stop"}',headers={'Origin':base,'Content-Type':'application/json'})
with op.open(q,timeout=3) as r:stop=json.load(r)
with op.open(base+'/api/state',timeout=3) as r:state=json.load(r)
u={k:state.get(k) for k in ['phase','ui_page','error','manual_pan','ui_runtime']}
with op.open('http://127.0.0.1:8790/health',timeout=3) as r:health=json.load(r)
editor=subprocess.run(['systemctl','status','aura-face-zone-editor.service','--no-pager','-n','6'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True).stdout[-2000:]
tail=Path('/home/root/aura-pan-current-20261024/463c9307/gui-face-edge-v5/runtime/stage.log').read_text()[-5000:]
"""Private display capture for debugging preview placement, never shared."""
import base64,json,os
os.environ['DISPLAY']=':0'
import gi
gi.require_version('Gdk','3.0')
from gi.repository import Gdk
Gdk.init([]);root=Gdk.get_default_root_window();w=root.get_width();h=root.get_height()
image=Gdk.pixbuf_get_from_window(root,0,0,w,h);ok,raw=image.save_to_bufferv('png',[],[]);assert ok
print(json.dumps({'width':w,'height':h,'png_base64':base64.b64encode(raw).decode(),'ui':u,'camera':health,'stop':stop,'editor':editor,'gui_tail':tail}))
