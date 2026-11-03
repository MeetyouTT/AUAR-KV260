import hashlib
from pathlib import Path
p=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/current-boot-follow-v1/stage_left_frame_v5.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='c18019d3240a86f6d4c04cf0388e0452444746a3b571020bc982fcc61060e481'
exec(compile(p.read_bytes(),str(p),'exec'))
