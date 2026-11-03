import fcntl,json,subprocess,time,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/da36c36a');G=R/'gui-reference-bound-v2'
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=2) as f:return json.load(f)
def props():
 raw=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ExecStart','-p','ActiveState'],text=True)
 return dict(x.split('=',1) for x in raw.splitlines() if '=' in x)
h=get(8790,'/health');before=props();assert not h['dpu_schedule']['owner_fenced'] and str(G/'startup/config.json') in before['ExecStart']
cam_pid=h['pid'];cfg=json.loads((G/'runtime/aura/config/pan_face.local.json').read_text())
assert cfg['manifest_sha256']=='524ad777aec14dc2d853708412bcef4f75e1e6937d528674cc154b361b8ce76d'
with Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/operation.lock').open('a+') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 subprocess.run(['systemctl','stop','--no-block','aura-avatar-ui.service'],check=True,timeout=5)
 end=time.monotonic()+35
 while time.monotonic()<end and props()['MainPID']!='0':time.sleep(.2)
 assert props()['MainPID']=='0','GUI stop not confirmed'
 assert get(8790,'/health')['pid']==cam_pid
 subprocess.run(['systemctl','start','--no-block','aura-avatar-ui.service'],check=True,timeout=5)
s=json.loads((R/'state.json').read_text());s.update(phase='GUI_RECONNECTING_TO_RECOVERED_CAMERA',current_camera_pid=cam_pid,automatic_following=False)
(R/'state.json').write_text(json.dumps(s,indent=2)+'\n')
print(json.dumps({'status':s['phase'],'previous_gui_pid':before['MainPID'],'gui_pid':props()['MainPID'],
 'camera_pid':cam_pid,'camera_not_restarted':True,'recenter_controller_preserved':True,'motor_commands':0}))
