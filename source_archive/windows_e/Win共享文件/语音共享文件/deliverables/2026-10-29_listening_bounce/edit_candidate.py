"""Apply small checked transformations to the isolated candidate."""
import hashlib,json,sys,types
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura';C=H/'candidate_source'
def change(name,old,new):
 p=C/name;s=p.read_text(encoding='utf-8');assert s.count(old)==1,(name,old[:80],s.count(old));p.write_text(s.replace(old,new),encoding='utf-8',newline='')
name='tools/board_model_host.py'
change(name,'        self.lock=threading.Lock()','        self.lock=threading.Lock()\n        from common.voice_admission import RequestDiagnostics\n        self.request_diagnostics=RequestDiagnostics()')
change(name,'class ModelHandler(Handler):','class ModelHandler(Handler):\n    def _voice_note(self,meta,outcome,**fields):\n        observer=getattr(self.server.models,\'request_diagnostics\',None)\n        if observer is not None:observer.record(meta,outcome,**fields)\n')
change(name,"                           'busy':self.server.models.lock.locked()});return","                           'voice_request_diagnostics':(self.server.models.request_diagnostics.public()\n                               if getattr(self.server.models,'request_diagnostics',None) is not None else {'version':0}),\n                           'busy':self.server.models.lock.locked()});return")
change(name,"                self.send(422,{'code':'entry_rejected','stage':'audio','error':'No sustained initial audio activity'});return",
"                self._voice_note(meta,'entry_audio_rejected',entry=entry_headers[0])\n                self.send(422,{'code':'entry_rejected','stage':'audio','error':'No sustained initial audio activity'});return")
change(name,"        if not self.server.models.lock.acquire(blocking=False):self.send(503,{'error':'Voice host busy'});return",
"""        from common.voice_admission import acquire_turn
        admission,wait_ms=acquire_turn(self.server.models.lock,self.connection,started+meta['budget_ms']/1000)
        if admission!='acquired':
            self._voice_note(meta,admission,entry=entry_headers[0] if entry_headers else '',wait_ms=wait_ms)
            if admission=='cancelled':self.close_connection=True;return
            self.send(504 if admission=='expired' else 503,
                      {'error':'Conversation budget expired' if admission=='expired' else 'Voice host busy',
                       'code':'voice_budget_expired' if admission=='expired' else 'voice_busy','retry_after_ms':250});return""")
change(name,"                text=wake_request(prepare_spoken_input(text)['text'])","                recognized_characters=len(text)\n                text=wake_request(prepare_spoken_input(text)['text'])")
change(name,"                    self.send(422,{'code':'entry_rejected','error':'Wake word not detected'});return",
"                    self._voice_note(meta,'wake_word_not_detected',entry='wake-word-v1',characters=recognized_characters,wait_ms=wait_ms)\n                    self.send(422,{'code':'entry_rejected','error':'Wake word not detected'});return")
change(name,'                if not text:\n                    self.send_response(204)',
"                if not text:\n                    self._voice_note(meta,'wake_only',entry='wake-word-v1',characters=recognized_characters,wait_ms=wait_ms)\n                    self.send_response(204)")
change(name,"                    self.send(422,{'code':'entry_rejected','error':'No valid initial speech'});return",
"                    self._voice_note(meta,'entry_text_rejected',entry=entry_headers[0],characters=len(text),wait_ms=wait_ms)\n                    self.send(422,{'code':'entry_rejected','error':'No valid initial speech'});return")
change(name,"            if self.path=='/v1/voice/channel':\n                if not text:",
"            self._voice_note(meta,'accepted',entry=entry_headers[0] if entry_headers else '',characters=len(text),wait_ms=wait_ms)\n            if self.path=='/v1/voice/channel':\n                if not text:")
name='tools/voice_channel_source.py'
change(name,'visual_exchange=None,device_reply=None):','visual_exchange=None,device_reply=None,is_cancelled=lambda:False):')
change(name,'    from tools.device_client import DeviceReplyStream','    def check_current():\n        if is_cancelled():raise InterruptedError(\'Voice client disconnected\')\n    check_current()\n    from tools.device_client import DeviceReplyStream')
change(name,'        while True:\n            if time.monotonic()>=deadline:raise TimeoutError(\'Channel synthesis budget expired\')',
"        while True:\n            check_current()\n            if time.monotonic()>=deadline:raise TimeoutError('Channel synthesis budget expired')")
change(name,"            while True:\n                if hasattr(models,'validate_conversation'):models.validate_conversation(meta)",
"            while True:\n                check_current()\n                if hasattr(models,'validate_conversation'):models.validate_conversation(meta)")
change(name,"        while True:\n            if hasattr(models,'validate_conversation'):models.validate_conversation(meta)",
"        while True:\n            check_current()\n            if hasattr(models,'validate_conversation'):models.validate_conversation(meta)")
change(name,"                if hasattr(models,'complete_stream'):",
"                check_current()\n                if hasattr(models,'complete_stream'):")
change(name,"    from tools.board_model_host import MODEL, OLLAMA_HOST",
"    from tools.board_model_host import MODEL, OLLAMA_HOST\n    from common.voice_admission import disconnected")
change(name,"                            motion=handler.headers.get('X-Aura-Motion')=='speech-v1')",
"                            motion=handler.headers.get('X-Aura-Motion')=='speech-v1',\n                            is_cancelled=lambda:disconnected(handler.connection))")
name='common/voice_service_capabilities.py'
change(name,"SERVICE_REVISION = 'voice-dialogue-memory-20261029-r4'","SERVICE_REVISION = 'voice-turn-handoff-20261029-r5'")
change(name,"'natural_fact_answers':1,'memory_source_coverage':1}","'natural_fact_answers':1,'memory_source_coverage':1,'queued_voice_admission':1,'bounded_voice_request_diagnostics':1}")
change(name,"SOURCE_FILES = (\n","SOURCE_FILES = (\n    'common/voice_admission.py',\n")
plan=json.loads((H/'source_plan.json').read_text(encoding='utf-8'))
plan['files']['common/voice_admission.py']={'before':None}
for name,row in plan['files'].items():row['candidate']=hashlib.sha256((C/name).read_bytes()).hexdigest()
sys.path.insert(0,str(A))
ns={};exec(compile((C/'common/voice_service_capabilities.py').read_text(encoding='utf-8'),'candidate_caps','exec'),ns)
d=hashlib.sha256()
for name in ns['SOURCE_FILES']:
 p=C/name
 if not p.exists():p=A/name
 d.update(name.encode()+b'\0');d.update(hashlib.sha256(p.read_bytes()).digest())
plan.update(candidate_revision=ns['SERVICE_REVISION'],candidate_fingerprint=d.hexdigest())
(H/'source_plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
print(json.dumps({'status':'CANDIDATE','files':len(plan['files']),'revision':plan['candidate_revision'],'fingerprint':plan['candidate_fingerprint']}))
