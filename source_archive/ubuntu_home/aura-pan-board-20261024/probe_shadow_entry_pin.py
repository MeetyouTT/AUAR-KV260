"""Return only hashes and basenames needed to pin a shadow bootstrap."""
import hashlib,json
from pathlib import Path
import re,subprocess
c=subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','DropInPaths','-p','ExecStart'],text=True)
paths=[];entry=''
for line in c.splitlines():
 if line.startswith('DropInPaths='):paths=line.split('=',1)[1].split()
 if line.startswith('ExecStart='):entry=line.split('=',1)[1]
root=None
for name in paths:
 p=Path(name)
 try:s=p.read_text()
 except OSError:continue
 m=re.search(r'--root\s+(\S+)',s)
 if m and 'native-maintenance' in name:root=Path(m.group(1));break
assert root
meta=json.loads((root/'meta.json').read_text())
pin=next((v for k,v in meta.get('source_pins',{}).items() if Path(k).name=='native_entry.py'),None)
native=root/'native_entry.py'
print(json.dumps({'ops_root_basename':root.name,'native_entry_exists':native.is_file(),
 'native_entry_pin':pin,'native_entry_sha256':hashlib.sha256(native.read_bytes()).hexdigest() if native.is_file() else None,
 'pin_matches':bool(pin and native.is_file() and hashlib.sha256(native.read_bytes()).hexdigest()==pin),
 'active_exec_basename':Path(entry.split()[-1]).name if entry else None,
 'camera_ui_pin':meta.get('candidate_ui_sha256')},sort_keys=True))
