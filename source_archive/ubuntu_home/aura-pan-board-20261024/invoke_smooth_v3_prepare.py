import hashlib,runpy
from pathlib import Path
p=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/smooth-deploy-v3/prepare.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='c0a0061a67d963bfe8ecf69822888034f3d1bff2d7e9846cc944e92066afd4bc'
runpy.run_path(str(p),run_name="__main__")
