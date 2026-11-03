expected={'board/interaction/avatar_player.py': '65993e32e7d59893f1906506d224c4c577dd7e6c17801b2213678c82a2f16e39', 'board/runtime/audio/attention_gate.py': 'd81e8775ca02544b328041d7a787316ea234670c2313dcdaebb490e2e1b41861', 'board/runtime/audio/selected_voice.py': '9bc2185f721eea529e1f873d3b235240f2b670b24ca7c2cedd0e7355dbc02f3f', 'tests/framework/test_handsfree_dialogue.py': '0faa2db4efae1a92dad25c6f7af0ca394a0daba38d366f28954c687e85b780d9', 'tests/framework/test_persistent_audio.py': '312b6676dd035b57184ae95b19bd4b6dc81f20481f864da3c24a5b4e39b8f26d'}
import base64,gzip,hashlib,json
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='008f3e1b-c627-4b98-b120-d2a460cdbcbe'
root=Path('/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-vision-recovery-c76110abefc304bb/aura')
files={}
for name,pin in expected.items():
 p=root/name;assert p.resolve().is_relative_to(root) and p.suffix=='.py' and not p.is_symlink()
 raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==pin
 files[name]=base64.b64encode(raw).decode()
raw=json.dumps(files,sort_keys=True,separators=(',',':')).encode()
compressed=gzip.compress(raw,mtime=0);assert len(compressed)<150000
print(json.dumps({'scope':'read-only own source, exact pinned hashes, no model/config/DB',
 'sha256':hashlib.sha256(raw).hexdigest(),'gzip_base64':base64.b64encode(compressed).decode()}))
