"""Apply the reviewed, narrowly scoped removal to the frozen source baseline."""
import ast,hashlib,json
from pathlib import Path
from maintenance import A,H,P,read,save

b=read('baseline.json')
for name,sha in b['sources'].items():
    assert hashlib.sha256((P/name).read_bytes()).hexdigest()==sha, 'Concurrent source change: '+name
changes={}
def load(name):return (P/name).read_text(encoding='utf-8-sig')
def replace(text,old,new):
    assert text.count(old)==1,repr(old[:100])
    return text.replace(old,new)

name='aura/tools/device_hub.py';s=load(name)
s=replace(s,'from common.visual_question import validate_jpeg\nfrom tools.visual_question_host import LocalVisualQuestion',
          'from common.visual_policy import visual_status')
s=replace(s,'        self.visual=LocalVisualQuestion();self.visual_lock=threading.Lock()\n','')
s=replace(s,"        self.visual_error='';self.last_visual=None;self.last_frame={}\n",'')
start=s.index('    def observe(self,value):');end=s.index('    def speaker_call(',start)
s=s[:start]+'''    def observe(self,value):
        # Never decode, infer or persist images through the retired API.
        return {'accepted':False,'reason':'semantic_vision_removed','image_persisted':False}
'''+s[end:]
s=replace(s,"'visual_error':self.visual_error,'last_visual_unix':self.last_visual,'image_persisted':False,",
          "'visual_error':'','last_visual_unix':None,'image_persisted':False,'visual_processing':visual_status(),")
s=replace(s,"    def do_POST(self):\n        if not self.allowed():self.reply(403,{'error':'Wired device access only'});return\n",
'''    def do_POST(self):
        if not self.allowed():self.reply(403,{'error':'Wired device access only'});return
        if self.path=='/v1/observations':
            self.close_connection=True
            self.reply(410,{'error':'semantic_vision_removed','image_upload_enabled':False});return
''')
s=replace(s,"            elif self.path=='/v1/observations':out=hub.observe(v)\n",'')
changes[name]=s

name='aura/tools/voice_channel_source.py';s=load(name)
s=replace(s,"        from tools.visual_voice_host import open_exchange\n        visual_exchange=open_exchange(handler.server.models,meta,text,timeout)",
          "        from common.visual_policy import RETIRED_VISUAL_REPLY\n        device_reply=RETIRED_VISUAL_REPLY")
changes[name]=s

name='aura/tools/board_model_host.py';s=load(name)
s=replace(s,'from common.spoken_input import prepare_spoken_input',
          'from common.spoken_input import prepare_spoken_input\nfrom common.visual_policy import visual_status')
s=replace(s,"                           'busy':self.server.models.lock.locked()});return",
          "                           'visual_processing':visual_status(),\n                           'busy':self.server.models.lock.locked()});return")
s=replace(s,"            from tools.visual_voice_host import handle_frame\n            handle_frame(self);return",
          "            self.send(410,{'error':'semantic_vision_removed','image_upload_enabled':False});return")
changes[name]=s

name='aura/tools/memory_timeline_host.py';s=load(name)
start=s.index('def live_context(');end=s.index('def memory_context(',start)
s=s[:start]+'''def live_context(models,meta,text):
    """Retired VLM observations are historical only, never current sight."""
    return None

'''+s[end:]
changes[name]=s

name='aura/common/voice_service_capabilities.py';s=load(name)
s=replace(s,"SERVICE_REVISION = 'voice-identity-gpu-20261030-r11'", "SERVICE_REVISION = 'voice-board-vision-20261030-r12'")
s=replace(s,"    'common/visual_question.py',", "    'common/visual_question.py',\n    'common/visual_policy.py',")
for old in ("    'tools/visual_question_host.py',\n","    'tools/visual_voice_host.py',\n"):s=replace(s,old,'')
changes[name]=s

name='deliverables/2026-10-28_device_skills/start_devices.py';s=load(name)
start=s.index('manifest=json.loads(');end=s.index('if not occupied(8812):',start)
s=s[:start]+s[end:]
s=replace(s,"        v=health(8810);h=health(8812)\n        if v.get('status')=='ok' and h.get('speaker_ready'):",
          "        h=health(8812)\n        if h.get('speaker_ready'):")
s=replace(s,"{'visual':v,'hub':h}","{'visual':{'enabled':False,'reason':'semantic_vision_removed'},'hub':h}")
s=replace(s,'"""Start isolated CPU services only; never unload or terminate other models."""',
          '"""Start the shared speaker/memory Hub; generic Qwen-VL inference is retired."""')
changes[name]=s

name='aura/config/model_storage.local.json';cfg=json.loads(load(name));assert cfg.pop('visual_directory')=='D:/AIModels/qwen3-vl-2b-interaction'
changes[name]=json.dumps(cfg,ensure_ascii=False,indent=2)+'\n'
for name,source in changes.items():
    if name.endswith('.py'):ast.parse(source,filename=name)
for name,source in changes.items():(P/name).write_text(source,encoding='utf-8',newline='\n')
removed=['aura/tools/visual_question_host.py','aura/tools/visual_voice_host.py']
for name in removed:(P/name).unlink()
save('source_changes.json',{'status':'APPLIED','changed':{n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in changes},'removed_active_modules':removed})
print(json.dumps({'status':'APPLIED','changed':len(changes),'removed':removed}))
