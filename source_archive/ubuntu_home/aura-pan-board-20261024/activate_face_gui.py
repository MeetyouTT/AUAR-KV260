"""Activate only the prepared GUI, preserving the camera and stopped axis."""
import hashlib,json,os,shutil,subprocess,time,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/463c9307');N=R/'gui-face-edge-v4';F=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v4');GUI='aura-avatar-ui.service'
DROP=Path('/etc/systemd/system/aura-avatar-ui.service.d/zzzzzzzzzzzzzzzzzzzzz-aura-face-edge-v4.conf')
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
def pid():return subprocess.check_output(['systemctl','show',GUI,'-p','MainPID','--value'],text=True).strip()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
s=json.loads((F/'stage-state.json').read_text());st=json.loads((N/'stage.json').read_text());u=get(8783,'/api/state');h=get(8790,'/health');m=u['manual_pan'];r=m['readback']
assert st['phase']=='PREPARED' and st['config_sha256']==sha(N/'startup/config.json') and st['launcher_sha256']==sha(N/'startup/launcher.py') and not DROP.exists()
assert h['pid']==s['camera_pid'] and pid()==str(s['gui_pid']) and u['phase']=='IDLE' and not u['playing']
assert m['state']=='READY' and r['flags']==0 and r['lease_left_ms']==0
subprocess.run(['systemctl','stop','--no-block',GUI],check=True);end=time.monotonic()+30
while time.monotonic()<end and pid()!='0':time.sleep(.2)
assert pid()=='0'
for p in (R/'gui-release/runtime').glob('*settings*.json'):
 if p.is_file():shutil.copy2(p,N/'runtime'/p.name)
raw=('[Service]\nExecStart=\nExecStart=/usr/bin/python3 -B '+str(N/'startup/launcher.py')+' --config '+str(N/'startup/config.json')+'\nWorkingDirectory='+str(N/'runtime/aura')+'\n').encode()
with DROP.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
subprocess.run(['systemctl','daemon-reload'],check=True);subprocess.run(['systemctl','start','--no-block',GUI],check=True)
end=time.monotonic()+110;ready=None
while time.monotonic()<end:
 try:
  u=get(8783,'/api/state');p=u.get('manual_pan',{})
  if u['phase']=='IDLE' and p.get('state')=='READY':ready=p;break
 except Exception:pass
 time.sleep(.5)
assert ready is not None,'GUI startup hold'
base='http://127.0.0.1:8783'
for typ in (['pan_reverse'] if ready['left_sign']==-1 else [])+['pan_dialog']:
 req=urllib.request.Request(base+'/api/command',data=json.dumps({'type':typ}).encode(),headers={'Origin':base,'Content-Type':'application/json'})
 with o.open(req,timeout=3) as r:assert json.load(r)['ok']
 time.sleep(.2)
assert get(8790,'/health')['pid']==h['pid']
s['gui_pid']=int(pid());(F/'stage-state.json').write_text(json.dumps(s,indent=2)+'\n');st.update(phase='READY',gui_pid=int(pid()),camera_pid=h['pid'],dropin=str(DROP),dropin_sha256=sha(DROP));(N/'stage.json').write_text(json.dumps(st,indent=2)+'\n')
print(json.dumps(dict(st,manual=get(8783,'/api/state')['manual_pan'],physical_commands=0),sort_keys=True))
