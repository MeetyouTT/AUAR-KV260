"""Accept a fresh exact-owner checkpoint before the new protected entry starts."""
import hashlib,json
from pathlib import Path
import subprocess
OPS=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735');SH=OPS/'pan-face-edge-v5/face-source-v14';CAM='aura-camera-ui.service'
def props():
 x=subprocess.check_output(['systemctl','show',CAM,'-p','MainPID','-p','Result','-p','ExecMainStatus'],text=True)
 return dict(a.split('=',1) for a in x.splitlines() if '=' in a)
s=json.loads((SH/'stage-state.json').read_text());boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert s['phase']=='CAMERA_STOPPED_AWAIT_CHECKPOINT' and s['boot']==boot and props()=={'MainPID':'0','Result':'success','ExecMainStatus':'0'}
pid=s['stop_source_pid'];birth=s['stop_source_birth_ticks']
if (Path('/proc')/str(pid)/'stat').exists():assert int((Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()[19])!=birth
assert Path('/sys/module/zocl/refcnt').read_text().strip()=='0'
meta=json.loads((OPS/'meta.json').read_text());cfg=json.loads(Path(meta['candidate_config']).read_text());cp=Path(cfg['native_execution']['checkpoint_output'])
d=json.loads(cp.read_text());x=d['seed'];a=d['auxiliary'];b=s['counters_before']
assert d['schema']=='aura-native-protection-checkpoint-2' and d['scope']=='final_quiescent_before_native_owner_close'
assert x['boot_id']==boot and x['source_pid']==pid and x['source_birth_ticks']==birth and x['checkpoint_kind']==1 and not x['fenced']
assert not a['fenced'] and not a['active'] and not a['primary_waiting'] and not any(a['pending_result_tokens'])
assert x['primary_calls']>=b['primary_calls'] and x['primary_period_overruns']>=b['primary_overruns']
for n,k in ((1,'yunet'),(2,'sface')):assert x['admissions'][n]>=b['optional'][k]['calls'] and x['overruns'][n]>=b['optional'][k]['overruns']
assert a['sface_counters']['completed']>=b['sface_completed'] and cp.is_file() and not cp.is_symlink()
s.update(phase='CAMERA_STOPPED_CHECKPOINT_PASS',checkpoint_sha256=hashlib.sha256(cp.read_bytes()).hexdigest(),checkpoint_source_pid=pid,zocl_refcnt=0)
(SH/'stage-state.json.tmp').write_text(json.dumps(s,indent=2)+'\n');Path.replace(SH/'stage-state.json.tmp',SH/'stage-state.json')
print(json.dumps({'phase':s['phase'],'checkpoint_sha256':s['checkpoint_sha256'],'source_pid':pid,'pending_results':0,'zocl_refcnt':0}))
