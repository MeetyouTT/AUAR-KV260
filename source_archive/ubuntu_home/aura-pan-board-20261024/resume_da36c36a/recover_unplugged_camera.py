import fcntl,hashlib,json,subprocess,time,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/da36c36a');O=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735');CAM='aura-camera-ui.service'
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip();assert boot=='da36c36a-ef4d-4122-8ad6-cfae3931303e'
def props():
 raw=subprocess.check_output(['systemctl','show',CAM,'-p','MainPID','-p','ActiveState','-p','ExecStart'],text=True)
 return dict(x.split('=',1) for x in raw.splitlines() if '=' in x)
assert props()['MainPID']=='0' and not Path('/proc/54394').exists()
meta=json.loads((O/'meta.json').read_text());cfg=json.loads(Path(meta['candidate_config']).read_text());path=Path(cfg['native_execution']['checkpoint_output']);raw=path.read_bytes();cp=json.loads(raw)
x=cp['seed'];a=cp['auxiliary'];assert cp['schema']=='aura-native-protection-checkpoint-2' and cp['scope']=='final_quiescent_before_native_owner_close'
assert x['boot_id']==boot and x['source_pid']==54394 and x['source_birth_ticks']==524853 and x['checkpoint_kind']==1
assert cp['source_unit_sha256']=='7cf7eaeecd70e62301d3e12e95d5df6a23bd3e5847ed854200c712598b703c32'
assert not x['fenced'] and not a['fenced'] and not a['active'] and not a['primary_waiting'] and not any(a['pending_result_tokens'])
assert x['primary_period_overruns']>=2 and x['overruns'][1:]==[0,0]
source=O/'pan-face-edge-v5/face-source-v17';manifest=json.loads((source/'deployment-manifest.json').read_text())
assert hashlib.sha256((source/'deployment-manifest.json').read_bytes()).hexdigest()=='84d7359f18a5a98aa5dabba967c4ededf5e35d0c43153166fc6998729a30219c'
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in manifest['pins'].items())
assert str(source/'entry.py') in props()['ExecStart']
with (O/'operation.lock').open('a+') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 with Path('/run/aura-person-dpu.lock').open('a+') as dpu:
  fcntl.flock(dpu,fcntl.LOCK_EX|fcntl.LOCK_NB);assert Path('/sys/module/zocl/refcnt').read_text().strip()=='0' and props()['MainPID']=='0'
  with (R/'camera-unplug-quiescent-checkpoint.json').open('xb') as f:f.write(raw)
 subprocess.run(['systemctl','reset-failed',CAM],check=True,timeout=5)
 subprocess.run(['systemctl','start','--no-block',CAM],check=True,timeout=5)
o=urllib.request.build_opener(urllib.request.ProxyHandler({}));end=time.monotonic()+40;health=None
while time.monotonic()<end:
 try:
  with o.open('http://127.0.0.1:8790/health',timeout=2) as f:h=json.load(f)
  if h['pid']==int(props()['MainPID']) and h['pid']!=54394 and h['detected_frames']>=3:
   health=h;break
 except Exception:pass
 time.sleep(.3)
assert health is not None,'Camera startup not confirmed; do not kill native owner'
d=health['dpu_schedule'];assert not d['owner_fenced'] and d['seed_loaded'] and d['primary_calls']>=x['primary_calls'] and d['primary_period_overruns']>=x['primary_period_overruns']
for index,name in ((1,'yunet'),(2,'sface')):assert d['optional'][name]['overruns']>=x['overruns'][index] and d['optional'][name]['calls']>=x['admissions'][index]
s=json.loads((R/'state.json').read_text());s.update(phase='CAMERA_RECONNECTED_NATIVE_HISTORY_PRESERVED',current_camera_pid=health['pid'],automatic_following=False)
(R/'state.json').write_text(json.dumps(s,indent=2)+'\n')
print(json.dumps({'status':s['phase'],'camera_pid':health['pid'],
 'primary_overruns':d['primary_period_overruns'],'optional_overruns':{k:v['overruns'] for k,v in d['optional'].items()},
 'protection_handoff':d['protection_handoff'],'checkpoint_sha256':hashlib.sha256(raw).hexdigest(),'motor_commands':0}))
