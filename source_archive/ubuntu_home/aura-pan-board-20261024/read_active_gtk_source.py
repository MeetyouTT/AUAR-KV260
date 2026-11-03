import base64,gzip,hashlib,json
from pathlib import Path
p=Path('/home/root/aura-pan-current-20261024/463c9307/gui-face-edge-v5/runtime/aura/tools/board_avatar_gtk.py');raw=p.read_bytes()
print(json.dumps({'sha256':hashlib.sha256(raw).hexdigest(),'gzip_base64':base64.b64encode(gzip.compress(raw,mtime=0)).decode()}))
