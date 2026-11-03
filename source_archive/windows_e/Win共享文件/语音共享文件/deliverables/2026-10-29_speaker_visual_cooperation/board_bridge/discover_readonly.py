"""Read current entry points and metadata only. Does not open identity templates."""
import datetime, hashlib, json, sys
from pathlib import Path
H=Path(__file__).resolve().parent
sys.path.insert(0,str(H.parents[1]/'2026-10-29_audio_animation_polish'))
from board_guard import capture,ssh

state=capture()
state_path=H/'board_preflight.json'
state_path.write_text(json.dumps(state,indent=2,ensure_ascii=False),encoding='utf-8')
script=r'''
import hashlib,json,subprocess
from pathlib import Path
def process(unit):
 info=dict(line.split('=',1) for line in subprocess.check_output(['systemctl','show',unit,'-p','MainPID','-p','ExecStart','-p','DropInPaths'],text=True).splitlines() if '=' in line)
 args=Path('/proc/'+info['MainPID']+'/cmdline').read_bytes().decode().split('\0')
 sources={}
 for arg in args:
  p=Path(arg)
  if p.is_file() and p.suffix in ('.py','.json'):
   raw=p.read_bytes();sources[str(p)]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
 return dict(unit=info,argv=args,sources=sources)
print(json.dumps({'camera':process('aura-camera-ui.service'),'readonly':True}))
'''
result=json.loads(ssh('python3 -B -',script,timeout=20))
result['checked_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
(H/'camera_entry.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({'runtime':state['actual_runtime'],'boot':state['boot'],'pins':len(state['pins']),
 'safe':state['safe'],'mismatches':state['mismatches'],'camera':result},ensure_ascii=True))
