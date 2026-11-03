"""Run full portrait/voice regression on ARM with no hardware/external network."""
import base64,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))
names=json.loads((HERE.parent/'2026-10-26_animation_dialogue/candidate.json').read_text(encoding='utf-8'))['test_names']+['portrait_offload']
focused='--focused' in sys.argv
if focused:names=['portrait_offload','animation_dialogue','board_avatar_worker']
runner=r'''
import importlib,os,socket,sys
from pathlib import Path
stage=Path(__file__).resolve().parent;root=stage/'runtime/aura';overlay=stage/'test_overlay'
sys.path[:0]=[str(overlay),str(root)];sys.dont_write_bytecode=True
for name in ('common','tools'):
    module=importlib.import_module(name);module.__path__=[str(overlay/name),str(root/name)]
os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1'
bind=socket.socket.bind;connect=socket.socket.connect;connect_ex=socket.socket.connect_ex;ports=set()
def owned_bind(sock,address):
    if address!=('127.0.0.1',0):raise RuntimeError('Only owned test loopback bind allowed')
    value=bind(sock,address);ports.add(sock.getsockname()[1]);return value
def owned_connect(sock,address):
    if not isinstance(address,tuple) or address[0]!='127.0.0.1' or address[1] not in ports:raise RuntimeError('External test network forbidden')
    return connect(sock,address)
def owned_connect_ex(sock,address):
    if not isinstance(address,tuple) or address[0]!='127.0.0.1' or address[1] not in ports:raise RuntimeError('External test network forbidden')
    return connect_ex(sock,address)
socket.socket.bind=owned_bind;socket.socket.connect=owned_connect;socket.socket.connect_ex=owned_connect_ex
def audit(event,args):
    if event=='open' and isinstance(args[0],str) and args[0].startswith('/dev/') and args[0] not in ('/dev/null','/dev/urandom'):
        raise RuntimeError('Physical device access forbidden in regression')
sys.addaudithook(audit)
import tools.board_avatar_affine
import pytest
raise SystemExit(pytest.main(['-q','-p','no:cacheprovider','--basetemp',str(stage/'tests_tmp'),
 '--junitxml',str(stage/'tests.xml'),*[str(root/'tests/framework'/('test_'+n+'.py')) for n in NAMES]]))
'''.replace('NAMES',repr(names))
if focused:runner=runner.replace("'tests_tmp'","'focused_tmp'").replace("'tests.xml'","'focused.xml'")
script=r'''
import base64,hashlib,json,os,subprocess
from pathlib import Path
c=CANDIDATE;stage=Path(c['stage']);runner=stage/'run_tests.py';runner.write_bytes(base64.b64decode(RUNNER))
result=subprocess.run(['python3','-B',str(runner)],cwd=stage,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True,timeout=300)
(stage/'tests.log').write_text(result.stdout+result.stderr)
hashes={n:hashlib.sha256((stage/'runtime/aura'/n).read_text().encode()).hexdigest() for n in c['changes']+['tests/framework/test_portrait_offload.py']}
print(json.dumps({'passed':result.returncode==0,'code':result.returncode,'out':result.stdout[-8000:],'error':result.stderr[-2000:],'source_text_sha256':hashes}))
'''.replace('CANDIDATE',repr(c)).replace('RUNNER',repr(base64.b64encode(runner.encode()).decode()))
if focused:script=script.replace("'run_tests.py'","'run_focused.py'").replace("'tests.log'","'focused.log'")
v=json.loads(ssh('python3 -B -',script,timeout=325))
(HERE/('board_focused.json' if focused else 'board_tests.json')).write_text(json.dumps(v,indent=2),encoding='utf-8')
print(json.dumps(v));raise SystemExit(0 if v['passed'] else 1)
