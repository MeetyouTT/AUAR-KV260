import hashlib,json,subprocess,urllib.request
from pathlib import Path
names=('aura-camera-ui.service','aura-avatar-ui.service','xserver-nodm.service')
out={'read_only':True,'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
out['services']={name:subprocess.check_output(['systemctl','show',name,'-p','MainPID','-p','ActiveState',
 '-p','SubState','-p','NRestarts','-p','Result','-p','ExecMainCode','-p','ExecMainStatus',
 '-p','ExecMainStartTimestampMonotonic','-p','ExecMainExitTimestampMonotonic'],timeout=5).decode().strip() for name in names}
r=subprocess.run(['journalctl','-u','aura-camera-ui.service','-n','45','-o','json','--no-pager'],
 stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=8)
events=[]
for line in r.stdout.splitlines():
 try:d=json.loads(line);s=d.get('MESSAGE','')
 except ValueError:continue
 if any(token in s.lower() for token in ('exited','failed','started','stopped','killed','segmentation','core-dump','traceback','error','exception','assertion','line ','restart','abort')):
  events.append({'mono_us':d.get('__MONOTONIC_TIMESTAMP'),'message':s[:700]})
out['camera_journal_returncode']=r.returncode;out['filtered_camera_events']=events
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8783/api/state',timeout=3) as response:ui=json.load(response)
out['ui']={k:ui.get(k) for k in ('phase','playing','paused','audio_output_state')}
out['unit_sha256']=hashlib.sha256(Path('/etc/systemd/system/aura-camera-ui.service').read_bytes()).hexdigest()
print(json.dumps(out))
