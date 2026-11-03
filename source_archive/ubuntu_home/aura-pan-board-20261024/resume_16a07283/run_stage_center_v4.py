import hashlib
from pathlib import Path
p=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/current-boot-follow-v1/stage_center_v4.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='9859a99cb3ff0288a047653b756a9f4f1fd80dd143ff0bf9ecb0032217b754f1'
exec(compile(p.read_bytes(),str(p),'exec'))
