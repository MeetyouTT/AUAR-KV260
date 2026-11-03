from pathlib import Path
HERE=Path(__file__).resolve().parent
p=HERE/'stable_fps_sources/board_avatar_worker.py'
text=p.read_text(encoding='utf-8')
# Normalize only excess blank lines from the historical exported snapshot.
while '\n\n\n' in text:text=text.replace('\n\n\n','\n\n')
text=text.replace('        self.next_visual=0.0','        self.next_visual=0.0\n        self.visual_slot=0.0')
old="        self.thread = threading.Thread(target=self.work, name='aura-avatar-render', daemon=True)"
assert old in text
text=text.replace(old,"""        self.presenter=FramePresenter(native_video,lambda:self.generation) if native_video and self.visual_period else None

"""+old)
text=text.replace("        with self.condition:\n\n            packet = dict(self.packet)","        with self.condition:\n\n            packet = dict(self.packet)")
text=text.replace("            packet['state']['avatar_renderer'] = {", "            packet['state']['avatar_renderer'] = {")
text=text.replace("'profile':copy.deepcopy(self.profile)}", "'profile':copy.deepcopy(self.profile),\n                'presentation':self.presenter.read() if self.presenter else None}")
old='                    if self.visual_period is not None:self.next_visual=started+self.visual_period'
assert old in text
text=text.replace(old,"""                    if self.visual_period is not None:
                        if not self.next_visual:self.next_visual=started
                        self.visual_slot=self.next_visual
                        self.next_visual+=self.visual_period
                        while self.next_visual<=started:self.next_visual+=self.visual_period""")
old='                                self.native_video.push(rgb,self.sequence)'
assert old in text
text=text.replace(old,"""                                if self.presenter:
                                    self.presenter.offer(rgb,self.sequence,generation,
                                        self.visual_slot+min(.085,self.visual_period*.85))
                                else:self.native_video.push(rgb,self.sequence)""")
# Honor the next capture deadline after a rendered frame as well as between frames.
old='                    if self.native_video:\n\n                        next_frame+=self.interval'
assert old in text
text=text.replace(old,"""                    if self.visual_period is not None:
                        next_frame=max(time.monotonic(),min(started+self.interval,self.next_visual))
                    elif self.native_video:

                        next_frame+=self.interval""")
text=text.replace('            if self.preview_encoder:self.preview_encoder.close()', '            if self.presenter:self.presenter.close()\n            if self.preview_encoder:self.preview_encoder.close()')
text+='''

class FramePresenter:
    """One pending unique frame, fixed release deadlines; never duplicate frames.

    Rendering and controls continue while the presenter waits. A generation
    change invalidates held pixels. The maximum deliberate hold is 85 ms from
    capture start, explicitly exposed rather than counted as render work.
    """
    def __init__(self,sink,generation):
        self.sink=sink;self.generation=generation;self.condition=threading.Condition()
        self.pending=None;self.closed=False;self.presented=self.dropped=0
        self.last={};self.error=''
        self.thread=threading.Thread(target=self.work,name='aura-avatar-present',daemon=True)
        self.thread.start()

    def offer(self,rgb,sequence,generation,deadline):
        with self.condition:
            if self.closed:return
            if self.pending:self.dropped+=1
            self.pending=(rgb,sequence,generation,deadline)
            self.condition.notify()

    def read(self):
        with self.condition:
            return dict(self.last,presented=self.presented,dropped=self.dropped,error=self.error,
                        deliberate_hold_limit_ms=85)

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
                rgb,sequence,generation,deadline=self.pending;self.pending=None
            if generation!=self.generation():
                with self.condition:self.dropped+=1
                continue
            try:
                started=time.monotonic();self.sink.push(rgb,sequence);ended=time.monotonic()
                with self.condition:
                    self.presented+=1
                    self.last=dict(sequence=sequence,lateness_ms=max(0,started-deadline)*1000,
                                   push_ms=(ended-started)*1000)
            except Exception as exc:
                with self.condition:self.error=type(exc).__name__+': '+str(exc)

    def close(self):
        with self.condition:self.closed=True;self.pending=None;self.condition.notify()
        self.thread.join(timeout=3)
        if self.thread.is_alive():raise RuntimeError('Avatar presenter did not stop')
'''
p.write_text(text,encoding='utf-8')
print('Frame pacing source prepared')
