import hashlib,runpy
from pathlib import Path
p=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/helpers/deploy-2ffe3fab6f2fd499.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='2ffe3fab6f2fd499cc2395dfdd155693a4ee114a3f0603b003496043a4838733'
runpy.run_path(str(p),run_name="__main__")
