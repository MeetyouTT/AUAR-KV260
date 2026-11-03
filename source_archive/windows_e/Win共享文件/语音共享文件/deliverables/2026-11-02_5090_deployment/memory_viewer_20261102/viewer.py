"""Loopback-only viewer; memory contents stay in RAM and are never logged."""
import datetime
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import os
from pathlib import Path
import secrets
import threading
from urllib.parse import parse_qs, urlsplit

HERE = Path(__file__).resolve().parent
TRANSPORT = HERE.parent.parent / '2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(TRANSPORT.read_bytes()).hexdigest() == '6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec = importlib.util.spec_from_file_location('memory_view_transport', TRANSPORT)
transport = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transport)
QUERY_SOURCE = (HERE / 'board_readonly_query.py').read_text(encoding='utf-8')
HTML = (HERE / 'index.html').read_bytes()
TOKEN = secrets.token_urlsafe(24)
PREFIX = '/' + TOKEN + '/'
LOCK = threading.Lock()

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send_body(self, status, payload, mime):
        self.send_response(status)
        self.send_header('Content-Type',mime)
        self.send_header('Content-Length',str(len(payload)))
        self.send_header('Cache-Control','no-store')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'self' http://localhost:* http://127.0.0.1:*")
        self.end_headers()
        try:
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        target = urlsplit(self.path)
        if self.headers.get('Host') != '127.0.0.1:' + str(self.server.server_port) or not target.path.startswith(PREFIX):
            self.send_body(404,b'Not found','text/plain');return
        route = target.path[len(PREFIX):]
        if route == '':
            self.send_body(200,HTML,'text/html; charset=utf-8');return
        if route != 'api/memory':
            self.send_body(404,b'Not found','text/plain');return
        if self.headers.get('Sec-Fetch-Site') == 'cross-site':
            self.send_body(403,b'Forbidden','text/plain');return
        expected_origin = 'http://127.0.0.1:' + str(self.server.server_port)
        if self.headers.get('Origin') not in (None,expected_origin):
            self.send_body(403,b'Forbidden','text/plain');return
        params = parse_qs(target.query)
        try:
            request = {'kind':params.get('kind',['conversation'])[0],
                       'page':int(params.get('page',['0'])[0]),
                       'query':params.get('q',[''])[0]}
            assert request['kind'] in ('all','conversation','vision','device','facts','recent')
            assert 0 <= request['page'] <= 10000 and len(request['query']) <= 100
        except (ValueError,AssertionError):
            self.send_body(400,b'Invalid query','text/plain');return
        if not LOCK.acquire(timeout=1):
            self.send_body(429,json.dumps({'error':'正在读取，请稍后刷新。'}).encode(),'application/json; charset=utf-8');return
        try:
            script = 'REQUEST = ' + repr(request) + '\n' + QUERY_SOURCE
            result = json.loads(transport.ssh('/usr/bin/python3 -B -I -S -',script,timeout=12))
            assert result['read_only'] is True and result['profile_content_included'] is False
            payload = json.dumps(result,ensure_ascii=False).encode('utf-8')
            self.send_body(200,payload,'application/json; charset=utf-8')
        except Exception:
            # Never put remote stderr, query terms or returned memory in logs.
            self.send_body(503,json.dumps({'error':'暂时无法读取板卡记忆，请确认连接后刷新。'}).encode(),'application/json; charset=utf-8')
        finally:
            LOCK.release()

server = ThreadingHTTPServer(('127.0.0.1',0),Handler)
server.daemon_threads = True
url = 'http://127.0.0.1:' + str(server.server_port) + PREFIX
session = {'url':url,'pid':os.getpid(),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'bind_address':'127.0.0.1','read_only':True,'memory_contents_written_to_local_files':False}
with (HERE / 'viewer_session.json').open('x',encoding='utf-8') as stream:
    json.dump(session,stream,indent=2)
    stream.flush()
    os.fsync(stream.fileno())
server.serve_forever(poll_interval=.5)
