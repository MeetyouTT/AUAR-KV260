"""Local staging verification only, no board connection or live UI access."""
import hashlib
import importlib.util
from pathlib import Path
import sys
H=Path(__file__).resolve().parent;D=H/'candidate_m03_v90_stage'
sys.path.insert(0,r'C:\Users\35870\.codex\scratch\feature_trigger_collaboration\test_dependencies')
m=D/'SOURCE_MANIFEST.json'
args=[str(D/'arm_public_worker.py'),'--local-replay','--runtime-root',str(D/'public_runtime_v90'),
    '--candidate-root',str(D/'after'),'--mapping',str(D/'source_mapping.v90.json'),
    '--candidate-manifest',str(m),'--candidate-manifest-sha256',hashlib.sha256(m.read_bytes()).hexdigest(),
    '--original-review',str(H/'review_m03_win_inference/test_delete_boundaries.py'),
    '--independent-tests',str(H/'review_m03_r2_root_agent/test_independent_boundaries.py'),
    '--public-worker',str(H/'board_integration_v17/worker.py'),'--output',sys.argv[1]]
spec=importlib.util.spec_from_file_location('local_v90_entry',D/'arm_public_worker.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);sys.argv=args
raise SystemExit(module.main())
