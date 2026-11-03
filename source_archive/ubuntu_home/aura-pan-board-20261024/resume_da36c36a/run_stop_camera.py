import hashlib,runpy
from pathlib import Path
p=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/power-return-da36c36a/restore/stop_camera.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='e6b2aa6ea2bf35643dcfb6ce4e46d20c1a0e6990b004f713d1a106e3fb216c03'
runpy.run_path(str(p),run_name="__main__")
