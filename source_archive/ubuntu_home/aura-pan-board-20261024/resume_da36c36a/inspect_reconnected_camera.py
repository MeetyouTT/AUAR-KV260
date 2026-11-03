import fcntl,json,os,subprocess,urllib.request
from pathlib import Path
O=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735');meta=json.loads((O/'meta.json').read_text())
cfg=json.loads(Path(meta['candidate_config']).read_text());cp=Path(cfg['native_execution']['checkpoint_output'])
units={}
for name in ('aura-camera-ui.service','aura-avatar-ui.service'):
 raw=subprocess.run(['systemctl','show',name,'-p','MainPID','-p','ActiveState','-p','SubState','-p','Result','-p','ExecMainStatus','-p','ExecMainCode'],capture_output=True,text=True,timeout=3)
 units[name]=dict(x.split('=',1) for x in raw.stdout.splitlines() if '=' in x)
lock_free=False
with Path('/run/aura-person-dpu.lock').open('a+') as lock:
 try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);lock_free=True
 except BlockingIOError:pass
checkpoint=json.loads(cp.read_text()) if cp.exists() else None
j=subprocess.run(['journalctl','-u','aura-camera-ui.service','-n','70','--no-pager','-o','cat'],capture_output=True,text=True,timeout=4)
lines=[x for x in j.stdout.splitlines() if any(k in x.lower() for k in ('traceback','error','checkpoint','quiescen','native owner','exception','camera','failed','terminated'))]
o=urllib.request.build_opener(urllib.request.ProxyHandler({}));reach={}
for port,path,name in ((8790,'/health','camera'),(8783,'/api/state','gui')):
 try:
  with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=2) as f:d=json.load(f)
  reach[name]={'reachable':True}
  if name=='gui':reach[name].update(manual=d['manual_pan'],phase=d['phase'])
 except Exception as e:reach[name]={'reachable':False,'error_type':type(e).__name__}
print(json.dumps({'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'units':units,'dpu_lock_free':lock_free,
 'zocl_refcnt':Path('/sys/module/zocl/refcnt').read_text().strip(),'prior_camera_process_exists':Path('/proc/54394').exists(),
 'checkpoint_path':str(cp),'checkpoint':checkpoint,'filtered_camera_errors':lines[-20:],'endpoints':reach,
 'camera_devices':[str(x) for x in Path('/dev').glob('video*')],'motor_commands':0,'MMIO_opened':False}))
