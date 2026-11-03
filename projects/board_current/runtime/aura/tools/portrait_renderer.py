"""CPU portrait composition using a pinned snapshot of the active board core."""
import hashlib
import importlib
import json
from pathlib import Path
import sys
import time
import types
from common import portrait_wire as wire

class PortraitRenderer:
    def __init__(self,aura,snapshot,size,background):
        self.aura=Path(aura);snapshot=Path(snapshot);manifest=json.loads((snapshot/'manifest.json').read_text(encoding='utf-8'))
        for relative,digest in manifest['sources'].items():
            if hashlib.sha256((snapshot/relative).read_bytes()).hexdigest()!=digest:raise ValueError('Renderer snapshot changed: '+relative)
        for relative,digest in manifest['project_sources'].items():
            if hashlib.sha256((self.aura/relative).read_text(encoding='utf-8').encode()).hexdigest()!=digest:
                raise ValueError('Shared renderer changed: '+relative)
        for relative,item in manifest['assets'].items():
            path=self.aura.parent/relative
            if path.stat().st_size!=item['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:
                raise ValueError('Visual resource changed: '+relative)
        self.revision=manifest['revision'];self.size=tuple(size);self.background=background
        # Resource lookup uses the existing shared visual assets. Executed code
        # stays the separately hashed effective-board snapshot, not another CLI.
        def load(name,relative):
            importlib.import_module(name.rsplit('.',1)[0])
            module=types.ModuleType(name);module.__package__=name.rsplit('.',1)[0]
            module.__file__=str(self.aura/relative);sys.modules[name]=module
            source=(snapshot/relative).read_text(encoding='utf-8')
            exec(compile(source,str(snapshot/relative),'exec'),module.__dict__)
            return module
        for relative in ('board/runtime/fsm.py','board/interaction/avatar_player.py','tools/facial_layers.py'):
            load(relative[:-3].replace('/','.'),relative)
        factory=load('tools.pinned_portrait_factory','tools/demo_script.py')
        from tools.board_avatar_affine import configure_board_rendering,resize_rgb
        from tools.realtime_facials import RealtimeFacials
        from board.runtime.fsm import RuntimeFSM
        self.resize=resize_rgb;self.core=factory.create_demo_core('reuse')
        self.core.fsm=RuntimeFSM(publish_state_changes=False)
        configure_board_rendering(self.core,background);self.core.MAX_CACHED_SEQUENCES=12
        self.facials=RealtimeFacials(self.core,expressive_body=True);self.current=None;self.completed=False;self.last_sequence=0
        # Decode all normal interaction/action materials before declaring ready.
        for state in ('IDLE','PRESENT','LISTENING','THINKING','ACK_NOD','DENY_SHAKE','AWAKE','PUZZLED',
                      'SPEAKING','SPEAKING_NEUTRAL','SPEAKING_LOW'):
            self.core.sequence(state);self.core.sop(state)
            meta=self.core.display_frame(state,1.)
            if meta:self.facials.apply(meta,1.,.5,.5)
        self.facials.body.warmup()
        self.core.reset_playback()

    def render(self,request):
        from PIL import Image
        wire.plan(request)
        if request['revision']!=self.revision or (request['width'],request['height'])!=self.size:raise ValueError('Renderer revision/size differs')
        identity=wire.owner(request);key=identity[:2]
        if self.current is None or self.current[:2]!=key:
            self.core.reset_playback();self.last_sequence=0
            from tools.idle_body_compositor import seed_speaking_materials
            seed_speaking_materials(self.core,request['generation'],request['clock'])
        if self.current!=identity:self.completed=False
        if request['sequence']<=self.last_sequence:raise ValueError('Portrait request is not newer')
        self.current=identity;self.last_sequence=request['sequence']
        core=self.core;core.talk_gen=request['generation'];core.emotion=request['emotion']
        core.reply_text='x'*request['characters'];core.idle_gain=request['idle_gain'];core.speech_gain=request['gain']
        started=time.perf_counter();meta=core.display_frame(request['state'],request['clock'])
        if meta is None:raise ValueError('Requested portrait material is unavailable')
        finished=core.take_burst_finished();self.completed=self.completed or finished
        meta=self.facials.apply(meta,request['clock'],request['gain'],request['level'])
        image=meta['image']
        if image.mode!='RGB':
            flat=Image.new('RGB',image.size,self.background);flat.paste(image,mask=image.getchannel('A'));image=flat
        pixels=self.resize(image,self.size)
        header={k:request[k] for k in ('session','generation','sequence','state','clock','audio_sample','track','revision','width','height')}
        header.update(protocol=wire.PROTOCOL,kind='frame',asset=meta['asset'],index=int(meta['index']),
            display_state=meta.get('display_state',request['state']),transitioning=bool(meta.get('transitioning')),
            mouth_level=float(meta.get('mouth_level',0)),speech_gain=float(meta.get('speech_gain',request['gain'])),
            burst_finished=bool(self.completed),render_ms=(time.perf_counter()-started)*1000)
        wire.frame(header,pixels,request)
        return header,pixels
