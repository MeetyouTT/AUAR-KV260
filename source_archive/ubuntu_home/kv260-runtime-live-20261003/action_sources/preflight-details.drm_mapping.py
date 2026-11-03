import json,os
from pathlib import Path
rows=[]
for p in Path('/sys/class/drm').iterdir():
 if (p/'dev').exists():
  rows.append({'name':p.name,'device':str((p/'device').resolve()),'driver':str((p/'device/driver').resolve()),'module':str((p/'device/driver/module').resolve()),'dev':(p/'dev').read_text().strip()})
print(json.dumps(rows,indent=2),flush=True)
print('XORG',Path('/proc/1109/status').read_text(),flush=True)
