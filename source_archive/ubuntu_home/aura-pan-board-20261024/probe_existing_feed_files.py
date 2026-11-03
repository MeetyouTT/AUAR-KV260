"""Find whether the running pinned camera candidate already contains feed code."""
import hashlib,json
from pathlib import Path
import re,subprocess
paths=subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','DropInPaths'],text=True).split('=',1)[1].strip().split()
root=None
for name in paths:
 p=Path(name)
 try:s=p.read_text()
 except OSError:continue
 m=re.search(r'--root\s+(\S+)',s)
 if m and 'native-maintenance' in name:root=Path(m.group(1));break
assert root
meta=json.loads((root/'meta.json').read_text());base=Path(meta['candidate_root'])/'aura'
files=['board/motion/camera_feed.py','board/motion/follow.py','common/motion_observation.py',
 'tools/board_camera_motion.py','tools/board_pan_follow.py','config/pan_follow.shadow.json']
result={name:{'exists':(base/name).is_file(),
 'sha256':hashlib.sha256((base/name).read_bytes()).hexdigest() if (base/name).is_file() else None}
 for name in files}
print(json.dumps({'candidate_root_basename':base.parent.name,'feed_files':result},sort_keys=True))
