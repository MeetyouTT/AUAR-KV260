import base64,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
b=json.loads((HERE/'baseline.json').read_text(encoding='utf-8-sig'))
names=['aura/board/interaction/avatar_player.py','aura/tools/board_avatar_gtk.py','aura/tools/board_avatar_worker.py','aura/tools/facial_layers.py']
remote="import base64,json\nfrom pathlib import Path\nr=Path(%r)\nprint(json.dumps({n:base64.b64encode((r/n).read_bytes()).decode() for n in %r}))"%(b['runtime'],names)
files=json.loads(ssh('python3 -B -',remote,timeout=20))
for name,raw in files.items():
 p=HERE/'baseline_sources'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(base64.b64decode(raw))
print('baseline sources retained')
