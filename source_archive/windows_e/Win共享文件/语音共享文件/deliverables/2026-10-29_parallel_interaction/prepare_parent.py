"""Combine parent-owned integration from exact baseline bytes; no live writes."""
import hashlib,json
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parents[1];A=P/'aura';b=json.loads((H/'baseline.json').read_text(encoding='utf-8'))
name='tools/board_model_host.py';path=A/name
assert hashlib.sha256(path.read_bytes()).hexdigest()==b['sources'][name]
source=path.read_text(encoding='utf-8')
def replace(old,new,count=1):
    global source
    assert source.count(old)==count,(old[:80],source.count(old))
    source=source.replace(old,new)
replace('import argparse\n','import argparse\nfrom contextlib import nullcontext\n')
replace('        self.root=Path(root)\n', '''        from common.gpu_coordination import GpuCoordinator,GpuPolicy,NvidiaMemoryProbe,OllamaResidencyProbe
        gpu_config=AURA/'config/gpu_runtime.local.json'
        gpu_values=json.loads(gpu_config.read_text(encoding='utf-8')) if gpu_config.is_file() else {}
        self.gpu_coordinator=GpuCoordinator(GpuPolicy.from_dict(gpu_values),NvidiaMemoryProbe(),
            llm_residency=OllamaResidencyProbe(OLLAMA_HOST,MODEL))
        self.root=Path(root)
''')
replace("self.voice=VoiceWorker(self.root,python=python,model_path=model_path,engine='omnivoice')",
        "self.voice=VoiceWorker(self.root,python=python,model_path=model_path,engine='omnivoice',gpu_coordinator=self.gpu_coordinator)")
replace('        latency_path=AURA/', '''        from tools.speaker_conversation import SpeakerConversation
        self.speaker_capture_local=threading.local()
        self.speaker_turns=SpeakerConversation(self.conversations,scope_for=lambda meta:turn_profile(self,meta))
        self.speaker_visual_invalid_headers=0
        latency_path=AURA/''')
replace('if request in getattr(self,\'conversation_turns\',{}):self.conversations.failed(owner)',
        'if request in getattr(self,\'conversation_turns\',{}):self.interrupt_conversation(owner)')
replace("            while len(self.conversation_turns)>64:self.conversation_turns.pop(next(iter(self.conversation_turns)))\n            return reply",
'''            while len(self.conversation_turns)>64:self.conversation_turns.pop(next(iter(self.conversation_turns)))
        from tools.speaker_capture_scope import begin_speaker_turn
        begin_speaker_turn(self,meta,cid)
        return reply''')
replace("        if meta['request_id'] in getattr(self,'conversation_turns',{}):self.conversations.failed(meta)\n",
'''        if meta['request_id'] in getattr(self,'conversation_turns',{}):self.conversations.failed(meta)
        from tools.speaker_capture_scope import cancel_speaker_turn
        cancel_speaker_turn(self,meta)
''')
old="        reply=dialogue.build_response(request,'ollama',MODEL,history=history,strict=True,fast=True,host=OLLAMA_HOST)"
replace('    def answer(self,meta,text):', '''    def answer(self,meta,text,*,deadline=None,is_cancelled=lambda:False):''')
replace(old,"""        coordinator=getattr(self,'gpu_coordinator',None)
        deadline=started+meta.get('budget_ms',120000)/1000 if deadline is None else deadline
        if is_cancelled():raise InterruptedError('Legacy conversation cancelled')
        lease=coordinator.acquire('llm',deadline=deadline,cancelled=is_cancelled) if coordinator is not None else nullcontext()
        with lease:
            remaining=deadline-time.monotonic()
            if remaining<=0:raise TimeoutError('Original conversation budget expired')
            if is_cancelled():raise InterruptedError('Legacy conversation cancelled')
            options={'timeout_s':remaining} if coordinator is not None else {}
            reply=dialogue.build_response(request,'ollama',MODEL,history=history,strict=True,fast=True,host=OLLAMA_HOST,**options)""")
replace("        generated=self.voice.generate(reply['reply_text'])", '''        if is_cancelled():raise InterruptedError('Legacy conversation cancelled')
        if time.monotonic()>=deadline:raise TimeoutError('Original conversation budget expired')
        if coordinator is not None:
            class Cancellation:
                def is_set(self):return bool(is_cancelled())
            generated=self.voice.generate_bounded(reply['reply_text'],deadline=deadline,
                cancelled=Cancellation(),request_id=meta['request_id'])
        else:generated=self.voice.generate(reply['reply_text'])''')
# The original warmup LLM budget stays 120s including admission waiting.
replace("        if self.latency_options.get('reply_first'):\n            from tools.dialogue_stream import OllamaReplyStream", """        warm_deadline=time.monotonic()+120
        coordinator=getattr(self,'gpu_coordinator',None)
        lease=coordinator.acquire('llm',deadline=warm_deadline) if coordinator is not None else nullcontext()
        with lease:
            self._warmup_llm(warm_deadline)
        from tools.thinking_feedback import prepare
        prepare(self)
        from tools.social_feedback import prepare as prepare_social
        try:prepare_social(self)
        except Exception:self.social_assets={}
        self.warmed_up=True

    def _warmup_llm(self,deadline):
        if self.latency_options.get('reply_first'):
            from tools.dialogue_stream import OllamaReplyStream""")
