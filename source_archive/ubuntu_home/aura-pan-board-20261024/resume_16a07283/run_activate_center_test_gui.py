import hashlib
from pathlib import Path
p=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/current-boot-follow-v1/activate_center_test_gui.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='b72646ed71a098acf0ba8ca971e402c9d50e5ae979ed0ac1c48931b846f4ab82'
exec(compile(p.read_bytes(),str(p),'exec'))
