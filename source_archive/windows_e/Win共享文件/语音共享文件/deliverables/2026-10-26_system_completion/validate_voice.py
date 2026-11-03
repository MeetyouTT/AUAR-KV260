"""Portable voice regressions with only process-owned loopback test sockets."""
import os
from pathlib import Path
import socket
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
AURA=HERE.parents[1]/'aura'
sys.path.insert(0,str(AURA))
os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1'
original_bind=socket.socket.bind
original_connect=socket.socket.connect
original_connect_ex=socket.socket.connect_ex
ports=set()
def bind(sock,address):
    if not isinstance(address,tuple) or address!=('127.0.0.1',0):raise RuntimeError('Only test loopback ephemeral bind is allowed')
    value=original_bind(sock,address);ports.add(sock.getsockname()[1]);return value
def connect(sock,address):
    if not isinstance(address,tuple) or address[0]!='127.0.0.1' or address[1] not in ports:raise RuntimeError('External test networking disabled')
    return original_connect(sock,address)
def connect_ex(sock,address):
    if not isinstance(address,tuple) or address[0]!='127.0.0.1' or address[1] not in ports:raise RuntimeError('External test networking disabled')
    return original_connect_ex(sock,address)
socket.socket.bind=bind;socket.socket.connect=connect;socket.socket.connect_ex=connect_ex
names=['voice_worker_lifecycle','voice_service_health','voice_stack_startup','cached_voice',
    'voice_channel','first_sentence_latency','memory_controls','long_conversation',
    'voice_barge_in','barge_verification','remote_frontend','automatic_conversation',
    'listening_timing','history_reuse','thinking_feedback','spoken_input','reply_quality',
    'channel_jobs','conversation']
run=sys.argv[1] if len(sys.argv)>1 else 'portable'
if not run.replace('_','').isalnum():raise ValueError('Use a simple run name')
temporary=(HERE/(run+'_tmp')).resolve()
assert temporary.parent==HERE.resolve()
import pytest
raise SystemExit(pytest.main(['-q','-p','no:cacheprovider','--basetemp',str(temporary),
    '--junitxml',str(HERE/('voice_'+run+'.xml')),*[str(AURA/'tests/framework'/('test_'+name+'.py')) for name in names]]))
