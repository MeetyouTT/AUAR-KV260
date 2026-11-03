"""Reuse pinned normal-closed publisher, extending one explicit config enum."""
import hashlib
import importlib.util
from pathlib import Path

HERE=Path(__file__).resolve().parent
path=HERE.parent.parent/'listening_entry_fix/apply_closed_revision.py'
assert hashlib.sha256(path.read_bytes()).hexdigest()=='74bd266353d58f7edd8728ef0dd1ae1ab613eb8386884bba32940018b510bfe2'
spec=importlib.util.spec_from_file_location('_reviewed_closed_publisher',path)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
old="assert set(REVISION['business_options'])<=set(('frontend_process','frontend_capture_process','frontend_optimization','capture_priority_nice','frontend_threads','asr_threads'))"
new="assert set(REVISION['business_options'])<=set(('frontend_process','frontend_capture_process','frontend_optimization','capture_priority_nice','frontend_threads','asr_threads','dialogue_output_format'))\nassert REVISION['business_options'].get('dialogue_output_format','json') in ('json','dialogue_abc_v1')"
assert module.REMOTE.count(old)==1
module.REMOTE=module.REMOTE.replace(old,new)

if __name__=='__main__': module.main()
