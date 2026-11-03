"""Current running sources, redacted turn timings and bounded audio stderr."""
import datetime,hashlib,json,sys
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parents[1]
sys.path.insert(0,str(P/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
assert not (H/'baseline.json').exists()
script=r'''
import hashlib,json,re,subprocess,urllib.request
from pathlib import Path
def unit(name):
 raw=subprocess.check_output(['systemctl','show',name,'-p','MainPID','-p','ExecStart','-p','NRestarts','-p','ActiveState'],text=True)
 return dict(line.split('=',1) for line in raw.splitlines() if '=' in line)
ui=unit('aura-avatar-ui.service');camera=unit('aura-camera-ui.service');pid=ui['MainPID']
args=Path('/proc/'+pid+'/cmdline').read_bytes().decode().split('\0');path=Path(args[args.index('--config')+1]);cfg=json.loads(path.read_text())
root=Path(cfg['runtime'])/'aura';pins=cfg['component_sha256']
assert not [name for name,sha in pins.items() if hashlib.sha256((root/name).read_bytes()).hexdigest()!=sha]
names=[name for name in pins if name in ('tools/gstreamer_audio.py','tools/gstreamer_audio_worker.py','tools/gstreamer_persistent_engine.py',
 'tools/realtime_audio.py','tools/streaming_controller.py','tools/realtime_controller.py','tools/motion_queue.py',
 'tools/board_avatar_gtk.py','board/runtime/avatar_actions.py','common/speech_motion.py','board/runtime/avatar_assets.py',
 'board/runtime/fsm.py','board/runtime/audio/channel_jobs.py','tools/portrait_renderer.py','common/portrait_wire.py')]
files={name:(root/name).read_bytes().decode('utf-8') for name in names}
def redact(v,key=''):
 if isinstance(v,dict):return {k:redact(value,k) for k,value in v.items()}
 if isinstance(v,list):return [redact(value,key) for value in v[-40:]]
 if isinstance(v,str) and re.search(r'text|transcript|reply|summary|caption|utterance|prompt|name|identity',key,re.I):
  return {'characters':len(v),'sha256':hashlib.sha256(v.encode()).hexdigest()}
 return v
with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4) as response:s=json.load(response)
keys=('phase','state','display_state','asset','index','error','playing','audio_output_state','audio_time','duration',
 'generation','turns','log','metrics','handsfree_dialogue','voice_barge_in','automatic_conversation',
 'speech_motion','portrait_offload','ui_runtime','ui_tick_ms','avatar_display','manual_pan')
state=redact({k:s.get(k) for k in keys})
processes=[];todo=[pid];seen=set()
while todo and len(seen)<24:
 p=todo.pop(0)
 if p in seen:continue
 seen.add(p)
 try:
  argv=Path('/proc/'+p+'/cmdline').read_bytes().decode().split('\0');children=Path('/proc/'+p+'/task/'+p+'/children').read_text().split();todo+=children
  processes.append({'pid':p,'arguments':argv})
 except OSError:pass
print(json.dumps({'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'runtime':str(root.parent),
 'running_config':str(path),'config':cfg,'config_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'pins':pins,
 'ui':ui,'camera':camera,'state':state,'processes':processes,'files':files,'readonly':True},ensure_ascii=True))
'''
data=json.loads(ssh('python3 -B -',script,timeout=25));files=data.pop('files')
for name,source in files.items():
 path=H/'board_source'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(source.encode('utf-8'))
 assert hashlib.sha256(path.read_bytes()).hexdigest()==data['pins'][name]
data['checked_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
(H/'baseline.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'runtime':data['runtime'],'ui_pid':data['ui']['MainPID'],'config_keys':list(data['config']),
 'state':data['state'],'processes':data['processes'],'source_files':list(files)},ensure_ascii=True))
