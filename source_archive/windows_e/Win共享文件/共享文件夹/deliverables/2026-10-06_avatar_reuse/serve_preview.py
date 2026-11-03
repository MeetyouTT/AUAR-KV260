"""Loopback-only preview; explicit assets and one validated candidate-save endpoint."""
import argparse
import io
import json
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import re
from urllib.parse import unquote,urlsplit
import zipfile
from PIL import Image

HERE=Path(__file__).resolve().parent
SHARED=HERE.parent.parent
RAW=SHARED/'deliverables/avatar_candidates/batch_003_guide_probe/raw/e2_rest_s421001_L124_guide62'
class Handler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path not in ('/candidate','/candidate_b') or self.headers.get('Origin')!=f'http://127.0.0.1:{self.server.server_port}':
            self.send_error(403);return
        size=int(self.headers.get('Content-Length','0'))
        if not 0<size<32*1024*1024:self.send_error(413);return
        try:
            data=self.rfile.read(size)
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                expected={f'{i:06d}.png' for i in range(39)}|{'meta.json'}
                assert len(archive.infolist())==40 and set(archive.namelist())==expected
                assert sum(i.file_size for i in archive.infolist())<32*1024*1024
                assert archive.testzip() is None
                contents={name:archive.read(name) for name in expected}
                meta=json.loads(contents['meta.json'])
                assert meta['frames']==39 and meta['fps']==24 and meta['size']==[464,480]
                assert all(value.startswith(b'\x89PNG\r\n\x1a\n') for name,value in contents.items() if name.endswith('.png'))
            name='talking_calm_reuse_v1_b' if self.path=='/candidate_b' else 'talking_calm_reuse_v1'
            assert meta['name']==name
            target=HERE/'candidates'/name
            if target.exists():
                for name,value in contents.items():
                    if name.endswith('.png'):
                        with Image.open(target/name) as saved,Image.open(io.BytesIO(value)) as incoming:
                            assert saved.size==incoming.size and saved.mode==incoming.mode and saved.tobytes()==incoming.tobytes(),'different candidate already exists'
                    else:
                        assert (target/name).read_bytes()==value,'different metadata already exists'
            else:
                target.mkdir(parents=True)
                for name,value in contents.items():(target/name).write_bytes(value)
            result=json.dumps({'saved':str(target),'frames':39,'pngBytes':sum(p.stat().st_size for p in target.glob('*.png'))}).encode()
            self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(result)));self.end_headers();self.wfile.write(result)
        except Exception as exc:
            self.send_error(400,str(exc))
    def translate_path(self,path):
        route=unquote(urlsplit(path).path)
        if route in ('/','/index.html','/player.js','/profile.json'):
            return str(HERE/('index.html' if route=='/' else route[1:]))
        if route=='/media/anchor.png':return str(SHARED/'aura/assets/avatar/idle_normal/000000.png')
        match=re.fullmatch(r'/media/e2/(\d{6})\.png',route)
        if match and 0<=int(match[1])<124:return str(RAW/(match[1]+'.png'))
        return str(HERE/'__not_found__')
    def log_message(self,*args):pass

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--port',type=int,default=8767);args=ap.parse_args()
    print(f'Preview: http://127.0.0.1:{args.port}',flush=True)
    ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()
