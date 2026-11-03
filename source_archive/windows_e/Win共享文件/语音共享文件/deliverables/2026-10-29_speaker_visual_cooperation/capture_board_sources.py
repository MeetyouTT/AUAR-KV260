"""Only read two current pinned transport modules; no runtime mutation."""
import base64,hashlib,json,sys
from pathlib import Path
H=Path(__file__).resolve().parent
sys.path.insert(0,str(H.parent/'2026-10-29_audio_animation_polish'))
from board_guard import capture,ssh
b=capture();assert not b['mismatches']
names=('board/runtime/audio/channel_jobs.py','board/runtime/audio/voice_channel.py')
script=r'''
import base64,hashlib,json
from pathlib import Path
root=Path(ROOT)/'aura';out={}
for name in NAMES:
 raw=(root/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==PINS[name],name
 out[name]=base64.b64encode(raw).decode()
print(json.dumps(out))
'''.replace('ROOT',repr(b['actual_runtime'])).replace('NAMES',repr(names)).replace('PINS',repr(b['pins']))
files=json.loads(ssh('python3 -B -',script,timeout=20))
for name,encoded in files.items():
 raw=base64.b64decode(encoded)
 for directory in ('board_source','candidate'):
  path=H/directory/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
(H/'board_baseline.json').write_text(json.dumps({'runtime':b['actual_runtime'],'boot':b['boot'],
 'ui_pid':b['ui']['MainPID'],'pins':{n:b['pins'][n] for n in names},'source_byte_checked':True,'read_only':True},indent=2),encoding='utf-8')
print(json.dumps({'status':'PASS','runtime':b['actual_runtime'],'files':list(files),'read_only':True}))
