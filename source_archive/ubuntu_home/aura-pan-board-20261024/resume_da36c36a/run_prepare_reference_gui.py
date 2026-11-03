import hashlib,runpy
from pathlib import Path
p=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/current-reference-connection-v1/prepare_gui.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='c7e4a1c82135e3e57b7d00a5751f13b75c43aedc787a71c3d50bf233669b786c'
runpy.run_path(str(p),run_name="__main__")
