import json,subprocess,time,urllib.request
from pathlib import Path
op=urllib.request.build_opener(urllib.request.ProxyHandler({}));rows=[]
for _ in range(3):
 raw=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ControlPID','-p','ActiveState','-p','SubState','-p','Result','-p','ExecMainStatus'],text=True)
 row=dict(x.split('=',1) for x in raw.splitlines() if '=' in x)
 try:
  with op.open('http://127.0.0.1:8783/api/state',timeout=2) as response:u=json.load(response)
  row['ui_ready']=True;row['manual_state']=u['manual_pan']['state'];row['automatic_following']=u['manual_pan']['automatic_following'];row['audio_state']=u.get('audio_output_state')
 except Exception as error:row['ui_ready']=False;row['error_type']=type(error).__name__
 rows.append(row)
 if row['ui_ready']:break
 time.sleep(5)
print(json.dumps({'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'samples':rows,'service_changes':0,'motor_commands':0}))
