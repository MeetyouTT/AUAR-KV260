"""Independent wired CPU renderer; one active board stream and bounded packets."""
import argparse
import json
from pathlib import Path
import socket
import socketserver
import sys
import threading
import time

AURA=Path(__file__).resolve().parents[1]
if str(AURA) not in sys.path:sys.path.insert(0,str(AURA))
from common import portrait_wire as wire

class PortraitServer(socketserver.ThreadingMixIn,socketserver.TCPServer):
    daemon_threads=True;allow_reuse_address=False;request_queue_size=2
    def __init__(self,address,renderer):
        self.renderer=renderer;self.stream=threading.Lock();self.connections=threading.BoundedSemaphore(3)
        self.frames=0;self.errors=0
        super().__init__(address,PortraitHandler)
    def verify_request(self,request,address):return address[0] in ('192.168.50.2','192.168.50.1','127.0.0.1')
    def process_request(self,request,address):
        if not self.connections.acquire(blocking=False):request.close();return
        try:super().process_request(request,address)
        except Exception:self.connections.release();raise
    def process_request_thread(self,*args):
        try:super().process_request_thread(*args)
        finally:self.connections.release()
    def handle_error(self,request,address):self.errors+=1

class PortraitHandler(socketserver.BaseRequestHandler):
    def handle(self):
        owned=False;connection=self.request;connection.settimeout(2)
        connection.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
        try:
            while True:
                header,payload=wire.receive(connection,0)
                if header=={'protocol':wire.PROTOCOL,'kind':'health'}:
                    wire.send(connection,dict(protocol=wire.PROTOCOL,kind='health',ready=True,
                        revision=self.server.renderer.revision,width=self.server.renderer.size[0],height=self.server.renderer.size[1],
                        frames=self.server.frames,errors=self.server.errors));return
                wire.plan(header)
                if not owned:
                    if not self.server.stream.acquire(timeout=.1):return
                    owned=True
                frame,pixels=self.server.renderer.render(header)
                wire.send(connection,frame,pixels);self.server.frames+=1
        except (OSError,EOFError,ValueError):pass
        finally:
            if owned:self.server.stream.release()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True);args=parser.parse_args()
    config=json.loads(args.config.read_text(encoding='utf-8'))
    if config['listen']!='192.168.50.1':raise ValueError('Renderer must bind to the dedicated wired interface')
    from tools.portrait_renderer import PortraitRenderer
    renderer=PortraitRenderer(AURA,config['snapshot'],(config['width'],config['height']),config['background'])
    with PortraitServer((config['listen'],config['port']),renderer) as server:
        print(json.dumps({'status':'READY','port':config['port'],'revision':renderer.revision,'cpu_only':True}),flush=True)
        server.serve_forever(poll_interval=.2)

if __name__=='__main__':main()
