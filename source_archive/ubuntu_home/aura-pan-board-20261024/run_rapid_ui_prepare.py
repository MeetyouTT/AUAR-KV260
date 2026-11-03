import hashlib,runpy
from pathlib import Path
p=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-follow-shadow-stream-v2/rapid_ui_prepare-5783ff9b.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='5783ff9b68d4d14622899d930cfdf07791ff9962e0828bbe6b6644248cae6acf'
runpy.run_path(str(p),run_name='__main__')
