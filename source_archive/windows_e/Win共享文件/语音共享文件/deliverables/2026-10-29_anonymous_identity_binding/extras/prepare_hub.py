"""Create the extras Hub overlay from the final frozen 55-test core."""
import hashlib,json
from pathlib import Path
H=Path(__file__).resolve().parent
B=H.parent.parent/'2026-10-29_speaker_visual_cooperation'
source=B/'candidate/tools/device_hub.py';raw=source.read_bytes();code=raw.decode('utf-8')
expected=json.loads((B/'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))['files']['tools/device_hub.py']['sha256']
assert hashlib.sha256(raw).hexdigest()==expected
def replace(old,new):
    global code
    assert code.count(old)==1,old[:80]
    code=code.replace(old,new)
replace('def __init__(self,root,model_directory,calibration=None,timeline=None):',
 'def __init__(self,root,model_directory,calibration=None,timeline=None,*,anonymous_config=None,encoder_factory=None,private_root_validator=None):')
replace("self.speaker_gate=threading.Lock();self.speaker=None;self.speaker_error='initializing'",
 "self.speaker_gate=threading.Lock();self.speaker=None;self.speaker_error='initializing'\n        self.binding=None;self.binding_error='disabled'")
replace("                import torch\n                from common.speaker_identity import EcapaEncoder\n                from tools.speaker_device import SpeakerDevice\n                torch.set_num_threads(2)\n                self.speaker=SpeakerDevice(EcapaEncoder(model_directory),self.root/'speakers.sqlite3',calibration=calibration)\n                self.speaker_error=''",
 "                from tools.speaker_device import SpeakerDevice\n                if encoder_factory is None:\n                    import torch\n                    from common.speaker_identity import EcapaEncoder\n                    torch.set_num_threads(2);encoder=EcapaEncoder(model_directory)\n                else:encoder=encoder_factory(model_directory)\n                self.speaker=SpeakerDevice(encoder,self.root/'speakers.sqlite3',calibration=calibration)\n                self.speaker_error=''\n                if anonymous_config and anonymous_config.get('enabled') is True:\n                    try:\n                        from tools.binding_hub_runtime import BindingHubRuntime\n                        options={} if private_root_validator is None else {'validate_root':private_root_validator}\n                        self.binding=BindingHubRuntime(self,anonymous_config,**options);self.binding_error=''\n                    except Exception as exc:self.binding_error=type(exc).__name__+': '+str(exc)[:160]")
replace("future=self.speaker_pool.submit(getattr(self.speaker,method),*args)",
 "future=self.speaker_pool.submit(self._speaker_method,method,args)")
replace('    def health(self):', '''    def _speaker_method(self,method,args):
        value=getattr(self.speaker,method)(*args)
        if method=='turn' and getattr(self,'binding',None) is not None:self.binding.after_original_voice_turn(args[0],args[1])
        return value
    def binding_call(self,path,value):
        if self.binding is None:raise ValueError('Binding runtime unavailable')
        if not self.speaker_gate.acquire(False):raise ValueError('Speaker worker busy')
        from tools.binding_dispatch import dispatch
        job={'value':value,'cancelled':False}
        def run():
            if job['cancelled']:raise InterruptedError('Binding request expired')
            body=job['value'];job['value']=None
            try:return dispatch(self.binding,path,body)
            finally:
                if isinstance(body,dict) and 'pcm' in body:body['pcm']=None
        try:future=self.speaker_pool.submit(run)
        except Exception:self.speaker_gate.release();raise
        future.add_done_callback(lambda _:self.speaker_gate.release())
        try:return future.result(timeout=12)
        finally:
            job['cancelled']=True
            body=job['value'];job['value']=None
            if isinstance(body,dict) and 'pcm' in body:body['pcm']=None
            future.cancel()
    def analysis_submit(self,meta,pcm,cid,visual):
        value=self.binding.precomputed_analysis(meta,cid,visual) if self.binding is not None else None
        if value is not None:
            # Preserve normal result/cancel receipt ownership without a CPU job.
            from common.asr_wire import context
            meta=context(meta,pcm);service=self.speaker_turns;key=service.key(meta)
            with service.lock:
                service._expire();old=service.rows.get(key)
                if old is not None:return service._row(meta,cid)['value']
                now=service.clock()
                while len(service.rows)>=service.max_rows:
                    removed,_=service.rows.popitem(last=False);service._release_pending(removed)
                service.rows[key]=dict(meta=meta,cid=cid,visual=value['visual'],value=value,deadline=now,remove_at=now+service.result_lifetime)
                return value
        return self.speaker_turns.submit(meta,pcm,cid,visual)
    def health(self):''')
replace("'speaker_turn_attribution':self.speaker_turns.health(),",
 "'speaker_turn_attribution':self.speaker_turns.health(),\n            'anonymous_binding':{'version':1,'enabled':self.binding is not None,'error':self.binding_error,'automatic_profile_access':False},")
replace("if self.path=='/v1/observations':out=hub.observe(v)",
 "if self.path.startswith('/v1/binding/'):\n                if self.client_address[0]!='127.0.0.1':raise ValueError('Binding requires loopback model adapter')\n                out=hub.binding_call(self.path,v)\n            elif self.path=='/v1/observations':out=hub.observe(v)")
replace("try:out=hub.speaker_turns.submit(v['context'],pcm,v['conversation_id'],v['visual'])",
 "try:out=getattr(hub,'analysis_submit',hub.speaker_turns.submit)(v['context'],pcm,v['conversation_id'],v['visual'])")
replace("                now=service.clock()\n                while len(service.rows)>=service.max_rows:",
 "                actor=service.actor(meta);previous=service.latest.get(actor)\n                if previous is not None and meta['generation']<=previous[0]:raise ValueError('Stale or reused speaker generation')\n                service.latest[actor]=(meta['generation'],meta['request_id']);service.latest.move_to_end(actor)\n                while len(service.latest)>32:\n                    removed,_=service.latest.popitem(last=False);service.streaks.pop(removed,None)\n                if value['voice'] is None:service.streaks.pop(actor,None)\n                now=service.clock()\n                while len(service.rows)>=service.max_rows:")
replace("server.hub=Hub(args.root,args.speaker_model,c,timeline=timeline)",
 "anonymous_path=Path(__file__).resolve().parents[1]/'config/anonymous_identity.local.json'\n    anonymous=json.loads(anonymous_path.read_text(encoding='utf-8')) if anonymous_path.exists() else None\n    server.hub=Hub(args.root,args.speaker_model,c,timeline=timeline,anonymous_config=anonymous)")
target=H/'candidate/tools/device_hub.py';target.parent.mkdir(parents=True,exist_ok=True);target.write_text(code,encoding='utf-8',newline='')
(H/'hub_base.json').write_text(json.dumps(dict(source=str(source),sha256=expected,pcm_descriptor_preserved=True),indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':'EXTRAS_HUB_STAGED','sha256':hashlib.sha256(target.read_bytes()).hexdigest()}))
