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


class AvatarRenderWorker:
    def __init__(self, controller, background, size, interval=.033):
        self.controller = controller
        self.background, self.size = background, tuple(size)
        self.condition = threading.Condition()
        self.interval = interval
        self.closed = False
        self.generation = self.sequence = 0
        self.waiting = deque()
        self.results = deque(maxlen=16)
        self.active = None
        self.packet = {'sequence':0,'state':copy.deepcopy(controller.public()),
                       'image':None,'rgb':None,'jpeg':b'','render_ms':None,'at':time.monotonic()}
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
    def configure_transcription(self,values):return self.request('configure_transcription',values)

    def read(self):
        with self.condition:
            packet = dict(self.packet)
            packet['state'] = copy.deepcopy(packet['state'])
            packet['state']['avatar_command_pending'] = len(self.waiting)+bool(self.active)
            packet['state']['avatar_renderer'] = {
                'sequence':packet['sequence'],'render_ms':packet['render_ms'],
                'frame_age_ms':round((time.monotonic()-packet['at'])*1000),
                'command_results':copy.deepcopy(list(self.results))}
            return packet

    def public(self):return self.read()['state']

    def work(self):
        from PIL import Image
        from tools.pillow_compat import LANCZOS
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
                    meta = self.controller.tick()
                    image = rgb = None
                    jpeg = b''
                    if meta:
                        image = Image.new('RGBA',meta['image'].size,self.background)
                        image.alpha_composite(meta['image'])
                        image = image.convert('RGB')
                        rgb = image.resize(self.size,LANCZOS).tobytes()
                        stream = io.BytesIO()
                        image.save(stream,format='JPEG',quality=85)
                        jpeg = stream.getvalue()
                    state = copy.deepcopy(self.controller.public())
                    with self.condition:
                        # Do not publish a frame completed after a cancel/reset.
                        if generation == self.generation:
                            self.sequence += 1
                            self.packet = {'sequence':self.sequence,'state':state,'image':image,
                                'rgb':rgb,'jpeg':jpeg,'render_ms':(time.monotonic()-started)*1000,
                                'at':time.monotonic()}
                except Exception as exc:
                    self.controller.last_error = type(exc).__name__+': '+str(exc)
                    self.controller.cancel()
                    with self.condition:
                        self.packet = dict(self.packet,state=copy.deepcopy(self.controller.public()))
                with self.condition:
                    # Skip missed render slots instead of building a frame queue.
                    next_frame = max(started+self.interval,time.monotonic())
        finally:
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
