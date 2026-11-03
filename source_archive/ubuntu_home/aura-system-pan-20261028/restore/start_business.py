"""Restore the exact existing services, retaining all native recovery counters."""
import hashlib,json,subprocess,time,urllib.request
from pathlib import Path
R=Path('/home/root/aura-system-pan-20261028/restore-5f167a36');OPS=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
def get(port,path):
 o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
def pid(unit):return subprocess.check_output(['systemctl','show',unit,'-p','MainPID','--value'],text=True).strip()
s=json.loads((R/'state.json').read_text());assert s['phase']=='JOINT_FIRMWARE_ID_STOP_PASS'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==s['boot']
assert hashlib.sha256(Path('/home/root/aura-windows-portrait-20261027/handoff-31b0c262c5b74d52966c00b978dfef3f/startup/config.json').read_bytes()).hexdigest()=='3d84681a728617eea1cb28b619a376f9b3798a41c04d8fb57759947a3479294f'
assert pid('aura-camera-ui.service')=='0' and pid('aura-avatar-ui.service')=='0'
assert hashlib.sha256(Path(s['checkpoint']).read_bytes()).hexdigest()==s['checkpoint_sha256']
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==v for rows in s['units'].values() for p,v in rows.items())
assert hashlib.sha256(Path(s['database_path']).read_bytes()).hexdigest()==s['database_sha256']
subprocess.run(['systemctl','reset-failed','aura-camera-ui.service','aura-avatar-ui.service'],check=True)
subprocess.run(['systemctl','start','--no-block','aura-camera-ui.service'],check=True)
until=time.monotonic()+75;health=None
while time.monotonic()<until:
 try:
  h=get(8790,'/health');d=h['dpu_schedule'];i=h['identity']
  if h['pid']==int(pid('aura-camera-ui.service')) and d['native_critical'] and not d['owner_fenced'] and i['face_targets']['worker_alive'] and h['detected_frames']>=5:health=h;break
 except Exception:pass
 time.sleep(.5)
assert health is not None,'Native owner startup hold; no automatic kill'
b=s['counters_before'];assert d['primary_calls']>=b['primary_calls'] and d['primary_period_overruns']>=b['primary_overruns']
for k in ('yunet','sface'):assert d['optional'][k]['calls']>=b['optional'][k]['calls'] and d['optional'][k]['overruns']>=b['optional'][k]['overruns']
assert i['ready'], 'Identity not ready after preserved fresh checkpoint'
assert all(not d['optional'][k]['disabled'] for k in ('yunet','sface'))
assert i['feature_inference']['completed']>=b['sface_completed']
subprocess.run(['systemctl','start','--no-block','aura-avatar-ui.service'],check=True)
s.update(phase='JOINT_NATIVE_RUNNING_GUI_STARTING',current_camera_pid=h['pid'],sface_recovery_preserved=d['optional']['sface']['recovery']['phase'])
(R/'state.json').write_text(json.dumps(s,indent=2)+'\n')
print(json.dumps({'phase':s['phase'],'camera_pid':h['pid'],'gui_pid':pid('aura-avatar-ui.service'),'owner_fenced':False,'sface_phase':d['optional']['sface']['recovery']['phase'],'native_counters_preserved':True,'ARM_sent':False}))
