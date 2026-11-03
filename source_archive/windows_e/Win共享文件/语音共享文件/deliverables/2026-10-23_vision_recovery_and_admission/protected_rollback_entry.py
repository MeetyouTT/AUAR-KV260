"""Old camera code with optional jobs held disabled after an interrupted promotion."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


def launch(argv, *, metadata_path=None):
    metadata_path=Path(metadata_path) if metadata_path is not None else Path(__file__).with_name('rollback-metadata.json')
    meta=json.loads(metadata_path.read_text())
    if Path('/proc/sys/kernel/random/boot_id').read_text().strip()!=meta['boot']:
        raise RuntimeError('Protected rollback belongs to a different boot')
    for name,digest in meta['pins'].items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest()!=digest:
            raise RuntimeError('Protected rollback source changed')
    sys.path.insert(0,str(Path(meta['parent'])/'aura'))
    from board.vision.dpu_vision_schedule import DpuVisionSchedule
    from board.vision.dpu_recovery_policy import YuNetRecoveryPolicy
    spec=importlib.util.spec_from_file_location('_rollback_handoff',meta['handoff_module'])
    handoff=importlib.util.module_from_spec(spec);spec.loader.exec_module(handoff)
    original=DpuVisionSchedule.__init__
    original_health=DpuVisionSchedule.health
    def held_init(self,*args,**kwargs):
        original(self,*args,**kwargs)
        self.sface_recovery=YuNetRecoveryPolicy()
        handoff.restore_protection(self,meta['seed'],boot_id=meta['boot'])
        self.yunet_recovery.phase='LATCHED';self.yunet_recovery.reason='protected_old_code_rollback'
        self.sface_recovery.phase='LATCHED';self.sface_recovery.reason='protected_old_code_rollback'
        self.jobs['yunet']['disabled']=self.jobs['sface']['disabled']=True
    def held_health(self):
        value=original_health(self)
        value['protection_handoff']=dict(self.protection_handoff)
        value['sface_recovery']=self.sface_recovery.snapshot()
        value['rollback_holds_both_optional_tasks']=True
        return value
    DpuVisionSchedule.__init__=held_init
    DpuVisionSchedule.health=held_health
    spec=importlib.util.spec_from_file_location('_old_runtime_entry',Path(meta['parent'])/'runtime_entry.py')
    runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)
    return runtime.launch(argv,root=Path(meta['parent']))


if __name__=='__main__':launch(sys.argv[1:])
