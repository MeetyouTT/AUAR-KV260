"""Read a prewarmed test's readiness or trigger it without device startup delay."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
control=json.loads((HERE/'controlled_test.json').read_text())
remote=r'''
import json,time
from pathlib import Path
p=Path(CONTROL);ready=p.with_suffix('.ready');running=False
if ready.exists():
 info=json.loads(ready.read_text());cmd=Path('/proc/%d/cmdline'%info['pid'])
 running=cmd.exists() and str(p) in cmd.read_bytes().decode().split('\0')
if GO:
 assert running,'Controlled test window expired; prepare devices again'
 p.with_suffix('.go').write_text('start');print(json.dumps({'started':True}))
else:print(json.dumps({'ready':running,'control':str(p)}))
'''.replace('CONTROL',repr(control['path']),1).replace('GO',repr('--go' in sys.argv),1)
print(ssh('python3 -B -',remote,timeout=15))
