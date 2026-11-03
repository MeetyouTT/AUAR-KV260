"""Stage exact shared sources and the existing pinned CPU-renderer snapshot."""
import hashlib,json,shutil,sys
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parents[1];A=P/'aura'
sys.path.insert(0,str(P/'deliverables/2026-10-18_board_dialogue'));from board_ssh import ssh
b=json.loads((H/'baseline.json').read_text(encoding='utf-8'))
assert not (H/'candidate/shared').exists()
for name in ('tools/realtime_facials.py','tools/idle_body_compositor.py'):
 raw=(A/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==b['pins'][name]
 path=H/'candidate/shared'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
name='tools/facial_layers.py'
script="from pathlib import Path\nimport base64,hashlib,json\np=Path("+repr(b['runtime'])+")/'aura/tools/facial_layers.py'\nr=p.read_bytes()\nassert hashlib.sha256(r).hexdigest()=="+repr(b['pins'][name])+"\nprint(json.dumps({'hex':r.hex()}))\n"
raw=bytes.fromhex(json.loads(ssh('python3 -B -',script,timeout=15))['hex'])
path=H/'board_source'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
path=H/'candidate/board'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
path=H/'candidate/windows/tools/portrait_renderer.py';path.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(A/'tools/portrait_renderer.py',path)
shutil.copytree(H.parent/'2026-10-27_windows_portrait/renderer_snapshot',H/'candidate/renderer_snapshot')
print('Visual inputs staged; no live source/config changed')
