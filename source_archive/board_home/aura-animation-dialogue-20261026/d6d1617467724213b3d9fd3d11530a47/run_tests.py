
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
import pytest
names=['profile_memory', 'profile_frontend', 'animation_dialogue', 'board_avatar_worker', 'voice_worker_lifecycle', 'voice_service_health', 'cached_voice', 'voice_channel', 'first_sentence_latency', 'memory_controls', 'long_conversation', 'session_memory', 'voice_barge_in', 'barge_verification', 'remote_frontend', 'automatic_conversation', 'listening_timing', 'history_reuse', 'thinking_feedback', 'spoken_input', 'reply_quality', 'channel_jobs', 'conversation']
raise SystemExit(pytest.main(['-q','-p','no:cacheprovider','--basetemp',str(stage/'tests_tmp'),
    '--junitxml',str(stage/'tests.xml'),*[str(root/'tests/framework'/('test_'+name+'.py')) for name in names]]))
