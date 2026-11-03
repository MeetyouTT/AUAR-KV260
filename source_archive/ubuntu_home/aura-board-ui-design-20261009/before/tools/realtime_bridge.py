"""Loopback controls for the actual live Qt stage (no baked script frames)."""
import json
from pathlib import Path
import queue
import threading
import time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit

class StageBridge:
    def __init__(self,root,port,extra_commands=()):
        self.root=Path(root);self.port=port;self.commands=queue.Queue(maxsize=16)
        self.lock=threading.Lock();self.state={};self.frame=b'';self.sequence=0
        self.allowed_commands={'speak','event','pause','demo','snapshot','save_evidence','dialogue'}|set(extra_commands)
        bridge=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def respond(self,status,payload,mime='application/json; charset=utf-8'):
                if not isinstance(payload,bytes):payload=json.dumps(payload,ensure_ascii=False).encode('utf-8')
                self.send_response(status);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(payload)))
                self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
                self.send_header('Content-Security-Policy',"default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' blob:; connect-src 'self'")
                self.end_headers()
                try:self.wfile.write(payload)
                except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError):pass
            def do_GET(self):
                path=urlsplit(self.path).path
                if path=='/api/state':
                    with bridge.lock:state=dict(bridge.state)
                    self.respond(200,state);return
                if path=='/api/frame':
                    with bridge.lock:frame=bridge.frame
                    self.respond(200,frame,'image/jpeg');return
                if path=='/':self.respond(200,(bridge.root/'index.html').read_bytes(),'text/html; charset=utf-8');return
                if path=='/player.js':self.respond(200,(bridge.root/'player.js').read_bytes(),'text/javascript; charset=utf-8');return
                self.send_error(404)
            def do_POST(self):
                port=bridge.port
                if self.headers.get('Origin') not in {f'http://127.0.0.1:{port}',f'http://localhost:{port}'} or self.headers.get('Host') not in {f'127.0.0.1:{port}',f'localhost:{port}'}:
                    self.respond(403,{'error':'请通过本机演示页面操作'});return
                if self.path!='/api/command':self.send_error(404);return
                try:
                    length=int(self.headers.get('Content-Length','0'))
                    if not 0<length<=8192 or self.headers.get('Content-Type','').split(';')[0]!='application/json':raise ValueError()
                    data=json.loads(self.rfile.read(length))
                    if not isinstance(data,dict) or data.get('type') not in bridge.allowed_commands:raise ValueError()
                    if data['type']=='speak':
                        from board.runtime.audio.selected_voice import normalize_text
                        normalize_text(data.get('text'))
                    request={'data':data,'done':threading.Event(),'deadline':time.monotonic()+3};bridge.commands.put_nowait(request)
                    if not request['done'].wait(3):self.respond(503,{'error':'演示台暂忙，请重试'});return
                    self.respond(400 if request.get('error') else 200,{'error':request['error']} if request.get('error') else request.get('result',{'ok':True}))
                except (ValueError,TypeError,queue.Full):self.respond(400,{'error':'请检查台词、表情或动作选项'} )
        self.server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()

    def publish(self,state,frame):
        with self.lock:self.sequence+=1;self.state=dict(state,sequence=self.sequence);self.frame=frame

    def close(self):self.server.shutdown();self.server.server_close()
