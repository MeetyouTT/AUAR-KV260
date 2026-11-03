"""Read failure state and request STOP via the existing owner; never arms."""
import json,subprocess,time,urllib.request
from pathlib import Path
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def api(data=None):
 url='http://127.0.0.1:8783'
 req=url+'/api/state' if data is None else urllib.request.Request(url+'/api/command',data=json.dumps(data).encode(),headers={'Content-Type':'application/json','Origin':url})
 try:
  with opener.open(req,timeout=.6) as r:v=json.load(r)
  return {k:v.get(k) for k in ['phase','playing','ui_page','manual_pan','ui_tick_ms','sequence']} if data is None else v
 except Exception as e:return {'unavailable':type(e).__name__}
value={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'before':api(),'stop_request':api({'type':'pan_stop'}),'units':{},'processes':[]}
time.sleep(.15);value['after']=api()
for u in ['aura-avatar-ui.service','aura-camera-ui.service']:
 value['units'][u]={k:subprocess.check_output(['systemctl','show',u,'-p',k,'--value'],text=True).strip() for k in ['ActiveState','MainPID','WorkingDirectory','ExecStart']}
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  args=(p/'cmdline').read_bytes()
  if b'/tools/board_avatar_pan.py' not in args:continue
  threads=[]
  for t in (p/'task').iterdir():threads.append({'tid':t.name,'name':(t/'comm').read_text().strip(),'wchan':(t/'wchan').read_text().strip()})
  value['processes'].append({'pid':p.name,'threads':threads})
 except OSError:pass
root=Path(value['units']['aura-avatar-ui.service']['WorkingDirectory']).parent
try:
 lines=(root/'stage.log').read_text(errors='replace').splitlines()[-160:]
 value['error_lines']=[s for s in lines if any(w in s for w in ['Traceback','manual.py','manual_vsrv.py','pan_controls.py','Error:','Exception:'])][-30:]
except OSError:pass
print(json.dumps(value),flush=True)
