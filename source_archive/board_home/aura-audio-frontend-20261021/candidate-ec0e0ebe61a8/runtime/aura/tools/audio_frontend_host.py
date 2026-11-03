"""Prewarmed stock GTCRN/Silero CPU pipelines, independent of ASR/LLM/TTS."""
import argparse
import hashlib
from pathlib import Path
import queue
import socketserver
import sys
import threading

AURA=Path(__file__).resolve().parents[1]
if str(AURA) not in sys.path:sys.path.insert(0,str(AURA))
from common.frontend_wire import PROTOCOL,owner,send,receive

HASHES={'gtcrn_simple.onnx':'e77603ac0c23dac3227dd2d7135b3a585cbee2679048aecfa886657d3ae1b534',
        'silero_vad_v5.onnx':'6b99cbfd39246b6706f98ec13c7c50c6b299181f2474fa05cbc8046acc274396'}


class Pipeline:
    def __init__(self,directory):
        import numpy as np
        import sherpa_onnx as s
        self.np=np
        for name,expected in HASHES.items():
            if hashlib.sha256((Path(directory)/name).read_bytes()).hexdigest()!=expected:
                raise ValueError('Audio frontend model fingerprint mismatch: '+name)
        config=s.OnlineSpeechDenoiserConfig(model=s.OfflineSpeechDenoiserModelConfig(
            gtcrn=s.OfflineSpeechDenoiserGtcrnModelConfig(model=str(Path(directory)/'gtcrn_simple.onnx')),
            num_threads=1,provider='cpu'))
        if not config.validate():raise ValueError('Invalid GTCRN configuration')
        self.denoiser=s.OnlineSpeechDenoiser(config)
        vc=s.VadModelConfig();vc.silero_vad.model=str(Path(directory)/'silero_vad_v5.onnx')
        # Existing board endpoint owns onset and 700 ms silence. Avoid applying
        # a second duration threshold here; stock SDK still owns model state.
        vc.silero_vad.threshold=.5;vc.silero_vad.min_speech_duration=0.;vc.silero_vad.min_silence_duration=0.
        vc.silero_vad.max_speech_duration=19.;vc.num_threads=1;vc.sample_rate=16000
        self.vad=s.VoiceActivityDetector(vc,buffer_size_in_seconds=22)
        self.samples=0
        for _ in range(32):self.process(bytes(640))
        self.reset()

    def reset(self):
        self.denoiser.reset();self.vad.reset();self.samples=0

    def process(self,pcm):
        if len(pcm)!=640:raise ValueError('Require one 20 ms PCM16 frame')
        samples=self.np.frombuffer(pcm,dtype='<i2').astype(self.np.float32)/32768
        out=self.denoiser(samples,16000)
        self.samples+=len(out.samples)
        if len(out.samples):self.vad.accept_waveform(out.samples)
        speech=bool(self.vad.is_speech_detected())
        while not self.vad.empty():self.vad.pop()
        return speech,self.samples


class FrontendServer(socketserver.ThreadingTCPServer):
    allow_reuse_address=True;daemon_threads=True;block_on_close=False

    def __init__(self,address,pipelines):
        self.pool=queue.Queue(maxsize=len(pipelines))
        for value in pipelines:self.pool.put_nowait(value)
        self.capacity=len(pipelines);self.connections=threading.BoundedSemaphore(4)
        super().__init__(address,Handler)

    def process_request(self,request,address):
        if not self.connections.acquire(blocking=False):self.shutdown_request(request);return
        try:super().process_request(request,address)
        except Exception:self.connections.release();raise

    def process_request_thread(self,*args):
        try:super().process_request_thread(*args)
        finally:self.connections.release()


class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        engine=None
        try:
            if self.client_address[0] not in ('127.0.0.1','192.168.50.2'):return
            hello,pcm=receive(self.request,1.)
            if pcm:raise ValueError('Handshake must not carry audio')
            if hello=={'protocol':PROTOCOL,'kind':'health'}:
                send(self.request,{'protocol':PROTOCOL,'kind':'health','ready':True,
                    'backend':'gtcrn-silero-v5-cpu','available':self.server.pool.qsize(),'capacity':self.server.capacity});return
            stream=hello.get('stream_id');owner(hello,'open',stream,0)
            engine=self.server.pool.get_nowait();engine.reset()
            send(self.request,{'protocol':PROTOCOL,'kind':'ready','stream_id':stream,'sequence':0})
            sequence=0
            while True:
                meta,pcm=receive(self.request,2.)
                sequence+=1;owner(meta,'frame',stream,sequence)
                if len(pcm)!=640:raise ValueError('Require one 20 ms frame')
                speech,processed=engine.process(pcm)
                send(self.request,{'protocol':PROTOCOL,'kind':'decision','stream_id':stream,
                    'sequence':sequence,'speech':speech,'input_samples':sequence*320,'processed_samples':processed})
        except Exception:
            # A failed/expired stream ends. It never becomes a speech decision.
            pass
        finally:
            if engine is not None:
                engine.reset();self.server.pool.put_nowait(engine)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--models',type=Path,required=True)
    parser.add_argument('--listen',default='192.168.50.1');parser.add_argument('--port',type=int,default=8795)
    args=parser.parse_args()
    pipelines=[Pipeline(args.models) for _ in range(2)]
    with FrontendServer((args.listen,args.port),pipelines) as server:server.serve_forever()


if __name__=='__main__':main()
