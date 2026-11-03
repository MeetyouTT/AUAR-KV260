import hashlib,runpy
from pathlib import Path
p=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/helpers/deploy-e83bab383d210636.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='e83bab383d21063670a3f2543413646064ac2f04e4fbd323c0b23585a6dfbed2'
runpy.run_path(str(p),run_name="__main__")
