"""Collect exact active GUI sources and interval CPU load without images."""
import hashlib,json,time,urllib.request
from pathlib import Path
base=Path('/home/root/aura-pan-current-20261024/463c9307/gui-release')
cfg=json.loads((base/'startup/config.json').read_text());root=Path(cfg['runtime'])/'aura'
def cpu():
 result={}
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   data=(p/'stat').read_text().rsplit(')',1)[1].split();result[p.name]=(int(data[11])+int(data[12]),(p/'comm').read_text().strip())
  except OSError:pass
 return result
b=cpu();start=time.monotonic();time.sleep(1);a=cpu();elapsed=time.monotonic()-start
top=sorted([(round((v[0]-b[k][0])/elapsed,1),k,v[1]) for k,v in a.items() if k in b],reverse=True)[:10]
files={}
for n in ('tools/board_camera_preview.py','board/vision/local_preview.py'):
 raw=(root/n).read_bytes();files[n]={'sha256':hashlib.sha256(raw).hexdigest(),'text':raw.decode()}
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://127.0.0.1:8783/api/state',timeout=3) as r:u=json.load(r)
print(json.dumps({'files':files,'startup_config':cfg,'cpu_percent_100hz':top,
 'preview':u['ui_runtime'].get('preview_metrics'),'ui_link':u['ui_runtime'].get('link')},sort_keys=True))
