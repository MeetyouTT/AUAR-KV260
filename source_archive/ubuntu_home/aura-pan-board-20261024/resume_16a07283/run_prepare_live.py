import hashlib
from pathlib import Path
p=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/current-boot-follow-v1/prepare_live.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='19ec7e8789a4fded3b0a090b6208e94e8ae731362911393a1f55c4009302f6e6'
exec(compile(p.read_bytes(),str(p),'exec'))
