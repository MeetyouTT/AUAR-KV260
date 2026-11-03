"""Read-only loopback audition server with WAV seeking; no project directory listing."""
import argparse
import mimetypes
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

HERE = Path(__file__).resolve().parent
TOP = {'index.html', 'player.js', 'comparison.json'}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.serve(False)

    def do_HEAD(self):
        self.serve(True)

    def serve(self, head):
        relative = unquote(urlsplit(self.path).path).lstrip('/') or 'index.html'
        if relative not in TOP and not re.fullmatch(r'audio/[a-z0-9_]+\.wav|assets/avatar\.png', relative):
            self.send_error(404)
            return
        target = (HERE / relative).resolve()
        if not target.is_relative_to(HERE) or not target.is_file():
            self.send_error(404)
            return
        size = target.stat().st_size
        start, end = 0, size - 1
        partial = False
        if self.headers.get('Range'):
            match = re.fullmatch(r'bytes=(\d*)-(\d*)', self.headers['Range'])
            if not match or not any(match.groups()):
                self.send_error(416)
                return
            if match[1]:
                start = int(match[1])
                end = min(end, int(match[2])) if match[2] else end
            else:
                start = max(0, size - int(match[2]))
            if start > end or start >= size:
                self.send_response(416)
                self.send_header('Content-Range', f'bytes */{size}')
                self.end_headers()
                return
            partial = True
        self.send_response(206 if partial else 200)
        content_type = mimetypes.guess_type(target.name)[0] or 'application/octet-stream'
        if target.suffix == '.wav':
            content_type = 'audio/wav'
        if target.suffix in {'.html', '.js', '.json'}:
            content_type += '; charset=utf-8'
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(end - start + 1))
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; style-src 'self' 'unsafe-inline'; media-src 'self'; img-src 'self'; connect-src 'self'")
        if partial:
            self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.end_headers()
        if head:
            return
        try:
            with target.open('rb') as stream:
                stream.seek(start)
                remaining = end - start + 1
                while remaining:
                    block = stream.read(min(remaining, 65536))
                    if not block:
                        break
                    self.wfile.write(block)
                    remaining -= len(block)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8774)
    args = parser.parse_args()
    print(f'AURA audition: http://127.0.0.1:{args.port}/', flush=True)
    ThreadingHTTPServer(('127.0.0.1', args.port), Handler).serve_forever()