replace("stream=OllamaReplyStream(OLLAMA_HOST,MODEL,[],'你好',120,reply_first=True,", "stream=OllamaReplyStream(OLLAMA_HOST,MODEL,[],'你好',max(.001,deadline-time.monotonic()),reply_first=True,")
replace("                                    'ollama',MODEL,strict=True,fast=True,host=OLLAMA_HOST)",
        "                                    'ollama',MODEL,strict=True,fast=True,host=OLLAMA_HOST,timeout_s=max(.001,deadline-time.monotonic()))")
old='''        from tools.thinking_feedback import prepare
        prepare(self)
        from tools.social_feedback import prepare as prepare_social
        try:prepare_social(self)
        except Exception:self.social_assets={}
        self.warmed_up=True'''
# Remove the second copy left at the end of the moved original LLM body.
assert source.count(old)==2
position=source.rfind(old);source=source[:position]+source[position+len(old):]
replace("                'source_fingerprint':self.service_fingerprint,'capabilities':dict(CAPABILITIES)}",
"""                'source_fingerprint':self.service_fingerprint,'capabilities':dict(CAPABILITIES),
                'gpu_coordination':(self.gpu_coordinator.public() if getattr(self,'gpu_coordinator',None) is not None else {'version':0}),
                'speaker_attribution':(dict(self.speaker_turns.health(),invalid_visual_headers=getattr(self,'speaker_visual_invalid_headers',0))
                    if getattr(self,'speaker_turns',None) is not None else {'version':0})}""")
replace('''                serve_channel(self,meta,text,remaining,recognition_ms=round(asr_ms,2),device_reply=device_reply)''',
'''                from tools.speaker_capture_scope import speaker_capture_scope
                cid=conversation_headers[0][3:] if conversation_headers else None
                with speaker_capture_scope(self.server.models,meta,pcm,cid,
                        self.headers.get_all('X-Aura-Speaker-Visual',[]),deadline=started+meta['budget_ms']/1000):
                    pcm=None
                    serve_channel(self,meta,text,remaining,recognition_ms=round(asr_ms,2),device_reply=device_reply)''')
replace("            if text:reply['voice_reply']=self.server.models.answer(meta,text)",
'''            if text:
                from common.voice_admission import disconnected
                reply['voice_reply']=self.server.models.answer(meta,text,deadline=started+meta['budget_ms']/1000,
                    is_cancelled=lambda:disconnected(self.connection))''')
replace('    finally:models.voice.close()', '''    finally:
        tracker=getattr(models,'speaker_turns',None)
        if tracker is not None:tracker.close()
        models.voice.close()''')
compile(source,name,'exec')
target=H/'candidate/windows'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(source,encoding='utf-8')
config=H/'candidate/windows/config/gpu_runtime.local.json';config.parent.mkdir(parents=True,exist_ok=True)
if not config.exists():config.write_text(json.dumps({'mode':'observe'},indent=2),encoding='utf-8')
extra='tools/dialogue_host_ollama.py';original=(A/extra).read_bytes()
backup=H/'source_before'/extra
if backup.exists():assert backup.read_bytes()==original,'Concurrent legacy dialogue change'
else:backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(original)
legacy=original.decode('utf-8');needle='host: str = OLLAMA_HOST) -> typing.Dict:'
assert legacy.count(needle)==1
legacy=legacy.replace(needle,'host: str = OLLAMA_HOST, timeout_s: typing.Optional[float] = None) -> typing.Dict:')
needle='    scene_state = request.get("scene_state") or {}'
assert legacy.count(needle)==1
legacy=legacy.replace(needle,'''    timeout_options={}
    if timeout_s is not None:
        import math
        if type(timeout_s) not in (int,float) or not math.isfinite(timeout_s) or not 0<timeout_s<=180:
            raise ValueError('Invalid original request timeout')
        timeout_options['timeout_s']=timeout_s
    scene_state = request.get("scene_state") or {}''')
needle="history=history,fast=True,host=host)";assert legacy.count(needle)==1
legacy=legacy.replace(needle,"history=history,fast=True,host=host,**timeout_options)")
needle='history=history,host=host)';assert legacy.count(needle)==1
legacy=legacy.replace(needle,'history=history,host=host,**timeout_options)')
compile(legacy,extra,'exec');target=H/'candidate/windows'/extra;target.write_text(legacy,encoding='utf-8')
(H/'parent_additional_sources_before.json').write_text(json.dumps({extra:hashlib.sha256(original).hexdigest()},indent=2),encoding='utf-8')
print(json.dumps({'status':'STAGED','file':name,'production_changed':False}))
