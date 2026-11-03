"""Generate small, opt-in patches against the current accepted live UI."""
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
b=json.loads((HERE/'baseline.json').read_text(encoding='utf-8-sig'))
out=HERE/'sources'
def load(n):return (HERE/'baseline_sources'/n).read_text(encoding='utf-8')
def save(n,t):
 p=out/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(t,encoding='utf-8')
def sub(t,a,b):
 assert t.count(a)==1,(a,t.count(a));return t.replace(a,b)
n='aura/board/interaction/avatar_player.py';t=load(n)
t=sub(t,'image = Image.blend(image, frames[left + 1], interpolation)',"image = getattr(self,'blend_frames',Image.blend)(image,frames[left+1],interpolation)")
t=sub(t,'image = Image.blend(image, other, alpha)',"image = getattr(self,'blend_frames',Image.blend)(image,other,alpha)")
save(n,t)
n='aura/tools/facial_layers.py';t=load(n)
t=sub(t,"            image=Image.alpha_composite(meta['image'],layer);image.putalpha(meta['image'].getchannel('A'));result['image']=image",
 '''            base=meta['image']
            if getattr(core,'native_pixels',None):base=core.native_pixels.materialize(base)
            if getattr(core,'native_pixels',None):
                box=layer.getbbox();image=base.copy()
                if box:
                    patch=Image.alpha_composite(base.crop(box),layer.crop(box));patch.putalpha(base.crop(box).getchannel('A'));image.paste(patch,box[:2])
            else:
                image=Image.alpha_composite(base,layer);image.putalpha(base.getchannel('A'))
            result['image']=image''')
save(n,t)
n='aura/tools/board_avatar_gtk.py';t=load(n)
t=sub(t,'        self.jobs = self.output = self.bridge = self.mixer = self.services = self.preview_output = self.transcriber = None',
 '        self.jobs = self.output = self.bridge = self.mixer = self.services = self.preview_output = self.transcriber = None\n        self.native_pixels = self.native_video = None')
t=sub(t,"            configure_board_rendering(core,self.tokens['colors']['panel_bg'])",
 '''            if config.get('native_avatar'):
                from tools.native_pixels import NativePixels
                from tools.native_video import NativeVideo
                library=AURA/'tools/libaura_pixels.so'
                self.native_pixels=NativePixels(library,self.tokens['colors']['panel_bg'],(self.rect['w'],self.rect['h']),threads=int(config.get('native_pixel_threads',2)))
                self.native_pixels.configure(core)
                self.native_video=NativeVideo(library,(self.rect['w'],self.rect['h']))
            else:configure_board_rendering(core,self.tokens['colors']['panel_bg'])''')
t=sub(t,"            core.MAX_CACHED_SEQUENCES = int(config['cache_sequences'])",
 '''            core.MAX_CACHED_SEQUENCES = int(config['cache_sequences'])
            if config.get('native_avatar'):
                for name in ('IDLE','PRESENT','LISTENING','THINKING','ACK_NOD','DENY_SHAKE','AWAKE','PUZZLED'):
                    core.sequence(name);core.sop(name)''')
t=sub(t,".25 if self.preferences['economy'] else config['tick_ms']/1000)",
 ".25 if self.preferences['economy'] else (1/24 if config.get('native_avatar') else config['tick_ms']/1000),native_video=self.native_video)")
t=sub(t,"        interval = int(self.config['tick_ms'])", "        interval = int(self.config['tick_ms'])") if False else t
t=sub(t,"            self.controller.set_interval(.25 if self.preferences['economy'] else interval/1000)",
 "            self.controller.set_interval(.25 if self.preferences['economy'] else (1/24 if self.config.get('native_avatar') else interval/1000))\n        if self.config.get('native_avatar'):interval=int(self.config.get('native_ui_tick_ms',200))")
t=sub(t,'        self.portrait = gtk.Image()',
 '''        self.portrait = gtk.DrawingArea() if self.native_video else gtk.Image()
        if self.native_video:
            self.portrait.set_size_request(self.rect['w'],self.rect['h'])
            self.portrait.connect('map',self.attach_native_portrait)''')
