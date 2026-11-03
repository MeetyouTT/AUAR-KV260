"""Real wired ASR/LLM/TTS; replay received PCM through actual assets without sound."""
import base64,json,sys,wave
from pathlib import Path
HERE=Path(__file__).resolve().parent;AURA=HERE.parents[1]/'aura'
sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))
with wave.open(str(AURA/'models/asr/sherpa-onnx-paraformer-zh-2023-09-14/test_wavs/0.wav'),'rb') as f:pcm=f.readframes(f.getnframes())
script=r'''
import base64,hashlib,http.client,json,math,sys,time,uuid
from pathlib import Path
root=Path(RUNTIME_TOKEN);sys.path.insert(0,str(root/'aura'))
from board.runtime.audio.voice_channel import VoiceChannel
from tools.demo_script import create_demo_core
from tools.streaming_controller import StreamingController
from board.runtime.fsm import RuntimeFSM
pcm=base64.b64decode('PCM_PAYLOAD')
conn=http.client.HTTPConnection('192.168.50.1',8792,timeout=3)
try:
    conn.request('GET','/health');r=conn.getresponse();health=json.loads(r.read())
    assert r.status==200 and health['capabilities'].get('audio_clock_animation')==1
finally:conn.close()
meta=dict(protocol='aura-asr-1',board_boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
    session_id=uuid.uuid4().hex,request_id=uuid.uuid4().hex,generation=1,capture_id='public-animation-dialogue',
    sample_count=len(pcm)//2,pcm_sha256=hashlib.sha256(pcm).hexdigest(),budget_ms=120000)
frames=[];received=bytearray();first={};start=time.perf_counter()
channel=VoiceChannel('192.168.50.1')
def receive(h,p):
    first.setdefault(h['kind'],round((time.perf_counter()-start)*1000,3));frames.append((dict(h),bytes(p)))
    if h['kind']=='audio':received.extend(p)
try:result=channel.exchange(meta,pcm,receive)
finally:channel.close()
assert result['network_complete'] and result['sample_count']>0
assert hashlib.sha256(received).hexdigest()==result['pcm_sha256']
assert frames[0][0]['speech_motion']=='v1'
class SilentOutput:
    def __init__(self):
        self.active=self.paused=False;self.duration=0.;self.pcm=bytearray()
        self.state=dict(clock=0.,ready=False,done=False,error='',audible=False,track=None)
    def read(self):return dict(self.state)
    @property
    def ready(self):return self.state['ready']
    def position(self):return self.state['clock']
    def stop(self):self.active=False;self.paused=False
    def begin_stream(self):self.active=True
    def append_pcm(self,data,at):assert at*2==len(self.pcm);self.pcm.extend(data)
    def end_stream(self):self.duration=len(self.pcm)/48000.
    def finished(self):
        if self.active and self.state['done']:self.active=False;return True
        return False
core=create_demo_core('reuse');core.fsm=RuntimeFSM(publish_state_changes=False)
output=SilentOutput();clock=[100.]
controller=StreamingController(core,object(),output,clock=lambda:clock[0])
for h,p in frames:controller.channel_event(h,p,meta,{},100.)
controller.channel_complete(meta,result)
positions=[];mouth=[];hashes=set();states=set()
for index in range(math.ceil(output.duration*8)):
    at=index/8.;clock[0]=100.+at
    output.state.update(clock=at,answer_clock=at,audible=True,ready=True,track='answer',answer_started_at=100.)
    frame=controller.tick();assert frame is not None
    states.add(core.fsm.state.label);mouth.append(float(frame.get('mouth_level',0)))
    positions.append(frame.get('body_source_position'))
    hashes.add(hashlib.sha256(frame['image'].tobytes()).hexdigest())
output.state.update(done=True,clock=output.duration,answer_clock=output.duration)
clock[0]=100.+output.duration;controller.tick()
completion=controller.take_completion()
assert completion and completion[1]['pcm_sha256']==result['pcm_sha256']
assert controller.phase=='IDLE' and max(mouth)>0 and len(hashes)>1
assert len(set(p for p in positions if p is not None))>1
value=dict(status='PASS',scope='real wired model dialogue plus actual avatar assets and deterministic silent PCM clock',
    first_ms=first,samples=result['sample_count'],pcm_sha256=result['pcm_sha256'],
    speech_motion_negotiated=True,control_count=sum(h['kind']=='control' for h,p in frames),
    end_timing=frames[-1][0].get('timing',{}),tts_cache_hits=frames[-1][0].get('tts_cache_hits'),
    screen_gestures=[h.get('action') for h,p in frames if h['kind']=='control' and h.get('action')],
    replay_frames=len(mouth),different_pixel_hashes=len(hashes),peak_mouth_level=max(mouth),
    body_source_positions_changed=True,completed_to_idle=True,states=sorted(states),
    physical_audio_playback=False,playback_ack_sent=False,microphone=False,physical_motion=False,
    native_display_performance_measured=False)
print(json.dumps(value))
'''.replace('RUNTIME_TOKEN',repr(c['runtime'])).replace('PCM_PAYLOAD',base64.b64encode(pcm).decode())
compile(script,'<live-animation-dialogue>','exec')
value=json.loads(ssh('python3 -B -',script,timeout=160))
(HERE/'live_dialogue_animation.json').write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(value))
