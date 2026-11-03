import hashlib,runpy
from pathlib import Path
p=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/attended-reference-1420/execute_reference_r1.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='3d0a778769d8c73b7830af89e0eae677890870de3d2563e131bcbd7900dfcb71'
runpy.run_path(str(p),run_name='__main__')
