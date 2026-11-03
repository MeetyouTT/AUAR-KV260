"""Parent-owned final hooks, staged from retained reviewed candidates only."""
import ast, json
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parents[1]
OUT=H/'candidate/final_parent';G=H.parent/'2026-10-29_gpu_coordination'

def change(source,old,new,count=1):
    assert source.count(old)==count,(old[:100],source.count(old))
    return source.replace(old,new)

name='tools/board_model_host.py'
s=(H/'candidate/windows'/name).read_text(encoding='utf-8')
start=s.index('        if (not isinstance(value,dict)',s.index('    def accept_identity_result'))
end=s.index('\n    def history_for_stream',start)
s=s[:start]+'''        from tools.binding_model_adapter import accept_model_result
        return accept_model_result(self,value)
'''+s[end:]
s=change(s,"                from tools.device_client import command\n                device_reply=command(meta,text,pcm)",'''                from tools.binding_model_adapter import prepare_channel
                device_reply,binding_exchange,binding_route=prepare_channel(
                    self.server.models,meta,text,pcm,self.headers,
                    timeout=max(.001,started+meta['budget_ms']/1000-time.monotonic()))''')
s=change(s,"serve_channel(self,meta,text,remaining,recognition_ms=round(asr_ms,2),device_reply=device_reply)",
    "serve_channel(self,meta,text,remaining,recognition_ms=round(asr_ms,2),device_reply=device_reply,identity_exchange_override=binding_exchange)")
s=change(s,"                if remaining<=0:self.send(504,{'error':'Conversation budget expired'});return",'''                if remaining<=0:
                    if binding_exchange is not None:binding_exchange.cancel()
                    self.send(504,{'error':'Conversation budget expired'});return''')
old='''                with speaker_capture_scope(self.server.models,meta,pcm,cid,
                        self.headers.get_all('X-Aura-Speaker-Visual',[]),deadline=started+meta['budget_ms']/1000):
                    pcm=None
                    serve_channel(self,meta,text,remaining,recognition_ms=round(asr_ms,2),device_reply=device_reply,identity_exchange_override=binding_exchange)'''
s=change(s,old,'''                try:
                    with speaker_capture_scope(self.server.models,meta,pcm,cid,
                            self.headers.get_all('X-Aura-Speaker-Visual',[]),deadline=started+meta['budget_ms']/1000):
                        pcm=None
                        serve_channel(self,meta,text,remaining,recognition_ms=round(asr_ms,2),device_reply=device_reply,identity_exchange_override=binding_exchange)
                finally:
                    if binding_exchange is not None:binding_exchange.cancel()''')
# Keep the small JSON route independent of the audio lock, as identity_result is.
needle="    def do_POST(self):\n"
s=change(s,needle,needle+'''        if self.path=='/v1/voice/identity/gallery':
            try:
                if (self.headers.get('Origin') or self.headers.get('Content-Type')!='application/json'
                    or len(self.headers.get_all('Content-Length',[]))!=1
                    or self.headers.get('Transfer-Encoding')):raise ValueError('Expected bounded JSON')
                size=int(self.headers['Content-Length'])
                if not 2<=size<=24576:raise ValueError('Gallery metadata too large')
                self.connection.settimeout(3)
                from tools.binding_model_adapter import accept_model_gallery
                self.send(200,accept_model_gallery(self.server.models,json.loads(self.rfile.read(size))))
            except (ValueError,UnicodeError,KeyError,TypeError,socket.timeout):self.send(400,{'error':'Invalid gallery metadata'})
            except OSError:self.send(503,{'error':'Identity service unavailable'})
            return
''')
s=change(s,'    def warmup(self):','    def warmup(self,*,deadline=None):')
s=change(s,'        self.voice.warmup()\n', '''        if deadline is None:self.voice.warmup()
        else:
            remaining=deadline-time.monotonic()
            if remaining<=0:raise TimeoutError('Original service startup budget expired')
            self.voice.warmup(timeout=min(240.,remaining))
''')
s=change(s,'        warm_deadline=time.monotonic()+120','        warm_deadline=min(time.monotonic()+120,deadline) if deadline is not None else time.monotonic()+120')
s=change(s,'        prepare(self)\n',"        prepare(self,**({'deadline':deadline} if deadline is not None else {}))\n")
s=change(s,'        try:prepare_social(self)',"        try:prepare_social(self,**({'deadline':deadline} if deadline is not None else {}))")
s=change(s,'        self.warmed_up=True\n',"        if deadline is not None and time.monotonic()>=deadline:raise TimeoutError('Original service startup budget expired')\n        self.warmed_up=True\n")
s=change(s,"                'gpu_coordination':(self.gpu_coordinator.public()", "                'cold_startup':getattr(self,'startup_evidence',None),\n                'gpu_coordination':(self.gpu_coordinator.public()")
main=s.index('def main():\n')
s=s[:main]+'''def main():
    parser=argparse.ArgumentParser();parser.add_argument('--listen',default='192.168.50.1')
    parser.add_argument('--port',type=int,default=8792);parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--voice-python',default=sys.executable)
    parser.add_argument('--startup-deadline-utc')
    args=parser.parse_args()
    startup_deadline=time.monotonic()+300
    if args.startup_deadline_utc:
        import datetime
        supplied=datetime.datetime.fromisoformat(args.startup_deadline_utc.replace('Z','+00:00'))
        if supplied.tzinfo is None:raise ValueError('Startup deadline requires UTC offset')
        remaining=(supplied-datetime.datetime.now(datetime.timezone.utc)).total_seconds()
        if not 0<remaining<=300:raise TimeoutError('Invalid or expired original startup deadline')
        startup_deadline=time.monotonic()+remaining
    from tools.voice_startup_guard import voice_startup_guard
    with voice_startup_guard(AURA,args.root,host=OLLAMA_HOST,model=MODEL,
            listen=args.listen,port=args.port,deadline=startup_deadline) as startup_evidence:
        models=ModelHost(args.root,args.voice_python,AURA/'models/tts/OmniVoice')
        models.startup_evidence=startup_evidence
        try:
            engine=Paraformer(AURA/'models/asr/sherpa-onnx-paraformer-zh-2023-09-14')
            models.warmup(deadline=startup_deadline)
            if time.monotonic()>=startup_deadline:raise TimeoutError('Original service startup budget expired')
            server=AsrServer((args.listen,args.port),engine,handler=ModelHandler);server.models=models
            print(json.dumps({'status':'READY','listen':args.listen,'port':args.port,'protocol':PROTOCOL,
                              'asr':engine.model_id,'llm':MODEL,'tts_revision':REVISION,'num_step':16}),flush=True)
            try:server.serve_forever(poll_interval=.2)
            finally:server.server_close()
        finally:
            tracker=getattr(models,'speaker_turns',None)
            if tracker is not None:tracker.close()
            models.voice.close()

if __name__=='__main__':main()
'''
target=OUT/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(s,encoding='utf-8');compile(s,name,'exec')

