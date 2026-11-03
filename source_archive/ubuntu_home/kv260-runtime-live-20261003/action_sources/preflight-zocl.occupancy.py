import os,json
from pathlib import Path
nodes=[]
for p in Path('/sys/class/drm').iterdir():
 m=p/'device/driver/module'
 if m.exists() and m.resolve()==Path('/sys/module/zocl'):nodes.append('/dev/dri/'+p.name)
assert set(nodes)=={'/dev/dri/card1','/dev/dri/renderD128'}
clients=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  for fd in (p/'fd').iterdir():
   try:t=os.readlink(fd).split(' (deleted)')[0]
   except FileNotFoundError:continue
   if t in nodes:clients.append({'pid':p.name,'target':t})
 except FileNotFoundError:continue
print(json.dumps({'zocl_nodes':nodes,'zocl_clients':clients,'refcnt':Path('/sys/module/zocl/refcnt').read_text().strip()}),flush=True)
assert not clients
assert Path('/sys/module/zocl/refcnt').read_text().strip()=='0'
