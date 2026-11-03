"""Read-only local preview with range support and a fixed file allow-list."""
import argparse
import mimetypes
from pathlib import Path
import re
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import unquote,urlsplit

HERE=Path(__file__).resolve().parent
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):self.serve(False)
    def do_HEAD(self):self.serve(True)
    def serve(self,head):
        relative=unquote(urlsplit(self.path).path).lstrip('/') or 'index.html'
        if relative not in {'index.html','player.js','timeline.json'} and not re.fullmatch(r'audio/script\.wav|frames/[0-9]{3}\.webp',relative):
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
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--port',type=int,default=8771)
    args=parser.parse_args();print(f'AURA voice-script: http://127.0.0.1:{args.port}/',flush=True)
    ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()
