"""Export exact non-secret source dependencies and component fingerprints."""
import base64,gzip,hashlib,json
from pathlib import Path
N=Path('/home/root/aura-pan-current-20261024/463c9307/gui-face-edge-v5');A=N/'runtime/aura'
meta=json.loads(Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/meta.json').read_text())
paths={'tools/board_avatar_gtk.py':A/'tools/board_avatar_gtk.py','tools/board_camera_preview.py':A/'tools/board_camera_preview.py',
 'common/motion_observation.py':Path(meta['candidate_root'])/'aura/common/motion_observation.py'}
files={}
for name,path in paths.items():
 raw=path.read_bytes();files[name]={'sha256':hashlib.sha256(raw).hexdigest(),'gzip_base64':base64.b64encode(gzip.compress(raw,mtime=0)).decode()}
cfg=json.loads((N/'startup/config.json').read_text())
print(json.dumps({'files':files,'component_sha256':cfg['component_sha256'],'gui_entry_sha256':cfg['gui_sha256']}))
