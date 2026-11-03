import hashlib,importlib.util
from pathlib import Path
p=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/audio-queue-bound-v1/audio_queue_deploy.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='a6d91c971cf3d1c1a16a2da9c473b76dd6ac0002a96792941e78dc143ac52519'
s=importlib.util.spec_from_file_location('queue_deploy',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
m.main('verify')
