"""Prove the unchanged old worker refuses the new mapping before app import."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace as NS
H=Path(__file__).resolve().parent;D=H/'candidate_m03_v90_stage'
path=H/'candidate_m03_newboot/arm_public_worker.py'
assert hashlib.sha256(path.read_bytes()).hexdigest()=='16b67f5c93fa4c86f62f64667c58bae395bc353cd5d0f8e7b4f0bf00a3b3eb77'
spec=importlib.util.spec_from_file_location('unchanged_old_binding',path)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
args=NS(mapping=D/'source_mapping.v90.json',output=D/'SHOULD_NOT_BE_CREATED.json')
assert not args.output.exists()
try:module.verify(args)
except ValueError as exc:
    assert str(exc)=='frozen_mapping_changed';code=str(exc)
else:raise AssertionError('Old worker silently accepted v90')
loaded=[n for n in sys.modules if n in ('common','board','tools') or n.startswith(('common.','board.','tools.'))]
assert not loaded and not args.output.exists()
value=dict(status='PASS_STALE_MAPPING_REJECTED_BEFORE_APP_IMPORT',code=code,
    application_modules_loaded=loaded,output_created=False,production_or_hardware_accessed=False)
(D/'STALE_REJECTION.json').write_bytes((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode())
print(json.dumps(value))
