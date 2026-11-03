import hashlib
from pathlib import Path
p=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/current-boot-follow-v1/activate_center_test_gui_r1.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='c17cbe15eb4381113b64573e1e21d49b5e7eaf27673cf920f405ea102f8d34aa'
exec(compile(p.read_bytes(),str(p),'exec'))
