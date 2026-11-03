import json,base64,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/('action_candidate.json' if (HERE/'action_candidate.json').exists() else 'stable_fps_candidate.json')).read_text())
files={p.relative_to(HERE).as_posix():base64.b64encode(p.read_bytes()).decode() for p in (HERE/'action_sources').rglob('*.py')}
test=(HERE/'test_action_connection.py').read_text(encoding='utf-8').replace("APP=HERE.parents[1]/'aura'","APP=Path(%r)/'aura'"%c['runtime'])
files['test_action_connection.py']=base64.b64encode(test.encode()).decode()
remote=r'''
import base64,json,subprocess,os
from pathlib import Path
stage=Path(STAGE)/'action-check';stage.mkdir(exist_ok=True)
for name,raw in FILES.items():
 p=stage/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(base64.b64decode(raw))
# New pure policy is loaded via a package path; retain all other production modules.
root=Path(ROOT);env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(root/'aura'))
bootstrap="import sys,common;common.__path__.insert(0,%r);import pytest;raise SystemExit(pytest.main(['-q',%r]))"%(str(stage/'action_sources/common'),str(stage/'test_action_connection.py'))
r=subprocess.run(['python3','-B','-c',bootstrap],env=env,capture_output=True,text=True,timeout=120)
print(json.dumps(dict(code=r.returncode,out=r.stdout,error=r.stderr)))
'''.replace('STAGE',repr(c['stage']),1).replace('ROOT',repr(c['runtime']),1).replace('FILES',repr(files),1)
r=json.loads(ssh('python3 -B -',remote,timeout=135));(HERE/'action_connection_tests.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r))
