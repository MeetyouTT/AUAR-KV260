"""Old-code rollback after an exact, completed native checkpoint only.

Both optional tasks remain disabled. Current counters and prior boot history
remain visible; this entry is never a recovery-budget reset or unlock action.
"""
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys

root=Path(__file__).resolve().parent
meta=json.loads((root/'meta.json').read_text())
pin=json.loads((root/'rollback-pin.json').read_text())
raw=Path(pin['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==pin['sha256']
document=json.loads(raw);seed=document['seed'];aux=document['auxiliary']
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert document['schema']=='aura-native-protection-checkpoint-2' and seed['boot_id']==boot
assert seed['purpose']=='final_quiescent_business_checkpoint' and seed['checkpoint_kind']==1
assert not seed['fenced'] and not aux['fenced'] and not aux['active'] and not aux['primary_waiting']
assert not any(aux['pending_result_tokens'])
pid=seed['source_pid'];stat=Path('/proc')/str(pid)/'stat'
if stat.exists():assert int(stat.read_text().rsplit(')',1)[1].split()[19])!=seed['source_birth_ticks']
original=Path(meta['legacy_root'])
sys.path.insert(0,str(original/'aura'))
from board.vision.dpu_vision_schedule import DpuVisionSchedule
initialize=DpuVisionSchedule.__init__
def protected(self,*args,**kwargs):
    initialize(self,*args,**kwargs)
    assert self.yunet_recovery is not None and self.sface_recovery is not None
    self.primary_calls=seed['primary_calls'];self.primary_overruns=seed['primary_period_overruns']
    self.inherited_sface_counters=dict(aux['sface_counters'])
    for task,kind in ((1,'yunet'),(2,'sface')):
        policy=self.yunet_recovery if task==1 else self.sface_recovery
        source=seed['recovery'][task-1]
        policy.phase='LATCHED';policy.reason='protected_native_trial_rollback'
        for name in ('faults','attempts','recoveries','probe_successes'):
            setattr(policy,name,source[name])
        self.jobs[kind]=dict(calls=seed['admissions'][task],skipped=0,
            overruns=seed['overruns'][task],budget_exceeded=0,estimated_budget_ms=30.,
            maximum_ms=0.,disabled=True)
    self.protection_handoff=dict(mode='completed_native_trial_protected_old_code',
        native_checkpoint_sha256=pin['sha256'],source_pid=pid,
        native_snapshot=seed,previous_kernel_history=document.get('previous_kernel_history'),
        counter_scope='Native predecessor counters retained; optional jobs latched. Legacy diagnostic timings start fresh.')
DpuVisionSchedule.__init__=protected
config=json.loads((original/'board_camera_ui.json').read_text())
config.pop('dpu_protection_seed',None);config.pop('dpu_protection_allow_new_boot',None)
config_path=root/('rollback-config-'+boot+'-'+str(os.getpid())+'.json')
with config_path.open('x') as out:json.dump(config,out,indent=2)
sys.argv=[str(original/'runtime_entry.py'),str(original/'aura/tools/board_camera_motion.py'),
          '--config',str(config_path)]
runpy.run_path(str(original/'runtime_entry.py'),run_name='__main__')
