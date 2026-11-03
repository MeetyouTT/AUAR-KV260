import hashlib,runpy
from pathlib import Path
p=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v3/helpers/run-ca01fa12ad8f92dc.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='ca01fa12ad8f92dc6592071e707a1822a8830df9bd8787cffa137c7b43eacd50'
runpy.run_path(str(p),run_name="__main__")
