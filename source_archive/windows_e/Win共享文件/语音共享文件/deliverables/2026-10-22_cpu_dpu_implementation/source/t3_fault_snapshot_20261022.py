import json,subprocess,time,urllib.request
from pathlib import Path
out={'mono':time.monotonic()}
raw=subprocess.check_output(['journalctl','-k','-n','1000','-o','json','--no-pager'],timeout=6).decode()
rows=[]
for line in raw.splitlines():
 try:row=json.loads(line)
 except ValueError:continue
 if "WARN: HC couldn't access mem fast enough" in row.get('MESSAGE',''):
  rows.append({'mono_us':row.get('__MONOTONIC_TIMESTAMP'),'message':row['MESSAGE']})
out['last_1000_kernel_entries_matching_warnings']=len(rows)
out['first_matching_in_window']=rows[0] if rows else None
out['last_matching_in_window']=rows[-1] if rows else None
for name in ['aura-camera-ui.service','aura-avatar-ui.service','xserver-nodm.service','systemd-journald.service']:
 out[name]=subprocess.check_output(['systemctl','show',name,'-p','MainPID','-p','NRestarts','-p','ActiveState'],timeout=3).decode().strip()
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8783/api/state',timeout=3) as r:s=json.load(r)
out['ui']={k:s.get(k) for k in ['phase','playing','paused','audio_output_state']}
out['recording_state']=s.get('local_recording',{}).get('state')
out['pcm_status']={str(p):p.read_text()[:1000] for p in Path('/proc/asound').glob('card*/pcm*/sub*/status')}
out['timers']=subprocess.check_output(['systemctl','list-timers','--all','--no-pager','aura-sface-shadow-*'],timeout=3).decode().strip()
print(json.dumps(out))
