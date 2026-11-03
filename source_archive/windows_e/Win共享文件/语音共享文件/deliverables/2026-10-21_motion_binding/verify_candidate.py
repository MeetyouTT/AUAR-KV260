import json,sys,base64
from pathlib import Path
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'2026-10-20_avatar_24fps'
sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'));from board_ssh import ssh
c=json.loads((HERE/'candidate.json').read_text())
test=(OLD/'test_action_connection.py').read_text(encoding='utf-8')
test=test.replace("APP=HERE.parents[1]/'aura'","APP=Path(%r)/'aura'"%c['runtime'])
test=test.replace("HERE/'action_sources'/relative", "APP/relative")
test=test.replace("def test_host_control_precedes_corresponding_audio", "def test_host_control_precedes_corresponding_audio")
remote=r'''
import json,base64,subprocess,os
from pathlib import Path
c=CANDIDATE;root=Path(c['runtime']);stage=Path(c['stage']);test=stage/'test_binding_assets.py'
test.write_bytes(base64.b64decode(TEST))
env=dict(os.environ,PYTHONPATH=str(root/'aura'),PYTHONDONTWRITEBYTECODE='1',PATH='/usr/sbin:/usr/bin:/sbin:/bin')
paths=[str(p) for p in (root/'aura/tests/framework').glob('test_*.py') if any(x in p.name for x in ('voice','channel','barge','listening','frontend','handsfree','automatic','board_avatar_worker','persistent','long_conversation'))]
r=subprocess.run(['python3','-B','-m','pytest','-q','-p','no:cacheprovider',*paths,str(test)],cwd=root/'aura',env=env,capture_output=True,text=True,timeout=180)
pre=subprocess.run(['python3','-B',c['startup']+'/launcher.py','--config',c['startup']+'/config.json','--preflight'],env=env,capture_output=True,text=True,timeout=35)
print(json.dumps(dict(passed=r.returncode==0 and pre.returncode==0,tests=dict(code=r.returncode,out=r.stdout,error=r.stderr),preflight=dict(code=pre.returncode,out=pre.stdout,error=pre.stderr))))
'''.replace('CANDIDATE',repr(c),1).replace('TEST',repr(base64.b64encode(test.encode()).decode()),1)
r=json.loads(ssh('python3 -B -',remote,timeout=230));(HERE/'verification.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r))
