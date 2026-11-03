import json,subprocess,sys,time
from pathlib import Path
root=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735');sys.path.insert(0,str(root))
from boot_ops import Ops
ops=Ops(root);ops.verify();assert ops.state()['phase']=='NATIVE_START_HOLD'
h=ops.health();assert h['pid']==1747 and not h['dpu_schedule']['owner_fenced']
assert ops.props('aura-avatar-ui.service')['MainPID']=='0'
ops.phase('PAUSED_FOR_REPAIR',startup_metrics_failure_preserved=True)
ops.command(['systemctl','stop','--no-block','aura-camera-ui.service'])
until=time.monotonic()+18
while time.monotonic()<until and ops.props('aura-camera-ui.service')['MainPID']!='0':time.sleep(.2)
props=ops.props('aura-camera-ui.service');assert props['MainPID']=='0' and props['Result']=='success' and props['ExecMainStatus']=='0',props
checkpoint=Path(json.loads(Path(ops.meta['candidate_config']).read_text())['native_execution']['checkpoint_output'])
doc=json.loads(checkpoint.read_text());assert doc['seed']['source_pid']==1747 and not doc['seed']['fenced']
assert doc['scope']=='final_quiescent_before_native_owner_close' and not any(doc['auxiliary']['pending_result_tokens'])
ops.phase('PAUSED_FOR_REPAIR',repair_checkpoint=str(checkpoint),repair_checkpoint_sha256=__import__('hashlib').sha256(checkpoint.read_bytes()).hexdigest())
print(json.dumps({'native_shutdown_confirmed':True,'checkpoint_path':str(checkpoint),'checkpoint':doc,'unit':props,'no_restart_or_new_owner':True}))
