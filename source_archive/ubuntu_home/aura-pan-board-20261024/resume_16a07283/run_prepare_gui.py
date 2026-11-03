import hashlib
from pathlib import Path
p=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/current-boot-manual-v1/prepare_gui.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='0947e7062a8b02fbda3d09d90b3cb16ea6e68aadc7066666e4317335137ac1f1'
exec(compile(p.read_bytes(),str(p),'exec'))
