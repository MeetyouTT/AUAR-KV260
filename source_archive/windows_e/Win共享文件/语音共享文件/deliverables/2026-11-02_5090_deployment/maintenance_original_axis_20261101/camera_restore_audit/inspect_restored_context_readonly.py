import hashlib,json,subprocess
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='903cfade-b93c-48fa-804e-379be1967313'
r=subprocess.run(['systemctl','show','aura-camera-ui.service','--property=MainPID,ActiveState,SubState,Job'],capture_output=True,text=True,timeout=4);assert r.returncode==0
unit=dict(x.split('=',1) for x in r.stdout.splitlines() if '=' in x);pid=int(unit['MainPID']);assert pid==79866
ops=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
configpath=ops/('native-run-903cfade-b93c-48fa-804e-379be1967313-'+str(pid))/'config.json'
raw=configpath.read_bytes();j=json.loads(raw)
p=ops/('pan-face-edge-v5/native-operator-v1/recovery-audit-'+str(pid)+'.json');araw=p.read_bytes();a=json.loads(araw)
cp=Path('/home/root/aura-native-live-20261024/candidates/native-r4-metrics-fix/state/native-protection-checkpoint.json')
marker=Path(str(cp)+'.native-consumed-c6c8baab1de423e27740137330f8315796a7778e36735c93a0c87f2a56029471')
mr=marker.read_bytes();md=json.loads(mr)
print(json.dumps({'unit':unit,'pid':pid,'birth_ticks':(Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()[19],'cmdline_sha256':hashlib.sha256((Path('/proc')/str(pid)/'cmdline').read_bytes()).hexdigest(),'run_config_path':str(configpath),'run_config_sha256':hashlib.sha256(raw).hexdigest(),'run_config_keys':list(j),'native_execution':j.get('native_execution'),'audit_path':str(p),'audit_sha256':hashlib.sha256(araw).hexdigest(),'audit_keys':list(a),'audit':{k:a.get(k) for k in ('status','checkpoint_sha256','checkpoint_unit_sha256','exact_seed_before_operator_request','previous_kernel_history')},'marker_sha256':hashlib.sha256(mr).hexdigest(),'marker_keys':list(md),'marker':{k:md.get(k) for k in ('schema','boot_id','pid','owner_pid','source_pid','checkpoint_sha256','birth_ticks','owner_birth_ticks','consumed_mono_ns')}}))
