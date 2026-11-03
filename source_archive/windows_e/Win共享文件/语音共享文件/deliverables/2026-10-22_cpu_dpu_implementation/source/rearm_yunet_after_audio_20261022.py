import hashlib,json,subprocess,time,urllib.request
from pathlib import Path
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with op.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
unit=Path('/etc/systemd/system/aura-camera-ui.service')
assert hashlib.sha256(unit.read_bytes()).hexdigest()=='84116d8faf6f4d3972f5f2eac35f8c98cf8ecbe51752a8f78d803aa8a7cdd75c'
ui=get(8783,'/api/state');assert ui['phase']=='IDLE' and not ui['playing'] and ui['audio_output_state']=='IDLE_READY'
assert ui['local_recording']['state']=='IDLE'
now=time.monotonic();rows=subprocess.check_output(['journalctl','-k','-n','1000','-o','json','--no-pager'],timeout=6).decode()
recent=[]
for line in rows.splitlines():
 try:r=json.loads(line)
 except ValueError:continue
 if "HC couldn't access mem fast enough for slot 4 ep 3" in r.get('MESSAGE','') and now-int(r['__MONOTONIC_TIMESTAMP'])/1e6<30:recent.append(r)
assert not recent,'USB audio still faulting; refuse camera rearm'
before=get(8790,'/health');assert before['pid']==188288
protected={n:subprocess.check_output(['systemctl','show',n,'-p','MainPID','--value'],timeout=3).decode().strip() for n in ['aura-avatar-ui.service','xserver-nodm.service']}
subprocess.run(['systemctl','restart','--no-block','aura-camera-ui.service'],check=True,timeout=5)
after=None
for _ in range(50):
 try:
  s=get(8790,'/health')
  if s['pid']!=before['pid'] and s.get('identity',{}).get('face_targets',{}).get('backend')=='DPU_YUNET_INT8':after=s;break
 except Exception:pass
 time.sleep(.4)
assert after is not None,'Camera DPU face backend did not become ready'
assert hashlib.sha256(unit.read_bytes()).hexdigest()=='84116d8faf6f4d3972f5f2eac35f8c98cf8ecbe51752a8f78d803aa8a7cdd75c'
for n,pid in protected.items():assert subprocess.check_output(['systemctl','show',n,'-p','MainPID','--value'],timeout=3).decode().strip()==pid
print(json.dumps({'scope':'Restart same retained camera unit after audio recovered; reset prior optional-disabled state',
 'before_pid':before['pid'],'after_pid':after['pid'],'ui_xserver_pids_preserved':protected,
 'backend':after['identity']['face_targets']['backend'],'schedule':after.get('dpu_schedule')}))
