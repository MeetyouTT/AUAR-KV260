"""Read-only native maintenance phase, source pin and checkpoint audit."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

out=subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','DropInPaths'],text=True)
dropins=out.split('=',1)[1].strip().split()
root=None
for path in map(Path,dropins):
    try:raw=path.read_text()
    except OSError:continue
    match=re.search(r'--root\s+(\S+)',raw)
    if match and 'native-maintenance' in str(path):root=Path(match.group(1));break
assert root is not None
meta=json.loads((root/'meta.json').read_text())
state=json.loads((root/'state.json').read_text())
pins=meta.get('source_pins',{})
valid=all(hashlib.sha256((root/name).read_bytes()).hexdigest()==pin for name,pin in pins.items())
cfg=json.loads(Path(meta['candidate_config']).read_text())
cp=Path(cfg['native_execution']['checkpoint_output'])
value=None
if cp.exists() and not cp.is_symlink():
 d=json.loads(cp.read_text());s=d.get('seed',{});a=d.get('auxiliary',{})
 value={'exists':True,'schema':d.get('schema'),'scope':d.get('scope'),'source_pid':s.get('source_pid'),
  'boot':s.get('boot_id'),'fenced':bool(s.get('fenced') or a.get('fenced')),'active':bool(a.get('active')),
  'primary_waiting':bool(a.get('primary_waiting')),'pending_results':sum(bool(x) for x in a.get('pending_result_tokens',[]))}
else:value={'exists':False}
print(json.dumps({'maintenance_phase':state.get('phase'),'source_pin_count':len(pins),
 'source_pins_valid':valid,'candidate_root_basename':Path(meta['candidate_root']).name,
 'candidate_ui_pin_matches_file':hashlib.sha256((Path(meta['candidate_root'])/'aura/board/vision/ui_camera_service.py').read_bytes()).hexdigest()==meta.get('candidate_ui_sha256'),
 'checkpoint':value},sort_keys=True))
