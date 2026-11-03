"""Only this process's ephemeral loopback sockets; isolated synthetic databases."""
from pathlib import Path
import os,socket,sys
HERE=Path(__file__).resolve().parent;AURA=HERE.parents[1]/'aura'
sys.path.insert(0,str(AURA));sys.dont_write_bytecode=True
os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1'
bind=socket.socket.bind;connect=socket.socket.connect;connect_ex=socket.socket.connect_ex;ports=set()
def own_bind(sock,address):
    if address!=('127.0.0.1',0):raise RuntimeError('Only test-owned loopback bind is allowed')
    r=bind(sock,address);ports.add(sock.getsockname()[1]);return r
def own_connect(sock,address):
    if not isinstance(address,tuple) or address[0]!='127.0.0.1' or address[1] not in ports:raise RuntimeError('External network disabled')
    return connect(sock,address)
def own_connect_ex(sock,address):
    if not isinstance(address,tuple) or address[0]!='127.0.0.1' or address[1] not in ports:raise RuntimeError('External network disabled')
    return connect_ex(sock,address)
socket.socket.bind=own_bind;socket.socket.connect=own_connect;socket.socket.connect_ex=own_connect_ex
run=sys.argv[1] if len(sys.argv)>1 else 'initial'
if not run.replace('_','').isalnum():raise ValueError('Simple run name required')
names=['profile_memory','profile_frontend']
if '--full' in sys.argv:
    names+=['voice_worker_lifecycle','voice_service_health','voice_stack_startup','cached_voice',
    'voice_channel','first_sentence_latency','memory_controls','long_conversation','session_memory',
    'voice_barge_in','barge_verification','remote_frontend','automatic_conversation',
    'listening_timing','history_reuse','thinking_feedback','spoken_input','reply_quality','channel_jobs','conversation']
import pytest
raise SystemExit(pytest.main(['-q','-p','no:cacheprovider','--basetemp',str(HERE/(run+'_tmp')),
    '--junitxml',str(HERE/(run+'.xml')),*[str(AURA/'tests/framework'/('test_'+n+'.py')) for n in names]]))
