"""Serve the project's CPU Paraformer as a bounded, ASR-only PCM endpoint."""
import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import socket
import sys
import threading
import time
import wave

AURA=Path(__file__).resolve().parents[1]
if str(AURA) not in sys.path:sys.path.insert(0,str(AURA))
from common.asr_wire import PROTOCOL, MAX_PCM, decode_context, context


class Paraformer:
    def __init__(self,model_dir):
        import numpy as np
        from board.runtime.audio.asr import SherpaOfflineRecognizer, AsrConfig
        self.np=np
        self.recognizer=SherpaOfflineRecognizer(AsrConfig(model_dir=str(model_dir),prefer_int8=True,num_threads=2))
        self.model_id='paraformer-'+hashlib.sha256(Path(self.recognizer.model_path).read_bytes()).hexdigest()[:24]
        # Actual known speech is required before the endpoint can report READY.
        probe=Path(self.recognizer.model_path).parent/'test_wavs/0.wav'
        with wave.open(str(probe),'rb') as wav:
            if (wav.getnchannels(),wav.getsampwidth(),wav.getframerate())!=(1,2,16000):raise ValueError('Invalid model probe WAV')
            pcm=wav.readframes(wav.getnframes())
        self.probe_text=self.transcribe(pcm)
        if not self.probe_text:raise RuntimeError('Actual Paraformer speech probe returned no text')

    def transcribe(self,pcm):
        samples=self.np.frombuffer(pcm,dtype='<i2').astype(self.np.float32)/32768
        # Use the same recognizer with strict errors at this service boundary.
        decoder=self.recognizer._recognizer
        stream=decoder.create_stream();stream.accept_waveform(16000,samples)
        decoder.decode_stream(stream)
        return str(stream.result.text or '').strip()


class AsrServer(ThreadingHTTPServer):
    daemon_threads=True
    allow_reuse_address=True

    def __init__(self,address,engine,handler=None):
        self.engine=engine
        self.inference=threading.Lock()
        self.connections=threading.BoundedSemaphore(8)
        super().__init__(address,handler or Handler)

    def process_request(self,request,address):
        if not self.connections.acquire(blocking=False):
            self.shutdown_request(request);return
        try:super().process_request(request,address)
        except Exception:
            self.connections.release();raise

    def process_request_thread(self,*args):
        try:super().process_request_thread(*args)
        finally:self.connections.release()


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup();self.connection.settimeout(5)

    def log_message(self,*unused):pass

    def send(self,status,value):
        raw=json.dumps(value,ensure_ascii=False,allow_nan=False).encode()
        try:
            self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8')
            self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store')
            self.send_header('Connection','close');self.end_headers()
            self.wfile.write(raw)
        except ConnectionError:
            # Cancellation on Windows can abort during either headers or body.
            pass
        finally:self.close_connection=True

    def do_GET(self):
        if self.path!='/health':self.send(404,{'error':'Unknown route'});return
        self.send(200,{'protocol':PROTOCOL,'source_kind':'actual','ready':True,
                       'busy':self.server.inference.locked(),'model_id':self.server.engine.model_id,
                       'probe_text':self.server.engine.probe_text})

    def do_POST(self):
        if self.path!='/v1/asr/transcribe':self.send(404,{'error':'Unknown route'});return
        if self.headers.get('Origin') or self.headers.get('Transfer-Encoding'):
            self.send(403,{'error':'Browser/chunked requests are not supported'});return
        try:
            lengths=self.headers.get_all('Content-Length',[])
            metas=self.headers.get_all('X-Aura-Asr',[])
            if len(lengths)!=1 or len(metas)!=1:raise ValueError('Missing or repeated request headers')
            size=int(lengths[0])
            if not 6400<=size<=MAX_PCM or size%2:raise ValueError('PCM must be 0.2–20s / 16kHz / mono / PCM16')
            if self.headers.get('Content-Type')!='application/octet-stream':raise ValueError('Raw PCM is required')
            meta=decode_context(metas[0])
            if size!=meta['sample_count']*2:raise ValueError('PCM sample count mismatch')
            started=time.monotonic()
            pcm=self.rfile.read(size)
            context(meta,pcm)
        except (ValueError,UnicodeError,socket.timeout) as exc:
            self.send(400,{'error':str(exc)[:240]});return
        if not self.server.inference.acquire(blocking=False):
            self.send(503,{'error':'Recognizer is busy; current inference still owns CPU'});return
        try:
            text=self.server.engine.transcribe(pcm)
            elapsed=(time.monotonic()-started)*1000
            if elapsed>=meta['budget_ms']:
                self.send(504,{'error':'Recognition budget expired'});return
            self.send(200,{'context':meta,'source_kind':'actual','text':text,
                           'model_id':self.server.engine.model_id,'recognition_ms':round(elapsed,2)})
        except Exception as exc:self.send(500,{'error':type(exc).__name__+': '+str(exc)[:200]})
        finally:self.server.inference.release()


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--listen',default='127.0.0.1')
    parser.add_argument('--port',default=8791,type=int)
    parser.add_argument('--model-dir',type=Path,default=AURA/'models/asr')
    args=parser.parse_args(argv)
    engine=Paraformer(args.model_dir)
    server=AsrServer((args.listen,args.port),engine)
    print(json.dumps({'status':'READY','protocol':PROTOCOL,'host':args.listen,'port':server.server_port,
                      'model_id':engine.model_id,'probe_text':engine.probe_text},ensure_ascii=False),flush=True)
    try:server.serve_forever(poll_interval=.2)
    except KeyboardInterrupt:pass
    finally:server.server_close()
    return 0


if __name__=='__main__':raise SystemExit(main())
