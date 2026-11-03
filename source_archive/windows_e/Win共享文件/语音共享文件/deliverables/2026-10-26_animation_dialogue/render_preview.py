"""Render existing avatar materials with virtual PCM clocks, without devices."""
import base64,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))
script=r'''
import base64,hashlib,io,json,sys
from pathlib import Path
from PIL import Image,ImageDraw
root=Path(ROOT);sys.path.insert(0,str(root/'aura'))
from tools.demo_script import create_demo_core
from tools.streaming_controller import StreamingController
from board.runtime.fsm import RuntimeFSM
class Silent:
    def __init__(self):
        self.active=self.paused=False;self.duration=4.
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
frames=[];representative=[];checks=[]
core=create_demo_core('reuse');core.fsm=RuntimeFSM(publish_state_changes=False)
for action in ('ack_nod','deny_shake','emo_surprised','emo_puzzled'):
    core.fsm.reset();core.reset_playback();output=Silent();clock=[100.]
    controller=StreamingController(core,object(),output,clock=lambda:clock[0]);owner={'request_id':action,'generation':1}
    controller.channel_event({'kind':'start'},b'',owner,{},100.)
    controller.channel_event({'kind':'text','text':'Animation preview.'},b'',owner,{},100.)
    controller.channel_event({'kind':'audio','start_sample':0},b'\x00\x20'*96000,owner,{},100.)
    controller.channel_event({'kind':'control','emotion':'friendly','action':action,'at_sample':0},b'',owner,{},100.)
    states=[];hashes=set()
    for index in range(16):
        at=index/8.;clock[0]=100.+at
        output.state.update(clock=at,answer_clock=at,ready=True,audible=True,track='answer',answer_started_at=100.)
        frame=controller.tick();states.append(core.fsm.state.label)
        image=frame['image'].convert('RGB');hashes.add(hashlib.sha256(image.tobytes()).hexdigest())
        image.thumbnail((320,320));canvas=Image.new('RGB',(320,352),'white');canvas.paste(image,((320-image.width)//2,0))
        draw=ImageDraw.Draw(canvas);draw.text((8,322),action+' | '+states[-1],fill='black')
        draw.text((8,336),'Virtual PCM clock; no physical playback',fill='black')
        frames.append(canvas)
        if index==2:representative.append(canvas.copy())
    assert len(hashes)>1
    checks.append({'action':action,'states':list(dict.fromkeys(states)),'different_pixel_hashes':len(hashes)})
sheet=Image.new('RGB',(640,704),'white')
for i,item in enumerate(representative):sheet.paste(item,((i%2)*320,(i//2)*352))
files={}
for name,image,options in (('animation_preview.gif',frames[0],dict(save_all=True,append_images=frames[1:],duration=125,loop=0)),('animation_preview.png',sheet,{})):
    target=root.parent/name;image.save(str(target),**options);raw=target.read_bytes()
    files[name]={'base64':base64.b64encode(raw).decode(),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
print(json.dumps({'scope':'existing real materials; virtual PCM; no native sink, sound, microphone or motor','checks':checks,'files':files}))
'''.replace('ROOT',repr(c['runtime']))
compile(script,'<animation-preview>','exec')
value=json.loads(ssh('python3 -B -',script,timeout=90))
for name,item in value['files'].items():(HERE/name).write_bytes(base64.b64decode(item.pop('base64')))
(HERE/'preview_verification.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps(value))
