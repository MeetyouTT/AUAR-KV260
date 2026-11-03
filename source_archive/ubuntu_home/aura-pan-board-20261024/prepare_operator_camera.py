"""Verify staged ABI-compatible operator release without restarting services."""
import hashlib,json,os,subprocess,urllib.request
from pathlib import Path
OPS=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735');R=OPS/'pan-face-edge-v5/native-operator-v1'
manifest=R/'runtime-manifest.json';assert hashlib.sha256(manifest.read_bytes()).hexdigest()=='74e011db30a9d943a9512f7648190ac0c01060af06df1280d1e8ea006dc882ad'
assert all(hashlib.sha256(Path(n).read_bytes()).hexdigest()==h for n,h in json.loads(manifest.read_text())['files'].items())
assert not (R/'stage-state.json').exists()
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8790/health',timeout=3) as response:h=json.load(response)
with op.open('http://127.0.0.1:8783/api/state',timeout=3) as response:u=json.load(response)
camera=int(subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','MainPID','--value'],text=True))
gui=int(subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True))
assert camera==h['pid']==66241 and not h['dpu_schedule']['owner_fenced'] and gui==76450
p=u['manual_pan'];assert p['state']=='READY' and not p['automatic_following'] and p['readback']['flags']==0 and p['readback']['lease_left_ms']==0
old=os.sched_getscheduler(0);param=os.sched_getparam(0)
try:os.sched_setscheduler(0,os.SCHED_FIFO,os.sched_param(10))
finally:os.sched_setscheduler(0,old,param)
state={'phase':'PREPARED','boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'camera_pid_before':camera,'gui_pid':gui,
 'runtime_manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),'register_writes':0}
(R/'stage-state.json').write_text(json.dumps(state,indent=2)+'\n');print(json.dumps(state))
