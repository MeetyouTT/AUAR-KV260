"""Board-local Yuki GLArea adapter. Audio owner offers controls; GTK owns GLES.

No sockets, model service calls, pixel streams or audio device ownership here.
"""
from collections import deque
import ctypes as C
import hashlib
import json
import math
from pathlib import Path
import threading
import time
import uuid

EXPRESSION_MASK = 0xff
EYES_AUTHORED = 0
EYES_THINKING_CLOSED = 0x100
EYES_ANSWER_OPEN = 0x200
FACIAL_CONTROL_FEATURE = 1

def native_callback_metrics(timestamps):
    """Bounded numeric swap timing; callers cache this for a full second."""
    if len(timestamps)<2:return dict(callback_fps=None,callback_samples=len(timestamps),callback_interval_ms={})
    intervals=[(right-left)*1000. for left,right in zip(timestamps,timestamps[1:])]
    if any(not math.isfinite(value) or value<=0 for value in intervals):
        raise ValueError('Invalid native swap timestamps')
    ordered=sorted(intervals)
    def q(value):return ordered[min(len(ordered)-1,int((len(ordered)-1)*value))]
    span=timestamps[-1]-timestamps[0]
    return dict(callback_fps=(len(timestamps)-1)/span,callback_samples=len(timestamps),callback_window_seconds=span,
                callback_interval_ms=dict(p50=q(.5),p95=q(.95),p99=q(.99),maximum=q(1.)))

class Control(C.Structure):
    _fields_=[('owner',C.c_uint64),('sequence',C.c_uint64),('audio_sample',C.c_uint64),
      ('sample_rate',C.c_uint32),('track',C.c_uint32),('playing',C.c_uint32),('paused',C.c_uint32),
      ('expression',C.c_uint32),('pose',C.c_uint32),('gain',C.c_float),('level',C.c_float),('captured_at',C.c_double)]

class Stats(C.Structure):
    _fields_=[(key,C.c_uint64) for key in ('frames','author_ticks','owner','sequence','audio_sample','rejected_controls','stale_frames')]+[
      (key,C.c_double) for key in ('evaluate_ms','submit_ms','mouth','eye','elapsed_dropped_seconds')]

class Native:
    def __init__(self,library,model,resx,resource_root,seed=1):
        self.api=C.CDLL(str(library));self.ptr=None
        features=getattr(self.api,'yuki_control_features',None)
        if features is None:raise RuntimeError('Native Yuki library lacks dialogue facial controls')
        features.restype=C.c_uint32;features.argtypes=[]
        if features() & FACIAL_CONTROL_FEATURE != FACIAL_CONTROL_FEATURE:
            raise RuntimeError('Native Yuki dialogue facial controls are incompatible')
        declarations={
          'create':(C.c_void_p,[C.c_char_p,C.c_char_p,C.c_char_p,C.c_uint32]),
          'error':(C.c_char_p,[C.c_void_p]),'control':(C.c_int,[C.c_void_p,C.POINTER(Control)]),
          'render':(C.c_int,[C.c_void_p,C.c_double,C.c_int,C.c_int,C.POINTER(Stats)]),
          'capture':(C.c_int,[C.c_void_p,C.c_char_p,C.c_int,C.c_int]),'destroy':(None,[C.c_void_p])}
        for name,(result,args) in declarations.items():
            fn=getattr(self.api,'yuki_'+name);fn.restype=result;fn.argtypes=args
        self.ptr=self.api.yuki_create(*(str(p).encode() for p in (model,resx,resource_root)),seed)
        if not self.ptr:raise RuntimeError(self.error())
        self.stats=Stats()
        self.pose=self.expression=self.eye_policy=0
    def error(self):return self.api.yuki_error(self.ptr).decode(errors='replace')
    def offer(self,value):
        accepted=bool(self.api.yuki_control(self.ptr,C.byref(value)))
        if accepted:
            self.pose=int(value.pose);self.expression=int(value.expression)&EXPRESSION_MASK
            self.eye_policy=int(value.expression)&~EXPRESSION_MASK
        return accepted
    def render(self,now,width,height):
        if not self.api.yuki_render(self.ptr,now,width,height,C.byref(self.stats)):raise RuntimeError(self.error())
        return dict({name:getattr(self.stats,name) for name,_ in self.stats._fields_},
                    model_pose=self.pose,model_expression=self.expression,model_eye_policy=self.eye_policy)
    def capture(self,path,width,height):
        if not self.api.yuki_capture(self.ptr,str(path).encode(),width,height):raise RuntimeError(self.error())
    def close(self):
        if self.ptr:self.api.yuki_destroy(self.ptr);self.ptr=None

