"""Exercise the frozen joint worker on saved public files, without any board IO."""
import hashlib
import importlib.util
from pathlib import Path
import sys

D=Path(__file__).resolve().parent
stage=Path(sys.argv[1]).resolve()
output=Path(sys.argv[2]).resolve()
sys.path.insert(0,r'C:\Users\35870\.codex\scratch\feature_trigger_collaboration\test_dependencies')
manifest=stage/'SOURCE_MANIFEST.json'
args=[str(stage/'arm_public_worker.py'),'--local-replay','--runtime-root',str(stage/'public_runtime_v19'),
    '--candidate-root',str(stage/'after'),'--mapping',str(stage/'source_mapping.v19.json'),
    '--candidate-manifest',str(manifest),'--candidate-manifest-sha256',hashlib.sha256(manifest.read_bytes()).hexdigest(),
    '--original-review',str(stage/'tree/a/b/c/d/review_m03_win_inference/test_delete_boundaries.py'),
    '--independent-tests',str(stage/'test_independent_boundaries.py'),
    '--public-worker',str(stage/'public_worker.py'),'--applied-spec',str(stage/'applied_spec.v19.json'),
    '--identity-tests',str(stage/'identity_tests.py'),'--identity-independent',str(stage/'identity_independent.py'),
    '--speaker-fixtures',str(stage/'speaker_fixtures.py'),'--face-fixtures',str(stage/'face_fixtures.py'),
    '--identity-adapter',str(stage/'identity_stdlib_cases.py'),'--output',str(output)]
spec=importlib.util.spec_from_file_location('local_joint_public_entry',stage/'arm_public_worker.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
sys.argv=args
raise SystemExit(module.entry())
