"""Read the conflicting audit file without moving it or changing recovery markers."""
import hashlib,json
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='e004cfbf-fdde-433d-b372-c8e420db2699'
p=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/native-operator-v1/recovery-audit-1332.json.1332')
raw=p.read_bytes();d={'path':str(p),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'pid1332_exists':Path('/proc/1332').exists()}
try:
    v=json.loads(raw);d['json_valid']=True;d['top_keys']=list(v)
    d['provenance']={k:v.get(k) for k in ['boot','boot_id','pid','source_pid','checkpoint_sha256','checkpoint_unit_sha256','artificial_counter_reset','mechanical_actions']}
except (UnicodeDecodeError,ValueError):d['json_valid']=False
print(json.dumps(d))
