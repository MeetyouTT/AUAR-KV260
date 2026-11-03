"""Run only synthetic math; it imports no physical actuator or DPU model."""
import hashlib,json,runpy,sys
from pathlib import Path
OPS=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735');M=OPS/'pan-face-edge-v5/continuous-v2'
p=M/'deployment-manifest.json';assert hashlib.sha256(p.read_bytes()).hexdigest()=='7b94b6f7838878647c5efbad55fb33e8505fd59c4663d2f45cc12dda1a98f068'
assert all(hashlib.sha256(Path(x['destination']).read_bytes()).hexdigest()==x['sha256'] for x in json.loads(p.read_text())['files'])
meta=json.loads((OPS/'meta.json').read_text());sys.path.insert(0,str(Path(meta['candidate_root'])/'aura'))
runpy.run_path(str(M/'replay_feedback.py'),run_name='__main__')
