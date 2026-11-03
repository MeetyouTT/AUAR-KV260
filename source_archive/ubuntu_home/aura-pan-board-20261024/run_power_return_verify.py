import hashlib,runpy
from pathlib import Path
p=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/power-return-da36c36a/power_return_20261026_verify.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='a9b103901bbab2b28c4960c4abf0ed254eeb6f171f829f04dd4183ca7dd758b2'
runpy.run_path(str(p),run_name='__main__')
