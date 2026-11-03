import sys,json,base64
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'stable_fps_candidate.json').read_text());s=(HERE/'test_stable_fps.py').read_text(encoding='utf-8')
s=s.replace("HERE.parents[1]/'aura'","Path(%r)/'aura'"%c['runtime']).replace("HERE/'stable_fps_sources/","Path(%r)/'aura/tools/"%c['runtime'])
remote=r'''
import base64,subprocess,json,os
from pathlib import Path
p=Path(STAGE)/'test_stable_fps.py';p.write_bytes(base64.b64decode(TEST))
r=subprocess.run(['python3','-B',str(p)],capture_output=True,text=True,timeout=15,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
print(json.dumps({'passed':r.returncode==0,'code':r.returncode,'out':r.stdout,'error':r.stderr}))
'''.replace('STAGE',repr(c['stage']),1).replace('TEST',repr(base64.b64encode(s.encode()).decode()),1)
r=json.loads(ssh('python3 -B -',remote,timeout=25));(HERE/'stable_fps_target_tests.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r))
