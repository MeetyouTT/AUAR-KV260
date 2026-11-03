import hashlib,json,subprocess,urllib.request
from pathlib import Path
root=Path('/home/root/aura-dpu-vision-20261021')
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='7924ac9f-311d-4fcd-98be-57bf023cf1aa'
p=Path('/home/root/aura-adaptation-20261006/identity_dpu_engineering_20261018/helpers/4260e299e8312129/source.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='4260e299e8312129b83a257030f99ebbf515c84cac47b33cf301e56f58455ee9'
launch=root/'postpower-metrics-launches/4260e299e8312129/launch-result.json';r=json.loads(launch.read_text())
assert r.get('error')=='AssertionError: YuNet baseline lost'
archive=launch.with_name('prelaunch-baseline-fault.json');assert not archive.exists();archive.write_bytes(launch.read_bytes())
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8790/health',timeout=3) as f:h=json.load(f)
assert h['identity']['face_targets']['backend']=='DPU_YUNET_INT8'
assert not h['dpu_schedule']['optional']['yunet']['overruns']
unit='aura-postpower-metrics-4260e299e8312129-relaunch'
subprocess.run(['systemd-run','--unit='+unit,'--property=RuntimeMaxSec=300','--setenv=AURA_RUN_POSTPOWER_METRICS=1','/usr/bin/python3','-B',str(p)],check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=8)
print(json.dumps({'started':True,'unit':unit,'baseline_pid':h['pid'],'old_prelaunch_failure_preserved':True}))