class LocalPortrait:
    """Latest-one control mailbox, compatible with the current portrait owner API.

    Model generation survives ordinary expression/state changes. Audio turn/track
    changes invalidate the previous sample owner, including delayed old frames.
    """
    FACE={'normal':0,'smile':1,'angry':2,'sad':3,'concern':4,'shy':5}
    EMOTION={'neutral':0,'friendly':1,'happy':1,'excited':1,'sad':3,'low':4}
    def __init__(self,output,*,clock=time.monotonic,fps=24):
        if fps not in (8,12,16,24):raise ValueError('Unsupported native frame rate')
        self.output=output;self.clock=clock;self.target_fps=fps;self.enabled=True;self.ready=False;self.closed=False
        self.lock=threading.Lock();self.session=uuid.uuid4().hex;self.owner=1;self.sequence=0
        self.pending=None;self.identity=None;self.error='';self.latest_stats={};self.offered=0;self.dropped=0
        self.expression_override=None;self.pose=0;self.state_key=None;self.state_at=0;self.completed_state=None
    def invalidate(self):
        with self.lock:
            self.owner+=1;self.session=uuid.uuid4().hex;self.pending=None;self.identity=None;self.state_key=None
            self.sequence+=1
            self.pending=Control(self.owner,self.sequence,0,24000,0,0,0,0,self.pose,0,0,self.clock())
    def set_enabled(self,value):
        if type(value)is not bool:raise ValueError('Expected boolean')
        with self.lock:self.enabled=value
        self.invalidate();return {'enabled':value}
    def set_fps(self,value):
        if type(value)is not int or value not in (8,12,16,24):raise ValueError('Unsupported native frame rate')
        with self.lock:self.target_fps=value
        return {'fps':value}
    def set_expression(self,name=None):
        if name is not None and name not in self.FACE:raise ValueError('Unknown Yuki expression')
        with self.lock:self.expression_override=None if name is None else self.FACE[name]
    def set_pose(self,pose):
        if type(pose)is not int or pose not in (0,1):raise ValueError('Unsupported Yuki pose')
        with self.lock:self.pose=pose
    def offer(self,core,now,gain,level,audio_sample,track,*,waiting_for_answer=False):
        if not all(math.isfinite(float(v)) for v in (now,gain,level)):raise ValueError('Nonfinite avatar control')
        if track not in ('none','answer','feedback')or type(audio_sample)is not int or audio_sample<0:raise ValueError('Invalid audio clock')
        if type(waiting_for_answer)is not bool:raise ValueError('Expected an explicit waiting boolean')
        snapshot=self.output.read()
        actual_track=snapshot.get('track')
        if actual_track not in ('answer','feedback'):actual_track='none'
        with self.lock:
            if self.closed or not self.enabled or not self.ready:return None
            identity=(core.talk_gen,actual_track)
            if self.identity and core.talk_gen<self.identity[0]:return None
            if identity!=self.identity:self.identity=identity;self.owner+=1
            if self.pending is not None:self.dropped+=1
            self.sequence+=1;self.offered+=1
            paused=bool(getattr(self.output,'paused',False))
            # ready survives PCM gaps; active is also true before the first
            # sample. Only the sink's current answer interval may speak.
            playing=bool(self.output.active and snapshot.get('ready') is True and not paused
                         and snapshot.get('audible') is True and actual_track==track=='answer'
                         and not snapshot.get('done') and not snapshot.get('error'))
            expression=self.expression_override if self.expression_override is not None else self.EMOTION.get(core.emotion,0)
            state=core.fsm.state.label
            if self.state_key!=(core.talk_gen,state):self.state_key=(core.talk_gen,state);self.state_at=now;self.completed_state=None
            if self.expression_override is None and state=='PUZZLED':expression=4
            waiting=waiting_for_answer or state=='THINKING' or self.output.active
            eye_policy=EYES_ANSWER_OPEN if playing else EYES_THINKING_CLOSED if waiting else EYES_AUTHORED
            safe_gain=max(0,min(1,float(gain))) if playing else 0.
            safe_level=max(0,min(1,float(level))) if playing else 0.
            self.pending=Control(self.owner,self.sequence,audio_sample,24000,('none','answer','feedback').index(actual_track),
              playing,paused,expression|eye_policy,self.pose,safe_gain,safe_level,self.clock())
            finished=state in ('ACK_NOD','DENY_SHAKE','AWAKE') and now-self.state_at>=.8 and self.completed_state!=self.state_key
            if finished:self.completed_state=self.state_key
            return dict(asset='yuki/native',index=self.sequence,display_state=state,target_state=state,
              transitioning=False,mouth_level=round(max(0,min(1,float(level)))*5) if playing else 0,
              speech_gain=float(gain) if playing else 0,eye_policy=eye_policy,answer_audible=playing,
              _portrait_burst=finished,_native_yuki=True)
    def consume(self):
        with self.lock:value=self.pending;self.pending=None;return value
    def reset_local_if_needed(self,core):pass
    def fail(self,error):
        with self.lock:self.error=str(error);self.ready=False
        self.invalidate()
    def status(self):
        with self.lock:return dict(mode='native' if self.enabled and self.ready else 'local',selected=self.enabled,
          target_fps=self.target_fps,fallback_fps=8,ready=self.ready,backend='KV260 GLES2',error=self.error,
          offered=self.offered,replaced=self.dropped,pending=int(self.pending is not None),inflight_limit=1,**self.latest_stats)
    def close(self):
        with self.lock:self.closed=True;self.pending=None;self.ready=False

