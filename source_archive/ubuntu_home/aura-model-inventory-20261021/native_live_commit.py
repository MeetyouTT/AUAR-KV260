import json,subprocess,sys,time
from pathlib import Path
root=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735');sys.path.insert(0,str(root))
from boot_ops import Ops
from policy import require_native_healthy
ops=Ops(root);ops.verify();state=ops.state();assert state['phase']=='NATIVE_READY'
w=state['last_window'];assert w['seconds']>=180 and w['short_window_passed'] and w['new_sface_completions']>=1
h=ops.health();require_native_healthy(h);assert h['pid']==2174
assert all(h['dpu_schedule']['optional'][k]['overruns']==0 for k in ['yunet','sface'])
ops.phase('ACCEPTED',accepted_scope='REAL_THREE_MODEL_SHORT_BUSINESS_WINDOW_OUTPUT_EQUIVALENCE; LONG_STABILITY_AND_ACCURACY_PENDING',
 accepted_camera_pid=h['pid'],accepted_mono_ns=time.monotonic_ns(),
 accepted_sface_completed=h['identity']['feature_inference']['completed'])
ops.command(['systemctl','disable','--now',ops.paths()['rescue_timer'].name])
# Reset only completed/failed task-controller units, preserving journal history.
for unit in ['aura-native-activate-be72669aa53de735.service','aura-native-activate-r3-be72669aa53de735.service','aura-native-observe60-be72669aa53de735.service']:
 if subprocess.check_output(['systemctl','show',unit,'-p','ActiveState','--value'],text=True).strip()=='failed':
  ops.command(['systemctl','reset-failed',unit])
print(json.dumps({'retained':True,'scope':'short real business acceptance; not long-tail cure or accuracy certification',
 'state':ops.state(),'camera_pid':h['pid'],'sface_completed':h['identity']['feature_inference']['completed'],
 'rescue_timer_disabled':True,'rollback_entry':str(root/'rollback_entry.py')}))
