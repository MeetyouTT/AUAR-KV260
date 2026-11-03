"""Keep the workspace GUI and its renderer dependencies equal to tested sources."""
import base64,hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))
names=['aura/tools/board_avatar_gtk.py','aura/tools/board_avatar_affine.py','aura/tools/board_avatar_worker.py',
 'aura/tools/facial_layers.py','aura/tools/realtime_facials.py','aura/board/interaction/avatar_player.py',
 'deliverables/2026-10-06_avatar_reuse/preview_script.py']
before={n:(ROOT/n).read_bytes() if (ROOT/n).exists() else None for n in names}
remote=r'''
import base64,hashlib,json
from pathlib import Path
root=Path(ROOT);c=CANDIDATE;out={}
perf=json.loads((Path(c['source_runtime']).parent/'candidate.json').read_text())
assert perf['runtime']==c['source_runtime']
expected=dict(perf['files'],**c['preserved'],**c['files'])
for name in NAMES:
 raw=(root/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==expected[name],name
 out[name]=base64.b64encode(raw).decode()
print(json.dumps({'files':out,'expected':{n:expected[n] for n in NAMES},'source_manifest':perf}))
'''.replace('ROOT',repr(c['runtime']),1).replace('CANDIDATE',repr(c),1).replace('NAMES',repr(names))
result=json.loads(ssh('python3 -B -',remote,timeout=25));payload=result['files'];expected=result['expected']
(HERE/'performance_base_manifest.json').write_text(json.dumps(result['source_manifest'],indent=2),encoding='utf-8')
for n,old in before.items():assert ((ROOT/n).read_bytes() if (ROOT/n).exists() else None)==old,'Workspace source changed concurrently: '+n
changed=[]
for n,old in before.items():
 raw=base64.b64decode(payload[n]);assert hashlib.sha256(raw).hexdigest()==expected[n]
 if old==raw:continue
 if old is not None:
  backup=HERE/'workspace-before-render-merge'/n;backup.parent.mkdir(parents=True,exist_ok=True)
  if not backup.exists():backup.write_bytes(old)
 target=ROOT/n;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw);changed.append(n)
(HERE/'workspace_source_sync.json').write_text(json.dumps({'runtime':c['runtime'],'files':{n:expected[n] for n in names},'updated':changed},indent=2),encoding='utf-8')
print(json.dumps({'workspace_matches_tested_renderer':True,'updated':changed}))
