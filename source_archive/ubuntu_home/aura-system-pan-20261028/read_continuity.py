import hashlib,json
from pathlib import Path
p=Path('/home/root/aura-system-pan-20261028/restore-5f167a36/continuity-reference.json')
print(json.dumps({'document':json.loads(p.read_text()),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}))
