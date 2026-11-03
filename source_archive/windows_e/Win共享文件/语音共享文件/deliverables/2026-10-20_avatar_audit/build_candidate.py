"""Build a minimal patch against the current board snapshot, not an old release."""
import json,math,re
from pathlib import Path
HERE=Path(__file__).resolve().parent
baseline=json.loads((HERE/'performance_rebase.json').read_text(encoding='utf-8-sig'))
sources=baseline['sources'];out=HERE/'candidate_sources'
def save(name,text):
    target=out/name;target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(text,encoding='utf-8')
def replace(text,old,new,count=1):
    assert text.count(old)==count,(old,text.count(old))
    return text.replace(old,new)
name='aura/board/interaction/avatar_player.py';text=sources[name]
text=replace(text,'if self.idle_gain > 0.0:','if self.idle_gain > 0.0 and not getattr(self, "defer_portrait_offsets", False):')
text=replace(text,'        interpolation = 0.0\n',
             '        interpolation = 0.0\n        skip_mouth_pixels = getattr(self, "defer_portrait_offsets", False) and asset in getattr(self, "audio_mouth_assets", ())\n')
text=replace(text,'if interpolation > 1e-6 and left + 1 < len(frames):','if not skip_mouth_pixels and interpolation > 1e-6 and left + 1 < len(frames):')
text=replace(text,'if other.size == image.size:','if not skip_mouth_pixels and other.size == image.size:')
save(name,text)
name='deliverables/2026-10-06_avatar_reuse/preview_script.py';text=sources[name]
text=replace(text,'if self.idle_gain>0.0:','if self.idle_gain>0.0 and not getattr(self, "defer_portrait_offsets", False):')
text=replace(text,'            if gain<1.0:','            if gain<1.0 and not (getattr(self, "defer_portrait_offsets", False) and meta["asset"] in getattr(self, "audio_mouth_assets", ())):')
save(name,text)
name='aura/tools/realtime_facials.py';text=sources[name]
text=replace(text,'self.core=core;self.eyes=BlinkLayer();self.mouths=MouthBank(core)',
             'self.core=core;self.eyes=BlinkLayer();self.mouths=MouthBank(core)\n        core.audio_mouth_assets=frozenset(self.mouths.keys)')
text=replace(text,'if self.core.idle_gain>0:','if self.core.idle_gain>0 and not getattr(self.core, "defer_portrait_offsets", False):')
text=replace(text,'return self.eyes.apply(result,now,self.core)',
             'result["portrait_offsets_deferred"]=getattr(self.core, "defer_portrait_offsets", False)\n        return self.eyes.apply(result,now,self.core)')
save(name,text)
name='aura/tools/facial_layers.py';text=sources[name]
local=(HERE.parents[1]/name).read_text(encoding='utf-8')
warp=local[local.index('def warp('):local.index('\n\nclass BlinkLayer:')]
warp=warp.replace('Image.Transform.AFFINE','AFFINE').replace('Image.Resampling.BICUBIC','BICUBIC')
text=text[:text.index('def warp(')]+warp+text[text.index('\n\nclass BlinkLayer:'):]
text=text.replace('import json\n','import json\nimport math\n',1)
text=replace(text,"        if layer is not None:\n            if core is not None and core.idle_gain>0:",
             "        deferred=meta.get('portrait_offsets_deferred',False)\n        if layer is not None:\n            if not deferred and core is not None and core.idle_gain>0:")
text=replace(text,'        return result\n\n\ndef aperture_levels',
             "        if deferred and core is not None and core.idle_gain>0:\n            from board.interaction.avatar_timing import idle_offsets\n            result['image']=core._apply_offsets(result['image'],idle_offsets(t,gain=core.idle_gain))\n        result['portrait_offsets_deferred']=False\n        return result\n\n\ndef aperture_levels")
text=replace(text,'self.core=core;self.keys={}', 'self.core=core;self.keys={};self.patch_boxes={};self.patches={}')
text=replace(text,'            self.keys[name]=[(score/top,image) for score,image in keys]',
             '''            self.keys[name]=[(score/top,image) for score,image in keys]
            anchor=np.asarray(core._reuse_anchors[name]);changed=np.zeros(anchor.shape[:2],dtype=bool)
            for _,image in keys:changed |= np.any(np.asarray(image)!=anchor,axis=2)
            ys,xs=np.where(changed)
            box=(int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1) if len(xs) else (0,0,1,1)
            self.patch_boxes[name]=box
            self.patches[name]=[image.crop(box) for _,image in self.keys[name]]''')
