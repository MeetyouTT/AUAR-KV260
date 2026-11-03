import hashlib,runpy
from pathlib import Path
p=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/power-return-da36c36a/restore/verify_checkpoint.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='c3d341a528edc7498a314c0db9b77579e8c98ec18b635051bca11114e5ae5af9'
runpy.run_path(str(p),run_name="__main__")
