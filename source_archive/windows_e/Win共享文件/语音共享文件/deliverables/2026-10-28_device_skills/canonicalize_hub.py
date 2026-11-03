"""Save the already-tested CPU service in the main source tree, byte for byte."""
import hashlib,json,shutil
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura'
manifest=json.loads((H/'windows_applied.json').read_text());result={}
for name in ('tools/device_hub.py','tools/speaker_device.py'):
 source=H/'candidate_source'/name;target=A/name;raw=source.read_bytes()
 if target.exists():assert target.read_bytes()==raw,'Preserve independent edit: '+name
 else:shutil.copy2(source,target)
 digest=hashlib.sha256(raw).hexdigest();manifest[name]={'before':None,'after':digest};result[name]=digest
 compile(raw,str(target),'exec')
entry=H/'launch_hub.py';backup=H/'before/launch_hub.py'
if not backup.exists():shutil.copy2(entry,backup)
entry.write_text("import sys\nfrom pathlib import Path\nAURA=Path(__file__).resolve().parent.parents[1]/'aura'\nsys.path.insert(0,str(AURA))\nfrom tools.device_hub import main\nmain()\n",encoding='utf-8')
(H/'windows_applied.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
(H/'canonical_hub_source.json').write_text(json.dumps({'files':result,'production_code_bytes_changed':False,'next_start_source':str(A),'running_process_restarted':False},indent=2),encoding='utf-8')
print(json.dumps(result))
