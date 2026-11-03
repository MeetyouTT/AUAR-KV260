from pathlib import Path
import hashlib,json,sys,time
HERE=Path(__file__).resolve().parents[1];PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
source=(HERE/'remote/read_alsa_hardware_metadata.py').read_bytes()
result=json.loads(ssh('python3 -B -',source.decode('utf-8'),timeout=12))
report=dict(source_sha256=hashlib.sha256(source).hexdigest(),result=result)
path=HERE/'evidence'/('alsa_hardware_metadata_'+str(time.time_ns())+'.json')
raw=(json.dumps(report,indent=2)+'\n').encode()
with path.open('xb') as f:f.write(raw)
print(json.dumps(dict(evidence=str(path),sha256=hashlib.sha256(raw).hexdigest(),**report)))