name='tools/voice_channel_source.py';s=(G/'candidate'/name).read_text(encoding='utf-8')
s=change(s,'def serve_channel(handler, meta, text, timeout, *, recognition_ms=None,device_reply=None):',
    'def serve_channel(handler, meta, text, timeout, *, recognition_ms=None,device_reply=None,identity_exchange_override=None):')
s=change(s,"    identity_exchange=None;visual_exchange=None","    identity_exchange=identity_exchange_override;visual_exchange=None")
s=change(s,"    if device_reply is None and identity_feature in ('enrollment-v1','enrollment-active-v1'):",
    "    if identity_exchange is None and device_reply is None and identity_feature in ('enrollment-v1','enrollment-active-v1'):")
s=change(s,"    if identity_exchange is not None:transcript_fields['identity_request']=identity_exchange.token",'''    if identity_exchange is not None:
        transcript_fields['identity_request']=identity_exchange.token
        binding_request=getattr(identity_exchange,'binding_request',None)
        if binding_request is not None:transcript_fields['binding_request']=binding_request''')
target=OUT/name;target.write_text(s,encoding='utf-8');compile(s,name,'exec')

config=dict(mode='adaptive',max_pending=2,max_wait_seconds=5.,sample_max_age_seconds=.75,
    reserve_mib=768,llm_extra_mib=512,llm_cold_extra_mib=12032,tts_extra_mib=384,tts_cold_extra_mib=5120,
    gpu_uuid='GPU-fd752a2e-1923-22d0-63af-4e3d8e6f17b8',calibration_id='5060ti16gb-27biq4xs-ctx2048-fit4096-ov16-20261030-r1')
target=OUT/'config/gpu_runtime.local.json';target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(config,indent=2),encoding='utf-8')
for name in ('tools/thinking_feedback.py','tools/social_feedback.py'):
    s=(P/'aura'/name).read_text(encoding='utf-8')
    s=change(s,'import hashlib\n','import hashlib\nimport threading\nimport uuid\n')
    s=change(s,'def prepare(models):','def prepare(models,*,deadline=None):')
    statement="generated=models.voice.generate(TEXT)" if 'thinking' in name else 'generated=models.voice.generate(text)'
    expression='TEXT' if 'thinking' in name else 'text'
    s=change(s,statement,"generated=(models.voice.generate("+expression+") if deadline is None else\n"+
      "            models.voice.generate_bounded("+expression+",deadline=deadline,cancelled=threading.Event(),request_id='startup-cue-'+uuid.uuid4().hex))")
    target=OUT/name;target.write_text(s,encoding='utf-8');compile(s,name,'exec')
print(json.dumps({'status':'PARENT_FINAL_HOOKS_STAGED','production_changed':False}))
