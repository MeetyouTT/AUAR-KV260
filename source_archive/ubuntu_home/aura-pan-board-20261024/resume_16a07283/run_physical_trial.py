import hashlib
from pathlib import Path
p=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/current-boot-follow-v1/physical_trial.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='ab6e9a943c2db851fd8a7bdb901cc2a27a38814292b008e14edf5efda539ba9a'
exec(compile(p.read_bytes(),str(p),'exec'))
