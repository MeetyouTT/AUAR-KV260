import hashlib
from pathlib import Path
p=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/current-boot-follow-v1/shadow_live.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='5cf53a19fb59c14d2a59a0ae968159a173402f34dbd3dbcdabdc35439a4ca0c3'
exec(compile(p.read_bytes(),str(p),'exec'))
