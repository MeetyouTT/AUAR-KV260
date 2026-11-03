"""Generate a reversible source overlay from the exact running board snapshot.

This does not edit the repository's active aura tree or any board service.
"""
from pathlib import Path
import difflib,hashlib,json,shutil
BASE=Path(__file__).resolve().parent
SRC=BASE/'board_source/aura'
OUT=BASE/'ui_candidate/aura'
def change(name,edits):
    before=(SRC/name).read_text(encoding='utf8');after=before
    for old,new in edits:
        if after.count(old)!=1:raise RuntimeError(f'{name}: expected unique patch anchor: {old[:90]!r}')
        after=after.replace(old,new)
    dest=OUT/name;dest.parent.mkdir(exist_ok=True,parents=True);dest.write_text(after,encoding='utf8')
    return ''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='running/'+name,tofile='candidate/'+name))
patches=[]
patches.append(change('tools/board_avatar_worker.py',[
 ("fps=offload.target_fps if offload.status()['mode']=='remote' else 8","fps=offload.target_fps if offload.status()['mode'] in ('remote','native') else 8"),
 ("                    elif meta:\n", "                    elif meta and meta.get('_native_yuki'):\n                        # GTK owns the GL context; the audio worker only offers numeric controls.\n                        pass\n                    elif meta:\n")]))
patches.append(change('tools/board_avatar_gtk.py',[
 ("        self.native_pixels = self.native_video = None", "        self.native_pixels = self.native_video = None\n        self.native_yuki = self.yuki_portrait = self.native_yuki_config = None"),
 ("            if config.get('native_avatar'):\n                from tools.native_pixels", "            if config.get('native_avatar') and not config.get('native_yuki',{}).get('enabled'):\n                from tools.native_pixels"),
 ("            if config.get('native_avatar'):\n                for name", "            if config.get('native_avatar') and not config.get('native_yuki',{}).get('enabled'):\n                for name"),
 ("            if config.get('portrait_offload',{}).get('enabled'):",
  "            if config.get('native_yuki',{}).get('enabled'):\n                from tools.native_yuki import prepare_portrait\n                self.native_yuki,self.native_yuki_config=prepare_portrait(AURA,config['native_yuki'],self.output,self.source_hashes)\n                visual_controller.portrait_offload=self.native_yuki\n            elif config.get('portrait_offload',{}).get('enabled'):"),
 ("        self.fixed.put(self.portrait, self.geometry['x']+self.rect['x'], self.geometry['y']+self.rect['y'])",
  "        self.fixed.put(self.portrait, self.geometry['x']+self.rect['x'], self.geometry['y']+self.rect['y'])\n        if self.native_yuki_config:\n            from tools.native_yuki import create_gl_area\n            self.yuki_portrait=create_gl_area(self.native_yuki_config,self.native_yuki)\n            self.yuki_portrait.set_size_request(self.rect['w'],self.rect['h'])\n            self.fixed.put(self.yuki_portrait,self.geometry['x']+self.rect['x'],self.geometry['y']+self.rect['y'])"),
 ("        self.portrait.set_visible(not is_vision)",
  "        native_yuki=bool(self.native_yuki and self.native_yuki.ready and self.native_yuki.enabled)\n        self.portrait.set_visible(not is_vision and not native_yuki)\n        if self.yuki_portrait:self.yuki_portrait.set_visible(not is_vision and native_yuki)"),
 ("            if not self.native_video and packet['rgb'] and packet['sequence'] != self.last_avatar_sequence:",
  "            if self.yuki_portrait:\n                selected=bool(self.native_yuki.ready and self.native_yuki.enabled)\n                self.yuki_portrait.set_visible(self.page!='vision' and selected)\n                self.portrait.set_visible(self.page!='vision' and not selected)\n                if selected:self.displayed_frames=int(self.native_yuki.latest_stats.get('frames',0))\n            if not self.native_video and packet['rgb'] and packet['sequence'] != self.last_avatar_sequence:"),
 ("            if self.native_video:state['avatar_display']=dict(self.native_video.read(),kind='native_sink_handoff')",
  "            if self.native_yuki and self.native_yuki.ready and self.native_yuki.enabled:\n                state['avatar_display']=dict(self.native_yuki.latest_stats,kind='native_yuki_egl')\n            elif self.native_video:state['avatar_display']=dict(self.native_video.read(),kind='native_sink_handoff')"),
 ("        self.controls['portrait_toggle'].set_label('画面：电脑' if mode=='remote' else\n            '画面：电脑连接中，板卡显示' if portrait.get('selected') else '画面：板卡')",
  "        if self.native_yuki:\n            self.controls['portrait_toggle'].set_label('形象：雪妃' if mode=='native' else '形象：默认')\n        else:\n            self.controls['portrait_toggle'].set_label('画面：电脑' if mode=='remote' else\n                '画面：电脑连接中，板卡显示' if portrait.get('selected') else '画面：板卡')")]))
(OUT/'tools/native_yuki.py').write_bytes((BASE/'host/native_yuki.py').read_bytes())
(OUT/'tools/egl_window.py').write_bytes((BASE/'host/egl_window.py').read_bytes())
for p in OUT.rglob('*.py'):compile(p.read_text(encoding='utf8'),str(p),'exec')
(BASE/'ui_candidate.patch').write_text('\n'.join(patches),encoding='utf8')
manifest={'deployed':False,'basis':json.loads((BASE/'board_source/manifest.json').read_text(encoding='utf8')),
 'files':{p.relative_to(OUT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.rglob('*') if p.is_file()},
 'native_config_example':{'enabled':True,'fps':24,
   'library':'tools/libaura_yuki.so',
   'model':'assets/yuki/model.runtime.json',
   'resx':'assets/yuki/yuk_0.ems.resx.json',
   'resource_root':'assets/yuki','seed':1}}
(BASE/'ui_candidate/manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
print(json.dumps({'candidate_files':len(manifest['files']),'syntax':'PASS','deployed':False}))
