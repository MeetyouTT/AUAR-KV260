"""Back up and apply only declared host-side code; never copy models/config secrets."""
import hashlib,json
from pathlib import Path
H=Path(__file__).resolve().parent;C=H/'candidate_source';A=H.parents[1]/'aura'
names=['tools/board_model_host.py','tools/voice_channel_source.py','tools/native_grammar.py','tools/dialogue_stream.py',
 'tools/visual_voice_host.py','tools/visual_question_host.py','tools/device_client.py','tools/social_feedback.py',
 'common/voice_service_capabilities.py','common/voice_channel.py','common/visual_question.py','common/voice_wake.py',
 'common/device_policy.py','common/device_memory.py','board/runtime/audio/voice_channel.py']
manifest={}
for n in names:
 p=A/n;src=C/n;backup=H/'before/aura'/n
 assert not backup.exists(), 'Already applied; inspect before retry'
 if p.exists():backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(p.read_bytes())
 manifest[n]={'before':hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None,'after':hashlib.sha256(src.read_bytes()).hexdigest()}
for n in names:
 p=A/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((C/n).read_bytes())
for p in (C/'skills').rglob('*'):
 if p.is_file():target=A/p.relative_to(C);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(p.read_bytes())
(H/'windows_applied.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps({'host_files':len(names),'models_copied':False,'services_restarted':False}))
