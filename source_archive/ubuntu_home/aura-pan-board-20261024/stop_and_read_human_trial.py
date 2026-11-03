import json,urllib.request
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}));base='http://127.0.0.1:8783'
request=urllib.request.Request(base+'/api/command',data=b'{"type":"pan_stop"}',headers={'Origin':base,'Content-Type':'application/json'})
with opener.open(request,timeout=3) as response:assert json.load(response)['ok']

"""Read the latest completed GUI follow report, waiting for a live session."""
import json,time,urllib.request
from pathlib import Path
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def read():
 with o.open('http://127.0.0.1:8783/api/state',timeout=3) as response:return json.load(response)
end=time.monotonic()+15
while True:
 u=read();m=u['manual_pan']
 if not m.get('automatic_following') and m['state']=='READY':break
 if time.monotonic()>=end:break
 time.sleep(.1)
p=m.get('face_follow',{}).get('report');report=json.loads(Path(p).read_text()) if p and Path(p).is_file() else None
print(json.dumps({'manual':m,'trial':report,'page':u.get('ui_page'),'preview':u['ui_runtime'].get('preview_metrics')},sort_keys=True))
