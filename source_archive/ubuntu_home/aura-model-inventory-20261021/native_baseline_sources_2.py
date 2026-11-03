expected={'tools/gstreamer_persistent_engine.py': '443031586ea38d3acf775713a7d603ab140df4f07cf1525c0545c34ce830b02a', 'tools/handsfree_recording.py': '84e712b7963e5eb7184538b0eaf435cba64ff99b1aed4d993951f76c2cba97fe', 'tools/package_board_avatar.py': 'd26dd7006e1f989f5f2ec0b50ce33bce9948ecb1f6a43453cd1c82125ac88ea0', 'tools/realtime_audio.py': '60cd206da06639dad286692736f3fb89b2c98da75b9d674eaf07ed1fcee3237f', 'tools/realtime_facials.py': '6c280ab71d938e4ebb8894bf0088c0cf17dcff5b0f493ebb530ca11c4b514399'}
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
