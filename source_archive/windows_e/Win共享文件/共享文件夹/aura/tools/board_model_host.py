"""Actual Paraformer -> Qwen3 -> OmniVoice16 service for the GTK board client."""
import argparse
import hashlib
import json
from pathlib import Path
import socket
import sys
import threading
import time

AURA=Path(__file__).resolve().parents[1]
if str(AURA) not in sys.path:sys.path.insert(0,str(AURA))
from common.asr_wire import context,decode_context,MAX_PCM
from common.voice_wire import PROTOCOL,REVISION,voice_reply
from tools.asr_server import AsrServer,Handler,Paraformer
from tools import dialogue_host_ollama as dialogue
from tools.selected_voice_service import VoiceWorker

MODEL='qwen3:4b-instruct-2507-q4_K_M'

class ModelHost:
    def __init__(self,root,python,model_path):
        self.root=Path(root)
        self.voice=VoiceWorker(self.root,python=python,model_path=model_path,engine='omnivoice')
        self.lock=threading.Lock()
        self.histories={}

    def answer(self,meta,text):
        key=(meta['board_boot_id'],meta['session_id'])
        history=self.histories.get(key,[])
        request={'request_id':meta['request_id'],'transcript':text,'scene_state':{'scene_seq':meta['generation']},
                 'allowed_emotions':['neutral','friendly','happy','sad'],'allowed_avatar_actions':[]}
        started=time.monotonic()
        reply=dialogue.build_response(request,'ollama',MODEL,history=history,strict=True,fast=True)
        llm_ms=(time.monotonic()-started)*1000
        started=time.monotonic()
        generated=self.voice.generate(reply['reply_text'])
        tts_ms=(time.monotonic()-started)*1000
        wav=Path(generated['path']);sha=hashlib.sha256(wav.read_bytes()).hexdigest()
        # Audio transport keys are content hashes, separate from engine cache identity.
        target=self.root/'audio'/f'{sha}.wav';target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists():target.write_bytes(wav.read_bytes())
        result=voice_reply({'protocol':PROTOCOL,'source_kind':'actual','engine':'omnivoice','revision':REVISION,
                           'num_step':16,'reply_text':reply['reply_text'],'emotion':reply['emotion'],
                           'sha256':sha,'bytes':target.stat().st_size,'duration_seconds':generated['duration_seconds'],
                           'llm_ms':round(llm_ms,2),'tts_ms':round(tts_ms,2),'llm_model':MODEL})
        history=(history+[{'role':'user','content':text},{'role':'assistant','content':reply['reply_text']}])[-8:]
        self.histories[key]=history
        while len(self.histories)>32:self.histories.pop(next(iter(self.histories)))
        return result

    def warmup(self):
        self.voice.warmup()
        if not self.voice.ready:raise RuntimeError(self.voice.error)
        dialogue.build_response({'request_id':'warmup','transcript':'你好','scene_state':{'scene_seq':1}},
                                'ollama',MODEL,strict=True,fast=True)

class ModelHandler(Handler):
    def do_GET(self):
        if self.path=='/health':
            self.send(200,{'ready':True,'source_kind':'actual','asr_model':self.server.engine.model_id,
                           'llm_model':MODEL,'tts':'omnivoice','num_step':16,'voice_protocol':PROTOCOL,
                           'busy':self.server.models.lock.locked()});return
        prefix='/v1/voice/audio/'
        if self.path.startswith(prefix):
            import re
            name=self.path[len(prefix):]
            if not re.fullmatch(r'[0-9a-f]{64}\.wav',name):self.send(400,{'error':'Invalid audio key'});return
            file=self.server.models.root/'audio'/name
            if not file.is_file():self.send(404,{'error':'Audio expired or missing'});return
            raw=file.read_bytes()
            try:
                self.send_response(200);self.send_header('Content-Type','audio/wav')
                self.send_header('Content-Length',str(len(raw)));self.send_header('Connection','close');self.end_headers()
                self.wfile.write(raw)
            except ConnectionError:pass
            finally:self.close_connection=True
            return
        self.send(404,{'error':'Unknown route'})

    def do_POST(self):
        if self.path!='/v1/voice/converse':super().do_POST();return
        if self.headers.get('Origin') or self.headers.get('Transfer-Encoding'):
            self.send(403,{'error':'Browser/chunked requests rejected'});return
        try:
            if len(self.headers.get_all('Content-Length',[]))!=1 or len(self.headers.get_all('X-Aura-Asr',[]))!=1:
                raise ValueError('Missing or repeated headers')
            size=int(self.headers['Content-Length'])
            if not 6400<=size<=MAX_PCM or size%2 or self.headers.get('Content-Type')!='application/octet-stream':
                raise ValueError('Bounded PCM16 required')
            meta=decode_context(self.headers['X-Aura-Asr'])
            started=time.monotonic();pcm=self.rfile.read(size);context(meta,pcm)
        except (ValueError,UnicodeError,socket.timeout) as exc:self.send(400,{'error':str(exc)});return
        if not self.server.models.lock.acquire(blocking=False):self.send(503,{'error':'Voice host busy'});return
        try:
            with self.server.inference:
                before=time.monotonic();text=self.server.engine.transcribe(pcm);asr_ms=(time.monotonic()-before)*1000
            reply={'context':meta,'source_kind':'actual','text':text,'model_id':self.server.engine.model_id,
                   'recognition_ms':round(asr_ms,2)}
            if text:reply['voice_reply']=self.server.models.answer(meta,text)
            if (time.monotonic()-started)*1000>=meta['budget_ms']:
                self.send(504,{'error':'Conversation budget expired'});return
            self.send(200,reply)
        except Exception as exc:self.send(500,{'error':type(exc).__name__+': '+str(exc)[:240]})
        finally:self.server.models.lock.release()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--listen',default='192.168.50.1')
    parser.add_argument('--port',type=int,default=8792);parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--voice-python',default=sys.executable)
    args=parser.parse_args()
    models=ModelHost(args.root,args.voice_python,AURA/'models/tts/OmniVoice')
    try:
        engine=Paraformer(AURA/'models/asr/sherpa-onnx-paraformer-zh-2023-09-14')
        models.warmup()
        server=AsrServer((args.listen,args.port),engine,handler=ModelHandler);server.models=models
        print(json.dumps({'status':'READY','listen':args.listen,'port':args.port,'protocol':PROTOCOL,
                          'asr':engine.model_id,'llm':MODEL,'tts_revision':REVISION,'num_step':16}),flush=True)
        try:server.serve_forever(poll_interval=.2)
        finally:server.server_close()
    finally:models.voice.close()

if __name__=='__main__':main()
