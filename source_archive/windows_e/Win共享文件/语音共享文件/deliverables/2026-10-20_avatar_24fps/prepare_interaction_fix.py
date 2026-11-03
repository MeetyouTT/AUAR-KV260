from pathlib import Path
HERE=Path(__file__).resolve().parent
out=HERE/'interaction_fix_sources/tools';out.mkdir(parents=True,exist_ok=True)
text=(HERE/'action_sources/tools/realtime_facials.py').read_text(encoding='utf-8')
text=text.replace("        body,face=self.body.sample(now)\n        if asset in self.mouths.keys or meta.get('display_state')=='IDLE':", "        if asset in self.mouths.keys or meta.get('display_state')=='IDLE':\n            body,face=self.body.sample(now)")
(out/'realtime_facials.py').write_text(text,encoding='utf-8')
text=(HERE/'action_sources/tools/idle_body_compositor.py').read_text(encoding='utf-8')
text=text.replace('        self.player.idle_gain = 0.0',
    "        self.player.idle_gain = 0.0\n        native=getattr(core,'native_pixels',None)\n        if native:self.player.blend_frames=native.materialize_blend")
(out/'idle_body_compositor.py').write_text(text,encoding='utf-8')
source=(HERE/'prepare_action_candidate.py').read_text(encoding='utf-8')
source=source.replace("HERE/'action_sources'","HERE/'interaction_fix_sources'")
source=source.replace("'f8e48486023d'","'0e98f7830e27'")
source=source.replace("'action_candidate.json'","'interaction_fix_candidate.json'")
exec(compile(source,str(HERE/'prepare_action_candidate.py'),'exec'))
