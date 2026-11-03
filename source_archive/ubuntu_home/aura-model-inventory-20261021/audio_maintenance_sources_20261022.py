import base64,gzip,hashlib,json,subprocess
from pathlib import Path
pid=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],timeout=3).decode().strip()
args=(Path('/proc')/pid/'cmdline').read_bytes().decode().split('\0')
config=Path(args[args.index('--config')+1]);value=json.loads(config.read_text());root=Path(value['runtime'])/'aura'
out={'scope':'Only explicit Python dependency sources; no configuration contents or identity/audio data',
 'supervisor_pid':int(pid),'root':str(root),'config_sha256':hashlib.sha256(config.read_bytes()).hexdigest(),'source':{},'missing':[]}
for name in ['tools/board_avatar_worker.py','tools/board_recording.py','tools/barge_in_capture.py','board/runtime/audio/echo_cancel.py','board/runtime/audio/channel_jobs.py']:
 p=root/name
 if not p.is_file():out['missing'].append(name);continue
 raw=p.read_bytes();assert len(raw)<=150000
 out['source'][name]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'gzbase64':base64.b64encode(gzip.compress(raw)).decode()}
print(json.dumps(out))
