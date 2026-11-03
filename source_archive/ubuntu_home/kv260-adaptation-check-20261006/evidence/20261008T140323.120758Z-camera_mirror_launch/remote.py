from pathlib import Path
import hashlib
p=Path('/home/root/aura-adaptation-20261006/camera-mirror-ecc45f12f19f3c4f/mirror.py')
source=p.read_bytes()
assert hashlib.sha256(source).hexdigest()=='ecc45f12f19f3c4f88d0584f316fadb803c33f87b6727dee2db5bda732ce8175'
exec(compile(source,str(p),'exec'))
