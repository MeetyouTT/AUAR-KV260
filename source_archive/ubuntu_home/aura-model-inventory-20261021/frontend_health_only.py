"""Query the configured frontend health endpoint without sending audio."""
import json,subprocess,sys
from pathlib import Path
pid=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True).strip()
args=Path('/proc/'+pid+'/cmdline').read_bytes().decode().split('\0')
cfg=Path(args[args.index('--config')+1]);r=Path(json.loads(cfg.read_text())['runtime'])
if r.name!='aura':r=r/'aura'
sys.path.insert(0,str(r))
from board.runtime.audio.remote_frontend import health
config=json.loads((r/'config/board_avatar_gtk.json').read_text())['audio_frontend']
out={'config':config,'sent_audio':False}
try:out['health']=health(config)
except Exception as e:out['health']={'error':type(e).__name__,'detail':str(e)}
print(json.dumps(out),flush=True)
