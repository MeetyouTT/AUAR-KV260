import hashlib,runpy
from pathlib import Path
p=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/power-return-da36c36a/restore/switch_joint.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='f81e9522d72d53a20c093448c8835079c2c11dd1a8320cf863c6b36c8abc1d24'
runpy.run_path(str(p),run_name="__main__")
