import json,subprocess,time,urllib.request
from pathlib import Path
units={name:subprocess.check_output(['systemctl','show',name,'-p','MainPID','-p','NRestarts','-p','ActiveState'],timeout=3).decode().strip() for name in ('aura-camera-ui.service','aura-avatar-ui.service','xserver-nodm.service','systemd-journald.service')}
result={};start=time.monotonic()
try:
 raw=subprocess.check_output(['journalctl','-k','-n','1','-o','json','--no-pager'],timeout=10).decode();rows=[json.loads(x) for x in raw.splitlines() if x.strip()]
 result={'ok':True,'duration_seconds':time.monotonic()-start,'last_mono_us':rows[-1].get('__MONOTONIC_TIMESTAMP') if rows else None,'last_cursor':rows[-1].get('__CURSOR') if rows else None}
except Exception as exc:result={'ok':False,'error':type(exc).__name__+': '+str(exc),'duration_seconds':time.monotonic()-start}
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8790/health',timeout=3) as f:s=json.load(f)
print(json.dumps({'read_only':True,'units':units,'kernel_journal_probe':result,'camera_pid':s['pid'],'face_backend':s.get('identity',{}).get('face_targets',{}).get('backend'),'schedule':s.get('dpu_schedule')}))
