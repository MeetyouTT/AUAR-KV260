"""Stage one uniquely owned camera ExecStart override; do not restart."""
import hashlib,json,os,subprocess,urllib.request
from pathlib import Path
ops=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735');sh=ops/'pan-face-edge-v1'
entry=ops/'native_entry_pan_face_v1.py';drop=Path('/etc/systemd/system/aura-camera-ui.service.d/zzzzzzzzzzzzzz-aura-pan-face-v1.conf')
boot='463c9307-5e47-49b0-b22f-5fd3fc21451c';assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==boot
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def get(port,path):
 o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
def props(unit):
 x=subprocess.check_output(['systemctl','show',unit,'-p','MainPID','-p','ActiveState','-p','SubState','-p','Restart','-p','KillMode','-p','SendSIGKILL','-p','TimeoutStopUSec'],text=True)
 return dict(q.split('=',1) for q in x.splitlines() if '=' in q)
m=json.loads((sh/'deployment-manifest.json').read_text());pin=m.pop('manifest_sha256')
assert hashlib.sha256(json.dumps(m,sort_keys=True,separators=(',',':')).encode()).hexdigest()==pin
for f in m['files']:assert Path(f['destination']).is_file() and sha(f['destination'])==f['sha256']
c=props('aura-camera-ui.service');g=props('aura-avatar-ui.service');assert c['MainPID']=='27275' and c['ActiveState']=='active' and c['Restart']=='no' and c['KillMode']=='process' and c['SendSIGKILL']=='no' and c['TimeoutStopUSec']=='infinity'
h=get(8790,'/health');u=get(8783,'/api/state');p=u.get('manual_pan',{});r=p.get('readback',{})
assert str(h['pid'])==c['MainPID'] and h['dpu_schedule']['native_critical'] and not h['dpu_schedule']['owner_fenced'] and h['identity']['face_targets']['worker_alive']
assert u['phase']=='IDLE' and not u.get('playing') and u.get('audio_output_state')=='IDLE_READY' and g['ActiveState']=='active'
assert p.get('state') not in ('MOVING','STOPPING','CONNECTING') and not p.get('automatic_following')
assert not drop.exists() and not (sh/'stage-state.json').exists()
checks=[(str(entry),sha(entry))]+[(f['destination'],f['sha256']) for f in m['files']]+[(str(sh/'deployment-manifest.json'),sha(sh/'deployment-manifest.json'))]
code="import hashlib;checks="+repr(checks)+";assert all(hashlib.sha256(open(p,'rb').read()).hexdigest()==h for p,h in checks)"
raw=('[Service]\nExecStart=\nExecStartPre=/usr/bin/python3 -B -c "'+code+'"\nExecStart=/usr/bin/python3 -B '+str(entry)+'\n').encode()
with drop.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
try:
 subprocess.run(['systemctl','daemon-reload'],check=True,timeout=15)
 q=props('aura-camera-ui.service');shown=subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','LoadState','-p','LoadError','-p','ExecStart','-p','ExecStartPre'],text=True)
 assert q['MainPID']==c['MainPID'] and q['ActiveState']=='active' and 'LoadState=loaded' in shown and 'LoadError=' in shown and entry.name in shown
 state={'phase':'DROPIN_STAGED_NO_RESTART','boot':boot,'camera_pid_before':int(c['MainPID']),'gui_pid':int(g['MainPID']),'dropin':str(drop),'dropin_sha256':sha(drop),'entry_sha256':sha(entry),'manual_state':p.get('state'),'pan_panel_open':p.get('panel_open')}
 with (sh/'stage-state.json').open('x') as f:json.dump(state,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 print(json.dumps(state,sort_keys=True))
except BaseException:
 if drop.is_file() and sha(drop)==hashlib.sha256(raw).hexdigest():drop.unlink();subprocess.run(['systemctl','daemon-reload'],timeout=15)
 raise
