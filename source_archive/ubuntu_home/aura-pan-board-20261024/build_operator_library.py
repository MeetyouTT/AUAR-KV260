import hashlib,runpy
from pathlib import Path
p=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/native-operator-v1/build_on_board.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='499729658ae4b4c09987b0abbee71dd4953702897b3a461c6774b071328280de'
runpy.run_path(str(p),run_name='__main__')
