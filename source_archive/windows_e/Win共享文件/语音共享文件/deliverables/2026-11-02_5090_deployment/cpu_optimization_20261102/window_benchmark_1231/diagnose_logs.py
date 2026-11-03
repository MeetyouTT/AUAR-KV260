import json,re
from pathlib import Path
root=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13');s=json.loads((root/'startup/config.json').read_bytes());runtime=Path(s['runtime']);out={}
for p in [runtime/'launch.json',runtime/'startup.json',root/'startup/status.json']:
 if p.is_file():
  raw=p.read_bytes();v=json.loads(raw);out[str(p)]={'keys':sorted(v),'technical':{k:v[k] for k in ('pid','status','state','stdout','stderr','stdout_path','stderr_path','returncode') if k in v and (type(v[k]) in (bool,int) or k in ('stdout','stderr','stdout_path','stderr_path'))}}
logs=[]
for parent in (runtime,runtime/'logs',root/'startup',root/'logs'):
 if parent.is_dir():
  for p in parent.iterdir():
   if p.is_file() and any(k in p.name.lower() for k in ('log','stdout','stderr')):logs.append({'path':str(p),'bytes':p.stat().st_size})
print(json.dumps({'status':'TECHNICAL_LOG_PATHS_ONLY','public_files':out,'logs':logs}))
