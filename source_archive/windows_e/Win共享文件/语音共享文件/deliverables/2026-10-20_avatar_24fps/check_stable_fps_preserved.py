import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'stable_fps_candidate.json').read_text())
remote=r'''
from pathlib import Path
import hashlib,json
c=CANDIDATE;source=Path(c['source_runtime']);root=Path(c['runtime']);allowed={'aura/tools/board_avatar_gtk.py','aura/tools/board_avatar_worker.py','aura/tools/realtime_controller.py','aura/tools/streaming_controller.py'}
same=[];changed=[]
for package in ('tools','board','common','host'):
 for p in (source/'aura'/package).rglob('*.py'):
  n=p.relative_to(source).as_posix()
  if p.read_bytes()==(root/n).read_bytes():same.append(n)
  else:changed.append(n)
assert set(changed)<=allowed,changed
critical=['aura/board/runtime/audio/barge_verify.py','aura/tools/barge_in_capture.py','aura/tools/barge_in_recording.py','aura/tools/handsfree_recording.py','aura/tools/board_avatar_pan.py','aura/config/board_avatar_gtk.json']
hashes={n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in critical}
for n in critical:assert (root/n).read_bytes()==(source/n).read_bytes(),n
print(json.dumps({'passed':True,'unchanged_python_count':len(same),'changed':changed,'critical_preserved':hashes}))
'''.replace('CANDIDATE',repr(c),1)
r=json.loads(ssh('python3 -B -',remote,timeout=20));(HERE/'stable_fps_preserved.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r))
