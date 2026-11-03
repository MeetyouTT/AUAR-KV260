"""Offline migration regression against unchanged application sources."""
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
AURA = HERE.parents[1] / '语音共享文件' / 'aura'
sys.path.insert(0, str(AURA))
os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

original_bind = socket.socket.bind
original_connect = socket.socket.connect
original_connect_ex = socket.socket.connect_ex
test_ports = set()

def test_bind(sock, address):
    if not isinstance(address, tuple) or address != ('127.0.0.1', 0):
        raise RuntimeError('Only an ephemeral loopback fixture may bind')
    result = original_bind(sock, address)
    test_ports.add(sock.getsockname()[1])
    return result

def local_connect(sock, address):
    if not isinstance(address, tuple) or address[0] != '127.0.0.1' or address[1] not in test_ports:
        raise RuntimeError('Only this process-owned loopback fixture may connect')
    return original_connect(sock, address)

def local_connect_ex(sock, address):
    if not isinstance(address, tuple) or address[0] != '127.0.0.1' or address[1] not in test_ports:
        raise RuntimeError('External networking disabled during migration simulation')
    return original_connect_ex(sock, address)

socket.socket.bind = test_bind
socket.socket.connect = local_connect
socket.socket.connect_ex = local_connect_ex

FILES = [
    'test_long_conversation.py', 'test_memory_controls.py',
    'test_session_memory.py', 'test_speaker_identity.py',
    'test_thinking_feedback.py', 'test_spoken_input.py',
    'test_reply_quality.py', 'test_silero_gate.py', 'test_history_reuse.py',
]
http_only = any(arg.startswith('--http-recheck') for arg in sys.argv)
targets = [str(AURA / 'tests' / 'framework' / name) for name in FILES]
if http_only:
    targets = [str(AURA/'tests/framework/test_long_conversation.py')+'::test_http_conversation_header_survives_new_transport_session',
        str(AURA/'tests/framework/test_memory_controls.py')+'::test_http_spoken_command_route_keeps_conversation_and_uses_database_result']
prefix = ('regression_http_permitted' if '--http-recheck-permitted' in sys.argv else 'regression_http') if http_only else 'regression'
import pytest
code = pytest.main(['-q', '-p', 'no:cacheprovider',
    '--basetemp', str(HERE / (prefix + '_tmp')),
    '--junitxml', str(HERE / (prefix + '.xml')), *targets])
tree = ET.parse(HERE / (prefix + '.xml'))
groups = []
for suite in tree.getroot().iter('testsuite'):
    groups.append(dict(suite.attrib))
cases = list(tree.getroot().iter('testcase'))
summary = {
    'exit_code': int(code), 'tests': len(cases),
    'failures': sum(c.find('failure') is not None for c in cases),
    'errors': sum(c.find('error') is not None for c in cases),
    'skipped': sum(c.find('skipped') is not None for c in cases),
    'suites': groups, 'source_tests': [str(p) for p in targets],
    'external_network_blocked': True, 'owned_loopback_test_ports': sorted(test_ports), 'real_model_inference': False,
    'scope': 'Windows x86-64 logic regression; not ARM or board acceptance',
}
summary['passed'] = summary['tests'] - summary['failures'] - summary['errors'] - summary['skipped']
(HERE / (prefix + '_summary.json')).write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(summary, ensure_ascii=False))
raise SystemExit(code)
