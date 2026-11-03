import json,subprocess,time,urllib.request
from pathlib import Path
o=urllib.request.build_opener(urllib.request.ProxyHandler({}));rows=[]
for i in range(4):
 with o.open('http://127.0.0.1:8783/api/state',timeout=3) as r:u=json.load(r)
 row={k:u.get(k) for k in ('phase','playing','audio_output_state','audio_output_error','audio_error','error')}
 row['manual']=u['manual_pan'];row['top_keys']=list(u)
 rows.append(row)
 if i<3:time.sleep(1)
pcm=Path('/proc/asound/card1/pcm0p/sub0/status')
print(json.dumps({'samples':rows,'pcm':pcm.read_text()[:500] if pcm.exists() else 'missing',
 'gui_unit':subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ActiveState','-p','NRestarts'],text=True),
 'kernel_window':subprocess.check_output(['journalctl','-k','--since','8 seconds ago','-n','12','--no-pager','-o','cat'],text=True)[-2000:],
 'motor_commands_sent':0}))