def prepare_portrait(runtime,config,output,source_hashes):
    """Validate pinned assets before widget creation; preserve the default fallback."""
    mailbox=LocalPortrait(output)
    try:
        mailbox.set_fps(config.get('fps',24))
        runtime=Path(runtime).resolve(strict=True);validated=dict(config);pending={}
        for key in ('library','model','resx','resource_root'):
            path=(runtime/validated[key]).resolve(strict=True)
            if not path.is_relative_to(runtime):raise ValueError('Yuki asset escapes pinned runtime')
            validated[key]=str(path)
            if path.is_file():pending[path.relative_to(runtime).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
        root=Path(validated['resource_root']);profile_path=root/'source_profile.json'
        profile=json.loads(profile_path.read_text(encoding='utf8'))
        if not isinstance(profile,dict) or profile.get('profile_id')!='fuyukiss-yuki-freemote39-frame-mesh':raise ValueError('Unsupported Yuki source profile')
        if not isinstance(profile.get('files'),dict):raise ValueError('Invalid Yuki profile file manifest')
        required={'model.runtime.json','model.source.ems.json','yuk_0.ems.resx.json','yuk_0.ems/tex-texture.png'}
        if not required.issubset(profile['files']):raise ValueError('Incomplete Yuki profile file manifest')
        for relative,expected in profile['files'].items():
            path=(root/relative).resolve(strict=True)
            if not path.is_relative_to(root):raise ValueError('Yuki profile asset escapes resource root')
            actual=hashlib.sha256(path.read_bytes()).hexdigest()
            if actual!=expected:raise ValueError('Yuki profile hash mismatch: '+relative)
            pending[path.relative_to(runtime).as_posix()]=actual
        for key,profile_name in (('model','model.runtime.json'),('resx','yuk_0.ems.resx.json')):
            if profile['files'][profile_name]!=pending[Path(validated[key]).relative_to(runtime).as_posix()]:raise ValueError('Yuki '+key+' does not match source profile')
        for path in (runtime/'tools/native_yuki.py',runtime/'tools/egl_window.py',profile_path):
            path=path.resolve(strict=True)
            if not path.is_relative_to(runtime):raise ValueError('Yuki adapter escapes pinned runtime')
            pending[path.relative_to(runtime).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
        source_hashes.update(pending)
        return mailbox,validated
    except (OSError,ValueError,KeyError,TypeError) as error:
        mailbox.fail(error)
        return mailbox,None


def create_gl_area(config,mailbox,*,on_error=None):
    import gi
    gi.require_version('Gtk','3.0')
    from gi.repository import Gtk,GLib
    try:from .egl_window import EGLWindow
    except ImportError:from egl_window import EGLWindow
    gi.require_version('GdkX11','3.0')
    from gi.repository import GdkX11
    class YukiArea(Gtk.DrawingArea):
        def __init__(self):
            super().__init__();self.native=None;self.egl=None;self.next_frame=0.;self.frame_times=deque(maxlen=3600)
            self.frame_observer=None;self.frame_source=None;self.rate_stats={};self.next_rate_report=0.
            self.set_has_window(True);self.set_app_paintable(True)
            visual=self.get_screen().get_rgba_visual() if config.get('rgba_window',False) else None
            self.set_visual(visual or self.get_screen().get_system_visual())
            self.connect('realize',self.realized);self.connect('unrealize',self.unrealized)
            self.connect('map',self.on_mapped);self.connect('unmap',self.on_unmapped)
            # The independent EGL child owns its backing pixels. GTK damage
            # must not schedule a second avatar paint or add frame-clock jitter.
            self.connect('draw',lambda *_:True)
        def realized(self,area):
            try:
                window=self.get_window()
                if not window.ensure_native():raise RuntimeError('GTK drawing window cannot become native')
                window.get_display().sync()  # Publish XID before a separate EGL/X connection uses it.
                self.egl=EGLWindow(GdkX11.X11Window.get_xid(window),max(1,self.get_allocated_width()),max(1,self.get_allocated_height()))
                self.native=Native(config['library'],config['model'],config['resx'],config['resource_root'],int(config.get('seed',1)))
                with mailbox.lock:mailbox.ready=True;mailbox.error=''
            except Exception as error:self.failed(error)
        def unrealized(self,area):
            self.stop_frame_source()
            with mailbox.lock:mailbox.ready=False
            if self.native:
                self.egl.current();self.native.close();self.native=None
            if self.egl:self.egl.close(parent_alive=self.get_window() is not None);self.egl=None
        def failed(self,error):
            self.stop_frame_source()
            mailbox.fail(error)
            if self.native:
                self.native.close();self.native=None
            if self.egl:self.egl.close(parent_alive=self.get_window() is not None);self.egl=None
            if on_error:on_error(str(error))
        def stop_frame_source(self):
            if self.frame_source is not None:
                GLib.source_remove(self.frame_source);self.frame_source=None
        def on_mapped(self,area):
            self.next_frame=time.monotonic();self.schedule_frame()
        def on_unmapped(self,area):
            self.stop_frame_source()
        def schedule_frame(self):
            if self.frame_source is None and self.native and self.get_mapped():
                delay=max(1,math.ceil((self.next_frame-time.monotonic())*1000))
                self.frame_source=GLib.timeout_add(delay,self.tick_native,priority=GLib.PRIORITY_DEFAULT_IDLE)
        def tick_native(self):
            self.frame_source=None
            if not self.native or not self.get_mapped():return False
            now=time.monotonic();period=1/mailbox.target_fps
            if mailbox.enabled:
                self.next_frame=(self.next_frame or now)+period
                if self.next_frame<=now:self.next_frame=now+period
                self.rendered(self,None)
            else:self.next_frame=now+.1
            self.schedule_frame()
            return False
        def rendered(self,area,context):
            if not self.native:return True
            try:
                callback_started=time.perf_counter()
                value=mailbox.consume()
                if value and not self.native.offer(value):raise RuntimeError('Native control owner/sample rejected')
                scale=self.get_scale_factor();now=time.monotonic()
                width=self.get_allocated_width()*scale;height=self.get_allocated_height()*scale
                bind_started=time.perf_counter();self.egl.current();self.egl.resize(width,height)
                bind_ms=(time.perf_counter()-bind_started)*1000
                native_started=time.perf_counter();stats=self.native.render(now,width,height)
                stats['native_call_ms']=(time.perf_counter()-native_started)*1000
                stats['egl_bind_ms']=bind_ms
                swap_started=time.perf_counter();self.egl.swap()
                stats['egl_swap_ms']=(time.perf_counter()-swap_started)*1000
                stats['gtk_callback_ms']=(time.perf_counter()-callback_started)*1000
                stats['paint_at']=time.monotonic()
                stats['window_visual']=self.egl.visual;stats['window_rgba_bits']=self.egl.config_bits
                paint=stats['paint_at'];self.frame_times.append(paint)
                if paint>=self.next_rate_report:
                    recent=[]
                    for stamp in reversed(self.frame_times):
                        if paint-stamp>4.:break
                        recent.append(stamp)
                    self.rate_stats=native_callback_metrics(list(reversed(recent)))
                    self.next_rate_report=paint+1.
                stats.update(self.rate_stats)
                with mailbox.lock:mailbox.latest_stats=stats
                if self.frame_observer:self.frame_observer(dict(stats))
            except Exception as error:self.failed(error)
            return True
    return YukiArea()
