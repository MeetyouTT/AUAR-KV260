"""Temporary read-only whitelist asset server bound to the existing board LAN.

Only the known board peer can GET prehashed public model/wheel/candidate assets.
No uploads, directory listings, business payloads, private paths or request logs.
"""
import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('manifest',type=Path)
    parser.add_argument('--host',default='192.168.50.1')
    parser.add_argument('--peer',default='192.168.50.2')
    parser.add_argument('--ttl',type=int,default=300)
    args=parser.parse_args()
    assert args.host=='192.168.50.1' and args.peer=='192.168.50.2' and 1<=args.ttl<=600
    manifest=json.loads(args.manifest.read_text(encoding='utf-8'))
    entries={item['sha256']:item for item in manifest['entries']}
    for item in entries.values():
        path=Path(item['source'])
        assert path.is_file() and not path.is_symlink() and path.stat().st_size==item['bytes']
        h=hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
        assert h.hexdigest()==item['sha256']
    public=dict(manifest,entries=[{k:v for k,v in item.items() if k!='source'} for item in manifest['entries']])
    encoded=json.dumps(public,separators=(',',':')).encode()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            if self.client_address[0]!=args.peer:
                self.send_error(403);return
            if self.path=='/manifest.json':
                self.send_response(200);self.send_header('Content-Length',str(len(encoded)));self.end_headers()
                self.wfile.write(encoded);return
            item=entries.get(self.path.removeprefix('/assets/')) if self.path.startswith('/assets/') else None
            if item is None:self.send_error(404);return
            self.send_response(200);self.send_header('Content-Length',str(item['bytes']));self.end_headers()
            with Path(item['source']).open('rb') as stream:
                for block in iter(lambda:stream.read(1024*1024),b''):self.wfile.write(block)
    server=ThreadingHTTPServer((args.host,0),Handler)
    timer=threading.Timer(args.ttl,server.shutdown);timer.daemon=True;timer.start()
    print(json.dumps({'address':server.server_address,'ttl':args.ttl,'public_entries':len(entries)}),flush=True)
    try:server.serve_forever(poll_interval=.2)
    finally:timer.cancel();server.server_close()


if __name__=='__main__':main()
