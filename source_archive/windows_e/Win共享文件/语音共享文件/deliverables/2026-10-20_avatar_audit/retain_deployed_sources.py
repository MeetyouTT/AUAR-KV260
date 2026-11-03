"""Retain the exact deployed performance sources, keeping the rejected trial."""
import base64,hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'performance_candidate.json').read_text())
names=[p.relative_to(HERE/'candidate_sources').as_posix() for p in (HERE/'candidate_sources').rglob('*.py')]
remote=r'''
import base64,json,subprocess,urllib.request
from pathlib import Path
root=Path(RUNTIME);names=NAMES
s=json.load(urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4))
print(json.dumps({'files':{n:base64.b64encode((root/n).read_bytes()).decode() for n in names},
 'current_unit':subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart,ActiveState,MainPID'],text=True),
 'state':{k:s.get(k) for k in ('phase','playing','handsfree_dialogue','avatar_renderer')}}))
'''.replace('RUNTIME',repr(c['runtime']),1).replace('NAMES',repr(names),1)
r=json.loads(ssh('python3 -B -',remote,timeout=20))
for name,value in r.pop('files').items():
    raw=base64.b64decode(value);assert hashlib.sha256(raw).hexdigest()==c['files'][name],name
    (HERE/'candidate_sources'/name).write_bytes(raw)
(HERE/'handoff_state.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
print(json.dumps({'retained_files':len(names),**r}))
