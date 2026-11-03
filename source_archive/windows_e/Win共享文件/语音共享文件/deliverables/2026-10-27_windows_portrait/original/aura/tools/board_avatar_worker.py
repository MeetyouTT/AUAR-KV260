"""Single-owner avatar rendering outside GTK; one latest frame, bounded intents.

The controller and its audio clock are used only by this worker after startup.

Published PIL images/bytes are immutable; GTK widgets stay in the main thread.

"""

from collections import deque

import copy

import io

import threading

import time

import uuid

def snapshot_copy(value):
    """Detach JSON-shaped snapshots without deepcopy's per-scalar dispatch.

    Public state is an acyclic JSON tree. Preserve tuples used by test/log
    clients; unsupported values keep the historical deepcopy behavior.
    """
    kind=type(value)
    if kind is dict:return {k:snapshot_copy(v) for k,v in value.items()}
    if kind is list:return [snapshot_copy(v) for v in value]
    if kind is tuple:return tuple(snapshot_copy(v) for v in value)
    if value is None or kind in (str,int,float,bool,bytes):return value
    return copy.deepcopy(value)

class AvatarRenderWorker:

    def __init__(self, controller, background, size, interval=.033, native_video=None, visual_fps=None, performance_path=None):

        self.controller = controller

        self.native_video=native_video
        if visual_fps is not None and not 1<=float(visual_fps)<=24:raise ValueError('Visual FPS must be 1..24')
        self.visual_period=1/float(visual_fps) if visual_fps is not None else None
        self.visual_owner=controller
        while hasattr(self.visual_owner,'controller'):self.visual_owner=self.visual_owner.controller
        self.next_visual=0.0
        self.visual_slot=0.0

        self.last_state_time=0.0

        self.preview_encoder=PreviewEncoder() if native_video else None

        self.background, self.size = background, tuple(size)

        self.condition = threading.Condition()

        self.interval = interval

        self.closed = False

        self.generation = self.sequence = 0

        self.waiting = deque()

        self.results = deque(maxlen=16)

        self.active = None

        self.frame_stats = deque(maxlen=240)

        self.profile = {}

        self.last_profile = self.previous_frame = 0.0

        self.packet = {'sequence':0,'state':snapshot_copy(controller.public()),

                       'image':None,'rgb':None,'jpeg':b'','render_ms':None,'at':time.monotonic()}

        from tools.render_performance import PerformanceRecorder
        performance=PerformanceRecorder(performance_path) if performance_path else None
        self.presenter=FramePresenter(native_video,lambda:self.generation,self.condition,performance) if native_video and self.visual_period else None

        self.thread = threading.Thread(target=self.work, name='aura-avatar-render', daemon=True)

        self.thread.start()

    def set_interval(self, interval):

        with self.condition:

            self.interval = interval

            self.condition.notify()

    def request(self, method, *args):

        with self.condition:

            if self.closed:

                raise ValueError('演示服务已关闭')

            if method in ('cancel','conversation_stop') or method == 'event' and args[0] in ('cancel','reset'):

                self.generation += 1

                for old in self.waiting:

                    self.results.append({'command_id':old['id'],'ok':False,'error':'已取消'})

                self.waiting.clear()

            if len(self.waiting) >= 4:

                raise ValueError('演示操作队列已满')

            command = {'id':uuid.uuid4().hex,'method':method,'args':args,

                       'generation':self.generation,'deadline':time.monotonic()+2.5}

            self.waiting.append(command)

            self.condition.notify()

            return command['id']

    def submit(self, *args):return self.request('submit', *args)

    def event(self, name):return self.request('event', name)

    def toggle_pause(self):return self.request('toggle_pause')

    def cancel(self):return self.request('cancel')

    def record_start(self):return self.request('record_start')

    def record_stop(self):return self.request('record_stop')

    def conversation_start(self):return self.request('conversation_start')

    def conversation_stop(self):return self.request('conversation_stop')

    def handsfree_toggle(self):return self.request('handsfree_toggle')

    def configure_transcription(self,values):return self.request('configure_transcription',values)

    def read(self):

        with self.condition:

            packet = dict(self.packet)

            packet['state'] = snapshot_copy(packet['state'])

            packet['state']['avatar_command_pending'] = len(self.waiting)+bool(self.active)

            packet['state']['avatar_renderer'] = {

                'sequence':packet['sequence'],'render_ms':packet['render_ms'],

                'frame_age_ms':round((time.monotonic()-packet['at'])*1000),

                'command_results':snapshot_copy(list(self.results)),

                'timings_ms':dict(packet.get('timings_ms',{})),

                'profile':snapshot_copy(self.profile),
                'presentation':self.presenter.read() if self.presenter else None}

            return packet

    def public(self):return self.read()['state']

    def work(self):

        from PIL import Image

        from tools.board_avatar_affine import resize_rgb

        next_frame = time.monotonic()

        try:

            while True:

                with self.condition:

                    while not self.closed and not self.waiting and time.monotonic()<next_frame:

                        self.condition.wait(next_frame-time.monotonic())

                    if self.closed:return

                    commands = list(self.waiting)

                    self.waiting.clear()

                    generation = self.generation

                for command in commands:

                    with self.condition:

                        current = command['generation'] == self.generation

                        self.active = command['id']

                    outcome = {'command_id':command['id'],'ok':False}

                    try:

                        if not current or time.monotonic()>command['deadline']:

                            raise ValueError('演示请求已取消或过期')

                        value = getattr(self.controller,command['method'])(*command['args'])

                        outcome.update(ok=True,result=value)

                    except Exception as exc:

                        outcome['error'] = str(exc)

                        self.controller.last_error = str(exc)

                    with self.condition:

                        self.results.append(outcome)

                        self.active = None

                started = time.monotonic()

                try:

                    render_due=self.visual_period is None or started>=self.next_visual
                    self.visual_owner.render_requested=render_due
                    meta = self.controller.tick()
                    if not render_due:
                        with self.condition:next_frame=max(time.monotonic(),min(started+self.interval,self.next_visual))
                        continue
                    if self.visual_period is not None:
                        if not self.next_visual:self.next_visual=started
                        self.visual_slot=self.next_visual
                        self.next_visual+=self.visual_period
                        while self.next_visual<=started:self.next_visual+=self.visual_period

                    core_done = time.monotonic()

                    resized = encoded = core_done

                    image = rgb = None

                    jpeg = b''

                    if meta:

                        if meta['image'].mode == 'RGB':

                            image = meta['image']

                        else:

                            image = Image.new('RGBA',meta['image'].size,self.background)

                            image.alpha_composite(meta['image'])

                            image = image.convert('RGB')

                        rgb = resize_rgb(image,self.size)

                        resized = time.monotonic()

                        if self.preview_encoder:

                            self.preview_encoder.offer(image)

                            jpeg=self.preview_encoder.read()

                        else:

                            stream = io.BytesIO()

                            image.save(stream,format='JPEG',quality=85)

                            jpeg = stream.getvalue()

                    encoded = time.monotonic()

                    if not self.native_video or time.monotonic()-self.last_state_time>=.1:

                        state = snapshot_copy(self.controller.public())

                        self.last_state_time=time.monotonic()

                    else:state=self.packet['state']

                    ended = time.monotonic()

                    timings={'core':(core_done-started)*1000,'compose_resize':(resized-core_done)*1000,

                             'jpeg':(encoded-resized)*1000,'public':(ended-encoded)*1000,

                             'total':(ended-started)*1000}

                    interval=(ended-self.previous_frame)*1000 if self.previous_frame else None

                    self.previous_frame=ended

                    self.frame_stats.append(dict(timings,interval=interval))

                    with self.condition:

                        # Do not publish a frame completed after a cancel/reset.

                        if generation == self.generation:

                            self.sequence += 1

                            if self.native_video and rgb:

                                push_started=time.monotonic()

                                if self.presenter:
                                    self.presenter.offer(rgb,self.sequence,generation,
                                        self.visual_slot+min(.085,self.visual_period*.85),
                                        getattr(self.visual_owner,'phase','UNKNOWN'),
                                        getattr(getattr(getattr(getattr(self.visual_owner,'core',None),'fsm',None),'state',None),'label','UNKNOWN'),dict(timings))
                                else:self.native_video.push(rgb,self.sequence)

                                delivered=time.monotonic()

                                timings['native_enqueue' if self.presenter else 'native_push']=(delivered-push_started)*1000

                                timings['total']=(delivered-started)*1000

                                self.frame_stats[-1].update(timings)

                                self.frame_stats[-1]['interval']=(delivered-self.previous_delivery)*1000 if getattr(self,'previous_delivery',0) else None

                                self.previous_delivery=delivered

                            self.packet = {'sequence':self.sequence,'state':state,'image':image,

                                'rgb':rgb,'jpeg':jpeg,'render_ms':(time.monotonic()-started)*1000,

                                'at':time.monotonic(),'timings_ms':timings}

                            if ended-self.last_profile>=1:

                                self.last_profile=ended

                                def stats(key):

                                    values=sorted(r[key] for r in self.frame_stats if r.get(key) is not None)

                                    return {'p50':values[len(values)//2],'p95':values[min(len(values)-1,int(len(values)*.95))],'max':values[-1]} if values else {}

                                self.profile={'frames':len(self.frame_stats),'window_seconds':sum(r['interval'] or 0 for r in self.frame_stats)/1000,

                                              **{key:stats(key) for key in (('core','compose_resize','jpeg','public','total','interval','native_push') if self.native_video else ('core','compose_resize','jpeg','public','total','interval'))}}

                except Exception as exc:

                    self.controller.last_error = type(exc).__name__+': '+str(exc)

                    self.controller.cancel()

                    with self.condition:

                        self.packet = dict(self.packet,state=snapshot_copy(self.controller.public()))

                with self.condition:

                    # Skip missed render slots instead of building a frame queue.

                    if self.visual_period is not None:
                        next_frame=max(time.monotonic(),min(started+self.interval,self.next_visual))
                    elif self.native_video:

                        next_frame+=self.interval

                        if next_frame<time.monotonic():next_frame=time.monotonic()

                    else:next_frame = max(started+self.interval,time.monotonic())

        finally:

            if self.presenter:self.presenter.close()
            if self.preview_encoder:self.preview_encoder.close()

            if hasattr(self.controller,'close'):

                self.controller.close()

            else:

                self.controller.cancel()

    def close(self):

        with self.condition:

            self.closed = True

            self.waiting.clear()

            self.condition.notify()

        self.thread.join(timeout=7)

        if self.thread.is_alive():

            raise RuntimeError('Avatar renderer did not stop')

class PreviewEncoder:

    """Latest-only web diagnostic image; never blocks native display."""

    def __init__(self):

        self.condition=threading.Condition();self.pending=None;self.jpeg=b'';self.closed=False;self.last=0

        self.thread=threading.Thread(target=self.work,name='aura-avatar-preview-jpeg',daemon=True);self.thread.start()

    def offer(self,image):

        with self.condition:

            if time.monotonic()-self.last>=.2:

                self.pending=image;self.last=time.monotonic();self.condition.notify()

    def read(self):

        with self.condition:return self.jpeg

    def work(self):

        while True:

            with self.condition:

                while not self.closed and self.pending is None:self.condition.wait()

                if self.closed:return

                image,self.pending=self.pending,None

            stream=io.BytesIO();image.save(stream,format='JPEG',quality=85)

            with self.condition:self.jpeg=stream.getvalue()

    def close(self):

        with self.condition:self.closed=True;self.pending=None;self.condition.notify()

        self.thread.join(timeout=3)



class FramePresenter:
    """One pending unique frame, fixed release deadlines; never duplicate frames.

    Rendering and controls continue while the presenter waits. A generation
    change invalidates held pixels. The maximum deliberate hold is 85 ms from
    capture start, explicitly exposed rather than counted as render work.
    """
    def __init__(self,sink,generation,guard,performance=None):
        self.sink=sink;self.generation=generation;self.condition=threading.Condition()
        self.guard=guard;self.performance=performance
        self.pending=None;self.closed=False;self.presented=self.dropped=0
        self.last={};self.error=''
        self.thread=threading.Thread(target=self.work,name='aura-avatar-present',daemon=True)
        self.thread.start()

    def offer(self,rgb,sequence,generation,deadline,phase=None,state=None,timings=None):
        with self.condition:
            if self.closed:return
            if self.pending:self.dropped+=1
            self.pending=(rgb,sequence,generation,deadline,phase,state,timings or {})
            self.condition.notify()

    def read(self):
        with self.condition:
            return dict(self.last,presented=self.presented,dropped=self.dropped,error=self.error,
                        deliberate_hold_limit_ms=85,
                        performance_log=self.performance.status() if self.performance else None)

    def work(self):
        while True:
            with self.condition:
                while not self.closed:
                    if self.pending:
                        left=self.pending[3]-time.monotonic()
                        if left<=0:break
                        self.condition.wait(left)
                    else:self.condition.wait()
                if self.closed:return
                rgb,sequence,generation,deadline,phase,state,timings=self.pending;self.pending=None
            try:
                with self.guard:
                    if generation!=self.generation():
                        with self.condition:self.dropped+=1
                        continue
                    started=time.monotonic();self.sink.push(rgb,sequence);ended=time.monotonic()
                with self.condition:
                    self.presented+=1
                    if self.performance:self.performance.observe(phase,state,ended,sequence,timings)
                    self.last=dict(sequence=sequence,lateness_ms=max(0,started-deadline)*1000,
                                   push_ms=(ended-started)*1000)
            except Exception as exc:
                with self.condition:self.error=type(exc).__name__+': '+str(exc)

    def close(self):
        with self.condition:self.closed=True;self.pending=None;self.condition.notify()
        self.thread.join(timeout=3)
        if self.thread.is_alive():raise RuntimeError('Avatar presenter did not stop')
        if self.performance:self.performance.close(time.monotonic())
