import hashlib
from pathlib import Path
p=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/current-boot-follow-v1/activate_test_gui.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='12be7e7cd952a886fd24b4473e7a0c4a508b601e6b15b7858682ea3c6e34055e'
exec(compile(p.read_bytes(),str(p),'exec'))
