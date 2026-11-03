expected={'tools/board_avatar_gtk.py': '70fac66010dc2b06ec31ab285ad3edf3eb41906fa2d58d553349b116fe2ffcd1', 'tools/demo_script.py': 'e5f37b604681127f6553df971bba5f96a8e89bb87c0fef60185dec1d403d166b', 'tools/facial_layers.py': '1152eca2f2e33057363883b6bff0558675d7783a45fd6f7cc1eb77a3b1d23ab6', 'tools/gstreamer_audio.py': '7eb8149cf124dbc0c5b54a8b56ab3eb7e4a935857cec38c9cf74b28cf4c3cdaf', 'tools/gstreamer_audio_worker.py': '91c79fd7cb3177b47e895a10095096b1af8ae9e9ff6c0a66d7502e0328889591'}
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
