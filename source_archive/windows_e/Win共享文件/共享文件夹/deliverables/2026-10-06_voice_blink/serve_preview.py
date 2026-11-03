"""Loopback voice/blink preview, bounded speech jobs and verified file routes."""
import argparse
import json
import mimetypes
from pathlib import Path
import re
import sys
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import unquote,urlsplit

HERE=Path(__file__).resolve().parent
AURA=HERE.parent.parent/'aura';sys.path.insert(0,str(AURA))
from tools.selected_voice_service import SpeechJobs

class Handler(BaseHTTPRequestHandler):
    def do_HEAD(self):self.serve(True)
    def reply(self,status,data):
        payload=json.dumps(data,ensure_ascii=False).encode('utf-8')
        self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(payload)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(payload)

    def do_GET(self):
        path=urlsplit(self.path).path
        if re.fullmatch(r'/api/job/[0-9a-f]{32}',path):
            try:self.reply(200,self.server.jobs.get(path.rsplit('/',1)[1]))
            except KeyError:self.reply(404,{'error':'Unknown speech job'})
            return
        self.serve(False)

    def do_POST(self):
        port=self.server.server_address[1]
        allowed={f'http://127.0.0.1:{port}',f'http://localhost:{port}'}
        if self.headers.get('Origin') not in allowed or self.headers.get('Host') not in {f'127.0.0.1:{port}',f'localhost:{port}'}:
            self.reply(403,{'error':'Use the local preview page to submit speech'});return
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=8192 or self.headers.get('Content-Type','').split(';')[0]!='application/json':raise ValueError('Invalid request')
            data=json.loads(self.rfile.read(size))
            if not isinstance(data,dict):raise ValueError('Invalid JSON request')
            if self.path=='/api/speech':
                if set(data)-{'text','emotion'}:raise ValueError('Unknown request fields')
                self.reply(202,self.server.jobs.submit(data.get('text'),data.get('emotion','neutral')))
            elif self.path=='/api/cancel':
                if set(data)!={'id'} or not re.fullmatch('[0-9a-f]{32}',str(data['id'])):raise ValueError('Invalid job id')
                self.reply(200,self.server.jobs.cancel(data['id']))
            else:self.reply(404,{'error':'Unknown endpoint'})
        except (ValueError,TypeError,json.JSONDecodeError):self.reply(400,{'error':'请输入1到240字的台词，并使用支持的表情。'})
        except KeyError:self.reply(404,{'error':'Unknown speech job'})

    def serve(self,head):
        relative=unquote(urlsplit(self.path).path).lstrip('/') or 'index.html'
        if relative not in {'index.html','player.js','timeline.json','live_assets.json'} and not re.fullmatch(r'audio/script\.wav|frames/[0-9]{3}\.webp|assets/mouths\.webp|eyes/[a-z_]+_[0-6]\.png|cache/[0-9a-f]{64}\.wav',relative):
            self.send_error(404);return
        path=(HERE/relative).resolve()
        if not path.is_relative_to(HERE) or not path.is_file():self.send_error(404);return
        size=path.stat().st_size;start=0;end=size-1;partial=False
        if self.headers.get('Range'):
            match=re.fullmatch(r'bytes=(\d*)-(\d*)',self.headers['Range'])
            if not match or not any(match.groups()):self.send_error(416);return
            if match[1]:
                start=int(match[1]);end=min(end,int(match[2])) if match[2] else end
            else:start=max(0,size-int(match[2]))
            if start>end or start>=size:
                self.send_response(416);self.send_header('Content-Range',f'bytes */{size}');self.end_headers();return
            partial=True
        self.send_response(206 if partial else 200)
        mime=mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
        if path.suffix=='.wav':mime='audio/wav'
        if path.suffix in {'.html','.js','.json'}:mime+='; charset=utf-8'
        self.send_header('Content-Type',mime);self.send_header('Content-Length',str(end-start+1))
        self.send_header('Accept-Ranges','bytes');self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'self'; style-src 'self' 'unsafe-inline'; media-src 'self'; img-src 'self'; connect-src 'self'")
        if partial:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
        self.end_headers()
        if head:return
        try:
            with path.open('rb') as stream:
                stream.seek(start);remaining=end-start+1
                while remaining:
                    chunk=stream.read(min(65536,remaining))
                    if not chunk:break
                    self.wfile.write(chunk);remaining-=len(chunk)
        except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError):pass


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--port',type=int,default=8772);args=parser.parse_args()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler);server.jobs=SpeechJobs(HERE)
    print(f'AURA voice/blink: http://127.0.0.1:{args.port}/',flush=True)
    try:server.serve_forever()
    finally:server.jobs.close();server.server_close()
