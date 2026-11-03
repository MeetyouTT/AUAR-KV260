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
from common.spoken_input import prepare_spoken_input

MODEL_CONFIG=json.loads((AURA/'config/board_dialogue_model.json').read_text(encoding='utf-8-sig'))
MODEL=MODEL_CONFIG['model']
OLLAMA_HOST=MODEL_CONFIG['ollama_host']

class ModelHost:
    def __init__(self,root,python,model_path):
        self.root=Path(root)
        self.voice=VoiceWorker(self.root,python=python,model_path=model_path,engine='omnivoice')
        self.lock=threading.Lock()
        self.histories={}
        self.meta_lock=threading.Lock();self.pending_streams={};self.latest_generations={};self.feedback_assets={}
        latency_path=AURA/'config/voice_latency.json'
        self.latency_options=json.loads(latency_path.read_text(encoding='utf-8-sig')) if latency_path.is_file() else {}
        if (set(self.latency_options)-{'reply_first','early_sentence','coalesce_chat'} or
                any(type(value) is not bool for value in self.latency_options.values())):
            raise ValueError('Invalid voice latency options')

    def register_stream(self,meta):
        key=(meta['board_boot_id'],meta['session_id'])
        with self.meta_lock:
            if meta['generation']<self.latest_generations.get(key,-1):raise ValueError('Stale stream generation')
            self.latest_generations[key]=meta['generation']
            while len(self.latest_generations)>32:self.latest_generations.pop(next(iter(self.latest_generations)))

    def complete_stream(self,meta,user,text,samples,sha):
        with self.meta_lock:
            self.pending_streams[meta['request_id']]={'context':dict(meta),'user':user,'text':text,
                'samples':samples,'sha256':sha,'expires':time.monotonic()+180}
            for key,value in list(self.pending_streams.items()):
                if value['expires']<time.monotonic():del self.pending_streams[key]
            while len(self.pending_streams)>32:self.pending_streams.pop(next(iter(self.pending_streams)))

    def acknowledge_stream(self,value):
        if not isinstance(value,dict) or set(value)!={'context','voice_sample_count','pcm_sha256'}:
            raise ValueError('Invalid playback acknowledgement')
        meta=context(value['context']);key=(meta['board_boot_id'],meta['session_id'])
        with self.meta_lock:
            pending=self.pending_streams.get(meta['request_id'])
            if (not pending or pending['context']!=meta or pending['expires']<time.monotonic()
                    or self.latest_generations.get(key)!=meta['generation']
                    or type(value['voice_sample_count']) is not int or value['voice_sample_count']!=pending['samples']
                    or value['pcm_sha256']!=pending['sha256']):raise ValueError('Stale or mismatched playback acknowledgement')
            self.histories[key]=(self.histories.get(key,[])+[{'role':'user','content':pending['user']},
                                 {'role':'assistant','content':pending['text']}])[-8:]
            while len(self.histories)>32:self.histories.pop(next(iter(self.histories)))
            del self.pending_streams[meta['request_id']]
        return {'committed':True}

    def answer(self,meta,text):
        text=prepare_spoken_input(text)['text']
        key=(meta['board_boot_id'],meta['session_id'])
        history=self.histories.get(key,[])
        request={'request_id':meta['request_id'],'transcript':text,'scene_state':{'scene_seq':meta['generation']},
                 'allowed_emotions':['neutral','friendly','happy','sad'],'allowed_avatar_actions':[]}
        started=time.monotonic()
        reply=dialogue.build_response(request,'ollama',MODEL,history=history,strict=True,fast=True,host=OLLAMA_HOST)
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
        if self.latency_options.get('reply_first'):
            from tools.dialogue_stream import OllamaReplyStream
            # Prime the same stable system prefix and serialization used by
            # live turns; do not write this maintenance request into history.
            stream=OllamaReplyStream(OLLAMA_HOST,MODEL,[],'你好',120,reply_first=True)
            try:
                for kind,value in stream:
                    if kind=='complete':break
            finally:stream.cancel()
        else:
            dialogue.build_response({'request_id':'warmup','transcript':'你好','scene_state':{'scene_seq':1}},
                                    'ollama',MODEL,strict=True,fast=True,host=OLLAMA_HOST)
        from tools.thinking_feedback import prepare
        prepare(self)

class ModelHandler(Handler):
    def do_GET(self):
        if self.path=='/health':
            from common.voice_channel import PROTOCOL as CHANNEL_PROTOCOL
            self.send(200,{'ready':True,'source_kind':'actual','asr_model':self.server.engine.model_id,
                           'llm_model':MODEL,'tts':'omnivoice','num_step':16,'voice_protocol':PROTOCOL,
                           'voice_channel_protocol':CHANNEL_PROTOCOL,'channel_experimental':True,
                           'thinking_feedback_ready':bool(getattr(self.server.models,'feedback_assets',{})),
                           'latency_options':getattr(self.server.models,'latency_options',{}),
                           'busy':self.server.models.lock.locked()});return
        prefix='/v1/voice/audio/'
        if self.path=='/v1/voice/feedback':
            self.send(200,{'assets':getattr(self.server.models,'feedback_assets',{})});return
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
        if self.path=='/v1/voice/channel/played':
            try:
                if self.headers.get('Origin') or self.headers.get('Transfer-Encoding'):raise ValueError('Invalid acknowledgement transport')
                if len(self.headers.get_all('Content-Length',[]))!=1:raise ValueError('Expected one length')
                size=int(self.headers['Content-Length'])
                if not 1<=size<=4096 or self.headers.get('Content-Type')!='application/json':raise ValueError('Invalid acknowledgement body')
                self.send(200,self.server.models.acknowledge_stream(json.loads(self.rfile.read(size))))
            except (ValueError,TypeError,KeyError):self.send(400,{'error':'Invalid/stale playback acknowledgement'})
            return
        if self.path not in ('/v1/voice/converse','/v1/voice/channel'):super().do_POST();return
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
            if self.path=='/v1/voice/channel':
                if not text:self.send(422,{'error':'No recognized speech'});return
                remaining=meta['budget_ms']/1000-(time.monotonic()-started)
                if remaining<=0:self.send(504,{'error':'Conversation budget expired'});return
                from tools.voice_channel_source import serve_channel
                serve_channel(self,meta,text,remaining,recognition_ms=round(asr_ms,2))
                return
            reply={'context':meta,'source_kind':'actual','text':text,'model_id':self.server.engine.model_id,
                   'recognition_ms':round(asr_ms,2)}
            adjustments=prepare_spoken_input(text)['adjustments']
            if adjustments:reply['input_adjustments']=adjustments
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
