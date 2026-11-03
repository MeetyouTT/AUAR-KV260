"""Read current running entry and redacted voice diagnostics; no device actions."""
import datetime,hashlib,json,sys,urllib.request
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parents[1]
sys.path.insert(0,str(P/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
assert not (H/'board_snapshot.json').exists(),'Preserve the original fault snapshot'
script=r'''
import hashlib,json,re,subprocess,urllib.request
from pathlib import Path
def unit(name):
 raw=subprocess.check_output(['systemctl','show',name,'-p','MainPID','-p','ExecStart','-p','NRestarts','-p','ActiveState'],text=True)
 return dict(line.split('=',1) for line in raw.splitlines() if '=' in line)
ui=unit('aura-avatar-ui.service');camera=unit('aura-camera-ui.service');pid=ui['MainPID']
args=Path('/proc/'+pid+'/cmdline').read_bytes().decode().split('\0')
assert '--config' in args
path=Path(args[args.index('--config')+1]);cfg=json.loads(path.read_text());root=Path(cfg['runtime'])/'aura'
pins=cfg['component_sha256']
bad=[name for name,digest in pins.items() if hashlib.sha256((root/name).read_bytes()).hexdigest()!=digest]
assert not bad
names=[name for name in pins if name.endswith('.py') and (
 any(word in name for word in ('barge','echo_cancel','voice_first','handsfree_recording','alsa_output','streaming_controller','automatic_capture'))
 or name in ('board/runtime/audio/output.py','board/runtime/audio/player.py','board/runtime/audio/channel_jobs.py','common/handsfree_entry.py'))]
files={name:(root/name).read_bytes().decode('utf-8') for name in names}
with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4) as response:s=json.load(response)
def redact(value,key=''):
 if isinstance(value,dict):return {k:redact(v,k) for k,v in value.items()}
 if isinstance(value,list):return [redact(v,key) for v in value[-40:]]
 if isinstance(value,str) and re.search(r'text|transcript|reply|summary|caption|utterance|prompt|name|identity',key,re.I):
  return {'characters':len(value),'sha256':hashlib.sha256(value.encode()).hexdigest()}
 return value
keys=('phase','playing','error','audio_output_state','handsfree_dialogue','voice_barge_in','automatic_conversation',
      'local_transcription','local_recording','generation','audio_frontend','voice_playback','speech_motion')
state=redact({k:s.get(k) for k in keys})
state['manual_pan']={k:s.get('manual_pan',{}).get(k) for k in ('state','automatic_following','busy','moving','active_motion','motion_active')}
print(json.dumps({'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'running_config':str(path),'config_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
 'runtime':str(root.parent),'pins':pins,'ui':ui,'camera':camera,'state':state,'state_keys':sorted(s),
 'files':files,'private_audio_exported':False,'actions_performed':False},ensure_ascii=True))
'''
data=json.loads(ssh('python3 -B -',script,timeout=25));files=data.pop('files')
for name,source in files.items():
 path=H/'board_source'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(source.encode('utf-8'))
 assert hashlib.sha256(path.read_bytes()).hexdigest()==data['pins'][name],name
data['source_files']=list(files);data['checked_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
(H/'board_snapshot.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
with urllib.request.urlopen('http://192.168.50.1:8792/health',timeout=5) as response:v=json.load(response)
health={k:v.get(k) for k in ('ready','busy','service_revision','source_fingerprint','voice_request_diagnostics')}
(H/'voice_health.json').write_text(json.dumps(health,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'runtime':data['runtime'],'running_config':data['running_config'],'ui_pid':data['ui']['MainPID'],
 'source_files':len(files),'state':data['state'],'voice_health':health},ensure_ascii=True))
