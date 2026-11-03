import hashlib,runpy
from pathlib import Path
p=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/power-return-da36c36a/restore/prepare_restore.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='d1f7730efd421547baf18907939a055152822399298d33a7e7564629ca81ec38'
runpy.run_path(str(p),run_name="__main__")
