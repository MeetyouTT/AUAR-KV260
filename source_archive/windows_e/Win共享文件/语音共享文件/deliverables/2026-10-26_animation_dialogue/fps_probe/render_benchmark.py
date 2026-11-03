"""Windows CPU probe of existing avatar materials at virtual 24 Hz; no devices."""
import hashlib,importlib,json,math,statistics,sys,time,types
from datetime import datetime,timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent;AURA=HERE.parents[2]/'aura'
DEPS=Path('C:/Users/35870/.codex/visualizations/2026/10/26/01a1772c-f263-75f1-bfa1-9bd865e5caa9/animation-fps-deps')
sys.path[:0]=[str(DEPS),str(AURA)]
import cv2,numpy as np
from PIL import Image

def board_module(name,relative,source):
    importlib.import_module(name.rsplit('.',1)[0])
    module=types.ModuleType(name);module.__package__=name.rsplit('.',1)[0]
    # Only resource lookup uses the shared resource root. Executed source bytes
    # are the unchanged downloaded effective board module, recorded by SHA.
    module.__file__=str(AURA/relative);sys.modules[name]=module
    exec(compile(source.read_text(encoding='utf-8'),str(source),'exec'),module.__dict__)
    return module

for relative in ('board/runtime/fsm.py','board/interaction/avatar_player.py','tools/facial_layers.py'):
    board_module(relative[:-3].replace('/','.'),relative,HERE/'board_source'/relative)
# Use the downloaded effective board factory. Its resource base is the existing
# shared assets; the shared demo CLI has a separate, newer constructor interface.
factory_path=HERE/'demo_script.py'
factory=board_module('tools.probe_board_factory','tools/demo_script.py',factory_path)
create_demo_core=factory.create_demo_core
from tools.board_avatar_affine import configure_board_rendering,resize_rgb
from tools.streaming_controller import StreamingController
from board.runtime.fsm import RuntimeFSM
from board.interaction import avatar_board

class Silent:
    def __init__(self):
        self.active=self.paused=False;self.duration=10.
        self.state={'clock':0.,'ready':False,'done':False,'error':'','audible':False,'track':None}
    def read(self):return dict(self.state)
    @property
    def ready(self):return self.state['ready']
    def position(self):return self.state['clock']
    def stop(self):self.active=False
    def begin_stream(self):self.active=True
    def append_pcm(self,data,at):pass
    def end_stream(self):pass
    def finished(self):return False

def percentile(values,p):
    a=sorted(values);return a[max(0,math.ceil(len(a)*p)-1)]

began=time.perf_counter()
layout=avatar_board.load_layout();box=avatar_board.avatar_box(layout)
rect=avatar_board.contain_rect(464,480,box['w'],box['h']);size=(rect['w'],rect['h'])
background=avatar_board.load_tokens()['colors']['panel_bg']
core=create_demo_core('reuse');core.fsm=RuntimeFSM(publish_state_changes=False)
configure_board_rendering(core,background);core.MAX_CACHED_SEQUENCES=12
setup_ms=(time.perf_counter()-began)*1000
t=np.arange(240000)/24000.;raw=(np.sin(t*440*2*np.pi)*(.05+.04*np.sin(t*5))*32767).astype('<i2').tobytes()
results=[];sample=None
for case in ('idle','speech','ack_nod','deny_shake','emo_surprised','emo_puzzled'):
    core.fsm.reset();core.reset_playback();output=Silent();clock=[100.]
    controller=StreamingController(core,object(),output,clock=lambda:clock[0]);owner={'request_id':case,'generation':1}
    if case!='idle':
        controller.channel_event({'kind':'start'},b'',owner,{},100.)
        controller.channel_event({'kind':'text','text':'CPU frame probe.'},b'',owner,{},100.)
        controller.channel_event({'kind':'audio','start_sample':0},raw,owner,{},100.)
        if case!='speech':controller.channel_event({'kind':'control','emotion':'friendly','action':case,'at_sample':0},b'',owner,{},100.)
        controller.tick()
    timings=[];hashes=set();states=set();first_ms=None
    for index in range(112):
        at=index/24.;clock[0]=100.+at
        if case!='idle':output.state.update(clock=at,answer_clock=at,ready=True,audible=True,track='answer',answer_started_at=100.)
        start=time.perf_counter();frame=controller.tick();assert frame is not None
        image=frame['image']
        if image.mode!='RGB':
            flat=Image.new('RGB',image.size,background);flat.paste(image,mask=image.getchannel('A'));image=flat
        rgb=resize_rgb(image,size);elapsed=(time.perf_counter()-start)*1000
        assert len(rgb)==size[0]*size[1]*3
        if first_ms is None:first_ms=elapsed
        if index>=16:timings.append(elapsed);hashes.add(hashlib.sha256(rgb).hexdigest())
        states.add(core.fsm.state.label)
        if case=='speech' and index==32:sample=rgb
    assert len(hashes)>1
    expected={'ack_nod':'ACK_NOD','deny_shake':'DENY_SHAKE','emo_surprised':'AWAKE','emo_puzzled':'PUZZLED'}.get(case)
    if expected:assert expected in states,(case,states)
    results.append({'case':case,'frames':len(timings),'first_frame_ms':first_ms,'mean_ms':statistics.mean(timings),
        'p95_ms':percentile(timings,.95),'p99_ms':percentile(timings,.99),'max_ms':max(timings),
        'compute_only_fps':1000/statistics.mean(timings),'unique_rgb_hashes':len(hashes),'states':sorted(states)})
assert sample is not None
(HERE/'sample_rgb.bin').write_bytes(sample)
value={'status':'PASS','scope':'CPU composition + final RGB resize; virtual PCM clock; no display/network/audio/LLM/GPU',
       'checked_at_utc':datetime.now(timezone.utc).isoformat(),'python':sys.version,'opencv':cv2.__version__,'numpy':np.__version__,
       'renderer':'Pillow/OpenCV path, not the board ARM native-pixels library','threads':cv2.getNumThreads(),
       'board_factory_sha256':hashlib.sha256(factory_path.read_bytes()).hexdigest(),
       'setup_ms':setup_ms,'target_size':list(size),'rgb_bytes':len(sample),'rgb_Mbps_at_24fps':len(sample)*24*8/1e6,
       'cold_frames_excluded':16,'cases':results,'sample_sha256':hashlib.sha256(sample).hexdigest(),
       'physical_fps_measured':False,'production_changed':False}
(HERE/'windows_render.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(value))
