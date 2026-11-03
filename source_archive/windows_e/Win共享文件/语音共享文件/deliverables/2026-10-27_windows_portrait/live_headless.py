"""Real wired portrait service with board PCM clocks; no physical audio/video."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))
script=r'''
import hashlib,json,math,socket,subprocess,sys,time,urllib.request,uuid,zlib
from pathlib import Path
root=Path(ROOT);sys.path.insert(0,str(root/'aura'))
from tools.demo_script import create_demo_core
from tools.streaming_controller import StreamingController
from tools.board_avatar_affine import configure_board_rendering
from tools.board_avatar_worker import AvatarRenderWorker
from board.runtime.fsm import RuntimeFSM
from board.runtime.portrait_offload import PortraitOffload
import numpy as np
def ui_state():
    with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4) as f:return json.load(f)
before=ui_state();assert before['handsfree_dialogue']['enabled'] is False
pid_before=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True)
def audit(event,args):
    if event=='open' and isinstance(args[0],str) and args[0].startswith('/dev/') and args[0] not in ('/dev/null','/dev/urandom'):
        raise RuntimeError('Physical device access forbidden')
sys.addaudithook(audit)
class Output:
    def __init__(self):self.active=self.paused=False;self.started=None;self.pause_at=None;self.pause_total=0.;self.samples=0;self.ended=False;self.stops=0
    @property
    def duration(self):return self.samples/24000
    @property
    def ready(self):return bool(self.started is not None)
    def position(self):
        return max(0.,(self.pause_at if self.paused else time.monotonic())-self.started-self.pause_total) if self.started is not None and self.active else 0.
    def read(self):return dict(clock=self.position(),answer_clock=self.position(),audible=self.ready and self.active and not self.paused,track='answer' if self.active else None,
        ready=self.ready,done=False,error='',answer_started_at=self.started,device_state='IDLE_READY' if not self.active else 'TEST_SILENT')
    def begin_stream(self):self.active=True;self.started=None;self.samples=0;self.pause_total=0.;self.ended=False
    def append_pcm(self,pcm,at):
        assert at==self.samples;self.samples+=len(pcm)//2
        if self.started is None:self.started=time.monotonic()
    def end_stream(self):self.ended=True
    def finished(self):
        if self.active and self.ended and self.position()>=self.duration:self.active=False;return True
        return False
    def stop(self):self.active=False;self.paused=False;self.stops+=1
    def pause(self,enabled):
        if enabled:self.pause_at=time.monotonic()
        else:self.pause_total+=time.monotonic()-self.pause_at
        self.paused=enabled
class Sink:
    def __init__(self):self.rows=[]
    def push(self,rgb,sequence):
        assert len(rgb)==423*438*3
        self.rows.append((time.monotonic(),sequence,zlib.crc32(rgb)));self.rows=self.rows[-600:]
core=create_demo_core('reuse');core.fsm=RuntimeFSM(publish_state_changes=False);configure_board_rendering(core,'#FCFCF3')
output=Output();controller=StreamingController(core,object(),output)
cfg=json.loads((root/'aura/config/board_avatar_gtk.json').read_text())['portrait_offload'];cfg['fps']=24
controller.portrait_offload=PortraitOffload(cfg,(423,438));sink=Sink()
worker=AvatarRenderWorker(controller,'#FCFCF3',(423,438),1/24,native_video=sink,visual_fps=24)
def until(predicate,timeout=5):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        if predicate():return
        time.sleep(.02)
    raise AssertionError('Live portrait condition timed out: '+str(worker.public()))
def command(method,*args):
    identity=worker.request(method,*args)
    until(lambda:any(x['command_id']==identity for x in worker.public()['avatar_renderer']['command_results']))
    row=next(x for x in worker.public()['avatar_renderer']['command_results'] if x['command_id']==identity)
    assert row['ok'],row
results=[]
try:
    until(lambda:worker.public()['portrait_offload']['mode']=='remote',12)
    t=np.arange(24000*5)/24000.;pcm=(np.sin(t*440*2*np.pi)*(.05+.04*np.sin(t*5))*32767).astype('<i2').tobytes()
    for action,state in (('ack_nod','ACK_NOD'),('deny_shake','DENY_SHAKE'),('emo_surprised','AWAKE'),('emo_puzzled','PUZZLED')):
        owner={'request_id':uuid.uuid4().hex,'generation':1}
        command('channel_event',{'kind':'start'},b'',owner,{},time.monotonic())
        command('channel_event',{'kind':'text','text':'Synthetic silent portrait test.'},b'',owner,{},time.monotonic())
        command('channel_event',{'kind':'control','action':action,'emotion':'friendly','at_sample':0},b'',owner,{},time.monotonic())
        command('channel_event',{'kind':'audio','start_sample':0},pcm,owner,{},time.monotonic())
        seen=set();mouth=[];started=time.monotonic()
        while time.monotonic()-started<3.2:
            status=worker.public();seen.add(status.get('display_state'));mouth.append(status.get('mouth_level') or 0)
            assert not status.get('error'),status.get('error');time.sleep(.025)
        assert state in seen and any(x and x.startswith('SPEAKING') for x in seen),(action,seen)
        assert max(mouth)>0
        if action=='ack_nod':
            stops=output.stops;generation=core.talk_gen
            command('portrait_toggle');until(lambda:worker.public()['portrait_offload']['mode']=='disabled')
            assert output.active and output.stops==stops and core.talk_gen==generation
            command('portrait_toggle');until(lambda:worker.public()['portrait_offload']['mode']=='remote')
            assert output.active and output.stops==stops and core.talk_gen==generation
            command('toggle_pause');assert output.paused
            position=output.position();time.sleep(.2);assert abs(output.position()-position)<.002
            command('toggle_pause');assert not output.paused
        command('cancel');until(lambda:worker.public()['phase']=='IDLE')
        results.append({'action':action,'display_states':sorted(x for x in seen if x),'peak_mouth':max(mouth),'completed_or_cancelled':True})
    assert len(set(r[2] for r in sink.rows))>20
    snapshot=worker.public();assert snapshot['phase']=='IDLE'
    report={'status':'PASS','scope':'real wired RGB composition with actual board assets/FSM and synthetic silent PCM clock',
        'actions':results,'received_presenter_frames':len(sink.rows),'unique_crc':len(set(r[2] for r in sink.rows)),
        'remote':snapshot['portrait_offload'],'mode_toggle_preserved_audio_and_generation':True,'pause_clock_frozen':True,
        'physical_native_sink':False,'physical_audio':False,'microphone':False,'motor':False}
except Exception as exc:
    report={'status':'FAIL','error':repr(exc),'action':locals().get('action'),'completed_actions':results,
        'board_state':worker.public(),'core_state':core.fsm.state.label,'output_active':output.active,
        'output_paused':output.paused,'audio_position':output.position(),'audio_duration':output.duration,
        'pcm_started_monotonic':output.started,'current_monotonic':time.monotonic(),
        'puzzled_visible_at':controller.stream.get('puzzled_visible_at') if controller.stream else None,
        'received_presenter_frames':len(sink.rows),'physical_native_sink':False,'physical_audio':False}
finally:worker.close()
after=ui_state();assert after['handsfree_dialogue']['enabled'] is False
assert pid_before==subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True)
print(json.dumps(report))
'''.replace('ROOT',repr(c['runtime']))
compile(script,'<wired-silent-portrait>','exec')
v=json.loads(ssh('python3 -B -',script,timeout=100))
(HERE/'live_headless.json').write_text(json.dumps(v,indent=2),encoding='utf-8');print(json.dumps(v))
raise SystemExit(0 if v['status']=='PASS' else 1)
