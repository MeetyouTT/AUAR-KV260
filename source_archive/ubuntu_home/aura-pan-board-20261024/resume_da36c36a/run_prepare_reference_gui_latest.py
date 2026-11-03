import hashlib,runpy
from pathlib import Path
p=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/current-reference-connection-v2/prepare_gui.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='24768166920193d3dee89bbb112eaa903bf86e40931e0216272138f3a29ae609'
runpy.run_path(str(p),run_name="__main__")
