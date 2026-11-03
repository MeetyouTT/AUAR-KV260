import hashlib,runpy
from pathlib import Path
p=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/power-return-da36c36a/restore/start_business.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='79982759cb67d540d32696cbd9d107d2d789c70cf8aab3b1f541e0b268c3e65e'
runpy.run_path(str(p),run_name="__main__")
