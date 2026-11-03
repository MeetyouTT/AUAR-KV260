"""Increment only the frozen Hub analysis callsite, preserving its PCM lifecycle."""
import hashlib,json
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent/'2026-10-29_speaker_visual_cooperation'
relative='tools/speaker_turns.py';path=B/'candidate'/relative;raw=path.read_bytes();source=raw.decode()
old='''            voice=self.hub.speaker.analyze(meta,raw)'''
new='''            analyzer=getattr(self.hub,'progressive_speaker',None)
            if analyzer is None:
                voice=self.hub.speaker.analyze(meta,raw);anonymous=None
            else:
                voice,anonymous=analyzer.analyze(meta,raw,is_current=lambda:not job['cancelled'] and self.clock()<row['deadline'] and row['value']['status']=='PENDING')'''
assert source.count(old)==1
source=source.replace(old,new)
old="voice=voice,visual=row['visual'])"
assert source.count(old)==1
source=source.replace(old,"voice=voice,visual=row['visual'],anonymous=anonymous)")
compile(source,relative,'exec')
target=H/'candidate'/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(source,encoding='utf-8')
base=H/'base_snapshot'/relative;base.parent.mkdir(parents=True,exist_ok=True);base.write_bytes(raw)
(H/'hub_adapter_base.json').write_text(json.dumps({'source':str(path),'sha256':hashlib.sha256(raw).hexdigest(),
 'pcm_job_descriptor_preserved':True,'changes':['optional analyzer call','optional version2 anonymous descriptor']},indent=2),encoding='utf-8')
print(json.dumps({'status':'STAGED','production_changed':False,'pcm_lifecycle_preserved':True}))
