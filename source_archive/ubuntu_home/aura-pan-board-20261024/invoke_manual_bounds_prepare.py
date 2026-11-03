import hashlib,runpy
from pathlib import Path
p=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/manual-bounds-v1/prepare_on_board.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='34d466fc5c783b8e87bbda5b75bb0a8735ad36282d084cdd76dcd836df2984f1'
runpy.run_path(str(p),run_name="__main__")
