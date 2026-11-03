"""Bounded post-rollback sampling; no control or display writes."""
import json,subprocess,time,urllib.request
from pathlib import Path
def cmd(args):return subprocess.check_output(args,text=True,timeout=3).strip()
def state():
 with urllib.request.build_opener(urllib.request.ProxyHandler({})).open('http://127.0.0.1:8783/api/state',timeout=1) as response:return json.load(response)
names=['aura-avatar-ui.service','aura-camera-ui.service','xserver-nodm.service']
before={name:cmd(['systemctl','show',name,'-p','MainPID','-p','ActiveState','-p','NRestarts']) for name in names}
log=Path('/var/log/Xorg.0.log');offset=log.stat().st_size;rows=[]
for i in range(7):
 s=state();v=s.get('avatar_display',{})
 rows.append({'page':s.get('ui_page'),'layer':s.get('ui_layer'),'phase':s.get('phase'),'error':s.get('error'),'frames':v.get('received'),'age_ms':v.get('age_ms'),'fps':v.get('fps')})
 if i<6:time.sleep(1)
after={name:cmd(['systemctl','show',name,'-p','MainPID','-p','ActiveState','-p','NRestarts']) for name in names}
assert before==after and all(row['page']=='main' and row['layer']=='presentation' and not row['error'] for row in rows)
assert rows[-1]['frames']>rows[0]['frames']
with log.open() as f:f.seek(offset);new=f.read()[-3000:]
print(json.dumps({'status':'PASS_POST_ROLLBACK_SOFTWARE_WINDOW','boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'units':after,'samples':rows,'new_xorg_log':new,'physical_panel_verified':False,'control_commands_sent':0,'movement_commands_sent':0}),flush=True)
