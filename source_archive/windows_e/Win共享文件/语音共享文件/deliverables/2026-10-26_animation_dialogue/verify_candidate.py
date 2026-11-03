"""Run animation/voice regressions on ARM with owned loopback test sockets."""
import base64,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
candidate=json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))
renderer_only='--renderer-only' in sys.argv
run='renderer_retry' if renderer_only else 'tests'
selected=['board_avatar_worker'] if renderer_only else candidate['test_names']
runner=r'''
import os,socket,sys
import importlib
from pathlib import Path
stage=Path(__file__).resolve().parent
root=stage/'runtime/aura';overlay=stage/'test_overlay'
sys.path[:0]=[str(overlay),str(root)];sys.dont_write_bytecode=True
for package in ('common','tools'):
    module=importlib.import_module(package)
    module.__path__=[str(overlay/package),str(root/package)]
os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1'
bind=socket.socket.bind;connect=socket.socket.connect;connect_ex=socket.socket.connect_ex;ports=set()
def own_bind(sock,address):
    if address!=('127.0.0.1',0):raise RuntimeError('Only owned loopback bind is allowed')
    value=bind(sock,address);ports.add(sock.getsockname()[1]);return value
def own_connect(sock,address):
    if not isinstance(address,tuple) or address[0]!='127.0.0.1' or address[1] not in ports:raise RuntimeError('External test network forbidden')
    return connect(sock,address)
def own_connect_ex(sock,address):
    if not isinstance(address,tuple) or address[0]!='127.0.0.1' or address[1] not in ports:raise RuntimeError('External test network forbidden')
    return connect_ex(sock,address)
socket.socket.bind=own_bind;socket.socket.connect=own_connect;socket.socket.connect_ex=own_connect_ex
def audit(event,args):
    if event=='open' and isinstance(args[0],str) and args[0].startswith('/dev/') and args[0] not in ('/dev/null','/dev/urandom'):
        raise RuntimeError('Hardware access forbidden in candidate tests')
sys.addaudithook(audit)
if PRELOAD:
    # Normal GUI construction loads this dependency before creating its worker.
    # Keep cold OpenCV import outside the 1-second scheduling/cancel assertions.
    import tools.board_avatar_affine
import pytest
names=NAMES
raise SystemExit(pytest.main(['-q','-p','no:cacheprovider','--basetemp',str(stage/'RUN_tmp'),
    '--junitxml',str(stage/'RUN.xml'),*[str(root/'tests/framework'/('test_'+name+'.py')) for name in names]]))
'''.replace('NAMES',repr(selected)).replace('PRELOAD',repr(renderer_only)).replace('RUN',run)
script=r'''
import base64,json,os,re,subprocess
from pathlib import Path
c=CANDIDATE;stage=Path(c['stage']);p=stage/'run_RUN.py';p.write_bytes(base64.b64decode(RUNNER))
result=subprocess.run(['python3','-B',str(p)],cwd=stage,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',
                     PATH='/usr/sbin:/usr/bin:/sbin:/bin'),capture_output=True,text=True,timeout=200)
(stage/'RUN_stdout.log').write_text(result.stdout);(stage/'RUN_stderr.log').write_text(result.stderr)
value=dict(passed=result.returncode==0,code=result.returncode,out=result.stdout[-1200:] if result.returncode==0 else result.stdout[-11000:],
           error=result.stderr[-2000:],log_path=str(stage/'RUN_stdout.log'),microphone_used=False,
           physical_audio_playback=False,physical_motion=False,production_changed=False)
(stage/'RUN_result.json').write_text(json.dumps(value,indent=2));print(json.dumps(value))
'''.replace('CANDIDATE',repr(candidate)).replace('RUNNER',repr(base64.b64encode(runner.encode()).decode())).replace('RUN',run)
value=json.loads(ssh('python3 -B -',script,timeout=220))
(HERE/('renderer_retry.json' if renderer_only else 'candidate_verification.json')).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(value))
raise SystemExit(0 if value['passed'] else 1)