text=replace(text,'        image=Image.blend(keys[left][1],keys[right][1],alpha)\n        return Image.blend(self.core._reuse_anchors[name],image,max(0,min(1,gain)))',
             '''        box=self.patch_boxes[name];patches=self.patches[name]
        patch=Image.blend(patches[left],patches[right],alpha)
        patch=Image.blend(self.core._reuse_anchors[name].crop(box),patch,max(0,min(1,gain)))
        image=self.core._reuse_anchors[name].copy();image.paste(patch,box[:2]);return image''')
save(name,text)
name='aura/tools/board_avatar_gtk.py';text=sources[name]
text=replace(text,'            core = create_runtime_core(create_demo_core)',
             '            core = create_runtime_core(create_demo_core)\n            from tools.board_avatar_affine import configure_board_rendering\n            configure_board_rendering(core)')
text=replace(text,'        self.last_avatar_sequence = 0',
             '        self.last_avatar_sequence = 0\n        self.last_runtime_refresh = 0.0\n        self.displayed_frames = 0')
text=replace(text,"                self.last_avatar_sequence = packet['sequence']\n            state = packet['state']",
             "                self.last_avatar_sequence = packet['sequence']\n                self.displayed_frames += 1\n            # Portrait and intents keep their own cadence; expensive labels/settings\n            # only need 10 Hz. Audio/VAD still run on the render owner.\n            if time.monotonic()-self.last_runtime_refresh < .1:\n                return True\n            self.last_runtime_refresh = time.monotonic()\n            state = packet['state']\n            state['avatar_display']={'frames':self.displayed_frames,'sequence':self.last_avatar_sequence,'at':time.monotonic()}")
save(name,text)
name='aura/tools/board_avatar_worker.py';text=sources[name]
text=replace(text,'        from tools.pillow_compat import LANCZOS', '        from tools.board_avatar_affine import resize_rgb')
text=replace(text,'                        rgb = image.resize(self.size,LANCZOS).tobytes()', '                        rgb = resize_rgb(image,self.size)')
text=replace(text,'        self.active = None\n        self.packet',
             "        self.active = None\n        self.frame_stats = deque(maxlen=240)\n        self.profile = {}\n        self.last_profile = self.previous_frame = 0.0\n        self.packet")
text=replace(text,"                'command_results':copy.deepcopy(list(self.results))}",
             "                'command_results':copy.deepcopy(list(self.results)),\n                'timings_ms':dict(packet.get('timings_ms',{})),\n                'profile':copy.deepcopy(self.profile)}")
text=replace(text,'                    meta = self.controller.tick()',
             "                    meta = self.controller.tick()\n                    core_done = time.monotonic()\n                    resized = encoded = core_done")
text=replace(text,'                        stream = io.BytesIO()',
             '                        resized = time.monotonic()\n                        stream = io.BytesIO()')
text=replace(text,'                    state = copy.deepcopy(self.controller.public())',
             "                    encoded = time.monotonic()\n                    state = copy.deepcopy(self.controller.public())\n                    ended = time.monotonic()\n                    timings={'core':(core_done-started)*1000,'compose_resize':(resized-core_done)*1000,\n                             'jpeg':(encoded-resized)*1000,'public':(ended-encoded)*1000,\n                             'total':(ended-started)*1000}\n                    interval=(ended-self.previous_frame)*1000 if self.previous_frame else None\n                    self.previous_frame=ended\n                    self.frame_stats.append(dict(timings,interval=interval))")
text=replace(text,"                                'at':time.monotonic()}",
             "                                'at':time.monotonic(),'timings_ms':timings}\n                            if ended-self.last_profile>=1:\n                                self.last_profile=ended\n                                def stats(key):\n                                    values=sorted(r[key] for r in self.frame_stats if r[key] is not None)\n                                    return {'p50':values[len(values)//2],'p95':values[min(len(values)-1,int(len(values)*.95))],'max':values[-1]} if values else {}\n                                self.profile={'frames':len(self.frame_stats),'window_seconds':sum(r['interval'] or 0 for r in self.frame_stats)/1000,\n                                              **{key:stats(key) for key in ('core','compose_resize','jpeg','public','total','interval')}}")
save(name,text)
for path in out.rglob('*.py'):compile(path.read_text(encoding='utf-8'),str(path),'exec')
print(json.dumps({'source_runtime':baseline['runtime'],'files':[str(p.relative_to(out)) for p in out.rglob('*.py')]}))
