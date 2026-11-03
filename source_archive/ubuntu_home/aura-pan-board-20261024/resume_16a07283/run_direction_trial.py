import hashlib
from pathlib import Path
p=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/current-boot-manual-v1/direction_trial.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='1e0c674a6cfdbd1e770b365703e5c4a9a4384b9abec4c66ac3f8dbbfb914fd42'
exec(compile(p.read_bytes(),str(p),'exec'))
