"""Use the existing Ubuntu Codex daemon's version-matched project API.

Run through ssh with python3 - [--apply]. Default is read-only inspection.
No chat is created or resumed, and no source, model, or board service is touched.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import socket
import struct
import time
import uuid

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--apply', action='store_true')
args = parser.parse_args()
target = '/home/ghmd/Win共享文件/语音共享文件'
assert Path(target).is_dir() and os.access(target, os.R_OK | os.X_OK)
socket_path = Path.home()/'.codex'/'app-server-control'/'app-server-control.sock'
connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
connection.settimeout(15)
connection.connect(str(socket_path))
buffer = b''

def receive_exact(count):
    global buffer
    while len(buffer) < count:
        chunk = connection.recv(max(4096, count-len(buffer)))
        if not chunk:
            raise RuntimeError('Codex control connection closed')
        buffer += chunk
    value, buffer = buffer[:count], buffer[count:]
    return value

def send_frame(payload, opcode=1):
    assert len(payload) < 1048576
    header = bytes([0x80 | opcode])
    length = len(payload)
    if length < 126:
        header += bytes([0x80 | length])
    elif length <= 65535:
        header += bytes([0x80 | 126]) + struct.pack('!H', length)
    else:
        header += bytes([0x80 | 127]) + struct.pack('!Q', length)
    mask = os.urandom(4)
    connection.sendall(header + mask + bytes(value ^ mask[index % 4] for index, value in enumerate(payload)))

def receive_message():
    fragments = []
    while True:
        header = receive_exact(2)
        final, opcode = bool(header[0] & 0x80), header[0] & 15
        masked, length = bool(header[1] & 0x80), header[1] & 127
        if length == 126:
            length = struct.unpack('!H', receive_exact(2))[0]
        elif length == 127:
            length = struct.unpack('!Q', receive_exact(8))[0]
        assert length <= 16777216, 'Unexpectedly large control message'
        mask = receive_exact(4) if masked else None
        payload = receive_exact(length)
        if mask:
            payload = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
        if opcode == 8:
            raise RuntimeError('Codex closed the WebSocket: ' + payload[2:].decode('utf-8', errors='replace'))
        if opcode == 9:
            send_frame(payload, 10)
            continue
        if opcode == 10:
            continue
        assert opcode in (0, 1), 'Unexpected non-text control message'
        fragments.append(payload)
        if final:
            return json.loads(b''.join(fragments))

def send(message):
    send_frame(json.dumps(message, ensure_ascii=False).encode('utf-8'))

def rpc(method, parameters, request_id):
    assert method in ('initialize', 'project/list', 'project/create', 'project/read')
    send({'method': method, 'id': request_id, 'params': parameters})
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        response = receive_message()
        if response.get('id') == request_id:
            if 'error' in response:
                raise RuntimeError(method + ': ' + json.dumps(response['error']))
            return response['result']
    raise TimeoutError(method)

try:
    nonce = base64.b64encode(os.urandom(16)).decode('ascii')
    request = ('GET / HTTP/1.1\r\nHost: localhost\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n'
               'Sec-WebSocket-Version: 13\r\nSec-WebSocket-Key: ' + nonce + '\r\n\r\n')
    connection.sendall(request.encode('ascii'))
    while b'\r\n\r\n' not in buffer:
        buffer += connection.recv(4096)
        assert len(buffer) < 65536
    handshake, buffer = buffer.split(b'\r\n\r\n', 1)
    lines = handshake.decode('ascii').split('\r\n')
    assert lines[0].split()[1] == '101', lines[0]
    headers = {line.split(':',1)[0].lower():line.split(':',1)[1].strip() for line in lines[1:] if ':' in line}
    expected_accept = base64.b64encode(hashlib.sha1((nonce+'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode('ascii')).digest()).decode('ascii')
    assert headers.get('sec-websocket-accept') == expected_accept, 'Invalid WebSocket upgrade response'
    initialized = rpc('initialize', {'clientInfo': {'name':'aura_connection_setup', 'title':'AURA Ubuntu connection setup', 'version':'1.0'}, 'capabilities':{'experimentalApi':True}}, 1)
    send({'method':'initialized', 'params':{}})
    projects = []
    cursor = None
    request_id = 2
    while True:
        parameters = {'limit':50}
        if cursor:
            parameters['cursor'] = cursor
        page = rpc('project/list', parameters, request_id)
        request_id += 1
        projects.extend(page['data'])
        cursor = page.get('nextCursor')
        if not cursor:
            break
    matches = [project for project in projects if any(root['path'] == target for root in project['roots'])]
    assert len(matches) <= 1, 'Multiple matching projects; inspect before changing metadata'
    report = {'mode':'CHECK_ONLY', 'transport':'WebSocket over the existing local Unix control socket, reached through strict SSH',
              'daemon_restarted':False, 'network_listener_created':False, 'remote_chat_started':False,
              'target_path':target, 'projects_before_count':len(projects), 'matching_projects_before':matches,
              'server_platform_os':initialized.get('platformOs'), 'metadata_changed':False}
    if args.apply:
        if matches:
            project = matches[0]
        else:
            key = str(uuid.uuid5(uuid.NAMESPACE_URL, 'ssh://ghmd@aura-ubuntu'+target))
            created = rpc('project/create', {'idempotencyKey':key, 'name':'语音共享文件', 'roots':[{'path':target}]}, request_id)
            request_id += 1
            project = created['project']
            report['metadata_changed'] = True
        assert [root['path'] for root in project['roots']] == [target], 'Unexpected project roots'
        checked = rpc('project/read', {'projectId':project['id']}, request_id)
        assert checked['project']['id'] == project['id']
        assert checked['project']['roots'] == project['roots']
        report.update(mode='REMOTE_PROJECT_REGISTERED', project=checked['project'], project_read_verified=True)
    print(json.dumps(report, ensure_ascii=True))
finally:
    connection.close()
