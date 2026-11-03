"""Use tests matching the actual pinned board, not an older Windows fixture."""
import hashlib,json,sys
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parents[1]
sys.path.insert(0,str(P/'deliverables/2026-10-18_board_dialogue'));from board_ssh import ssh
b=json.loads((H/'baseline.json').read_text(encoding='utf-8'))
names=['tests/framework/'+name for name in ('test_persistent_audio.py','test_gstreamer_audio.py','test_voice_barge_in.py',
 'test_barge_verification.py','test_channel_jobs.py','test_automatic_conversation.py')]
script=r'''
import hashlib,json
from pathlib import Path
root=Path(ROOT)/'aura';pins=PINS
files={}
for name in NAMES:
 raw=(root/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==pins[name],name
 files[name]={'sha256':pins[name],'text':raw.decode('utf-8')}
p=root.parent/'deliverables/2026-10-06_avatar_reuse/preview_script.py';raw=p.read_bytes()
files['preview_script.py']={'sha256':hashlib.sha256(raw).hexdigest(),'text':raw.decode('utf-8')}
print(json.dumps(files,ensure_ascii=True))
'''.replace('ROOT',repr(b['runtime'])).replace('PINS',repr(b['pins'])).replace('NAMES',repr(names))
files=json.loads(ssh('python3 -B -',script,timeout=25))
for name,value in files.items():
 path=H/'effective_tests'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(value['text'].encode('utf-8'))
 assert hashlib.sha256(path.read_bytes()).hexdigest()==value['sha256']
(H/'effective_test_sources.json').write_text(json.dumps({name:value['sha256'] for name,value in files.items()},indent=2),encoding='utf-8')
print(json.dumps({'effective_test_files':len(files),'pins_verified':True}))
