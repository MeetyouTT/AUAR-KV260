"""Isolated portrait regressions; only test-owned loopback connections allowed."""
import hashlib,json,os,socket,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;AURA=HERE.parents[1]/'aura'
sys.path[:0]=['C:/Users/35870/.codex/visualizations/2026/10/26/01a1772c-f263-75f1-bfa1-9bd865e5caa9/animation-fps-deps',str(AURA)]
os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1';sys.dont_write_bytecode=True
import tools.board_avatar_affine
bind=socket.socket.bind;connect=socket.socket.connect;connect_ex=socket.socket.connect_ex;ports=set()
def owned_bind(sock,address):
    if address!=('127.0.0.1',0):raise RuntimeError('Only test-owned loopback bind is allowed')
    value=bind(sock,address);ports.add(sock.getsockname()[1]);return value
def owned_connect(sock,address):
    if not isinstance(address,tuple) or address[0]!='127.0.0.1' or address[1] not in ports:raise RuntimeError('External test network forbidden')
    return connect(sock,address)
def owned_connect_ex(sock,address):
    if not isinstance(address,tuple) or address[0]!='127.0.0.1' or address[1] not in ports:raise RuntimeError('External test network forbidden')
    return connect_ex(sock,address)
socket.socket.bind=owned_bind;socket.socket.connect=owned_connect;socket.socket.connect_ex=owned_connect_ex
import pytest
code=pytest.main(['-q','-p','no:cacheprovider','--basetemp',str(HERE/'test_tmp'),
    '--junitxml',str(HERE/'tests.xml'),*[str(AURA/'tests/framework'/('test_'+name+'.py')) for name in
    ('portrait_offload','board_avatar_worker')]])
names=['common/portrait_wire.py','board/runtime/portrait_offload.py','tools/realtime_controller.py',
       'tools/streaming_controller.py','tools/board_avatar_worker.py','tools/portrait_host.py','tools/portrait_renderer.py',
       'tests/framework/test_portrait_offload.py']
hashes={n:hashlib.sha256((AURA/n).read_text(encoding='utf-8').encode()).hexdigest() for n in names}
hashes['tools/board_avatar_gtk.py']=hashlib.sha256((HERE/'candidate_source/tools/board_avatar_gtk.py').read_text(encoding='utf-8').encode()).hexdigest()
(HERE/'windows_tests_verified.json').write_text(json.dumps({'passed':code==0,'code':code,'source_text_sha256':hashes},indent=2),encoding='utf-8')
raise SystemExit(code)