t=sub(t,'    def attach_preview(self, area, name, width, height):',
 '''    def attach_native_portrait(self,area):
        import gi
        gi.require_version('GdkX11','3.0')
        from gi.repository import GdkX11
        handle=GdkX11.X11Window.get_xid(area.get_window())
        self.Gdk.Display.get_default().sync()
        self.native_video.attach(handle)

    def attach_preview(self, area, name, width, height):''')
t=sub(t,"            if packet['rgb'] and packet['sequence'] != self.last_avatar_sequence:",
 "            if self.native_video:\n                self.last_image=packet['image']\n                self.last_avatar_sequence=packet['sequence']\n            if not self.native_video and packet['rgb'] and packet['sequence'] != self.last_avatar_sequence:")
t=sub(t,"            state['avatar_display']={'frames':self.displayed_frames,'sequence':self.last_avatar_sequence,'at':time.monotonic()}",
 "            state['avatar_display']={'frames':self.displayed_frames,'sequence':self.last_avatar_sequence,'at':time.monotonic()}\n            if self.native_video:state['avatar_display']=dict(self.native_video.read(),kind='native_sink_handoff')")
t=sub(t,"        if getattr(self,'transcriber',None):",
 "        if self.native_video:\n            self.native_video.close();self.native_video=None\n        if self.native_pixels:\n            self.native_pixels.close();self.native_pixels=None\n        if getattr(self,'transcriber',None):")
save(n,t)
n='aura/tools/board_avatar_worker.py';t=load(n)
t=sub(t,'def __init__(self, controller, background, size, interval=.033):','def __init__(self, controller, background, size, interval=.033, native_video=None):')
t=sub(t,'        self.controller = controller', '        self.controller = controller\n        self.native_video=native_video\n        self.last_state_time=0.0\n        self.preview_encoder=PreviewEncoder() if native_video else None')
t=sub(t,"                        stream = io.BytesIO()\n                        image.save(stream,format='JPEG',quality=85)\n                        jpeg = stream.getvalue()",
 '''                        if self.preview_encoder:
                            self.preview_encoder.offer(image)
                            jpeg=self.preview_encoder.read()
                        else:
                            stream = io.BytesIO()
                            image.save(stream,format='JPEG',quality=85)
                            jpeg = stream.getvalue()''')
t=sub(t,'                    state = copy.deepcopy(self.controller.public())',
 '''                    if not self.native_video or time.monotonic()-self.last_state_time>=.1:
                        state = copy.deepcopy(self.controller.public())
                        self.last_state_time=time.monotonic()
                    else:state=self.packet['state']''')
t=sub(t,'                            self.sequence += 1',
 '''                            self.sequence += 1
                            if self.native_video and rgb:
                                push_started=time.monotonic()
                                self.native_video.push(rgb,self.sequence)
                                delivered=time.monotonic()
                                timings['native_push']=(delivered-push_started)*1000
                                timings['total']=(delivered-started)*1000
                                self.frame_stats[-1].update(timings)
                                self.frame_stats[-1]['interval']=(delivered-self.previous_delivery)*1000 if getattr(self,'previous_delivery',0) else None
                                self.previous_delivery=delivered''')
t=sub(t,"('core','compose_resize','jpeg','public','total','interval')",
 "(('core','compose_resize','jpeg','public','total','interval','native_push') if self.native_video else ('core','compose_resize','jpeg','public','total','interval'))")
t=sub(t,"if r[key] is not None","if r.get(key) is not None")
t=sub(t,'                    next_frame = max(started+self.interval,time.monotonic())',
 '''                    if self.native_video:
                        next_frame+=self.interval
                        if next_frame<time.monotonic():next_frame=time.monotonic()
                    else:next_frame = max(started+self.interval,time.monotonic())''')
t=sub(t,"        finally:\n            if hasattr(self.controller,'close'):",
 "        finally:\n            if self.preview_encoder:self.preview_encoder.close()\n            if hasattr(self.controller,'close'):")
t+='''

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
'''
save(n,t)
for name in ('native_pixels.cpp','native_pixels.py','native_video.py'):save('aura/tools/'+name,(HERE/name).read_text(encoding='utf-8'))
for p in out.rglob('*.py'):compile(p.read_text(encoding='utf-8'),str(p),'exec')
print('candidate sources generated')
