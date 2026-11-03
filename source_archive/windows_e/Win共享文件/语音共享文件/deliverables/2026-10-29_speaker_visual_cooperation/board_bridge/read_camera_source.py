import base64,hashlib,json,sys
from pathlib import Path
H=Path(__file__).resolve().parent
sys.path.insert(0,str(H.parents[1]/'2026-10-29_audio_animation_polish'))
from board_guard import ssh
entry=json.loads((H/'camera_entry.json').read_text())['camera']['argv'][2]
script="import base64,json;from pathlib import Path;p=Path("+repr(entry)+");print(base64.b64encode(p.read_bytes()).decode())"
raw=base64.b64decode(ssh('python3 -B -',script,timeout=15))
assert hashlib.sha256(raw).hexdigest()==json.loads((H/'camera_entry.json').read_text())['camera']['sources'][entry]['sha256']
(H/'camera_entry_source.py').write_bytes(raw)
print(raw.decode())
