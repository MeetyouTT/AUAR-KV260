import hashlib
from pathlib import Path
p=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/current-boot-manual-v1/activate_gui.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='e342ba0b9ec8fdcd3f5f4c4530b81c30f0f6458e37567aa76fbf27301814a2a9'
exec(compile(p.read_bytes(),str(p),'exec'))
