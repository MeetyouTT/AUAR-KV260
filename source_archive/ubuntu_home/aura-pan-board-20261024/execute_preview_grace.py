import hashlib,runpy
from pathlib import Path
p=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/helpers/deploy-c31c7d74892b0ac3.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='c31c7d74892b0ac3991ae8cd529cd35322949a8168658ef2f726fb335add47ac'
runpy.run_path(str(p),run_name="__main__")
