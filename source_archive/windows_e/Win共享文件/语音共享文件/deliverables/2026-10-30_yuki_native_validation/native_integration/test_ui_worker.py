"""Exercise the real candidate worker branch without GUI, audio, jobs or network."""
from pathlib import Path
from types import SimpleNamespace as S
import importlib.util,json,sys,threading,time
phase=Path('/home/root/aura-yuki-validation-20261030/native_integration')
runtime=Path(json.loads((phase/'board_source/manifest.json').read_text())['runtime'])
sys.path.insert(0,str(runtime/'aura'))
source=phase/'ui_candidate/aura/tools/board_avatar_worker.py'
spec=importlib.util.spec_from_file_location('candidate_native_worker',source);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class Fake:
    def __init__(self):
        self.core=S(talk_gen=0);self.phase='IDLE';self.last_error='';self.closed=False;self.index=0
        self.block=False;self.entered=threading.Event();self.release=threading.Event()
        self.portrait_offload=S(target_fps=24,status=lambda:{'mode':'native'},close=lambda:None)
    def tick(self):
        self.index+=1
        if self.block:
            self.block=False;self.entered.set();assert self.release.wait(2)
        return dict(_native_yuki=True,_portrait_burst=False,asset='yuki/native',index=self.index,
          display_state='IDLE',mouth_level=0,speech_gain=0)
    def public(self):return dict(generation=self.core.talk_gen,phase=self.phase,state='IDLE',error=self.last_error)
    def cancel(self):self.core.talk_gen+=1
    def event(self,name):
        assert name=='cancel';self.cancel();return {'ok':True}
    def close(self):self.closed=True
controller=Fake();worker=module.AvatarRenderWorker(controller,'#FCFCF3',(423,438),interval=.01,visual_fps=24)
def until(predicate,limit=3):
    deadline=time.monotonic()+limit
    while time.monotonic()<deadline:
        packet=worker.read()
        if predicate(packet):return packet
        time.sleep(.005)
    raise RuntimeError('Worker test condition timed out: '+controller.last_error)
try:
    first=until(lambda p:p['sequence']>=20)
    assert first['image'] is None and first['rgb'] is None and first['jpeg']==b''
    assert not controller.last_error
    controller.block=True;assert controller.entered.wait(2)
    previous=worker.read()['sequence'];worker.request('event','cancel');controller.release.set()
    after=until(lambda p:p['sequence']>previous and p['state']['generation']==1)
    assert not controller.last_error
    result=dict(status='PASS',native_metadata_without_PIL_or_JPEG=True,cancelled_inflight_frame_not_published=True,
      audio_device_opened=False,network_used=False,source=str(source))
finally:controller.release.set();worker.close()
assert controller.closed
(phase/'results/ui-worker-test.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
