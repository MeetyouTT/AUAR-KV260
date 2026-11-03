"""Archive only the copied log pointer, then start the prepared GUI."""
import json,subprocess,time,urllib.request
from pathlib import Path
N=Path('/home/root/aura-pan-current-20261024/463c9307/gui-face-edge-v5');F=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5');GUI='aura-avatar-ui.service'
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=2) as r:return json.load(r)
assert subprocess.check_output(['systemctl','show',GUI,'-p','MainPID','--value'],text=True).strip()=='0'
p=N/'runtime/stage.log';assert p.is_symlink() and str(p.resolve()).startswith('/home/root/aura-pan-current-20261024/463c9307/gui-release/runtime/managed-runs/')
backup=p.with_name('stage.log.copied-from-manual');assert not backup.exists();p.rename(backup)
b=get(8790,'/health');subprocess.run(['systemctl','reset-failed',GUI],check=True);subprocess.run(['systemctl','start','--no-block',GUI],check=True)
end=time.monotonic()+100;ready=None
while time.monotonic()<end:
 try:
  u=get(8783,'/api/state');m=u.get('manual_pan',{})
  if u['phase']=='IDLE' and m.get('state')=='READY':ready=u;break
 except Exception:pass
 time.sleep(.4)
if ready is None:
 print(json.dumps({'status':'GUI_HOLD','new_log':p.read_text()[-4000:] if p.exists() else None}));raise SystemExit(2)
base='http://127.0.0.1:8783'
for typ in (['pan_reverse'] if ready['manual_pan']['left_sign']==-1 else [])+['pan_dialog']:
 req=urllib.request.Request(base+'/api/command',data=json.dumps({'type':typ}).encode(),headers={'Origin':base,'Content-Type':'application/json'})
 with o.open(req,timeout=3) as r:assert json.load(r)['ok']
 time.sleep(.2)
a=get(8790,'/health');assert a['pid']==b['pid'];pid=int(subprocess.check_output(['systemctl','show',GUI,'-p','MainPID','--value'],text=True))
s=json.loads((F/'stage-state.json').read_text());s['gui_pid']=pid;(F/'stage-state.json').write_text(json.dumps(s,indent=2)+'\n')
st=json.loads((N/'stage.json').read_text());st.update(phase='READY',gui_pid=pid,camera_pid=a['pid']);(N/'stage.json').write_text(json.dumps(st,indent=2)+'\n')
print(json.dumps({'status':'FACE_GUI_READY','gui_pid':pid,'camera_pid':a['pid'],'manual':get(8783,'/api/state')['manual_pan'],'automatic_commands_sent':0}))
